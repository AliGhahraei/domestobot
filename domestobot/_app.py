#!/usr/bin/env python3
import sys
from dataclasses import dataclass
from enum import Enum, auto
from functools import partial
from logging import FileHandler, getLogger
from os import getenv
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any, Callable, List, Mapping, Optional, Union

from pydantic import ValidationError, parse_obj_as
from tomlkit import parse
from tomlkit.exceptions import TOMLKitError
from typer import Context, Option, Typer
from xdg import xdg_cache_home, xdg_config_home

from domestobot._config import Config
from domestobot._core import CommandRunner, DomestobotError, warning
from domestobot._steps import get_steps

CONFIG_PATH = xdg_config_home() / 'domestobot' / 'root.toml'
LOG_PATH = xdg_cache_home() / 'domestobot' / 'log'
DRY_RUN_HELP = 'Print commands for every step instead of running them'


logger = getLogger(__name__)


class Mode(Enum):
    DEFAULT = auto()
    DRY_RUN = auto()


def main(config_path: Optional[Path] = None) -> None:
    set_logger_handler()
    get_main_app(config_path)()


def set_logger_handler() -> None:
    if filename := getenv('DOMESTOBOT_LOG', LOG_PATH):
        path = Path(filename)
        path.parent.mkdir(exist_ok=True)
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])
        logger.addHandler(FileHandler(filename=path))


def get_main_app(config_path: Optional[Path]) -> Typer:
    try:
        app = get_app(get_root_path(config_path))
    except ConfigNotFoundError as e:
        warning(str(e), end='\n\n')
        app = get_app_from_config(Config())
    except (ValidationError, DomestobotError) as e:
        sys.exit(str(e))
    except Exception as e:
        logger.exception('')
        sys.exit(f'Unhandled error, please report it to the maintainer: "{e}"')

    return app


def get_app(config_path: Path) -> Typer:
    current_config = read_config(config_path)
    current_name = config_path.stem
    current_app = get_app_from_config(current_config, current_name)
    for sub_domestobot_path in current_config.sub_domestobots:
        sub_app = get_app(sub_domestobot_path)
        current_app.add_typer(sub_app)
    return current_app


def get_app_from_config(config: Config, name: str = 'root') -> Typer:
    runner_selector = RunnerSelector()
    commands = get_steps(config.steps, runner_selector.dynamic_mode_runner)
    params = AppParams(name,
                       config.help_message,
                       commands,
                       config.default_subcommands)
    return make_app(params, runner_selector.switch_mode)


def read_config(path: Path) -> Config:
    try:
        with open(path) as f:
            contents = f.read()
    except FileNotFoundError as e:
        raise ConfigNotFoundError(path) from e

    try:
        user_config = parse(contents)
    except TOMLKitError as e:
        raise ConfigError(f'Error while parsing config file {path}: {e}') \
            from e
    return parse_obj_as(Config, user_config)


class ConfigError(DomestobotError):
    pass


class ConfigNotFoundError(ConfigError):
    def __init__(self, path: Path):
        super().__init__(f'Config file {path} not found')


class RunnerSelector:
    def __init__(self) -> None:
        self._mode = Mode.DEFAULT
        self._modes = {
            Mode.DEFAULT: default_run,
            Mode.DRY_RUN: dry_run,
        }

    @property
    def dynamic_mode_runner(self) -> CommandRunner:
        class Runner:
            @staticmethod
            def run(*args: Union[str, Path], capture_output: bool = False) \
                    -> CompletedProcess[bytes]:
                return self._modes[self._mode](*args,
                                               capture_output=capture_output)

        return Runner()

    def switch_mode(self, mode: Mode) -> None:
        self._mode = mode


def default_run(*args: Union[str, Path], capture_output: bool = False) \
        -> CompletedProcess[bytes]:
    return run(args, check=True, capture_output=capture_output)


def dry_run(*args: Union[str, Path], capture_output: bool = False) \
        -> CompletedProcess[bytes]:
    print(args)
    return CompletedProcess(args, 0)


def make_app(app_params: 'AppParams', select_mode: Callable[[Mode], Any]) \
        -> Typer:
    app = Typer()
    dry_run_option = Option(False, help=DRY_RUN_HELP, show_default=False)

    @app.callback(invoke_without_command=True)
    def main(ctx: Context, dry_run: bool = dry_run_option) -> None:
        if dry_run:
            select_mode(Mode.DRY_RUN)

        if ctx.invoked_subcommand is None:
            nonlocal app
            if app_params.default_subcommands:
                callbacks = _get_callbacks(app, ctx, dry_run)
                _run_subcommands(callbacks, app_params.default_subcommands)
            else:
                print(ctx.get_help())

    main.__name__ = app_params.callback_name
    main.__doc__ = app_params.callback_help

    for command in app_params.commands:
        app.command()(command)
    return app


def _get_callbacks(app: Typer, *args: Any) -> Mapping[str, Callable[[], Any]]:
    """Get all the possible callbacks that a user could invoke.

    Maybe Typer provides some API to do this automatically, but probably not
    because Click discourages calling commands from other commands:
    https://click.palletsprojects.com/en/6.x/advanced/#invoking-other-commands
    """
    sub_instances = (instance for group in app.registered_groups
                     if (instance := group.typer_instance))
    sub_typer_infos = (typer_info for instance in sub_instances
                       if (typer_info := instance.registered_callback))

    sub_callbacks = {sub_callback.__name__: partial(sub_callback, *args)
                     for typer_info in sub_typer_infos
                     if (sub_callback := typer_info.callback)}
    app_callbacks = {callback.__name__: callback
                     for command in app.registered_commands
                     if (callback := command.callback)}
    return sub_callbacks | app_callbacks  # type: ignore[operator]


def _run_subcommands(callbacks: Mapping[str, Callable[[], Any]],
                     subcommands: List[str]) -> None:
    found_callbacks = [_search_callbacks(subcommand, callbacks)
                       for subcommand in subcommands]
    for callback in found_callbacks:
        callback()


def _search_callbacks(name: str, callbacks: Mapping[str, Callable[[], Any]]) \
        -> Callable[[], Any]:
    try:
        callback = callbacks[name]
    except KeyError as e:
        raise ConfigError(f"{e} is not a valid step") from e
    return callback


@dataclass
class AppParams:
    callback_name: str
    callback_help: str
    commands: List[Callable[..., Any]]
    default_subcommands: List[str]


def get_root_path(path: Optional[Path]) -> Path:
    return path or Path(getenv('DOMESTOBOT_ROOT_CONFIG', CONFIG_PATH))
