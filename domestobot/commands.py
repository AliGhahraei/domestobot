#!/usr/bin/env python3
from os import listdir
from os.path import expanduser, join
from platform import system

from sh import git, doom, fish, pipx, ErrorReturnCode_128
from typer import Context, Typer

from domestobot.core import info, task_title, title, warning


_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT = '->'
GIT_DIR = expanduser(join('~', 'g'))

app = Typer()


@app.callback(invoke_without_command=True)
def main(ctx: Context):
    """Your own trusty housekeeper.

    Run without specifying a command to perform all upgrades and check repos.
    Run --help and the name of a command to get more information about it
    (e.g. `domestobot upgrade-doom --help`).
    """
    if ctx.invoked_subcommand is None:
        upgrade_fisher()
        upgrade_os()
        upgrade_python_tools()
        upgrade_doom()
        check_repos_clean()


@app.command()
def upgrade_fisher():
    """Upgrade Fish package manager (Linux only)."""
    if system() == 'Linux':
        title('Upgrading fisher')
        fish('-c', 'fisher update', _fg=True)


@app.command()
def upgrade_os():
    """Upgrade using native package manager (Homebrew/Arch's Paru only)."""
    def get_macos_commands():
        from sh import brew

        @task_title('Upgrading with brew')
        def upgrade_macos():
            brew('update', _fg=True)
            brew('upgrade', _fg=True)

        return upgrade_macos

    def get_arch_linux_commands():
        from sh import paru

        @task_title('Upgrading with paru')
        def upgrade_arch():
            paru(_fg=True)

        return upgrade_arch

    os_upgrade_commands = {
        'Darwin': get_macos_commands,
        'Linux': get_arch_linux_commands,
    }
    current_platform = system()
    try:
        upgrade_os = os_upgrade_commands[current_platform]()
    except KeyError:
        def upgrade_os():
            warning(f"Package managers for {current_platform} aren't"
                    f"supported")
    upgrade_os()


@app.command()
def upgrade_python_tools():
    """Upgrade Pipx tool and packages."""
    title('Upgrading pipx and packages')
    pipx('upgrade-all', _fg=True)


@app.command()
def upgrade_doom():
    """Upgrade Doom Emacs distribution."""
    title('Upgrading doom')
    doom('upgrade', _fg=True)


@app.command()
def check_repos_clean(gitdir: str = GIT_DIR):
    """Check if repos in gitdir (~/g by default) have unpublished work."""
    def is_tree_dirty(dir_):
        try:
            unsaved_changes = git('-C', dir_, 'status',
                                  '--ignore-submodules', '--porcelain')
            unpushed_commits = git('-C', dir_, 'log', '--branches',
                                       '--not', '--remotes', '--oneline')
        except ErrorReturnCode_128 as e:
            raise ValueError(f'Invalid repository: {dir_}') from e

        is_dirty = any([
            decode_output(unsaved_changes),
            is_not_empty_ignoring_escape_sequences(unpushed_commits),
        ])
        return is_dirty

    def decode_output(output):
        return output.stdout.decode('utf-8')

    def is_not_empty_ignoring_escape_sequences(unpushed_commits_output):
        return (_SUBSTRING_ALWAYS_PRESENT_IN_NON_EMPTY_OUTPUT
                in decode_output(unpushed_commits_output))

    title('Checking git repos')
    all_repos = [join(gitdir, repo) for repo in listdir(gitdir)]
    dirty_repos = [repo for repo in all_repos if is_tree_dirty(repo)]
    if dirty_repos:
        for repo in dirty_repos:
            warning(f"{repo}'s tree was not clean")
    else:
        info("Everything's clean!")
