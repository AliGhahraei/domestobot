#!/usr/bin/env python3
from abc import abstractmethod
from pathlib import Path
from subprocess import CompletedProcess
from typing import Protocol, Union

from typer import style


def title(message: str) -> None:
    dotted_message = f'\n{message}...'
    print(style(dotted_message, 'magenta', bold=True))


class CommandRunner(Protocol):
    @abstractmethod
    def run(self, *args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        pass


class DomestobotError(Exception):
    pass
