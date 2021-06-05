#!/usr/bin/env python3
from abc import abstractmethod
from functools import wraps
from pathlib import Path
from subprocess import CompletedProcess
from typing import TYPE_CHECKING, Any, Callable, Protocol, Union

from typer import style


def task_title(message: str) \
        -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:

        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            title(message)
            return f(*args, **kwargs)

        return wrapper
    return decorator


def title(message: str) -> None:
    dotted_message = f'\n{message}...'
    print(_colorize(dotted_message, 'magenta', bold=True))


def info(message: str) -> None:
    print(_colorize(message, 'cyan'))


def warning(message: str) -> None:
    print(_colorize(message, 'yellow'))


def _colorize(message: str, foreground: str, **kwargs: Any) -> str:
    return style(message, foreground, **kwargs)


class CommandRunner(Protocol):
    @abstractmethod
    def run(self, *args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        pass


class _ExpandedPathType(type):
    def __getattr__(cls, item: str) -> Any:
        return getattr(Path, item)


if TYPE_CHECKING:
    expanded_path_base = Path
else:
    expanded_path_base = object


class ExpandedPath(expanded_path_base, metaclass=_ExpandedPathType):
    def __init__(self, *pathsegments: str, **kwargs: Any) -> None:
        self._path = Path(*pathsegments, **kwargs).expanduser()

    def __getattr__(self, item: str) -> Any:
        return getattr(self._path, item)

    def __eq__(self, other: object) -> bool:
        return self._path == other

    def __repr__(self) -> str:
        return repr(self._path).replace(self._path.__class__.__name__,
                                        self.__class__.__name__)

    def __fspath__(self) -> str:
        return self._path.__fspath__()


class DomestobotError(Exception):
    pass
