#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from sys import exit
from typing import Iterable, Union

from domestobot.core import (CommandRunner, ExpandedPath, info, task_title,
                             warning)

_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT = '->'


@task_title('Fetching yadm')
def fetch_yadm(runner: 'CommandRunner') -> None:
    """Fetch new changes for yadm."""
    runner.run('yadm', 'fetch')


@task_title('Checking yadm')
def check_yadm_clean(runner: 'CommandRunner') -> None:
    """Check if yadm has unpublished work."""
    if (_has_unsaved_changes(runner, 'yadm')
            or _has_unpushed_commits(runner, 'yadm')):
        warning('Yadm was not clean')
    else:
        info('Yadm was clean!')


@task_title('Fetching repos')
def fetch_repos(runner: 'CommandRunner', repos: Iterable[ExpandedPath]) \
        -> None:
    """Fetch new changes for repos."""
    for repo in repos:
        runner.run('git', '-C', repo, 'fetch')


@task_title('Checking git repos')
def check_repos_clean(runner: 'CommandRunner', repos: Iterable[ExpandedPath]) \
        -> None:
    """Check if repos have unpublished work."""
    if not repos:
        info('No repos to check')
    elif dirty_repos := [repo for repo in repos
                         if is_tree_dirty(repo, runner)]:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")


def is_tree_dirty(dir_: Path, runner: 'CommandRunner') -> bool:
    try:
        is_dirty = (_has_unsaved_changes(runner, 'git', '-C', dir_)
                    or _has_unpushed_commits(runner, 'git', '-C', dir_))
    except CalledProcessError as e:
        if e.returncode == 128:
            exit(f'Not a git repository: {dir_}')
        else:
            raise
    return is_dirty


def _has_unsaved_changes(runner: 'CommandRunner',
                         *command_prefix: Union[str, Path]) -> bool:
    unsaved_changes = runner.run(
        *command_prefix, 'status', '--ignore-submodules', '--porcelain',
        capture_output=True,
    )
    return bool(_decode(unsaved_changes))


def _has_unpushed_commits(runner: 'CommandRunner',
                          *command_prefix: Union[str, Path]) -> bool:
    unpushed_commits = runner.run(
        *command_prefix, 'log', '--branches', '--not', '--remotes',
        '--oneline', capture_output=True,
    )
    return (_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT
            in _decode(unpushed_commits))


def _decode(command_output: CompletedProcess[bytes]) -> str:
    return command_output.stdout.decode('utf-8')
