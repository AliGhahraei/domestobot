#!/usr/bin/env python3
from subprocess import CalledProcessError

from pytest import fixture, raises

from domestobot.core import AppObject


@fixture
def app_object() -> AppObject:
    return AppObject()


def test_run_command_executes_command(app_object: AppObject) -> None:
    output = app_object.run('echo', 'hello', capture_output=True)
    assert 'hello' in output.stdout.decode('utf-8')


def test_run_command_raises_exception_after_error(app_object: AppObject) \
        -> None:
    with raises(CalledProcessError):
        app_object.run('pwd', '--unknown-option')
