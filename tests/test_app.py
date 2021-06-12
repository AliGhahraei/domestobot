#!/usr/bin/env python3
from contextlib import contextmanager
from logging import FileHandler, getLogger
from pathlib import Path
from typing import ContextManager, Iterator, List, Protocol, cast
from unittest.mock import Mock, patch

from click.testing import Result
from pytest import (CaptureFixture, LogCaptureFixture, MonkeyPatch, fixture,
                    mark, raises)
from tomlkit import document, dumps
from typer import Typer
from typer.testing import CliRunner

from domestobot._app import (ConfigError, get_app, get_app_from_config,
                             get_main_app, get_path_or_default, main)
from domestobot._config import Config, ShellStep

DARWIN = 'Darwin'
UNKNOWN_OS = 'Unknown OS'
STEPS_MODULE = 'domestobot._steps'


class Invoker(Protocol):
    def __call__(*args: str, app: Typer) -> Result:
        pass


@fixture
def disable_log_file(monkeypatch: MonkeyPatch) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setenv('DOMESTOBOT_LOG', '')
        yield


@fixture
def log_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Iterator[Path]:
    with monkeypatch.context() as m:
        logdir = tmp_path / 'intermediate_dir' / 'log'
        m.setenv('DOMESTOBOT_LOG', str(logdir))
        yield logdir


@fixture
def cli_runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


@fixture
def invoke(cli_runner: CliRunner) -> Invoker:
    def _run(*args: str, app: Typer) -> Result:
        return cli_runner.invoke(app, args, catch_exceptions=False)
    return _run


@contextmanager
def system_exit(message: str) -> Iterator[None]:
    with raises(SystemExit, match=message):
        yield


def invalid_config(message: str) -> ContextManager[None]:
    return system_exit(f'Error while parsing config file {message}')


@fixture
def toml_path(tmp_path: Path) -> Path:
    return tmp_path / 'config.toml'


def assert_command_succeeded(result: Result) -> None:
    assert result.exit_code == 0


@mark.usefixtures('disable_log_file')
class TestMain:
    @staticmethod
    def test_main_exits_with_human_friendly_validation_error_message(
            toml_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        doc = document()
        doc['sub_domestobots'] = 'non-list value'
        with open(toml_path, 'w') as f:
            f.write(dumps(doc))

        with system_exit('value is not a valid list'):
            main(toml_path)

    @staticmethod
    def test_main_shows_invalid_config_file_format_message(
            toml_path: Path
    ) -> None:
        with open(toml_path, 'w') as f:
            f.write('invalid toml')

        with invalid_config(f'{toml_path}: Invalid key "invalid toml" at line '
                            '1 col 12'):
            main(toml_path)

    @staticmethod
    @patch('domestobot._app.get_app', side_effect=Exception('test error'))
    def test_main_exits_with_unhandled_error_message(
            _: Mock, toml_path: Path, caplog: LogCaptureFixture,
    ) -> None:
        error = (r'Unhandled error, please report it to the maintainer: '
                 '"test error"')

        with system_exit(error):
            main(toml_path)

        assert 'Traceback (most recent call last)' in caplog.text

    @staticmethod
    @patch('domestobot._app.get_main_app')
    def test_main_creates_log_dir(
            _: Mock, toml_path: Path, log_path: Path,
    ) -> None:
        main(toml_path)

        assert log_path.parent.exists()

    @staticmethod
    @patch('domestobot._app.get_main_app')
    def test_main_sets_logger_handler(
            _: Mock, toml_path: Path, log_path: Path,
    ) -> None:
        main(toml_path)

        handler = cast(FileHandler, getLogger('domestobot._app').handlers[0])
        assert handler.baseFilename == str(log_path)


class TestGetMainApp:
    @staticmethod
    def test_app_shows_help_if_config_is_missing(
            invoke: Invoker, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        path = tmp_path / 'missing_file.toml'

        result = invoke(app=get_main_app(path))

        assert 'Usage:' in result.stdout
        assert f'Config file {path} not found' in capsys.readouterr().err


class TestGetAppFromConfig:
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
            return Config([step.name], [step])

        @staticmethod
        def test_step_is_runnable(invoke: Invoker, config: Config) -> None:
            result = invoke('test-step', app=get_app_from_config(config))

            assert_command_succeeded(result)

        @staticmethod
        def test_step_produces_expected_output(
                invoke: Invoker, config: Config, step_output: str,
                capfd: CaptureFixture[str],
        ) -> None:
            invoke('test-step', app=get_app_from_config(config))

            assert step_output in capfd.readouterr().out

        @staticmethod
        def test_invocation_without_step_is_runnable(invoke: Invoker,
                                                     config: Config) -> None:
            result = invoke(app=get_app_from_config(config))

            assert_command_succeeded(result)

        @staticmethod
        def test_invocation_without_steps_calls_step(
                invoke: Invoker, config: Config, step_output: str,
                capfd: CaptureFixture[str]
        ) -> None:
            invoke(app=get_app_from_config(config))

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
            return Config([step.name for step in steps], steps=steps)

        @staticmethod
        def test_steps_are_runnable(invoke: Invoker, config: Config) -> None:
            results = [invoke(step_name, app=get_app_from_config(config))
                       for step_name in ('test-step', 'second-step')]

            for result in results:
                assert_command_succeeded(result)

        @staticmethod
        def test_steps_produce_expected_output(
                invoke: Invoker, config: Config, outputs: str,
                capfd: CaptureFixture[str],
        ) -> None:
            for step_name in ('test-step', 'second-step'):
                invoke(step_name, app=get_app_from_config(config))

            output = capfd.readouterr().out
            for expected_output in outputs:
                assert expected_output in output

        @staticmethod
        def test_invocation_without_step_is_runnable(invoke: Invoker,
                                                     config: Config) -> None:
            result = invoke(app=get_app_from_config(config))

            assert_command_succeeded(result)

        @staticmethod
        def test_invocation_without_step_runs_all_steps(
                invoke: Invoker, config: Config, outputs: str,
                capfd: CaptureFixture[str],
        ) -> None:
            invoke(app=get_app_from_config(config))

            output = capfd.readouterr().out
            for expected_output in outputs:
                assert expected_output in output

    @staticmethod
    def test_app_prints_commands_with_dry_run(invoke: Invoker) -> None:
        config = Config(steps=[
            ShellStep('test_step', 'doc', command=['command', 'param']),
        ])

        result = invoke('--dry-run', 'test-step',
                        app=get_app_from_config(config))

        assert "('command', 'param')" in result.stdout

    @staticmethod
    def test_app_shows_help_if_default_subcommands_are_not_configured(
            invoke: Invoker, step: ShellStep,
    ) -> None:
        config = Config(steps=[step])

        result = invoke(app=get_app_from_config(config))

        assert 'Usage:' in result.stdout

    @staticmethod
    def test_app_shows_custom_help(invoke: Invoker, step: ShellStep) -> None:
        config = Config(help_message='Custom help')

        result = invoke('--help', app=get_app_from_config(config))

        assert 'Custom help' in result.stdout

    @staticmethod
    def test_app_exits_without_output_if_default_subcommands_are_not_in_app(
            invoke: Invoker, step: ShellStep, capfd: CaptureFixture[str],
    ) -> None:
        config = Config(['test_step', 'invalid_step'], steps=[step])

        with raises(ConfigError, match="'invalid_step' is not a valid step"):
            invoke(app=get_app_from_config(config))

        assert not capfd.readouterr().out


class TestGetApp:
    @staticmethod
    @patch(f'{STEPS_MODULE}.system', return_value='Linux')
    def test_config_tutorial_invocation_matches_expected_commands(
            _: Mock, invoke: Invoker, capfd: CaptureFixture[str],
    ) -> None:
        invoke(app=get_app(Path('tutorial/root.toml')))

        assert capfd.readouterr().out == '\n'.join([
            'Hello!',
            'First echo',
            'Second echo',
            "You're using Linux",
            "Bye!"
        ]) + '\n'


class TestGetPathOrDefault:
    @staticmethod
    def test_default_path_is_correct() -> None:
        assert (get_path_or_default(None)
                == Path.home() / '.config/domestobot/root.toml')

    @staticmethod
    def test_path_can_be_read_from_env(monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv('DOMESTOBOT_ROOT', 'root_path')

        assert get_path_or_default(None) == Path('root_path/root.toml')
