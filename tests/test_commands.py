#!/usr/bin/env python3
from inspect import getmembers
from itertools import chain
from types import SimpleNamespace
from typing import Any, Protocol, cast
from unittest.mock import Mock, create_autospec

from click.testing import Result
from pytest import fixture
from typer.testing import CliRunner

from domestobot import routines
from domestobot.commands import app
from domestobot.context_objects import ContextObject

DARWIN = 'Darwin'
UNKNOWN_OS = 'Unknown OS'


class Invoker(Protocol):
    def __call__(*args: str, context_object: Mock) -> Result:
        pass


@fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@fixture
def context_object() -> Mock:
    all_members = chain(getmembers(ContextObject), getmembers(routines))
    namespace = SimpleNamespace()
    for name, attr in ((name, attr) for name, attr in all_members
                       if not name.startswith('_')):
        setattr(namespace, name, attr)
    return cast(Mock, create_autospec(namespace, spec_set=True))


@fixture
def invoke(cli_runner: CliRunner) -> Invoker:
    def _run(*args: str, context_object: Mock) -> Result:
        return cli_runner.invoke(app, args, obj=context_object)
    return _run


def assert_upgrade_fisher_called(context_object: Mock) -> None:
    assert_routine_called_with(context_object, 'upgrade_fisher',
                               context_object)


def assert_upgrade_os_called(context_object: Mock) -> None:
    assert_routine_called_with(context_object, 'upgrade_os', context_object)


def assert_upgrade_python_tools_called(context_object: Mock) -> None:
    assert_routine_called_with(context_object, 'upgrade_python_tools',
                               context_object)


def assert_upgrade_doom_called(context_object: Mock) -> None:
    assert_routine_called_with(context_object, 'upgrade_doom', context_object)


def assert_check_repos_clean_called(context_object: Mock) -> None:
    assert_routine_called_with(context_object, 'check_repos_clean',
                               context_object, context_object.config.repos)


def assert_routine_called_with(context_object: Mock, routine: str, *args: Any,
                               **kwargs: Any) -> None:
    getattr(context_object, routine).assert_called_once_with(*args, **kwargs)


def assert_main_subroutines_called(context_object: Mock) \
        -> None:
    assert_upgrade_fisher_called(context_object)
    assert_upgrade_os_called(context_object)
    assert_upgrade_python_tools_called(context_object)
    assert_upgrade_doom_called(context_object)
    assert_check_repos_clean_called(context_object)


def assert_command_succeeded(result: Result) -> None:
    assert result.exit_code == 0


def test_main_runs_subroutines(invoke: Invoker, context_object: Mock) -> None:
    result = invoke(context_object=context_object)
    assert_main_subroutines_called(context_object)
    assert_command_succeeded(result)


def test_upgrade_fisher_runs_subroutine(invoke: Invoker, context_object: Mock)\
        -> None:
    result = invoke('upgrade-fisher', context_object=context_object)
    assert_upgrade_fisher_called(context_object)
    assert_command_succeeded(result)


def test_upgrade_os_runs_subroutine(invoke: Invoker, context_object: Mock) \
        -> None:
    result = invoke('upgrade-os', context_object=context_object)
    assert_upgrade_os_called(context_object)
    assert_command_succeeded(result)


def test_upgrade_python_tools_runs_subroutine(invoke: Invoker,
                                              context_object: Mock) -> None:
    result = invoke('upgrade-python-tools', context_object=context_object)
    assert_upgrade_python_tools_called(context_object)
    assert_command_succeeded(result)


def test_upgrade_doom_runs_subroutine(invoke: Invoker, context_object: Mock) \
        -> None:
    result = invoke('upgrade-doom', context_object=context_object)
    assert_upgrade_doom_called(context_object)
    assert_command_succeeded(result)


def test_check_repos_clean_runs_subroutine(
        invoke: Invoker, context_object: Mock,
) -> None:
    result = invoke('check-repos-clean', context_object=context_object)
    assert_check_repos_clean_called(context_object)
    assert_command_succeeded(result)
