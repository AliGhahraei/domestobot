from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any, Protocol, Union, cast

from domestobot import routines
from domestobot.routines import CommandRunner


class ContextObject(CommandRunner, Protocol):
    def __getattr__(self, item: str) -> 'Routine':
        """Not abstract due to https://github.com/python/mypy/issues/10409."""


class AppObject(ContextObject):
    @staticmethod
    def run(*args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        return run(args, check=True, capture_output=capture_output)

    def __getattr__(self, item: str) -> 'Routine':
        return cast(Routine, getattr(routines, item))


class Routine(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        pass
