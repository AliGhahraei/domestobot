#!/usr/bin/env python3
from typing import Any, Callable
from unittest.mock import Mock, patch

from asserts import assert_no_stdout, assert_stdout
from pytest import CaptureFixture

from domestobot._config import EnvStep, ShellStep
from domestobot._steps import get_steps

MODULE_UNDER_TEST = "domestobot._steps"
LINUX = "Linux"
DARWIN = "Darwin"


def assert_metadata_equal(function: Callable[..., Any], name: str, doc: str) -> None:
    assert function.__name__ == name
    assert function.__doc__ == doc


class TestGetSteps:
    @staticmethod
    def test_get_steps_creates_empty_steps_from_empty_steps(runner: Mock) -> None:
        assert get_steps([], runner) == []

    class TestShellDefinition:
        @staticmethod
        def test_get_steps_creates_shell_definition_with_correct_metadata(
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep("name", "doc", command=["command"])

            function = get_steps([step], runner)[0]

            assert_metadata_equal(function, "name", "doc")

        @staticmethod
        def test_shell_definition_passes_command_to_runner(
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep("name", "doc", command=["command", "param"])

            function = get_steps([step], runner)[0]
            function()

            runner.assert_called_once_with("command", "param")

        @staticmethod
        def test_shell_definition_without_title_has_no_output(
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep("name", "doc", command=["command"])

            function = get_steps([step], runner)[0]
            function()

            assert_no_stdout(capsys)

        @staticmethod
        def test_shell_definition_with_title_outputs_title(
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep("name", "doc", "title", ["command", "param"])

            function = get_steps([step], runner)[0]
            function()

            assert_stdout("title", capsys)

        @staticmethod
        def test_shell_definition_with_multiple_commands_passes_them_to_runner(
            runner: Mock, capsys: CaptureFixture[str]
        ) -> None:
            step = ShellStep(
                "name", "doc", "title", commands=[["command1"], ["command2"]]
            )

            function = get_steps([step], runner)[0]
            function()

            runner.assert_any_call("command1")
            runner.assert_any_call("command2")

        @staticmethod
        def test_shell_definition_passes_shell_command_to_runner(
            runner: Mock,
        ) -> None:
            step = ShellStep("name", "doc", shell_command="echo hello")

            function = get_steps([step], runner)[0]
            function()

            runner.assert_called_once_with("echo hello", shell=True)

        @staticmethod
        def test_shell_definition_with_multiple_shell_commands_passes_them_to_runner(
            runner: Mock,
        ) -> None:
            step = ShellStep(
                "name", "doc", "title", shell_commands=["echo hello", "ls"]
            )

            function = get_steps([step], runner)[0]
            function()

            runner.assert_any_call("echo hello", shell=True)
            runner.assert_any_call("ls", shell=True)

    class TestEnvDefinition:
        @staticmethod
        def test_get_steps_creates_env_definition_with_correct_metadata(
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep(
                "name",
                "doc",
                envs=[
                    EnvStep(LINUX, "title", ["command"]),
                ],
            )

            function = get_steps([step], runner)[0]

            assert_metadata_equal(function, "name", "doc")

        @staticmethod
        @patch(f"{MODULE_UNDER_TEST}.system", return_value=LINUX)
        def test_env_definition_passes_matching_platform_command_to_runner(
            _: Mock,
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep(
                "name",
                "doc",
                envs=[
                    EnvStep(LINUX, "title", ["command"]),
                    EnvStep(DARWIN, "title", ["ignored_command"]),
                ],
            )

            function = get_steps([step], runner)[0]
            function()

            runner.assert_called_once_with("command")

        @staticmethod
        @patch(f"{MODULE_UNDER_TEST}.system", return_value=LINUX)
        def test_env_definition_outputs_shell_step_title(
            _: Mock,
            runner: Mock,
            capsys: CaptureFixture[str],
        ) -> None:
            step = ShellStep(
                "name",
                "doc",
                "title",
                envs=[
                    EnvStep(LINUX, "title", ["command"]),
                ],
            )

            function = get_steps([step], runner)[0]
            function()

            assert_stdout("title", capsys)

        @staticmethod
        @patch(f"{MODULE_UNDER_TEST}.system", return_value=LINUX)
        def test_env_definition_passes_matching_platform_shell_command_to_runner(
            _: Mock, runner: Mock
        ) -> None:
            step = ShellStep(
                "name",
                "doc",
                envs=[
                    EnvStep(LINUX, "title", shell_command="echo 'hello linux'"),
                    EnvStep(DARWIN, "title", shell_command="echo 'hello darwin'"),
                ],
            )

            function = get_steps([step], runner)[0]
            function()

            runner.assert_called_once_with("echo 'hello linux'", shell=True)

        @staticmethod
        @patch(f"{MODULE_UNDER_TEST}.system", return_value=DARWIN)
        def test_env_definition_passes_matching_platform_shell_commands_to_runner(
            _: Mock, runner: Mock
        ) -> None:
            step = ShellStep(
                "name",
                "doc",
                envs=[
                    EnvStep(
                        LINUX,
                        "title",
                        shell_commands=["echo 'hello linux'", "ls"],
                    ),
                    EnvStep(
                        DARWIN,
                        "title",
                        shell_commands=["echo 'hello darwin'", "pwd"],
                    ),
                ],
            )

            function = get_steps([step], runner)[0]
            function()

            runner.assert_any_call("echo 'hello darwin'", shell=True)
            runner.assert_any_call("pwd", shell=True)
