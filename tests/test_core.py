#!/usr/bin/env python3
from os import PathLike
from pathlib import Path

from domestobot.core import ExpandedPath


class TestExpandedPath:
    @staticmethod
    def test_expanded_path_equals_base() -> None:
        assert ExpandedPath('/test', '/path') == Path('/test', '/path')

    @staticmethod
    def test_path_is_expanded() -> None:
        assert ExpandedPath('~').expanduser() == Path.home()

    @staticmethod
    def test_path_repr_mimics_base() -> None:
        assert repr(ExpandedPath()) == "ExpandedPath('.')"

    @staticmethod
    def test_path_is_path_like() -> None:
        path = ExpandedPath()
        assert isinstance(path, PathLike)
        assert path.__fspath__() == '.'
