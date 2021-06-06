#!/usr/bin/env python3
from dataclasses import dataclass, field
from operator import xor
from typing import Any, List, Literal, Optional, cast


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