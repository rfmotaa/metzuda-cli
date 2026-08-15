"""Implements the metzuda fix command."""

import json
from pathlib import Path
from typing import Optional

import pyperclip
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from metzuda.cli.renderer import ErrorMessage, console, render_fix_prompt
from metzuda.core.prompt_builder import build_fix_prompt
from metzuda.models.finding import Severity
from metzuda.models.report import ScanReport

_SEV_STYLE = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "yellow",
    Severity.LOW: "dim",
}


def _load_report() -> ScanReport:
    path = Path.cwd() / ".metzuda" / "last-report.json"
    if not path.exists():
        ErrorMessage.display("No scan report found. Run: metzuda scan")
        raise typer.Exit(code=1)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ScanReport.from_dict(data)
    except Exception:
        ErrorMessage.display("Scan report is invalid or corrupted. Run: metzuda scan")
        raise typer.Exit(code=1)


def _show_findings_table(findings: list) -> None:
    """Prints a compact findings table to help the user pick one."""
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("#", style="dim", width=3)
    table.add_column("ID", style="cyan", width=9)
    table.add_column("Sev", width=8)
    table.add_column("File", overflow="fold", max_width=48)
    table.add_column("Line", width=5)
    table.add_column("Type")

    for idx, f in enumerate(findings, 1):
        sev_style = _SEV_STYLE.get(f.severity, "white")
        table.add_row(
            str(idx),
            f.id,
            f"[{sev_style}]{f.severity.value}[/{sev_style}]",
            f.file,
            str(f.line),
            f.type,
        )
    console.print(table)


def _interactive_select(findings: list):
    """Renders findings table and prompts user to pick one by ID or number."""
    _show_findings_table(findings)
    console.print()

    id_map = {f.id.upper(): f for f in findings}
    num_map = {str(i): f for i, f in enumerate(findings, 1)}

    while True:
        answer = Prompt.ask(
            "[bold]Select finding[/bold] (ID or number, e.g. [cyan]MTZ-001[/cyan] or [cyan]1[/cyan])",
        ).strip()

        if not answer:
            raise typer.Exit(code=0)

        target = id_map.get(answer.upper()) or num_map.get(answer)
        if target:
            return target

        console.print(f"[yellow]Not found: {answer!r}. Try again or press Ctrl+C to cancel.[/yellow]")


def fix(
    finding_id: Optional[str] = typer.Argument(
        None,
        help="The specific finding ID (e.g. MTZ-001). If omitted, an interactive menu is shown.",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all generated fix prompts at once.",
    ),
    no_copy: bool = typer.Option(
        False,
        "--no-copy",
        help="Display the fix prompt in the terminal but do not copy it to the clipboard.",
    ),
) -> None:
    """
    [bold green]View[/bold green] and copy the LLM fix prompt for a security finding.

    Paste the prompt directly into [bold]Cursor[/bold], [bold]Claude Code[/bold], or any AI assistant.

    [dim]Examples:[/dim]
      [cyan]metzuda fix[/cyan]            — interactive menu to pick a finding
      [cyan]metzuda fix MTZ-001[/cyan]    — direct access to a specific finding
      [cyan]metzuda fix --all[/cyan]      — show all fix prompts at once
    """
    report = _load_report()

    if not report.findings:
        console.print("[dim]No findings in last scan report.[/dim]")
        return

    # -- --all: show every finding --
    if show_all:
        prompts = []
        for f in report.findings:
            p = f.fix_prompt or build_fix_prompt(f)
            render_fix_prompt(f.id, p)
            prompts.append(p)

        if not no_copy:
            all_text = "\n\n".join(prompts)
            try:
                pyperclip.copy(all_text)
                console.print(f"[green]✓[/green] All {len(prompts)} fix prompts copied to clipboard.")
            except Exception:
                console.print("[yellow]Warning: Clipboard not available.[/yellow]")
        return

    # -- specific ID passed as argument --
    if finding_id:
        id_upper = finding_id.upper()
        target = next((f for f in report.findings if f.id.upper() == id_upper), None)
        if not target:
            ErrorMessage.display(
                f"Finding [bold]{finding_id}[/bold] not found.\n"
                "Run [bold]metzuda fix[/bold] (no args) to see all findings interactively."
            )
            raise typer.Exit(code=1)
    else:
        # -- no argument: interactive menu --
        console.print("\n[bold]Findings from last scan:[/bold]\n")
        target = _interactive_select(report.findings)

    prompt = target.fix_prompt or build_fix_prompt(target)
    console.print()
    render_fix_prompt(target.id, prompt)

    if not no_copy:
        try:
            pyperclip.copy(prompt)
            console.print("[green]✓[/green] Fix prompt copied to clipboard.")
        except Exception:
            console.print("[yellow]Warning: Clipboard not available.[/yellow]")
