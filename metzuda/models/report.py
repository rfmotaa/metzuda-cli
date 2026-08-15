"""Defines the ScanSummary and ScanReport models for security reports."""

from dataclasses import dataclass, field
from typing import Any

from metzuda.models.finding import Finding, Severity, Source


@dataclass
class ScanSummary:
    total: int
    critical: int
    high: int
    low: int
    files_scanned: int
    files_with_findings: int
    recommendation: str


@dataclass
class ScanReport:
    scan_id: str
    timestamp: str
    project: str = ""
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    api_calls_made: int = 0
    api_tokens_used: int = 0
    duration_seconds: float = 0.0
    git_commit: str = ""
    git_branch: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> 'ScanReport':
        """Reconstructs a ScanReport object from a dictionary representation."""
        findings_data = data.get("findings", [])
        findings = []
        for f in findings_data:
            findings.append(
                Finding(
                    id=f["id"],
                    type=f["type"],
                    severity=Severity(f["severity"]),
                    source=Source(f["source"]),
                    file=f["file"],
                    line=f["line"],
                    column=f.get("column", 0),
                    rule_id=f.get("rule_id"),
                    explanation=f.get("explanation", ""),
                    fix_prompt=f.get("fix_prompt", ""),
                    code_snippet=f.get("code_snippet", ""),
                )
            )
        return cls(
            scan_id=data["scan_id"],
            timestamp=data["timestamp"],
            project=data.get("project", ""),
            findings=findings,
            files_scanned=data.get("files_scanned", 0),
            api_calls_made=data.get("api_calls_made", 0),
            api_tokens_used=data.get("api_tokens_used", 0),
            duration_seconds=data.get("duration_seconds", 0.0),
            git_commit=data.get("git_commit", ""),
            git_branch=data.get("git_branch", ""),
        )

    def summary(self) -> ScanSummary:
        """Computes counts and generates a ScanSummary based on findings."""
        total = len(self.findings)
        critical = sum(1 for f in self.findings if f.severity == Severity.CRITICAL)
        high = sum(1 for f in self.findings if f.severity == Severity.HIGH)
        low = sum(1 for f in self.findings if f.severity == Severity.LOW)

        files_with_findings = len({f.file for f in self.findings if f.file})

        recommendation = "SAFE_TO_DEPLOY"
        if critical > 0 or high > 0:
            recommendation = "NOT_SAFE_FOR_DEPLOY"

        return ScanSummary(
            total=total,
            critical=critical,
            high=high,
            low=low,
            files_scanned=self.files_scanned,
            files_with_findings=files_with_findings,
            recommendation=recommendation,
        )

    def is_safe(self, threshold: Severity) -> bool:
        """Returns True if no finding has severity >= threshold.

        Severity order: LOW < HIGH < CRITICAL < NONE
        """
        order = {
            Severity.LOW: 0,
            Severity.HIGH: 1,
            Severity.CRITICAL: 2,
            Severity.NONE: 3,
        }
        threshold_val = order.get(threshold, 3)
        return all(order.get(f.severity, 0) < threshold_val for f in self.findings)

    def findings_by_severity(self, severity: Severity) -> list[Finding]:
        """Returns findings filtered by exact severity match."""
        return [f for f in self.findings if f.severity == severity]

    def to_dict(self) -> dict[str, Any]:
        """Returns a JSON-serializable dict of the full report including summary."""
        return {
            "scan_id": self.scan_id,
            "timestamp": self.timestamp,
            "project": self.project,
            "findings": [f.__dict__ for f in self.findings],
            "files_scanned": self.files_scanned,
            "api_calls_made": self.api_calls_made,
            "api_tokens_used": self.api_tokens_used,
            "duration_seconds": self.duration_seconds,
            "git_commit": self.git_commit,
            "git_branch": self.git_branch,
            "summary": self.summary().__dict__,
        }
