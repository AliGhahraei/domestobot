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

from domestobot.app import (AppObject, ConfigReader, DefaultCommandRunner,
                            DomestobotObject, get_app)
from domestobot.config import Config, ShellStep
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

        invoke(app=get_app(app_object))

        assert steps_stub.step_1_called
        assert steps_stub.step_2_called

    @staticmethod
    def test_dry_run_prints_commands(invoke: Invoker) -> None:
        config = Config(steps=[
            ShellStep('test_step', 'doc', command=['command', 'param']),
        ])
        result = invoke('--dry-run', app=get_app(DomestobotObject(config)))

        assert "('command', 'param')" in result.stdout


class TestDefaultCommandRunner:
    @staticmethod
    @fixture
    def command_runner(tmp_path: Path) -> DefaultCommandRunner:
        return DefaultCommandRunner()

    @staticmethod
    def test_run_executes_command(
            command_runner: DefaultCommandRunner,
    ) -> None:
        output = command_runner.run('echo', 'hello', capture_output=True)
        assert 'hello' in output.stdout.decode('utf-8')

    @staticmethod
    def test_run_raises_exception_after_error(
            command_runner: DefaultCommandRunner,
    ) -> None:
        with raises(CalledProcessError,
                    match='Command .* returned non-zero exit status 1.'):
            command_runner.run('pwd', '--unknown-option')


class TestDomestobotObject:
    class TestGetSteps:
        @staticmethod
        def test_get_steps_creates_empty_steps_for_empty_config() -> None:
            assert DomestobotObject(Config()).get_steps() == []


class TestConfigReader:
    @staticmethod
    @fixture
    def test_path(tmp_path: Path) -> Path:
        return tmp_path / 'file.toml'

    @staticmethod
    def test_default_path_is_correct() -> None:
        assert (ConfigReader().path
                == Path.home() / '.config/domestobot/config.toml')

    @staticmethod
    def test_path_can_be_read_from_env(monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv('DOMESTOBOT_CONFIG', 'path')

        assert ConfigReader().path == Path('path')

    @staticmethod
    def test_read_shows_message_for_invalid_config_file_format(
            test_path: Path,
    ) -> None:
        with open(test_path, 'w') as f:
            f.write('invalid toml')
        with invalid_config('Invalid key "invalid toml" at line 1 col 12'):
            ConfigReader(test_path).read()

    @staticmethod
    def test_read_shows_message_for_missing_config_file(
            test_path: Path,
    ) -> None:
        with raises(SystemExit, match="Config file 'invalid_path' not found"):
            ConfigReader(Path('invalid_path')).read()

    @staticmethod
    @patch(f'{STEPS_MODULE}.system', return_value='Linux')
    def test_config_tutorial_matches_expected_commands(runner: Mock) -> None:
        config = ConfigReader(Path('config_tutorial.toml')).read()
        for step in get_steps(config, runner, Mock()):
            step()

        assert runner.run.mock_calls == [
            call('echo', 'hello!'),
            call('echo', 'hello'),
            call('echo', 'hello'),
            call('echo', "You're using Linux")
        ]
