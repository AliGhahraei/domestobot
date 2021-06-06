#!/usr/bin/env python3
from typing import Protocol
from unittest.mock import Mock

from click.testing import Result
from pytest import fixture
from typer.testing import CliRunner

from domestobot.app import ContextObject, get_app

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
