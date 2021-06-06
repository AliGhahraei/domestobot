#!/usr/bin/env python3
from abc import abstractmethod
from functools import cached_property
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Callable, List, Protocol, Union

from tomlkit import parse
from typer import Context, Typer
from typic import transmute
from xdg import xdg_config_home

from domestobot import builtin_steps
from domestobot.config import Config
from domestobot.core import CommandRunner
from domestobot.steps import get_steps

CONFIG_PATH = xdg_config_home() / 'domestobot' / 'config.toml'


def main() -> None:
    get_app(AppObject())()


def get_app(context_object: 'ContextObject') -> Typer:
    app = Typer()
    steps = context_object.get_steps()

    for step in steps:
        app.command()(step)

    @app.callback(invoke_without_command=True)
    def main(ctx: Context) -> None:
        """Your own trusty housekeeper.

        Run without specifying a command to run all subroutines.
        Run --help and the name of a command to get more information about it
        (e.g. `domestobot upgrade-doom --help`).
        """
        if ctx.invoked_subcommand is None:
            for step in steps:
                step()

    return app


class ConfigReader(Protocol):
    @property
    @abstractmethod
    def config(self) -> Config:
        pass


class StepsGetter(Protocol):
    @abstractmethod
    def get_steps(self) -> List[Callable[..., None]]:
        pass


class ContextObject(CommandRunner, ConfigReader, StepsGetter, Protocol):
    pass


class AppObject(ContextObject):
    def __init__(self, config_path: Path = CONFIG_PATH):
        self._config_path = config_path

    # type ignored because of https://github.com/python/mypy/issues/8913
    @cached_property
    def config(self) -> Config:  # type: ignore[override]
        try:
            with open(self._config_path) as f:
                contents = f.read()
        except FileNotFoundError:
            return Config()

        try:
            return transmute(Config, parse(contents))
        except Exception as e:
            raise SystemExit(f'Error while parsing config file: {e}')

    def get_steps(self) -> List[Callable[..., None]]:
        return get_steps(self.config, self, builtin_steps)

    @staticmethod
    def run(*args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        return run(args, check=True, capture_output=capture_output)
