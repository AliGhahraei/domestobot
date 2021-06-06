#!/usr/bin/env python3
from abc import abstractmethod
from enum import Enum, auto
from os import getenv
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Callable, Dict, List, Optional, Protocol, Union

from tomlkit import parse
from typer import Context, Option, Typer
from typic import transmute
from xdg import xdg_config_home

from domestobot import builtin_steps
from domestobot.config import Config
from domestobot.core import CommandRunner
from domestobot.steps import get_steps

CONFIG_PATH = xdg_config_home() / 'domestobot' / 'config.toml'
DRY_RUN_HELP = 'Print commands for every step instead of running them'


def main() -> None:
    get_app()()


def get_app(app_object: Optional['AppObject'] = None) -> Typer:
    app_object_ = app_object or DomestobotObject()
    app = Typer()
    steps = app_object_.get_steps()

    for step in steps:
        app.command()(step)

    dry_run_option = Option(False, help=DRY_RUN_HELP, show_default=False)

    @app.callback(invoke_without_command=True)
    def main(ctx: Context, dry_run: bool = dry_run_option) -> None:
        """Your own trusty housekeeper.

        Run without specifying a command to run all subroutines.
        Run --help and the name of a command to get more information about it
        (e.g. `domestobot upgrade-doom --help`).
        """
        if dry_run:
            app_object_.mode = Mode.DRY_RUN

        if ctx.invoked_subcommand is None:
            for step in steps:
                step()

    return app


class Mode(Enum):
    DEFAULT = auto()
    DRY_RUN = auto()


class AppObject(Protocol):
    @property
    @abstractmethod
    def config(self) -> Config:
        pass

    @property
    @abstractmethod
    def mode(self) -> Mode:
        pass

    @mode.setter
    def mode(self, value: Mode) -> None:
        pass

    @abstractmethod
    def get_steps(self) -> List[Callable[..., None]]:
        pass


class ConfigReader:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path(getenv('DOMESTOBOT_CONFIG', CONFIG_PATH))

    def read(self) -> Config:
        try:
            with open(self.path) as f:
                contents = f.read()
        except FileNotFoundError:
            raise SystemExit(f"Config file '{str(self.path)}' not found")
        try:
            return transmute(Config, parse(contents))
        except Exception as e:
            raise SystemExit(f'Error while parsing config file: {e}')


class DefaultCommandRunner(CommandRunner):
    @staticmethod
    def run(*args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        return run(args, check=True, capture_output=capture_output)


class DryRunner(CommandRunner):
    @staticmethod
    def run(*args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        print(args)
        return CompletedProcess(args, 0)


class DomestobotObject(AppObject, CommandRunner):
    _runners: Dict[Mode, CommandRunner] = {
        Mode.DEFAULT: DefaultCommandRunner(),
        Mode.DRY_RUN: DryRunner(),
    }

    def __init__(self, config: Optional[Config] = None):
        self._config = config or ConfigReader().read()
        self._mode = Mode.DEFAULT

    @property
    def config(self) -> Config:
        return self._config

    @property
    def mode(self) -> Mode:
        return self._mode

    @mode.setter
    def mode(self, value: Mode) -> None:
        self._mode = value

    def get_steps(self) -> List[Callable[..., None]]:
        return get_steps(self.config, self, builtin_steps)

    def run(self, *args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        return self._runners[self.mode].run(*args,
                                            capture_output=capture_output)
