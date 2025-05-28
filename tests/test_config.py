#!/usr/bin/env python3
from unittest.mock import Mock

from pytest import raises

from domestobot._config import EnvStep, ShellStep


class TestShellStep:
    @staticmethod
    def test_step_raises_exception_with_command_and_commands_together(
        runner: Mock,
    ) -> None:
        with raises(TypeError):
            ShellStep(
                "name", "doc", "title", ["command1"], [["command2"], ["command3"]]
            )

    @staticmethod
    def test_step_raises_exception_with_command_and_env_together(runner: Mock) -> None:
        with raises(TypeError):
            ShellStep(
                "name",
                "doc",
                "title",
                ["command1"],
                envs=[EnvStep("Linux", "title", ["command2"])],
            )

    @staticmethod
    def test_step_raises_exception_without_command_fields_or_env(
        runner: Mock,
    ) -> None:
        with raises(TypeError):
            ShellStep("name", "doc", "title")


class TestEnvStep:
    @staticmethod
    def test_step_raises_exception_with_command_and_commands_together() -> None:
        with raises(TypeError):
            EnvStep("Linux", "title", ["command1"], [["command2"], ["command3"]])

    @staticmethod
    def test_step_raises_exception_with_shell_command_and_shell_commands_together() -> (
        None
    ):
        with raises(TypeError):
            EnvStep(
                "Linux",
                "title",
                shell_command="command1",
                shell_commands=["command2", "command3"],
            )

    @staticmethod
    def test_step_raises_exception_with_command_and_shell_command_together() -> None:
        with raises(TypeError):
            EnvStep(
                "Linux",
                "title",
                ["command1"],
                shell_command="command2",
            )

    @staticmethod
    def test_step_raises_exception_without_command_fields() -> None:
        with raises(TypeError):
            EnvStep("Linux", "title")
