from itertools import chain
from platform import system
from typing import Callable, Iterable, List

from domestobot._config import CommandStep, EnvStep, ShellStep
from domestobot._core import CommandRunner, title


def get_steps(steps: Iterable[ShellStep], runner: CommandRunner) \
        -> List[Callable[..., None]]:
    return list(chain.from_iterable(_get_definitions(step, runner)
                                    for step in steps))


def _get_definitions(step: 'ShellStep', runner: CommandRunner) \
        -> List[Callable[..., None]]:
    return _build_wrappers_from_shell_step(step, runner)


def _build_wrappers_from_shell_step(step: 'ShellStep', runner: CommandRunner) \
        -> List[Callable[..., None]]:
    return [_make_command_step_wrapper(runnable, step.name, step.doc, runner)
            for runnable in _get_command_steps(step)]


def _make_command_step_wrapper(step: 'CommandStep', name: str, doc: str,
                               runner: CommandRunner) -> Callable[..., None]:
    def step_wrapper() -> None:
        if step.title:
            title(step.title)

        commands = step.commands if step.commands else [step.command]
        for command in commands:
            runner.run(*command)

    step_wrapper.__name__ = name
    step_wrapper.__doc__ = doc
    return step_wrapper


def _get_command_steps(step: 'ShellStep') -> List['CommandStep']:
    return _get_steps_from_env(step.envs) if step.envs else [step]


def _get_steps_from_env(steps: Iterable['EnvStep']) -> List['CommandStep']:
    os = system()
    return [step for step in steps if step.os == os]
