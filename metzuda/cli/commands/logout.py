"""Implements the metzuda logout command."""

import typer

from metzuda.cli.renderer import ErrorMessage, console


app = typer.Typer()


@app.command()
def logout() -> None:
    """Remove stored credentials."""
    from metzuda.infra.auth import is_logged_in, logout as do_logout

    if not is_logged_in():
        console.print("[dim]Not logged in.[/dim]")
        return

    try:
        do_logout()
        console.print("[green]✓[/green] Logged out.")
    except Exception as e:
        ErrorMessage.display(f"Failed to logout: {e}")
        raise typer.Exit(code=1)
