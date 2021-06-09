#!/usr/bin/env python3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Protocol
from unittest.mock import Mock, call, patch

from click.testing import Result
from pytest import CaptureFixture, MonkeyPatch, fixture, raises
from typer import Typer
from typer.testing import CliRunner

from domestobot.app import ConfigReader, get_app
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
        return cli_runner.invoke(app, args, catch_exceptions=False)
    return _run


@contextmanager
def invalid_config(message: str) -> Iterator[None]:
    with raises(SystemExit,
                match=f'Error while parsing config file: {message}'):
        yield


def assert_command_succeeded(result: Result) -> None:
    assert result.exit_code == 0


class TestGetApp:
    @staticmethod
    @fixture
    def step_output() -> str:
        return 'echoed value'

    @staticmethod
    @fixture
    def step(step_output: str) -> ShellStep:
        return ShellStep('test_step', 'doc', command=['echo', step_output])

    class TestSingleStep:
        @staticmethod
        @fixture
        def config(step: ShellStep) -> Config:
            return Config(steps=[step])

        @staticmethod
        def test_step_is_runnable(invoke: Invoker, config: Config) -> None:
            result = invoke('test-step', app=get_app(config))

            assert_command_succeeded(result)

        @staticmethod
        def test_step_produces_expected_output(
                invoke: Invoker, config: Config, step_output: str,
                capfd: CaptureFixture[str],
        ) -> None:
            invoke('test-step', app=get_app(config))

            assert step_output in capfd.readouterr().out

        @staticmethod
        def test_invocation_without_step_is_runnable(invoke: Invoker,
                                                     config: Config) -> None:
            result = invoke(app=get_app(config))

            assert_command_succeeded(result)

        @staticmethod
        def test_invocation_without_steps_calls_step(
                invoke: Invoker, config: Config, step_output: str,
                capfd: CaptureFixture[str]
        ) -> None:
            invoke(app=get_app(config))

            assert step_output in capfd.readouterr().out

    class TestMultipleSteps:
        @staticmethod
        @fixture
        def second_output() -> str:
            return 'second value'

        @staticmethod
        @fixture
        def outputs(step_output: str, second_output: str) -> List[str]:
            return [step_output, second_output]

        @staticmethod
        @fixture
        def steps(step: ShellStep, second_output: str) -> List[ShellStep]:
            second = ShellStep('second_step', 'doc',
                               command=['echo', second_output])
            return [step, second]

        @staticmethod
        @fixture
        def config(steps: List[ShellStep]) -> Config:
            return Config(steps=steps)

        @staticmethod
        def test_steps_are_runnable(invoke: Invoker, config: Config) -> None:
            results = [invoke(step_name, app=get_app(config))
                       for step_name in ('test-step', 'second-step')]

            for result in results:
                assert_command_succeeded(result)

        @staticmethod
        def test_steps_produce_expected_output(
                invoke: Invoker, config: Config, outputs: str,
                capfd: CaptureFixture[str],
        ) -> None:
            for step_name in ('test-step', 'second-step'):
                invoke(step_name, app=get_app(config))

            output = capfd.readouterr().out
            for expected_output in outputs:
                assert expected_output in output

        @staticmethod
        def test_invocation_without_step_is_runnable(invoke: Invoker,
                                                     config: Config) -> None:
            result = invoke(app=get_app(config))

            assert_command_succeeded(result)

        @staticmethod
        def test_invocation_without_step_runs_all_steps(
                invoke: Invoker, config: Config, outputs: str,
                capfd: CaptureFixture[str],
        ) -> None:
            invoke(app=get_app(config))

            output = capfd.readouterr().out
            for expected_output in outputs:
                assert expected_output in output

    @staticmethod
    def test_app_prints_commands_with_dry_run(invoke: Invoker) -> None:
        config = Config(steps=[
            ShellStep('test_step', 'doc', command=['command', 'param']),
        ])

        result = invoke('--dry-run', app=get_app(config))

        assert "('command', 'param')" in result.stdout


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
