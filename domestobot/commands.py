#!/usr/bin/env python3
from typer import Context, Typer

from domestobot.context_objects import AppObject, ContextObject

app = Typer(context_settings={'obj': AppObject()})


class TypedContext(Context):
    obj: 'ContextObject'


@app.callback(invoke_without_command=True)
def main(ctx: TypedContext) -> None:
    """Your own trusty housekeeper.

    Run without specifying a command to run all subroutines.
    Run --help and the name of a command to get more information about it
    (e.g. `domestobot upgrade-doom --help`).
    """
    if ctx.invoked_subcommand is None:
        upgrade_fisher(ctx)
        upgrade_os(ctx)
        upgrade_python_tools(ctx)
        upgrade_doom(ctx)
        maintain_yadm(ctx)
        save_aconfmgr(ctx)
        maintain_repos(ctx)


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
def maintain_yadm(ctx: TypedContext) -> None:
    """check if yadm has unpublished work"""
    ctx.obj.fetch_yadm(ctx.obj)
    ctx.obj.check_yadm_clean(ctx.obj)


@app.command()
def save_aconfmgr(ctx: TypedContext) -> None:
    """Run `aconfmgr save`."""
    ctx.obj.save_aconfmgr(ctx.obj)


@app.command()
def maintain_repos(ctx: TypedContext) -> None:
    """Check if repos in config have unpublished work and fetch them."""
    ctx.obj.fetch_repos(ctx.obj, ctx.obj.config.repos)
    ctx.obj.check_repos_clean(ctx.obj, ctx.obj.config.repos)
