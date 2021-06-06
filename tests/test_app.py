#!/usr/bin/env python3
from contextlib import contextmanager
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterator, Protocol
from unittest.mock import Mock, call, patch

from click.testing import Result
from pytest import MonkeyPatch, fixture, raises
from typer import Typer
from typer.testing import CliRunner

from domestobot.app import AppObject, DomestobotObject, get_app, read_config
from domestobot.config import Config
from domestobot.steps import get_steps

DARWIN = 'Darwin'
UNKNOWN_OS = 'Unknown OS'
STEPS_MODULE = 'domestobot.steps'


class Invoker(Protocol):
    def __call__(*args: str, app: Typer) -> Result:
        pass


@fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@fixture
def invoke(cli_runner: CliRunner) -> Invoker:
    def _run(*args: str, app: Typer) -> Result:
        return cli_runner.invoke(app, args)
    return _run


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


class TestGetApp:
    @staticmethod
    def test_steps_are_runnable(invoke: Invoker, steps_stub: StepsStub) \
            -> None:
        app_object = Mock(spec_set=AppObject)
        app_object.get_steps.return_value = [steps_stub.step_1]

        result = invoke('step-1', app=get_app(app_object))

        assert_command_succeeded(result)
        assert steps_stub.step_1_called

    @staticmethod
    def test_main_runs_all_steps(invoke: Invoker, steps_stub: StepsStub) \
            -> None:
        app_object = Mock(spec_set=AppObject)
        app_object.get_steps.return_value = [steps_stub.step_1,
                                             steps_stub.step_2]

        result = invoke(app=get_app(app_object))

        assert_command_succeeded(result)
        assert steps_stub.step_1_called
        assert steps_stub.step_2_called


class TestDomestobotObject:
    class TestConfigPath:
        @staticmethod
        def test_default_path_is_correct() -> None:
            assert (DomestobotObject().config_path
                    == Path.home() / '.config/domestobot/config.toml')

        @staticmethod
        def test_path_can_be_read_from_env(monkeypatch: MonkeyPatch) -> None:
            monkeypatch.setenv('DOMESTOBOT_CONFIG', 'path')

            assert DomestobotObject().config_path == Path('path')

    @staticmethod
    @fixture
    def domestobot_object(tmp_path: Path) -> DomestobotObject:
        return DomestobotObject(tmp_path / 'non_existent_file')

    class TestRun:
        @staticmethod
        def test_run_executes_command(
                domestobot_object: DomestobotObject,
        ) -> None:
            output = domestobot_object.run('echo', 'hello',
                                           capture_output=True)
            assert 'hello' in output.stdout.decode('utf-8')

        @staticmethod
        def test_run_raises_exception_after_error(
                domestobot_object: DomestobotObject,
        ) -> None:
            with raises(CalledProcessError,
                        match='Command .* returned non-zero exit status 1.'):
                domestobot_object.run('pwd', '--unknown-option')

    class TestGetSteps:
        @staticmethod
        def test_get_steps_creates_empty_steps_for_default_app(
                domestobot_object: DomestobotObject,
        ) -> None:
            assert domestobot_object.get_steps() == []

    class TestConfig:
        @staticmethod
        def test_config_is_empty_for_default_app(
                domestobot_object: DomestobotObject,
        ) -> None:
            assert domestobot_object.config == Config()


class TestReadConfig:
    @staticmethod
    @fixture
    def test_path(tmp_path: Path) -> Path:
        return tmp_path / 'file.toml'

    @staticmethod
    def test_config_access_shows_message_for_invalid_config_file_format(
            test_path: Path,
    ) -> None:
        with open(test_path, 'w') as f:
            f.write('invalid toml')
        with invalid_config('Invalid key "invalid toml" at line 1 col 12'):
            read_config(test_path)

    @staticmethod
    @patch(f'{STEPS_MODULE}.system', return_value='Linux')
    def test_config_tutorial_matches_expected_commands(runner: Mock) -> None:
        config = read_config(Path('config_tutorial.toml'))
        for step in get_steps(config, runner, Mock()):
            step()

        assert runner.run.mock_calls == [
            call('echo', 'hello!'),
            call('echo', 'hello'),
            call('echo', 'hello'),
            call('echo', "You're using Linux")
        ]
