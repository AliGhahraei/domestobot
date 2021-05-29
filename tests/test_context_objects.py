#!/usr/bin/env python3
from inspect import getmembers, isfunction
from subprocess import CalledProcessError

from pytest import fixture, raises

from domestobot import routines
from domestobot.context_objects import AppObject


@fixture
def app_object() -> AppObject:
    return AppObject()


class TestAppObject:
    @staticmethod
    def test_run_command_executes_command(app_object: AppObject) -> None:
        output = app_object.run('echo', 'hello', capture_output=True)
        assert 'hello' in output.stdout.decode('utf-8')

    @staticmethod
    def test_run_command_raises_exception_after_error(app_object: AppObject) \
            -> None:
        with raises(CalledProcessError, match='Command .* returned non-zero '
                                              'exit status 1.'):
            app_object.run('pwd', '--unknown-option')

    @staticmethod
    def test_object_has_routines_as_attributes(app_object: AppObject) -> None:
        for routine_name, _ in getmembers(routines, isfunction):
            assert hasattr(app_object, routine_name)
