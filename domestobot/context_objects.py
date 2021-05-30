from abc import abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any, List, Protocol, Union, cast

from tomlkit import parse
from typic import transmute
from xdg import xdg_config_home

from domestobot import routines
from domestobot.routines import CommandRunner

CONFIG_PATH = xdg_config_home() / 'domestobot' / 'config.toml'


@dataclass
class Config:
    repos: List[Path] = field(default_factory=list)


class ConfigReader(Protocol):
    @property
    @abstractmethod
    def config(self) -> Config:
        pass


class ContextObject(CommandRunner, ConfigReader, Protocol):
    def __getattr__(self, item: str) -> 'Routine':
        """Not abstract due to https://github.com/python/mypy/issues/10409."""


class AppObject(ContextObject):
    def __init__(self, config_path: Path = CONFIG_PATH):
        self._config_path = config_path

    # https://github.com/python/mypy/issues/8913
    @cached_property
    def config(self) -> Config:  # type: ignore
        try:
            with open(self._config_path) as f:
                contents = f.read()
        except FileNotFoundError:
            return Config()

        try:
            return transmute(Config, parse(contents))
        except Exception as e:
            raise SystemExit(f'Error while parsing config file: {e}')

    @staticmethod
    def run(*args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        return run(args, check=True, capture_output=capture_output)

    def __getattr__(self, item: str) -> 'Routine':
        return cast(Routine, getattr(routines, item))


class Routine(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        pass
