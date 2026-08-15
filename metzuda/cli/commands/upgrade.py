"""Implements the metzuda upgrade command."""

import webbrowser
import typer
from rich import box
from rich.console import Console
from rich.table import Table

from metzuda.cli.renderer import console
from metzuda.infra.auth import is_logged_in
from metzuda.infra.backend_client import BackendClient

app = typer.Typer()

PLANS = {
    "solo": {"label": "Solo", "price": "$9/mo", "scans": "50", "desc": "para devs solo"},
    "dev": {"label": "Dev", "price": "$19/mo", "scans": "200", "desc": "um scan por PR"},
    "team": {"label": "Team", "price": "$59/mo", "scans": "1.000", "desc": "CI/CD completo com AI"},
}


@app.command()
def upgrade() -> None:
    """
    [bold green]Upgrade[/bold green] your Metzuda plan via Stripe checkout.
    """
    if not is_logged_in():
        console.print("[red]✗[/red] You are not logged in. Run [bold]metzuda login[/bold] first.")
        raise typer.Exit(code=1)

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Bullet", style="bold cyan")
    table.add_column("Plan", style="bold white")
    table.add_column("Price", style="green")
    table.add_column("Scans/mo")
    table.add_column("Description", style="dim")

    for key, p in PLANS.items():
        table.add_row("●", p["label"], p["price"], p["scans"], p["desc"])

    console.print()
    console.print("  [bold]Plans available:[/bold]")
    console.print()
    console.print(table)

    choice = typer.prompt("  Select plan", default="Solo").strip().lower()
    if choice not in PLANS:
        console.print(f"[red]✗[/red] Invalid plan: {choice}. Choose Solo, Dev, or Team.")
        raise typer.Exit(code=1)

    plan_key = choice.upper()
    client = BackendClient()

    with console.status("  Opening Stripe checkout..."):
        try:
            result = client.create_checkout_session(plan=plan_key)
        except Exception as e:
            console.print(f"[red]✗[/red] Failed to create checkout session: {e}")
            raise typer.Exit(code=1)

    url = result.get("url")
    if not url:
        console.print("[red]✗[/red] Failed to create checkout session.")
        raise typer.Exit(code=1)

    console.print(f"\n  [dim]→ {url}[/dim]")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    console.print()
    console.print("  [green]✓[/green] Browser opened. Complete the checkout to activate your plan.")
    console.print("    After payment, run: [bold]metzuda status[/bold]")
    console.print()
