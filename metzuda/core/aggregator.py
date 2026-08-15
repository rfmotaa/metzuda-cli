"""Merges, deduplicates, and orders vulnerability findings."""

from metzuda.models.finding import Finding, Severity


def aggregate(static_findings: list[Finding], semantic_findings: list[Finding]) -> list[Finding]:
    """Merges, deduplicates, sorts, and indexes findings from both static and semantic analysis."""
    all_findings = list(static_findings) + list(semantic_findings)

    severity_order = {
        Severity.LOW: 0,
        Severity.HIGH: 1,
        Severity.CRITICAL: 2,
    }

    grouped = {}
    for finding in all_findings:
        key = (finding.file, finding.line, finding.type)
        if key not in grouped:
            grouped[key] = finding
        else:
            existing = grouped[key]
            if severity_order.get(finding.severity, 0) > severity_order.get(existing.severity, 0):
                grouped[key] = finding

    sorted_findings = sorted(
        grouped.values(),
        key=lambda f: (
            -severity_order.get(f.severity, 0),
            f.file,
            f.line,
        ),
    )

    final_findings = []
    for idx, finding in enumerate(sorted_findings, 1):
        finding.id = f"MTZ-{idx:03d}"
        final_findings.append(finding)

    return final_findings
