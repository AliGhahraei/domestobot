#!/usr/bin/env python3
from dataclasses import field
from operator import xor
from typing import List, Optional, cast

from pydantic import FilePath
from pydantic.dataclasses import dataclass

HELP = """Your own trusty housekeeper.

Run `domestobot <step_name> --help` to get more information about that
particular step.
"""


@dataclass
class CommandStep:
    title: Optional[str] = None
    command: List[str] = field(default_factory=list)
    commands: List[List[str]] = field(default_factory=list)


@dataclass
class _EnvStepRequired:
    os: str


def _has_command_or_commands(step: 'CommandStep') -> bool:
    return cast(bool, xor(bool(step.command), bool(step.commands)))


@dataclass
class EnvStep(CommandStep, _EnvStepRequired):
    def __post_init__(self) -> None:
        if not(_has_command_or_commands(self)):
            raise TypeError('Exactly 1 of `command` or `commands` must be '
                            'specified and non-empty')


@dataclass
class _ShellStepRequired:
    name: str
    doc: str


@dataclass
class ShellStep(CommandStep, _ShellStepRequired):
    envs: List['EnvStep'] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not(xor(_has_command_or_commands(self), bool(self.envs))):
            raise TypeError('Exactly 1 of `command`, `commands` or `envs` must'
                            ' be specified and non-empty')


@dataclass
class Config:
    default_subcommands: List[str] = field(default_factory=list)
    steps: List['ShellStep'] = field(default_factory=list)
    help_message: str = HELP
    sub_domestobots: List[FilePath] = field(default_factory=list)
