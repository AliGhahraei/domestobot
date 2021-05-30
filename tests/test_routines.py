#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import List, Tuple, Union
from unittest.mock import Mock, call, patch

from asserts import assert_no_stdout, assert_stdout
from pytest import CaptureFixture, fixture, raises

from domestobot.routines import (CommandRunner, check_repos_clean,
                                 upgrade_doom, upgrade_fisher, upgrade_os,
                                 upgrade_python_tools)

MODULE_UNDER_TEST = 'domestobot.routines'
DARWIN = 'Darwin'
LINUX = 'Linux'
UNKNOWN_OS = 'Unknown OS'


@fixture
def runner() -> Mock:
    return Mock(spec_set=CommandRunner)


@fixture
def repo1(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo1'
    repo.mkdir()
    return repo


@fixture
def repos(repo1: Path, tmp_path: Path) -> List[Path]:
    repo2 = tmp_path / 'repo2'
    repo2.mkdir()
    return [repo1, repo2]


def assert_repo_not_clean(repo: Path, capsys: CaptureFixture[str]) -> None:
    assert_stdout(f"Repository in {repo} was not clean", capsys)


def assert_clean_message_shown(capsys: CaptureFixture[str]) -> None:
    assert_stdout("Everything's clean!", capsys)


def get_unpushed_commits_args(repo: Path) -> Tuple[Union[str, Path], ...]:
    return ('git', '-C', repo, 'log', '--branches', '--not', '--remotes',
            '--oneline')


def get_unsaved_changes_args(repo: Path) -> Tuple[Union[str, Path], ...]:
    return 'git', '-C', repo, 'status', '--ignore-submodules', '--porcelain'


class TestUpgradeFisher:
    @staticmethod
    @patch(f'{MODULE_UNDER_TEST}.system', return_value=LINUX)
    def test_upgrade_runs_on_linux(_: Mock, runner: Mock,
                                   capsys: CaptureFixture[str]) -> None:
        upgrade_fisher(runner)
        assert_stdout('Upgrading fisher', capsys)
        runner.run.assert_called_once_with('fish', '-c', 'fisher update')

    @staticmethod
    @patch(f'{MODULE_UNDER_TEST}.system', return_value=DARWIN)
    def test_upgrade_does_nothing_on_darwin(_: Mock, runner: Mock,
                                            capsys: CaptureFixture[str]) \
            -> None:
        upgrade_fisher(runner)
        assert_no_stdout(capsys)
        runner.run.assert_not_called()


class TestUpgradeOs:
    @staticmethod
    @patch(f'{MODULE_UNDER_TEST}.system', return_value=LINUX)
    def test_upgrade_uses_paru_on_linux(_: Mock, runner: Mock,
                                        capsys: CaptureFixture[str]) -> None:
        upgrade_os(runner)
        assert_stdout('Upgrading with paru', capsys)
        runner.run.assert_called_once_with('paru')

    @staticmethod
    @patch(f'{MODULE_UNDER_TEST}.system', return_value=DARWIN)
    def test_upgrade_uses_brew_on_darwin(_: Mock, runner: Mock,
                                         capsys: CaptureFixture[str]) -> None:
        upgrade_os(runner)
        assert_stdout('Upgrading with brew', capsys)
        runner.run.assert_has_calls([call('brew', 'update'),
                                     call('brew', 'upgrade')])

    @staticmethod
    @patch(f'{MODULE_UNDER_TEST}.system', return_value=UNKNOWN_OS)
    def test_upgrade_says_unsupported_without_running_commands_in_unknown_os(
            _: Mock, runner: Mock, capsys: CaptureFixture[str]
    ) -> None:
        upgrade_os(runner)
        assert_stdout(f"Package managers for {UNKNOWN_OS} aren't supported",
                      capsys)
        runner.run.assert_not_called()


def test_upgrade_python_tools(runner: Mock,
                              capsys: CaptureFixture[str]) -> None:
    upgrade_python_tools(runner)
    assert_stdout('Upgrading pipx and packages', capsys)
    runner.run.assert_called_once_with('pipx', 'upgrade-all')


def test_upgrade_doom(runner: Mock, capsys: CaptureFixture[str]) -> None:
    upgrade_doom(runner)
    assert_stdout('Upgrading doom', capsys)
    runner.run.assert_called_once_with('doom', 'upgrade')


class TestCheckReposClean:
    @staticmethod
    def test_check_says_checking_repos_with_no_repos(
        runner: Mock, capsys: CaptureFixture[str],
    ) -> None:
        check_repos_clean(runner, [])
        assert_stdout('Checking git repos', capsys)

    @staticmethod
    def test_check_says_no_repos_without_running_commands_with_no_repos(
        runner: Mock, capsys: CaptureFixture[str],
    ) -> None:
        check_repos_clean(runner, [])
        assert_stdout("No repos to check", capsys)
        runner.run.assert_not_called()

    @staticmethod
    def test_check_says_clean_on_clean_repos(
        runner: Mock, repos: List[Path], capsys: CaptureFixture[str],
    ) -> None:
        runner.run = Mock(side_effect=[CompletedProcess([], 0, b'')
                                       for _ in range(len(repos) * 2)])
        check_repos_clean(runner, repos)
        for repo in repos:
            runner.run.assert_has_calls([
                call(*get_unsaved_changes_args(repo), capture_output=True),
                call(*get_unpushed_commits_args(repo), capture_output=True),
            ])
        assert_clean_message_shown(capsys)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unsaved_changes(
        runner: Mock, repo1: Path, capsys: CaptureFixture[str],
    ) -> None:
        completed_process = CompletedProcess([], 0, b'M  fake_file')
        runner.run = Mock(side_effect=[completed_process])
        check_repos_clean(runner, [repo1])
        runner.run.assert_called_once_with(
            *get_unsaved_changes_args(repo1), capture_output=True,
        )
        assert_repo_not_clean(repo1, capsys)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unpushed_commits(
        runner: Mock, repo1: Path, capsys: CaptureFixture[str],
    ) -> None:
        runner.run = Mock(side_effect=[
            CompletedProcess([], 0, b''),
            CompletedProcess([], 0,
                             b'a9a152e (HEAD -> main) Create fake commit'),
        ])
        check_repos_clean(runner, [repo1])
        runner.run.assert_has_calls([
            call(*get_unsaved_changes_args(repo1), capture_output=True),
            call(*get_unpushed_commits_args(repo1), capture_output=True),
        ])
        assert_repo_not_clean(repo1, capsys)

    @staticmethod
    def test_check_exits_with_not_a_repo_error_on_invalid_repo(
        runner: Mock, repo1: Path,
    ) -> None:
        runner.run = Mock(side_effect=CalledProcessError(128, 'command'))
        with raises(SystemExit, match=f'Not a git repository: {repo1}'):
            check_repos_clean(runner, [repo1])
        runner.run.assert_called_once_with(
            *get_unsaved_changes_args(repo1), capture_output=True,
        )

    @staticmethod
    def test_check_reraises_unhandled_error(runner: Mock, repo1: Path) -> None:
        exception = CalledProcessError(1, 'command')
        runner.run = Mock(side_effect=exception)
        message = "Command 'command' returned non-zero exit status 1."
        with raises(CalledProcessError, match=message):
            check_repos_clean(runner, [repo1])
        runner.run.assert_called_once_with(
            *get_unsaved_changes_args(repo1), capture_output=True
        )
