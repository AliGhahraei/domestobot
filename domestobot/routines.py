#!/usr/bin/env python3
from abc import abstractmethod
from pathlib import Path
from platform import system
from subprocess import CalledProcessError, CompletedProcess
from sys import exit
from typing import Callable, Iterable, Protocol, Union

from domestobot.core import info, task_title, title, warning

_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT = '->'


class CommandRunner(Protocol):
    @abstractmethod
    def run(self, *args: Union[str, Path], capture_output: bool = False) \
            -> CompletedProcess[bytes]:
        pass


def upgrade_fisher(runner: CommandRunner) -> None:
    if system() == 'Linux':
        title('Upgrading fisher')
        runner.run('fish', '-c', 'fisher update')


def upgrade_os(runner: CommandRunner) -> None:
    def get_macos_commands() -> Callable[[], None]:
        @task_title('Upgrading with brew')
        def upgrade_macos() -> None:
            runner.run('brew', 'update')
            runner.run('brew', 'upgrade')

        return upgrade_macos

    def get_arch_linux_commands() -> Callable[[], None]:
        @task_title('Upgrading with paru')
        def upgrade_arch() -> None:
            runner.run('paru')

        return upgrade_arch

    os_upgrade_commands = {
        'Darwin': get_macos_commands,
        'Linux': get_arch_linux_commands,
    }
    current_platform = system()
    try:
        upgrade_current_os = os_upgrade_commands[current_platform]()
    except KeyError:
        def upgrade_current_os() -> None:
            warning(f"Package managers for {current_platform} aren't"
                    f" supported")
    upgrade_current_os()


@task_title('Upgrading pipx and packages')
def upgrade_python_tools(runner: CommandRunner) -> None:
    runner.run('pipx', 'upgrade-all')


@task_title('Upgrading doom')
def upgrade_doom(runner: CommandRunner) -> None:
    runner.run('doom', 'upgrade')


@task_title('Fetching repos')
def fetch_repos(runner: CommandRunner, repos: Iterable[Path]) -> None:
    for repo in repos:
        runner.run('git', '-C', repo, 'fetch')


@task_title('Checking git repos')
def check_repos_clean(runner: CommandRunner, repos: Iterable[Path]) -> None:

    def is_tree_dirty(dir_: Path) -> bool:
        try:
            is_dirty = (_has_unsaved_changes(dir_)
                        or _has_unpushed_commits(dir_))
        except CalledProcessError as e:
            if e.returncode == 128:
                exit(f'Not a git repository: {dir_}')
            else:
                raise
        return is_dirty

    def _has_unsaved_changes(dir_: Path) -> bool:
        unsaved_changes = runner.run(
            'git', '-C', dir_, 'status', '--ignore-submodules', '--porcelain',
            capture_output=True,
        )
        return bool(_decode(unsaved_changes))

    def _has_unpushed_commits(dir_: Path) -> bool:
        unpushed_commits = runner.run(
            'git', '-C', dir_, 'log', '--branches', '--not', '--remotes',
            '--oneline', capture_output=True,
        )
        return (_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT
                in _decode(unpushed_commits))

    def _decode(command_output: CompletedProcess[bytes]) -> str:
        return command_output.stdout.decode('utf-8')

    if not repos:
        info('No repos to check')
    elif dirty_repos := [repo for repo in repos if is_tree_dirty(repo)]:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")
