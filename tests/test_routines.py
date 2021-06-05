#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import List, Tuple, Union
from unittest.mock import Mock, call

from asserts import assert_stdout
from pytest import CaptureFixture, fixture, raises

from domestobot.routines import (check_repos_clean, check_yadm_clean,
                                 fetch_repos, fetch_yadm)

MODULE_UNDER_TEST = 'domestobot.routines'
DARWIN = 'Darwin'
LINUX = 'Linux'
UNKNOWN_OS = 'Unknown OS'


@fixture
def repo1() -> Path:
    return Path('repo1')


@fixture
def repos(repo1: Path) -> List[Path]:
    return [repo1, Path('repo2')]


@fixture
def clean_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b'')


@fixture
def unsaved_changes_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b'M  fake_file')


@fixture
def unpushed_commits_output() -> CompletedProcess[bytes]:
    return CompletedProcess([], 0, b'a9a152e (HEAD -> main) Create fake '
                            b'commit')


def assert_repo_not_clean(repo: Path, capsys: CaptureFixture[str]) -> None:
    assert_stdout(f"Repository in {repo} was not clean", capsys)


def assert_clean_message_shown(capsys: CaptureFixture[str]) -> None:
    assert_stdout("Everything's clean!", capsys)


def get_command_prefix_for_unpushed_commits() -> Tuple[str, ...]:
    return 'log', '--branches', '--not', '--remotes', '--oneline'


def get_unpushed_commits_args(repo: Path) -> Tuple[Union[str, Path], ...]:
    return ('git', '-C', repo, *get_command_prefix_for_unpushed_commits())


def get_command_prefix_for_unsaved_changes() -> Tuple[str, ...]:
    return 'status', '--ignore-submodules', '--porcelain'


def get_unsaved_changes_args(repo: Path) -> Tuple[Union[str, Path], ...]:
    return 'git', '-C', repo, *get_command_prefix_for_unsaved_changes()


class TestFetchYadm:
    @staticmethod
    def test_fetch_shows_fetching_yadm_message(
            runner: Mock, capsys: CaptureFixture[str]
    ) -> None:
        fetch_yadm(runner)
        assert_stdout('Fetching yadm', capsys)

    @staticmethod
    def test_fetch_runs_fetch(
            runner: Mock, capsys: CaptureFixture[str]
    ) -> None:
        fetch_yadm(runner)
        runner.run.assert_called_once_with('yadm', 'fetch')


class TestCheckYadmClean:
    @staticmethod
    def test_check_shows_checking_yadm_message(
            runner: Mock, capsys: CaptureFixture[str]
    ) -> None:
        check_yadm_clean(runner)
        assert_stdout('Checking yadm', capsys)

    @staticmethod
    def test_check_shows_not_clean_on_yadm_with_unsaved_changes(
            runner: Mock, capsys: CaptureFixture[str],
            unsaved_changes_output: CompletedProcess[bytes]
    ) -> None:
        runner = Mock(side_effect=[unsaved_changes_output])
        check_yadm_clean(runner)
        runner.run.assert_called_once_with(
            'yadm', *get_command_prefix_for_unsaved_changes(),
            capture_output=True,
        )
        assert_stdout('Yadm was not clean', capsys)

    @staticmethod
    def test_check_shows_not_clean_on_yadm_with_unpushed_commits(
        runner: Mock, capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes]
    ) -> None:
        runner.run = Mock(side_effect=[clean_output, unpushed_commits_output])
        check_yadm_clean(runner)
        runner.run.assert_has_calls([
            call('yadm', *get_command_prefix_for_unsaved_changes(),
                 capture_output=True),
            call('yadm', *get_command_prefix_for_unpushed_commits(),
                 capture_output=True),
        ])
        assert_stdout('Yadm was not clean', capsys)

    @staticmethod
    def test_check_shows_clean_on_clean_yadm(
        runner: Mock, capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
    ) -> None:
        runner.run = Mock(side_effect=[clean_output] * 2)
        check_yadm_clean(runner)
        runner.run.assert_has_calls([
            call('yadm', *get_command_prefix_for_unsaved_changes(),
                 capture_output=True),
            call('yadm', *get_command_prefix_for_unpushed_commits(),
                 capture_output=True),
        ])
        assert_stdout('Yadm was clean!', capsys)


class TestFetchRepos:
    @staticmethod
    def test_fetch_shows_fetching_repos_message(
            runner: Mock, repos: List[Path], capsys: CaptureFixture[str],
    ) -> None:
        fetch_repos(runner, repos)
        assert_stdout('Fetching repos', capsys)

    @staticmethod
    def test_fetch_is_run_for_every_repo(runner: Mock, repos: List[Path]) \
            -> None:
        fetch_repos(runner, repos)
        runner.run.assert_has_calls([
            call('git', '-C', repo, 'fetch') for repo in repos
        ])


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
        runner.assert_not_called()

    @staticmethod
    def test_check_says_clean_on_clean_repos(
        runner: Mock, repos: List[Path], capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes]
    ) -> None:
        runner.run = Mock(side_effect=[clean_output
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
        unsaved_changes_output: CompletedProcess[bytes]
    ) -> None:
        runner = Mock(side_effect=[unsaved_changes_output])
        check_repos_clean(runner, [repo1])
        runner.run.assert_called_once_with(
            *get_unsaved_changes_args(repo1), capture_output=True,
        )
        assert_repo_not_clean(repo1, capsys)

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unpushed_commits(
        runner: Mock, repo1: Path, capsys: CaptureFixture[str],
        clean_output: CompletedProcess[bytes],
        unpushed_commits_output: CompletedProcess[bytes],
    ) -> None:
        runner.run = Mock(side_effect=[clean_output, unpushed_commits_output])
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
