"""Implements the metzuda billing command."""

import webbrowser
import typer

from metzuda.cli.renderer import console
from metzuda.infra.auth import is_logged_in
from metzuda.infra.backend_client import BackendClient

app = typer.Typer()


@app.command()
def billing() -> None:
    """
    [bold green]Open Stripe Customer Portal[/bold green] to manage your subscription.
    """
    if not is_logged_in():
        console.print("[red]✗[/red] You are not logged in. Run [bold]metzuda login[/bold] first.")
        raise typer.Exit(code=1)

    client = BackendClient()

    with console.status("  Opening billing portal..."):
        try:
            result = client.open_billing_portal()
        except Exception:
            console.print("[red]✗[/red] No active subscription found.")
            console.print("  Run [bold]metzuda upgrade[/bold] to start a plan.")
            raise typer.Exit(code=1)

    url = result.get("url")
    if not url:
        console.print("[red]✗[/red] Failed to open billing portal.")
        raise typer.Exit(code=1)

    console.print(f"\n  [dim]→ {url}[/dim]")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    console.print()
    console.print("  [green]✓[/green] Browser opened — Stripe Customer Portal.")
    console.print("    Manage your plan, update payment method, or cancel.")
    console.print()
