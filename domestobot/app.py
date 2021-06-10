#!/usr/bin/env python3
from dataclasses import dataclass
from enum import Enum, auto
from os import getenv
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any, Callable, List, Optional, Union

from tomlkit import parse
from typer import Context, Option, Typer
from typic import transmute
from xdg import xdg_config_home

from domestobot.config import Config
from domestobot.core import CommandRunner
from domestobot.steps import get_steps

CONFIG_PATH = xdg_config_home() / 'domestobot' / 'config.toml'
DRY_RUN_HELP = 'Print commands for every step instead of running them'


class Mode(Enum):
    DEFAULT = auto()
    DRY_RUN = auto()


def main() -> None:
    get_app()()


def get_app(config_path: Optional[Path] = None) -> Typer:
    return get_app_from_config(ConfigReader(config_path).read())


def get_app_from_config(config: Config) -> Typer:
    runner_selector = RunnerSelector()
    commands = get_steps(config.steps, runner_selector.dynamic_mode_runner)
    return make_app(AppParams(commands, config.default_subcommands),
                    runner_selector.switch_mode)


class ConfigReader:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path(getenv('DOMESTOBOT_CONFIG', CONFIG_PATH))

    def read(self) -> Config:
        try:
            with open(self.path) as f:
                contents = f.read()
        except FileNotFoundError as e:
            raise SystemExit(f"Config file '{str(self.path)}' "
                             "not found") from e
        try:
            return transmute(Config, parse(contents))
        except Exception as e:
            raise SystemExit(f'Error while parsing config file: {e}') from e


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
        """Your own trusty housekeeper.

        Run `domestobot <step_name> --help` to get more information about that
        particular step.
        """
        if dry_run:
            select_mode(Mode.DRY_RUN)

        if ctx.invoked_subcommand is None:
            nonlocal app
            if app_params.default_subcommands:
                run_subcommands(app, app_params.default_subcommands)
            else:
                print(ctx.get_help())

    for command in app_params.commands:
        app.command()(command)
    return app


def run_subcommands(app: Typer, subcommands: List[str]) -> None:
    callbacks = {callback.__name__: callback
                 for command in app.registered_commands
                 if (callback := command.callback)}

    try:
        subcommand_callables = [callbacks[name] for name in subcommands]
    except KeyError as e:
        raise SystemExit(f"{e} is not a valid step")
    for subcommand in subcommand_callables:
        subcommand()


@dataclass
class AppParams:
    commands: List[Callable[..., Any]]
    default_subcommands: List[str]
