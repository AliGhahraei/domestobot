#!/usr/bin/env python3
from contextlib import contextmanager
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterator, Protocol
from unittest.mock import Mock

from click.testing import Result
from pytest import fixture, raises
from typer.testing import CliRunner

from domestobot.app import AppObject, ContextObject, get_app

DARWIN = 'Darwin'
UNKNOWN_OS = 'Unknown OS'


class Invoker(Protocol):
    def __call__(*args: str, context_object: ContextObject) -> Result:
        pass


@fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@fixture
def invoke(cli_runner: CliRunner) -> Invoker:
    def _run(*args: str, context_object: ContextObject) -> Result:
        return cli_runner.invoke(get_app(context_object), args)
    return _run


@fixture
def test_path(tmp_path: Path) -> Path:
    return tmp_path / 'file.toml'


@contextmanager
def invalid_config(message: str) -> Iterator[None]:
    with raises(SystemExit,
                match=f'Error while parsing config file: {message}'):
        yield


@fixture
def steps_stub() -> 'StepsStub':
    return StepsStub()


class StepsStub:
    def __init__(self) -> None:
        self.step_1_called = False
        self.step_2_called = False

    def step_1(self) -> None:
        self.step_1_called = True

    def step_2(self) -> None:
        self.step_2_called = True


def assert_command_succeeded(result: Result) -> None:
    assert result.exit_code == 0


def test_steps_are_runnable(invoke: Invoker, steps_stub: StepsStub) -> None:
    context_object = Mock(spec_set=ContextObject)
    context_object.get_steps.return_value = [steps_stub.step_1]

    result = invoke('step-1', context_object=context_object)

    assert_command_succeeded(result)
    assert steps_stub.step_1_called


def test_main_runs_all_steps(invoke: Invoker, steps_stub: StepsStub) -> None:
    context_object = Mock(spec_set=ContextObject)
    context_object.get_steps.return_value = [steps_stub.step_1,
                                             steps_stub.step_2]

    result = invoke(context_object=context_object)

    assert_command_succeeded(result)
    assert steps_stub.step_1_called
    assert steps_stub.step_2_called


class TestAppObject:
    @staticmethod
    @fixture
    def app_object(tmp_path: Path) -> AppObject:
        return AppObject(tmp_path / 'non_existent_file')

    class TestRun:
        @staticmethod
        def test_run_executes_command(
                app_object: AppObject,
        ) -> None:
            output = app_object.run('echo', 'hello', capture_output=True)
            assert 'hello' in output.stdout.decode('utf-8')

        @staticmethod
        def test_run_raises_exception_after_error(
                app_object: AppObject,
        ) -> None:
            with raises(CalledProcessError,
                        match='Command .* returned non-zero exit status 1.'):
                app_object.run('pwd', '--unknown-option')

    class TestGetSteps:
        @staticmethod
        def test_get_steps_creates_empty_steps_if_file_is_missing(
                app_object: AppObject,
        ) -> None:
            assert app_object.get_steps() == []

    class TestConfig:
        @staticmethod
        def test_config_access_shows_message_for_invalid_config_file_format(
                test_path: Path,
        ) -> None:
            test_path_object = AppObject(test_path)
            with open(test_path, 'w') as f:
                f.write('invalid toml')
            with invalid_config('Invalid key "invalid toml" at line 1'
                                ' col 12'):
                getattr(test_path_object, 'config')
