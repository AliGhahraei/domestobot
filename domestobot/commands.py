#!/usr/bin/env python3
from typer import Context, Typer

from domestobot.context_objects import AppObject, ContextObject


def main() -> None:
    get_app(AppObject())()


def get_app(context_object: ContextObject) -> Typer:
    app = Typer()
    steps = context_object.get_steps()

    for step in steps:
        app.command()(step)

    @app.callback(invoke_without_command=True)
    def main(ctx: Context) -> None:
        """Your own trusty housekeeper.

        Run without specifying a command to run all subroutines.
        Run --help and the name of a command to get more information about it
        (e.g. `domestobot upgrade-doom --help`).
        """
        if ctx.invoked_subcommand is None:
            for step in steps:
                step()

    return app
