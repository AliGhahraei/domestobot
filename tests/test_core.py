#!/usr/bin/env python3
from subprocess import CalledProcessError

from pytest import raises

from domestobot.core import run_command


def test_run_command_executes_command() -> None:
    output = run_command('echo', 'hello', capture_output=True)
    assert 'hello' in output.stdout.decode('utf-8')


def test_run_command_raises_exception_after_error() -> None:
    with raises(CalledProcessError):
        run_command('pwd', '--unknown-option')
