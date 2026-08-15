"""Provides rendering functions for Metzuda CLI output using Rich."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from metzuda.models.finding import Severity
from metzuda.models.report import ScanReport

console = Console()

def render_report(report: ScanReport) -> None:
    """Renders a detailed scan report as a formatted Rich table."""
    summary = report.summary()

    if report.findings:
        table = Table(title="Metzuda Security Scan Findings")
        table.add_column("ID", style="cyan")
        table.add_column("Severity")
        table.add_column("File")
        table.add_column("Line")
        table.add_column("Type")

        severity_styles = {
            Severity.CRITICAL: "bold red",
            Severity.HIGH: "yellow",
            Severity.LOW: "dim",
        }

        for finding in report.findings:
            sev_style = severity_styles.get(finding.severity, "white")
            table.add_row(
                finding.id,
                f"[{sev_style}]{finding.severity.value}[/{sev_style}]",
                finding.file,
                str(finding.line),
                finding.type,
            )

        console.print(table)
        console.print()

    # Summary line
    console.print(f"{summary.critical} critical · {summary.high} high · {summary.low} low")

    # Load config to get severity_threshold
    from metzuda.infra.config import load_config
    try:
        cfg = load_config()
        severity_threshold = cfg.severity_threshold
    except Exception:
        severity_threshold = Severity.HIGH

    is_safe = report.is_safe(severity_threshold)

    if is_safe:
        console.print("✓ Safe to deploy", style="green")
    else:
        console.print("✗ Not recommended for deploy", style="red")

def render_scan_start(file_count: int) -> None:
    """Renders scan start message."""
    console.print(f"→ Scanning {file_count} files...")

def render_scan_progress(current: int, total: int, filename: str) -> None:
    """Renders scan progress overwriting same line."""
    console.print(f"[{current}/{total}] Scanning {filename}...", end="\r")

def render_empty_scan() -> None:
    """Renders empty scan message when no changes are detected."""
    console.print("✓ No changes since last scan. Everything is up to date.", style="green")

class ErrorMessage:
    """Class representing a unified red-box formatted CLI error message."""
    @staticmethod
    def display(message: str) -> None:
        """Renders the error message inside a red panel to the console."""
        console.print(Panel(message, style="bold red", border_style="red", title="Error"))

def render_fix_prompt(finding_id: str, prompt: str) -> None:
    """Renders the fix prompt in a Rich Panel with finding_id as title."""
    console.print(Panel(prompt, title=finding_id))

def render_sarif(report: ScanReport) -> str:
    """Renders the scan report in SARIF v2.1.0 format."""
    import json
    
    # 1. Collect all rules
    rules_dict = {}
    for finding in report.findings:
        rule_id = finding.rule_id if finding.rule_id else finding.type
        if rule_id not in rules_dict:
            rules_dict[rule_id] = {
                "id": rule_id,
                "name": finding.type,
                "shortDescription": {"text": finding.type},
                "help": {"text": finding.explanation},
                "properties": {"problem.severity": finding.severity.value}
            }
    rules = list(rules_dict.values())

    # 2. Build results
    results = []
    level_map = {
        Severity.CRITICAL: "error",
        Severity.HIGH: "warning",
        Severity.LOW: "note"
    }
    for finding in report.findings:
        rule_id = finding.rule_id if finding.rule_id else finding.type
        level = level_map.get(finding.severity, "note")
        
        results.append({
            "ruleId": rule_id,
            "message": {"text": finding.explanation},
            "level": level,
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": finding.file},
                        "region": {"startLine": finding.line}
                    }
                }
            ]
        })

    # 3. Construct SARIF dict
    sarif_data = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Metzuda",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/rfmota/metzuda",
                        "rules": rules
                    }
                },
                "results": results
            }
        ]
    }
    return json.dumps(sarif_data, indent=2)
