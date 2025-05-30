#!/usr/bin/env python3
import sys
from enum import Enum, auto
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Protocol

from typer import Option, style

DRY_RUN_HELP = "Print commands for every step instead of running them"
dry_run_option = Option(help=DRY_RUN_HELP, show_default=False)


class RunningMode(Enum):
    DEFAULT = auto()
    DRY_RUN = auto()


class CmdRunner(Protocol):
    def run(
        self, *args: str | Path, capture_output: bool = False, shell: bool = False
    ) -> CompletedProcess[bytes]: ...


def title(message: str) -> None:
    dotted_message = f"\n{message}..."
    print(style(dotted_message, "magenta", bold=True))


def warning(message: str, **kwargs: Any) -> None:
    print(style(message, "yellow"), **kwargs, file=sys.stderr)


class DomestobotError(Exception):
    pass
