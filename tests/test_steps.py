#!/usr/bin/env python3
from contextlib import contextmanager
from pathlib import Path
from subprocess import CalledProcessError
from typing import Any, Callable, Iterator
from unittest.mock import Mock, patch

from asserts import assert_no_stdout, assert_stdout
from pytest import CaptureFixture, fixture, raises

from domestobot.app import AppObject
from domestobot.config import Config, EnvStep, ShellStep
from domestobot.steps import get_steps

MODULE_UNDER_TEST = 'domestobot.steps'
LINUX = 'Linux'


@fixture
def test_path(tmp_path: Path) -> Path:
    return tmp_path / 'file.toml'


def assert_metadata_equal(function: Callable[..., Any], name: str, doc: str) \
        -> None:
    assert function.__name__ == name
    assert function.__doc__ == doc


@contextmanager
def invalid_config(message: str) -> Iterator[None]:
    with raises(SystemExit,
                match=f'Error while parsing config file: {message}'):
        yield


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


class TestGetSteps:
    @staticmethod
    def test_get_steps_creates_empty_steps_from_empty_config(runner: Mock) \
            -> None:
        assert get_steps(Config(), runner, Mock()) == []

    class TestShellDefinition:
        @staticmethod
        def test_get_steps_creates_shell_definition_with_correct_metadata(
                runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', command=['command'])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]

            assert_metadata_equal(function, 'name', 'doc')

        @staticmethod
        def test_shell_definition_passes_command_to_runner(
                runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', command=['command', 'param'])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]
            function()

            runner.run.assert_called_once_with('command', 'param')

        @staticmethod
        def test_shell_definition_without_title_has_no_output(
                runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', command=['command'])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]
            function()

            assert_no_stdout(capsys)

        @staticmethod
        def test_shell_definition_with_title_outputs_title(
                runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', 'title', ['command', 'param'])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]
            function()

            assert_stdout('title', capsys)

        @staticmethod
        def test_shell_definition_with_multiple_commands_passes_them_to_runner(
                runner: Mock, capsys: CaptureFixture[str]
        ) -> None:
            step = ShellStep('name', 'doc', 'title',
                             commands=[['command1'], ['command2']])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]
            function()

            runner.run.assert_any_call('command1')
            runner.run.assert_any_call('command2')

    class TestEnvDefinition:
        @staticmethod
        def test_get_steps_creates_env_definition_with_correct_metadata(
                runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', env=[
                EnvStep(LINUX, 'title', ['command']),
            ])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]

            assert_metadata_equal(function, 'name', 'doc')

        @staticmethod
        @patch(f'{MODULE_UNDER_TEST}.system', return_value=LINUX)
        def test_env_definition_passes_matching_platform_command_to_runner(
                _: Mock, runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', env=[
                EnvStep(LINUX, 'title', ['command']),
                EnvStep('Darwin', 'title', ['ignored_command']),
            ])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]
            function()

            runner.run.assert_called_once_with('command')

        @staticmethod
        @patch(f'{MODULE_UNDER_TEST}.system', return_value=LINUX)
        def test_env_definition_outputs_shell_step_title(
                _: Mock, runner: Mock, capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep('name', 'doc', 'title', env=[
                EnvStep(LINUX, 'title', ['command']),
            ])

            function = get_steps(Config(steps=[step]), runner, Mock())[0]
            function()

            assert_stdout('title', capsys)
