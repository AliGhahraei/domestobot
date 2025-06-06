#!/usr/bin/env python3
import sys
from dataclasses import dataclass
from functools import partial
from logging import FileHandler, getLogger
from os import getenv
from pathlib import Path
from typing import Annotated, Any, Callable, Iterable, List, Mapping, Optional, Union

from pydantic import TypeAdapter, ValidationError
from tomlkit import parse
from tomlkit.exceptions import TOMLKitError
from typer import Context, Typer
from typer.models import CommandInfo, TyperInfo
from xdg import xdg_cache_home, xdg_config_home

from domestobot._config import Config
from domestobot._core import (
    DomestobotError,
    RunnerCommand,
    RunnerGroup,
    dry_run_option,
    set_obj_to_running_mode_if_unset,
    warning,
)
from domestobot._steps import get_steps

CONFIG_ROOT = xdg_config_home() / "domestobot"
LOG_PATH = xdg_cache_home() / "domestobot" / "log"

NamesToCallbacks = Mapping[str, Callable[..., Any]]


logger = getLogger(__name__)


def main(config_path: Optional[Path] = None) -> None:
    set_logger_handler()
    get_main_app(config_path)()


def set_logger_handler() -> None:
    if filename := getenv("DOMESTOBOT_LOG", LOG_PATH):
        path = Path(filename)
        path.parent.mkdir(exist_ok=True)
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])
        logger.addHandler(FileHandler(filename=path))


def get_main_app(config_path: Optional[Path]) -> Typer:
    try:
        app = get_app(get_path_or_default(config_path))
    except ConfigNotFoundError as e:
        warning(str(e))
        app = get_app_from_config(Config())
    except (ValidationError, DomestobotError) as e:
        sys.exit(str(e))
    except Exception as e:
        logger.exception("")
        sys.exit(f'Unhandled error, please report it to the maintainer: "{e}"')

    return app


def get_app(config_path: Path) -> Typer:
    """Build a Typer app using config_path as its specification."""
    current_config = read_config(config_path)
    current_name = config_path.stem
    current_app = get_app_from_config(current_config, current_name)
    for sub_domestobot_path in current_config.sub_domestobots:
        sub_app = get_app(sub_domestobot_path)
        current_app.add_typer(sub_app, name=current_name)
    return current_app


def get_app_from_config(config: Config, name: str = "root") -> Typer:
    commands = get_steps(config.steps)
    params = AppParams(name, config.help_message, commands, config.default_subcommands)
    return make_app(params)


def read_config(path: Path) -> Config:
    try:
        with open(path) as f:
            contents = f.read()
    except FileNotFoundError as e:
        raise ConfigNotFoundError(path) from e

    try:
        user_config = parse(contents)
    except TOMLKitError as e:
        raise ConfigError(f"Error while parsing config file {path}: {e}") from e
    adapter = TypeAdapter(Config)
    return adapter.validate_python(user_config)


class ConfigError(DomestobotError):
    pass


class ConfigNotFoundError(ConfigError):
    def __init__(self, path: Path):
        super().__init__(f"Config file {path} not found")


def make_app(
    app_params: "AppParams",
) -> Typer:
    app = Typer()

    @app.callback(cls=RunnerGroup, invoke_without_command=True)
    def main(ctx: Context, dry_run: Annotated[bool, dry_run_option] = False) -> None:
        set_obj_to_running_mode_if_unset(ctx, dry_run=dry_run)
        if ctx.invoked_subcommand is None:
            if app_params.default_subcommands:
                callbacks = _get_groups_and_commands_callbacks(app)
                _run_subcommands(callbacks, ctx, app_params.default_subcommands)
            else:
                print(ctx.get_help())

    main.__name__ = app_params.callback_name
    main.__doc__ = app_params.callback_help

    for command in app_params.commands:
        app.command(cls=RunnerCommand)(command)
    return app


def _get_groups_and_commands_callbacks(
    app: Typer, *sub_groups_args: Any
) -> NamesToCallbacks:
    """Get registered callbacks partially applying sub_groups_args to groups.

    Maybe Typer provides some API to do this automatically, but probably not
    because Click discourages calling commands from other commands:
    https://click.palletsprojects.com/en/6.x/advanced/#invoking-other-commands
    """
    return {
        **get_groups_callbacks(app, *sub_groups_args),
        **get_commands_callbacks(app),
    }


def get_groups_callbacks(app: Typer, *args: Any) -> NamesToCallbacks:
    """Get names from app.registered_groups mapped to their callback.

    Search through every typer_instance from registered_groups, get their
    registered callbacks and partially apply `args` to them.
    """
    sub_instances = (
        instance
        for group in app.registered_groups
        if (instance := group.typer_instance)
    )
    sub_typer_infos = (
        typer_info
        for instance in sub_instances
        if (typer_info := instance.registered_callback)
    )
    return _get_names_to_callbacks(sub_typer_infos, *args)


def get_commands_callbacks(app: Typer, *args: Any) -> NamesToCallbacks:
    """Get every name from app.registered_commands mapped to its callback.

    Get callbacks from registered_commands and partially apply `args` to them.
    """
    return _get_names_to_callbacks(app.registered_commands, *args)


def _get_names_to_callbacks(
    iterable: Iterable[Union[TyperInfo, CommandInfo]], *args: Any
) -> NamesToCallbacks:
    return {
        callback.__name__: partial(callback, *args)
        for item in iterable
        if (callback := item.callback)
    }


def _run_subcommands(
    callbacks: NamesToCallbacks, ctx: Context, subcommands: List[str]
) -> None:
    found_callbacks = [
        _search_callbacks(subcommand, callbacks) for subcommand in subcommands
    ]
    for callback in found_callbacks:
        callback(ctx)


def _search_callbacks(name: str, callbacks: NamesToCallbacks) -> Callable[..., Any]:
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


def get_path_or_default(path: Optional[Path]) -> Path:
    return path or get_root_path()


def get_root_dir() -> Path:
    """Get envvar `DOMESTOBOT_ROOT` or default path."""
    return Path(getenv("DOMESTOBOT_ROOT", CONFIG_ROOT))


def get_root_path() -> Path:
    """Get configured root config file path."""
    return get_root_dir() / "root.toml"
