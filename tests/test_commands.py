#!/usr/bin/env python3
from pathlib import Path
from subprocess import CalledProcessError, CompletedProcess
from typing import List, Optional, Protocol, Tuple, Union
from unittest.mock import Mock, call, patch

from click.testing import Result
from pytest import FixtureRequest, fixture
from typer.testing import CliRunner

from domestobot.commands import app

LINUX = 'Linux'
DARWIN = 'Darwin'
UNKNOWN_OS = 'Unknown OS'


class Invoker(Protocol):
    def __call__(*args: str, runner: Optional[Mock] = None) -> Result:
        pass


@fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@fixture
def command_runner() -> Mock:
    return Mock()


@fixture
def invoke(cli_runner: CliRunner, request: FixtureRequest) -> Invoker:
    def _run(*args: str, runner: Optional[Mock] = None) -> Result:
        runner = runner or request.getfixturevalue('command_runner')
        return cli_runner.invoke(app, args, obj=runner)
    return _run


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


def assert_upgrading_fisher_message_shown(stdout: str) -> None:
    assert 'Upgrading fisher' in stdout


def assert_upgrading_paru_message_shown(stdout: str) -> None:
    assert 'Upgrading with paru' in stdout


def assert_upgrading_python_tools_message_shown(stdout: str) -> None:
    assert 'Upgrading pipx and packages' in stdout


def assert_upgrading_doom_message_shown(stdout: str) -> None:
    assert 'Upgrading doom' in stdout


def assert_clean_message_shown(stdout: str) -> None:
    assert "Everything's clean!" in stdout


def assert_repo_not_clean(repo: Path, stdout: str) -> None:
    assert f"Repository in {repo} was not clean" in stdout


def get_unsaved_changes_args(repo: Path) -> Tuple[Union[str, Path], ...]:
    return 'git', '-C', repo, 'status', '--ignore-submodules', '--porcelain'


def get_unpushed_commits_args(repo: Path) -> Tuple[Union[str, Path], ...]:
    return ('git', '-C', repo, 'log', '--branches', '--not', '--remotes',
            '--oneline')


@patch('domestobot.commands.system', return_value=LINUX)
def test_main(system_mock: Mock, invoke: Invoker, command_runner: Mock,
              repo1: Path, tmp_path: Path) -> None:
    runner = Mock(return_value=CompletedProcess([], 0, b''))
    result = invoke('--gitdir', str(tmp_path), runner=runner)
    assert_upgrading_fisher_message_shown(result.stdout)
    assert_upgrading_paru_message_shown(result.stdout)
    assert_upgrading_python_tools_message_shown(result.stdout)
    assert_upgrading_doom_message_shown(result.stdout)
    assert_clean_message_shown(result.stdout)
    assert result.exit_code == 0


class TestUpgradeFisher:
    @staticmethod
    @patch('domestobot.commands.system', return_value=LINUX)
    def test_upgrade_runs_on_linux(system_mock: Mock, invoke: Invoker,
                                   command_runner: Mock) -> None:
        result = invoke('upgrade-fisher')
        assert_upgrading_fisher_message_shown(result.stdout)
        command_runner.assert_called_once_with('fish', '-c', 'fisher update')
        assert result.exit_code == 0

    @staticmethod
    @patch('domestobot.commands.system', return_value=DARWIN)
    def test_upgrade_does_nothing_on_darwin(system_mock: Mock, invoke: Invoker,
                                            command_runner: Mock) -> None:
        result = invoke('upgrade-fisher')
        assert not result.stdout
        command_runner.assert_not_called()
        assert result.exit_code == 0


class TestUpgradeOs:
    @staticmethod
    @patch('domestobot.commands.system', return_value=LINUX)
    def test_upgrade_uses_paru_on_linux(system_mock: Mock, invoke: Invoker,
                                        command_runner: Mock) -> None:
        result = invoke('upgrade-os')
        assert_upgrading_paru_message_shown(result.stdout)
        command_runner.assert_called_once_with('paru')
        assert result.exit_code == 0

    @staticmethod
    @patch('domestobot.commands.system', return_value=DARWIN)
    def test_upgrade_uses_brew_on_darwin(system_mock: Mock, invoke: Invoker,
                                         command_runner: Mock) -> None:
        result = invoke('upgrade-os')
        assert 'Upgrading with brew' in result.stdout
        command_runner.assert_has_calls([call('brew', 'update'),
                                         call('brew', 'upgrade')])
        assert result.exit_code == 0

    @staticmethod
    @patch('domestobot.commands.system', return_value=UNKNOWN_OS)
    def test_upgrade_says_unsupported_without_running_commands_in_unknown_os(
            system_mock: Mock, invoke: Invoker, command_runner: Mock
    ) -> None:
        result = invoke('upgrade-os')
        warning = f"Package managers for {UNKNOWN_OS} aren't supported"
        assert warning in result.stdout
        command_runner.assert_not_called()
        assert result.exit_code == 0


def test_upgrade_python_tools(invoke: Invoker, command_runner: Mock) -> None:
    result = invoke('upgrade-python-tools')
    assert_upgrading_python_tools_message_shown(result.stdout)
    command_runner.assert_called_once_with('pipx', 'upgrade-all')
    assert result.exit_code == 0


def test_upgrade_doom(invoke: Invoker, command_runner: Mock) -> None:
    result = invoke('upgrade-doom')
    assert_upgrading_doom_message_shown(result.stdout)
    command_runner.assert_called_once_with('doom', 'upgrade')
    assert result.exit_code == 0


class TestCheckReposClean:
    @staticmethod
    def test_check_says_checking_repos_on_empty_gitdir(
        invoke: Invoker, command_runner: Mock, tmp_path: Path
    ) -> None:
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path))
        assert 'Checking git repos' in result.stdout

    @staticmethod
    def test_check_says_clean_without_running_commands_on_empty_gitdir(
        invoke: Invoker, command_runner: Mock, tmp_path: Path
    ) -> None:
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path))
        assert_clean_message_shown(result.stdout)
        command_runner.assert_not_called()
        assert result.exit_code == 0

    @staticmethod
    def test_check_says_clean_on_clean_repos(
        invoke: Invoker, tmp_path: Path, repos: List[Path]
    ) -> None:
        runner = Mock(side_effect=[CompletedProcess([], 0, b'')
                                   for _ in range(len(repos) * 2)])
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path),
                        runner=runner)
        for repo in repos:
            runner.assert_has_calls([
                call(*get_unsaved_changes_args(repo), capture_output=True),
                call(*get_unpushed_commits_args(repo), capture_output=True),
            ])
        assert_clean_message_shown(result.stdout)
        assert result.exit_code == 0

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unsaved_changes(
            invoke: Invoker, tmp_path: Path, repo1: Path,
    ) -> None:
        runner = Mock(side_effect=[CompletedProcess([], 0, b'M  fake_file')])
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path),
                        runner=runner)
        runner.assert_called_once_with(*get_unsaved_changes_args(repo1),
                                       capture_output=True)
        assert_repo_not_clean(repo1, result.stdout)
        assert result.exit_code == 0

    @staticmethod
    def test_check_says_not_clean_on_repos_with_unpushed_commits(
            invoke: Invoker, tmp_path: Path, repo1: Path,
    ) -> None:
        runner = Mock(side_effect=[
            CompletedProcess([], 0, b''),
            CompletedProcess([], 0,
                             b'a9a152e (HEAD -> main) Create fake commit'),
        ])
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path),
                        runner=runner)
        runner.assert_has_calls([
            call(*get_unsaved_changes_args(repo1), capture_output=True),
            call(*get_unpushed_commits_args(repo1), capture_output=True),
        ])
        assert_repo_not_clean(repo1, result.stdout)
        assert result.exit_code == 0

    @staticmethod
    def test_check_exits_with_not_a_repo_error_on_invalid_repo(
            invoke: Invoker, tmp_path: Path, repo1: Path,
    ) -> None:
        runner = Mock(side_effect=CalledProcessError(128, 'command'))
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path),
                        runner=runner)
        runner.assert_called_once_with(*get_unsaved_changes_args(repo1),
                                       capture_output=True)
        assert result.exit_code == 1
        assert f'Not a git repository: {repo1}' in result.stdout

    @staticmethod
    def test_check_reraises_unhandled_error(
            invoke: Invoker, tmp_path: Path, repo1: Path,
    ) -> None:
        exception = CalledProcessError(1, 'command')
        runner = Mock(side_effect=exception)
        result = invoke('check-repos-clean', '--gitdir', str(tmp_path),
                        runner=runner)
        runner.assert_called_once_with(*get_unsaved_changes_args(repo1),
                                       capture_output=True)
        assert result.exception == exception
