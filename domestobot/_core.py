#!/usr/bin/env python3
import subprocess
from enum import Enum, auto
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, Protocol, override

from rich.console import Console
from typer import Context, Exit, Option

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


def error(message: str) -> None:
    err_console.print(message, style="red")


class CmdRunnerContext(Context, CmdRunner):
    mode: RunningMode = RunningMode.DEFAULT
    dry_runner: CmdRunner
    default_runner: CmdRunner

    def __init__(
        self,
        *args: Any,
        dry_runner: CmdRunner | None = None,
        default_runner: CmdRunner | None = None,
        **kwargs: Any,
    ) -> None:
        self.dry_runner = dry_runner or DryRunner()
        self.default_runner = default_runner or DefaultRunner()
        super().__init__(*args, **kwargs)  # pyright: ignore[reportArgumentType]

    @override
    def __call__(
        self, *args: str | Path, capture_output: bool = False, shell: bool = False
    ) -> CompletedProcess[bytes]:
        self.mode = self.find_object(RunningMode) or self.mode
        runner = (
            self.dry_runner if self.mode is RunningMode.DRY_RUN else self.default_runner
        )
        return runner(*args, capture_output=capture_output)


def set_obj_to_running_mode_if_unset(ctx: Context, *, dry_run: bool) -> None:
    if dry_run:
        if ctx.find_object(RunningMode):
            error("Cannot set dry-run more than once")
            raise Exit(1)
        ctx.obj = RunningMode.DRY_RUN


class DryRunner:
    mode: RunningMode = RunningMode.DRY_RUN

    def __call__(
        self, *args: str | Path, capture_output: bool = False, shell: bool = False
    ) -> CompletedProcess[bytes]:
        print(f"{{{'shell_cmd' if shell else 'cmd'}:{args}}}")
        return CompletedProcess(args, 0, str(args).encode())


class DefaultRunner:
    mode: RunningMode = RunningMode.DEFAULT

    def __call__(
        self, *args: str | Path, capture_output: bool = False, shell: bool = False
    ) -> CompletedProcess[bytes]:
        return subprocess.run(
            args, check=True, capture_output=capture_output, shell=shell
        )


class DomestobotError(Exception):
    pass
