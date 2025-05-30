#!/usr/bin/env python3
from enum import Enum, auto
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Protocol

from rich.console import Console
from typer import Option

console = Console()
err_console = Console(stderr=True)


DRY_RUN_HELP = "Print commands for every step instead of running them"
dry_run_option = Option(help=DRY_RUN_HELP, show_default=False)


class RunningMode(Enum):
    DEFAULT = auto()
    DRY_RUN = auto()


class CmdRunner(Protocol):
    def __call__(
        self, *args: str | Path, capture_output: bool = False, shell: bool = False
    ) -> CompletedProcess[bytes]: ...


def title(message: str) -> None:
    dotted_message = f"\n{message}..."
    console.print(dotted_message, style="bold magenta")


def warning(message: str, **kwargs: Any) -> None:
    err_console.print(message, style="yellow", **kwargs)


class DomestobotError(Exception):
    pass
