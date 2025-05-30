from itertools import chain
from platform import system
from typing import Callable, Iterable, List

from domestobot._config import CommandStep, EnvStep, ShellStep
from domestobot._core import CmdRunnerContext, title


def get_steps(
    steps: Iterable[ShellStep],
) -> List[Callable[..., None]]:
    return list(chain.from_iterable(_get_definitions(step) for step in steps))


def _get_definitions(step: "ShellStep") -> List[Callable[..., None]]:
    return _build_wrappers_from_shell_step(step)


def _build_wrappers_from_shell_step(
    step: "ShellStep",
) -> List[Callable[..., None]]:
    return [
        _make_command_step_wrapper(runnable, step.name, step.doc)
        for runnable in _get_command_steps(step)
    ]


def _make_command_step_wrapper(
    step: "CommandStep", name: str, doc: str
) -> Callable[..., None]:
    def step_wrapper(runner: CmdRunnerContext) -> None:
        if step.title:
            title(step.title)

        if step.command:
            _ = runner(*step.command)
        elif step.commands:
            for runner_args in step.commands:
                _ = runner(*runner_args)
        elif step.shell_command:
            _ = runner(step.shell_command, shell=True)
        else:
            for shell_runner_args in step.shell_commands:
                _ = runner(shell_runner_args, shell=True)

    step_wrapper.__name__ = name
    step_wrapper.__doc__ = doc
    return step_wrapper


def _get_command_steps(step: "ShellStep") -> List["CommandStep"]:
    return _get_steps_from_env(step.envs) if step.envs else [step]


def _get_steps_from_env(steps: Iterable["EnvStep"]) -> List["CommandStep"]:
    os = system()
    return [step for step in steps if step.os == os]
