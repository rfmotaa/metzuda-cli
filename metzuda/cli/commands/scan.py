"""Implements the metzuda scan command."""

import json
from pathlib import Path

import click
import typer

from metzuda.cli.renderer import ErrorMessage, console, render_empty_scan, render_report, render_sarif, render_scan_start
from metzuda.core.scanner import Scanner
from metzuda.core.walker import walk
from metzuda.infra.auth import is_logged_in
from metzuda.infra.config import load_config
from metzuda.infra.state_manager import get_files_for_static_scan, load_state, save_report, save_state
from metzuda.models.finding import Severity

app = typer.Typer()


@app.command()
def scan(
    full: bool = typer.Option(False, "--full", help="Ignore cache and re-analyze all files"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Layer 1 (Semgrep) only — skip AI analysis"),
    path: str = typer.Option(".", "--path", help="Directory to scan [default: current directory]"),
    fail_on: str = typer.Option(
        "HIGH",
        "--fail-on",
        help="Minimum severity to fail with exit code 1: [bold]LOW | HIGH | CRITICAL[/bold]",
    ),
    output: str = typer.Option(
        "terminal",
        "--output",
        click_type=click.Choice(["terminal", "json", "sarif"], case_sensitive=False),
        help="Output format. [bold](terminal | json | sarif)[/bold]",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        click_type=click.Choice(["claude", "gemini"], case_sensitive=False),
        help="AI provider for Layer 2 analysis. Overrides server default. [bold](claude | gemini)[/bold]",
    ),
) -> None:
    """
    [bold green]Run[/bold green] the security scan pipeline on the current repository.

    Executes Layer 1 (Semgrep, always free) and, if logged in, Layer 2 (AI analysis).
    Only files that changed since the last scan are re-analyzed.

    [dim]Examples:[/dim]
      [cyan]metzuda scan[/cyan]                       — incremental scan
      [cyan]metzuda scan --full[/cyan]                — re-scan all files
      [cyan]metzuda scan --no-ai[/cyan]               — Layer 1 only (fast, no API)
      [cyan]metzuda scan --provider gemini[/cyan]     — use Gemini for Layer 2
      [cyan]metzuda scan --output sarif[/cyan]        — SARIF output for GitHub Security tab
    """
    target_path = Path(path)
    if not target_path.exists():
        ErrorMessage.display(f"Target path does not exist: {path}")
        raise typer.Exit(code=1)

    try:
        config = load_config()
    except FileNotFoundError:
        ErrorMessage.display("Config not found. Run: metzuda init")
        raise typer.Exit(code=1)

    try:
        threshold_sev = Severity(fail_on.upper())
    except ValueError:
        ErrorMessage.display(f"Invalid severity: {fail_on}. Must be LOW, HIGH, or CRITICAL.")
        raise typer.Exit(code=1)

    state = load_state()
    all_files = walk(Path(path), config.ignore_paths)
    files_to_scan = all_files if full else get_files_for_static_scan(all_files, state)

    scanner = Scanner(config)

    output_lower = output.lower()
    if files_to_scan and output_lower not in ("json", "sarif"):
        render_scan_start(len(files_to_scan))

    run_ai = not no_ai
    report, new_state = scanner.run(Path(path), state, full, run_ai, ai_provider=provider)
    save_state(new_state)
    save_report(report)

    if output_lower == "json":
        console.print(json.dumps(report.to_dict(), indent=2), highlight=False)
    elif output_lower == "sarif":
        print(render_sarif(report))
    else:
        if not files_to_scan:
            render_empty_scan()
        render_report(report)

        if run_ai:
            if not is_logged_in():
                console.print("[dim]ℹ Layer 2 (AI analysis) skipped — not logged in. Run: metzuda login[/dim]")
            elif config.plan and config.plan.lower() == "free":
                console.print("[dim]ℹ Layer 2 (AI analysis) requires a paid plan. Run: metzuda upgrade[/dim]")
            elif report.api_calls_made == 0 and files_to_scan:
                console.print("[dim]✓ AI analysis up to date — no changed files since last scan[/dim]")
            elif provider:
                console.print(f"[dim]✓ AI analysis performed using [bold]{provider}[/bold][/dim]")

    if not report.is_safe(threshold_sev):
        raise typer.Exit(code=1)
