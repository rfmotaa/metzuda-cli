"""Implements the metzuda report command."""

import json
from pathlib import Path

import click
import typer

from metzuda.cli.renderer import ErrorMessage, console, render_report
from metzuda.models.finding import Severity
from metzuda.models.report import ScanReport


def report(
    min_severity: str = typer.Option(
        "LOW",
        "--min-severity",
        click_type=click.Choice(["LOW", "HIGH", "CRITICAL"], case_sensitive=False),
        help=(
            "Minimum severity to display. "
            "[bold]LOW[/bold] = all, [bold]HIGH[/bold] = HIGH + CRITICAL, "
            "[bold]CRITICAL[/bold] = CRITICAL only. "
            "[bold](LOW | HIGH | CRITICAL)[/bold]"
        ),
    ),
    output: str = typer.Option(
        "terminal",
        "--output",
        click_type=click.Choice(["terminal", "json"], case_sensitive=False),
        help="Format for displaying the report. [bold](terminal | json)[/bold]",
    ),
) -> None:
    """
    [bold green]Display[/bold green] the findings from the last scan.

    Loads cached results from [blue].metzuda/last-report.json[/blue] and shows
    the vulnerabilities table, summary, and deployment verdict.

    [dim]Examples:[/dim]
      [cyan]metzuda report[/cyan]                     — show all findings
      [cyan]metzuda report --min-severity HIGH[/cyan] — show only HIGH and CRITICAL
      [cyan]metzuda report --output json[/cyan]       — JSON output for CI pipelines
    """
    path = Path.cwd() / ".metzuda" / "last-report.json"
    if not path.exists():
        ErrorMessage.display("No scan report found. Run: metzuda scan")
        raise typer.Exit(code=1)

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        rpt = ScanReport.from_dict(data)
    except Exception:
        ErrorMessage.display("Scan report is invalid or corrupted. Run: metzuda scan")
        raise typer.Exit(code=1)

    # Which severities to display (all_findings preserved for CI exit code)
    all_findings = list(rpt.findings)
    sev = Severity(min_severity.upper())

    if sev == Severity.LOW:
        displayed = all_findings                                   # all
    elif sev == Severity.HIGH:
        displayed = [f for f in all_findings if f.severity in (Severity.HIGH, Severity.CRITICAL)]
    else:  # CRITICAL
        displayed = [f for f in all_findings if f.severity == Severity.CRITICAL]

    rpt.findings = displayed

    if output.lower() == "json":
        console.print(json.dumps(rpt.to_dict(), indent=2), highlight=False)
    else:
        render_report(rpt)

    # Exit code is always based on ALL findings vs config threshold
    try:
        from metzuda.infra.config import load_config
        cfg = load_config()
        threshold = cfg.severity_threshold
    except Exception:
        threshold = Severity.HIGH

    full_report = ScanReport(
        scan_id=rpt.scan_id,
        timestamp=rpt.timestamp,
        findings=all_findings,
        files_scanned=rpt.files_scanned,
    )
    if not full_report.is_safe(threshold):
        raise typer.Exit(code=1)
