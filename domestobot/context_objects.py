from abc import abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from itertools import chain
from operator import xor
from pathlib import Path
from platform import system
from subprocess import CompletedProcess, run
from typing import (Any, Callable, Iterable, List, Literal, Optional, Protocol,
                    Union, cast)

from tomlkit import parse
from typic import transmute
from xdg import xdg_config_home

from domestobot import routines
from domestobot.core import CommandRunner, title

CONFIG_PATH = xdg_config_home() / 'domestobot' / 'config.toml'


def get_steps(config: 'Config', runner: CommandRunner, builtin_registry: Any) \
        -> List[Callable[..., None]]:
    return list(chain.from_iterable(
        _get_definitions(step, runner, builtin_registry)
        for step in config.steps
    ))


def _get_definitions(step: 'ShellStep', runner: CommandRunner,
                     builtin_registry: Any) -> List[Callable[..., None]]:
    return _build_wrappers_from_shell_step(step, runner)


def _build_wrappers_from_shell_step(step: 'ShellStep', runner: CommandRunner) \
        -> List[Callable[..., None]]:
    return [_make_command_step_wrapper(runnable, step.name, step.doc, runner)
            for runnable in _get_command_steps(step)]


def _make_command_step_wrapper(step: 'CommandStep', name: str, doc: str,
                               runner: CommandRunner) -> Callable[..., None]:
    def step_wrapper() -> None:
        if step.title:
            title(step.title)

        commands = step.commands if step.commands else [step.command]
        for command in commands:
            runner.run(*command)

    step_wrapper.__name__ = name
    step_wrapper.__doc__ = doc
    return step_wrapper


def _get_command_steps(step: 'ShellStep') -> List['CommandStep']:
    return _get_steps_from_env(step.env) if step.env else [step]


def _get_steps_from_env(steps: Iterable['EnvStep']) -> List['CommandStep']:
    os = system()
    return [step for step in steps if step.os == os]


@dataclass
class Config:
    steps: List['ShellStep'] = field(default_factory=list)


@dataclass
class CommandStep:
    title: Optional[str] = None
    command: List[str] = field(default_factory=list)
    commands: List[List[str]] = field(default_factory=list)


def _has_command_or_commands(step: 'CommandStep') -> bool:
    return cast(bool, xor(bool(step.command), bool(step.commands)))


@dataclass
class _ShellStepRequired:
    name: str
    doc: str


@dataclass
class ShellStep(CommandStep, _ShellStepRequired):
    env: List['EnvStep'] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not(xor(_has_command_or_commands(self), bool(self.env))):
            raise TypeError('Exactly 1 of `command`, `commands` or `env` must'
                            ' be specified and non-empty')


@dataclass
class _EnvStepRequired:
    os: str


@dataclass
class EnvStep(CommandStep, _EnvStepRequired):
    def __post_init__(self) -> None:
        if not(_has_command_or_commands(self)):
            raise TypeError('Exactly 1 of `command` or `commands` must be '
                            'specified and non-empty')


@dataclass
class FunctionStep:
    name: str
    default_args: List[Any] = field(default_factory=list)
    kind: Literal['function'] = 'function'


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
        return get_steps(self.config, self, routines)

    @staticmethod
    def run(*args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        return run(args, check=True, capture_output=capture_output)
