#!/usr/bin/env python3
from unittest.mock import Mock

from pytest import fixture

from domestobot._core import CommandRunner


@fixture
def runner() -> Mock:
    return Mock(spec_set=CommandRunner)
