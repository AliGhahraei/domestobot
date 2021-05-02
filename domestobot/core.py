#!/usr/bin/env python3
from functools import wraps
from typing import Callable, Any

from typer import style


def task_title(message: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        wraps(f)
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
