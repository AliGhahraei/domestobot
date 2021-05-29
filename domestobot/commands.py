#!/usr/bin/env python3
from pathlib import Path

from typer import Context, Typer

from domestobot.context_objects import AppObject, ContextObject
from domestobot.routines import GIT_DIR

app = Typer(context_settings={'obj': AppObject()})


class TypedContext(Context):
    obj: 'ContextObject'


@app.callback(invoke_without_command=True)
def main(ctx: TypedContext, gitdir: Path = Path(GIT_DIR)) -> None:
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
def upgrade_fisher(ctx: TypedContext) -> None:
    """Upgrade Fish package manager (Linux only)."""
    ctx.obj.upgrade_fisher(ctx.obj)


@app.command()
def upgrade_os(ctx: TypedContext) -> None:
    """Upgrade using native package manager (Homebrew/Arch's Paru only)."""
    ctx.obj.upgrade_os(ctx.obj)


@app.command()
def upgrade_python_tools(ctx: TypedContext) -> None:
    """Upgrade Pipx tool and packages."""
    ctx.obj.upgrade_python_tools(ctx.obj)


@app.command()
def upgrade_doom(ctx: TypedContext) -> None:
    """Upgrade Doom Emacs distribution."""
    ctx.obj.upgrade_doom(ctx.obj)


@app.command()
def check_repos_clean(ctx: TypedContext, gitdir: Path = Path(GIT_DIR)) \
        -> None:
    """Check if repos in gitdir have unpublished work."""
    ctx.obj.check_repos_clean(ctx.obj, gitdir)
