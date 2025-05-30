#!/usr/bin/env python3
import sys
from abc import abstractmethod
from enum import Enum, auto
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Protocol, Union

from typer import Option, style

DRY_RUN_HELP = "Print commands for every step instead of running them"
dry_run_option = Option(help=DRY_RUN_HELP, show_default=False)


class RunningMode(Enum):
    DEFAULT = auto()
    DRY_RUN = auto()


def title(message: str) -> None:
    dotted_message = f"\n{message}..."
    print(style(dotted_message, "magenta", bold=True))


def warning(message: str, **kwargs: Any) -> None:
    print(style(message, "yellow"), **kwargs, file=sys.stderr)


class CommandRunner(Protocol):
    @abstractmethod
    def run(
        self, *args: Union[str, Path], capture_output: bool = False, shell: bool = False
    ) -> CompletedProcess[bytes]:
        pass


class DomestobotError(Exception):
    pass
