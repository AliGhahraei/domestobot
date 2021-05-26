#!/usr/bin/env python3
from pathlib import Path
from platform import system
from subprocess import CalledProcessError, CompletedProcess
from sys import exit
from typing import Callable, Protocol, Union

from typer import Context, Typer

from domestobot.core import AppObject, info, task_title, title, warning

_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT = '->'
GIT_DIR = Path.home() / 'g'

app = Typer(context_settings={'obj': AppObject()})


class RunnerContext(Context):
    obj: 'CommandRunner'


class CommandRunner(Protocol):
    def run(self, *args: Union[str, Path], capture_output: bool = False) \
      -> CompletedProcess[bytes]:
        pass


@app.callback(invoke_without_command=True)
def main(ctx: RunnerContext, gitdir: Path = Path(GIT_DIR)) -> None:
    """Your own trusty housekeeper.

    Run without specifying a command to perform all upgrades and check repos.
    Run --help and the name of a command to get more information about it
    (e.g. `domestobot upgrade-doom --help`).
    """
    if ctx.invoked_subcommand is None:
        upgrade_fisher(ctx)
        upgrade_os(ctx)
        upgrade_python_tools(ctx)
        upgrade_doom(ctx)
        check_repos_clean(ctx, gitdir)


@app.command()
def upgrade_fisher(ctx: RunnerContext) -> None:
    """Upgrade Fish package manager (Linux only)."""
    if system() == 'Linux':
        title('Upgrading fisher')
        ctx.obj.run('fish', '-c', 'fisher update')


@app.command()
def upgrade_os(ctx: RunnerContext) -> None:
    """Upgrade using native package manager (Homebrew/Arch's Paru only)."""
    def get_macos_commands() -> Callable[[], None]:
        @task_title('Upgrading with brew')
        def upgrade_macos() -> None:
            ctx.obj.run('brew', 'update')
            ctx.obj.run('brew', 'upgrade')

        return upgrade_macos

    def get_arch_linux_commands() -> Callable[[], None]:
        @task_title('Upgrading with paru')
        def upgrade_arch() -> None:
            ctx.obj.run('paru')

        return upgrade_arch

    os_upgrade_commands = {
        'Darwin': get_macos_commands,
        'Linux': get_arch_linux_commands,
    }
    current_platform = system()
    try:
        upgrade_os = os_upgrade_commands[current_platform]()
    except KeyError:
        def upgrade_os() -> None:
            warning(f"Package managers for {current_platform} aren't"
                    f" supported")
    upgrade_os()


@app.command()
def upgrade_python_tools(ctx: RunnerContext) -> None:
    """Upgrade Pipx tool and packages."""
    title('Upgrading pipx and packages')
    ctx.obj.run('pipx', 'upgrade-all')


@app.command()
def upgrade_doom(ctx: RunnerContext) -> None:
    """Upgrade Doom Emacs distribution."""
    title('Upgrading doom')
    ctx.obj.run('doom', 'upgrade')


@app.command()
def check_repos_clean(ctx: RunnerContext, gitdir: Path = Path(GIT_DIR)) \
        -> None:
    """Check if repos in gitdir have unpublished work."""
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
        unsaved_changes = ctx.obj.run(
            'git', '-C', dir_, 'status', '--ignore-submodules', '--porcelain',
            capture_output=True,
        )
        return bool(_decode(unsaved_changes))

    def _has_unpushed_commits(dir_: Path) -> bool:
        unpushed_commits = ctx.obj.run(
            'git', '-C', dir_, 'log', '--branches', '--not', '--remotes',
            '--oneline', capture_output=True,
        )
        return (_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT
                in _decode(unpushed_commits))

    def _decode(command_output: CompletedProcess[bytes]) -> str:
        return command_output.stdout.decode('utf-8')

    title('Checking git repos')
    dirty_repos = [repo for repo in gitdir.iterdir() if is_tree_dirty(repo)]
    if dirty_repos:
        for repo in dirty_repos:
            warning(f"Repository in {repo} was not clean")
    else:
        info("Everything's clean!")
