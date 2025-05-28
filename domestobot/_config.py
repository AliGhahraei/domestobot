#!/usr/bin/env python3
from dataclasses import field
from operator import xor

from pydantic import FilePath
from pydantic.dataclasses import dataclass

HELP = """Your own trusty housekeeper.

Run `domestobot <step_name> --help` to get more information about that
particular step.
"""


@dataclass
class CommandStep:
    title: str | None = None
    command: list[str] = field(default_factory=list)
    commands: list[list[str]] = field(default_factory=list)
    shell_command: str | None = None
    shell_commands: list[str] = field(default_factory=list)


@dataclass
class _EnvStepRequired:
    os: str


def _command_field_count(step: "CommandStep") -> int:
    return [
        bool(command_field)
        for command_field in (
            step.command,
            step.commands,
            step.shell_command,
            step.shell_commands,
        )
    ].count(True)


@dataclass
class EnvStep(CommandStep, _EnvStepRequired):
    def __post_init__(self) -> None:
        if _command_field_count(self) != 1:
            raise TypeError(
                "Exactly 1 of `command`, `commands`, `shell_command`, or `shell_commands` "
                "must be specified and non-empty"
            )


@dataclass
class _ShellStepRequired:
    name: str
    doc: str


@dataclass
class ShellStep(CommandStep, _ShellStepRequired):
    envs: list["EnvStep"] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not (xor(_command_field_count(self) == 1, bool(self.envs))):
            raise TypeError(
                "Exactly 1 of `command`, `commands`, `shell_command`, `shell_commands`, or `envs` must"
                " be specified and non-empty"
            )


@dataclass
class Config:
    default_subcommands: list[str] = field(default_factory=list)
    steps: list["ShellStep"] = field(default_factory=list)
    help_message: str = HELP
    sub_domestobots: list[FilePath] = field(default_factory=list)
