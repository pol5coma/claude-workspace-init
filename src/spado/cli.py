"""Typer entry point for SPADO."""

from __future__ import annotations

from typing import Annotated

import typer

from spado import __version__

app = typer.Typer(
    name="spado",
    help="SPADO: configure agentic organizations, workflows and shared project knowledge.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


from spado.commands.catalog import catalog_app  # noqa: E402

app.add_typer(catalog_app, name="catalog")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"spado {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show the SPADO version."),
    ] = False,
) -> None:
    """Software Product Agentic Development Organization."""


def main() -> None:
    app()


from spado.runtime.commands import register  # noqa: E402

register(app)
