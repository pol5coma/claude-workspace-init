"""Typer entry point: `cwi init`."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from cwi import __version__
from cwi.domain.errors import CWIError, UserCancelled

app = typer.Typer(
    name="cwi",
    help="Claude Workspace Init: bootstrap a minimal, project-specific Claude Code workspace.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


from cwi.commands.catalog import catalog_app  # noqa: E402

app.add_typer(catalog_app, name="catalog")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"cwi {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show the CWI version."),
    ] = False,
) -> None:
    """Claude Workspace Init."""


@app.command()
def init(
    root: Annotated[
        Path | None,
        typer.Option("--root", help="Project root to initialize (default: current directory)."),
    ] = None,
    catalog: Annotated[
        Path | None,
        typer.Option("--catalog", help="CWI catalog directory to source capabilities from."),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Scan, plan and preview with default answers. Writes nothing."
        ),
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Accept every default and apply without prompts.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show debug logs and tracebacks.")
    ] = False,
) -> None:
    """Scan the project, propose a minimal Claude workspace, preview it, then apply it safely."""
    from cwi.commands.init import InitOptions, run_init
    from cwi.ui import render

    console = Console()
    if verbose:
        from rich.logging import RichHandler

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(message)s",
            handlers=[RichHandler(console=Console(stderr=True))],
        )
    try:
        run_init(
            InitOptions(
                root=root,
                catalog=catalog,
                dry_run=dry_run,
                yes=yes,
                verbose=verbose,
                console=console,
            )
        )
    except UserCancelled as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=1) from None
    except CWIError as exc:
        render.error(
            console, str(exc) + ("" if verbose else "\n\nRun with --verbose for technical details.")
        )
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1) from None
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted.[/yellow]")
        raise typer.Exit(code=130) from None
    except Exception as exc:  # noqa: BLE001 - last-resort clean message
        if verbose:
            console.print_exception()
        else:
            render.error(
                console, f"Unexpected error: {exc}\n\nRun with --verbose for technical details."
            )
        raise typer.Exit(code=2) from None


def main() -> None:
    app()
