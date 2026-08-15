"""Implements the Semgrep static analyzer for Metzuda."""

import json
from pathlib import Path
import shutil
import subprocess

from metzuda.analyzers.base import BaseAnalyzer
from metzuda.models.finding import Finding, Severity, Source


def _map_type(check_id: str) -> str:
    """Maps Semgrep check IDs to Metzuda finding types."""
    check_id_lower = check_id.lower()
    if "sql-injection" in check_id_lower:
        return "SQL_INJECTION"
    if "secret" in check_id_lower:
        return "HARDCODED_SECRET"
    if "auth" in check_id_lower:
        return "AUTH"
    if "cors" in check_id_lower:
        return "CORS_WILDCARD"
    if "eval" in check_id_lower:
        return "EVAL"
    return "STATIC_VULNERABILITY"


def _map_severity(semgrep_sev: str, check_id: str) -> Severity:
    """Maps Semgrep severities and rule IDs to Metzuda Severity levels."""
    sev_upper = semgrep_sev.upper()
    check_lower = check_id.lower()
    if "gravissimo" in check_lower or "critical" in check_lower:
        return Severity.CRITICAL
    if sev_upper == "ERROR":
        return Severity.HIGH
    return Severity.LOW


# Sentinel values returned by some Semgrep versions when the match
# is produced by metavariable-regex rules (no literal match text available).
_SEMGREP_PLACEHOLDER_LINES = {"requires login", "requires login\n", ""}


def _read_file_snippet(path_str: str, line: int, context: int = 2) -> str:
    """Reads a real code snippet from the source file around the given line."""
    try:
        source = Path(path_str).read_text(encoding="utf-8", errors="replace").splitlines()
        start = max(0, line - 1 - context)
        end = min(len(source), line + context)
        return "\n".join(source[start:end])
    except Exception:
        return ""


class StaticAnalyzer(BaseAnalyzer):
    """Static analyzer wrapper for Semgrep CLI."""

    def is_available(self) -> bool:
        """Checks if the semgrep command-line tool is installed and available."""
        return shutil.which("semgrep") is not None

    def analyze(self, files: list[Path]) -> list[Finding]:
        """Runs Semgrep static analysis on a list of files."""
        if not files:
            return []

        if not self.is_available():
            # If Semgrep is missing, return empty findings gracefully
            return []

        rules_dir = Path(__file__).parent.parent / "rules"

        findings = []
        chunk_size = 100
        for i in range(0, len(files), chunk_size):
            chunk = files[i : i + chunk_size]
            cmd = (
                ["semgrep", "--config", str(rules_dir), "--json", "--no-git-ignore", "--quiet"]
                + [str(f) for f in chunk]
            )
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False, encoding="utf-8"
                )
            except Exception:  # pylint: disable=broad-exception-caught
                continue

            if not result.stdout:
                continue

            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                continue

            for raw in data.get("results", []):
                check_id = raw.get("check_id", "unknown-rule")
                path_str = raw.get("path", "")
                try:
                    rel_path = str(Path(path_str).relative_to(Path.cwd()))
                except ValueError:
                    rel_path = path_str

                start = raw.get("start", {})
                line = start.get("line", 1)
                col = start.get("col", 0)

                extra = raw.get("extra", {})
                message = extra.get("message", "")
                severity_str = extra.get("severity", "WARNING")
                semgrep_lines = extra.get("lines", "").strip()

                # Some Semgrep versions return a placeholder string instead of
                # the real matched code when metavariable-regex rules are used.
                # Fall back to reading the snippet directly from the source file.
                if semgrep_lines in _SEMGREP_PLACEHOLDER_LINES:
                    code_snippet = _read_file_snippet(path_str, line)
                else:
                    code_snippet = semgrep_lines

                findings.append(
                    Finding(
                        id="",  # Will be assigned sequentially by Aggregator
                        type=_map_type(check_id),
                        severity=_map_severity(severity_str, check_id),
                        source=Source.STATIC,
                        file=rel_path,
                        line=line,
                        column=col,
                        rule_id=check_id,
                        explanation=message,
                        code_snippet=code_snippet,
                        fix_prompt="",  # Will be built by PromptBuilder
                    )
                )

        return findings
