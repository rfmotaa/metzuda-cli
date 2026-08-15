"""Implements the metzuda config command."""

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from metzuda.infra.config import load_config, save_config
from metzuda.models.finding import Severity

console = Console()


def config(
    severity: str = typer.Option(
        None,
        "--severity",
        click_type=click.Choice(["LOW", "HIGH", "CRITICAL", "NONE"], case_sensitive=False),
        help="Minimum severity to break CI (exit code 1). [bold](LOW | HIGH | CRITICAL | NONE)[/bold]",
    ),
    lang: str = typer.Option(
        None,
        "--lang",
        click_type=click.Choice(["auto", "javascript", "python", "java"], case_sensitive=False),
        help="Set the primary language for this project. [bold](auto | javascript | python | java)[/bold]",
    ),
    ai: str = typer.Option(
        None,
        "--ai",
        click_type=click.Choice(["on", "off"], case_sensitive=False),
        help="Enable or disable Layer 2 AI analysis. [bold](on | off)[/bold]",
    ),
) -> None:
    """
    [bold green]View or update[/bold green] Metzuda project settings in [blue].metzuda/config.yml[/blue].

    Running without options prints the current configuration.

    [dim]Examples:[/dim]
      [cyan]metzuda config[/cyan]                 — show current config
      [cyan]metzuda config --severity HIGH[/cyan] — break CI on HIGH or CRITICAL findings
      [cyan]metzuda config --lang python[/cyan]   — set project language
      [cyan]metzuda config --ai off[/cyan]        — disable AI analysis (Layer 2)
    """
    try:
        cfg = load_config()
    except FileNotFoundError:
        from metzuda.cli.renderer import ErrorMessage
        ErrorMessage.display("Config not found. Run: metzuda init")
        raise typer.Exit(code=1)

    changed = False

    if severity is not None:
        cfg.severity_threshold = Severity(severity.upper())
        changed = True

    if lang is not None:
        detected = lang.lower()
        if detected == "auto":
            # Re-run auto-detection
            from metzuda.cli.commands.init import detect_language
            detected = detect_language()
            console.print(f"[dim]Auto-detected language: [cyan]{detected}[/cyan][/dim]")
        cfg.language = detected
        changed = True

    if ai is not None:
        cfg.ai_analysis = ai.lower() == "on"
        changed = True

    if changed:
        save_config(cfg)
        console.print("[green]✓[/green] Config updated.")

    # Always display current config (after any changes)
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="bold white", width=28)
    table.add_column("Value")

    ai_val = ("[green]on[/green]" if cfg.ai_analysis else "[red]off[/red]")
    logged_val = ("[green]Yes[/green]" if cfg.logged_in else "[yellow]No[/yellow]")

    table.add_row("Language", f"[cyan]{cfg.language}[/cyan]")
    table.add_row("CI Severity Threshold", f"[cyan]{cfg.severity_threshold.value}[/cyan]")
    table.add_row("AI Analysis (Layer 2)", ai_val)
    table.add_row("Max Context Lines", f"[cyan]{cfg.max_context_lines}[/cyan]")
    table.add_row("", "")
    table.add_row("Logged In", logged_val)
    table.add_row("Login Method", f"[cyan]{cfg.login_method}[/cyan]")
    table.add_row("User Email", f"[cyan]{cfg.email or 'N/A'}[/cyan]")

    console.print()
    console.print(Panel(table, title="[bold cyan]Metzuda Config[/bold cyan]", expand=False))
    console.print()
