"""Generates Claude/Cursor fix prompts for severe findings."""

from metzuda.models.finding import Finding


def build_fix_prompt(finding: Finding) -> str:
    """Generates a Cursor/Claude Code ready prompt for fixing the vulnerability."""
    if finding.fix_prompt:
        return finding.fix_prompt

    file_part = f"In file {finding.file}, line {finding.line}"
    type_part = f"fix the vulnerability {finding.type}"
    explanation_part = f"{finding.explanation}" if finding.explanation else "Review and resolve this issue."

    prompt = f"{file_part}, {type_part}: {explanation_part}"

    if finding.code_snippet:
        prompt += f"\n\nRelevant code:\n```\n{finding.code_snippet}\n```"

    return prompt


def update_findings_prompts(findings: list[Finding]) -> None:
    """Fills fix_prompt for all findings."""
    for finding in findings:
        finding.fix_prompt = build_fix_prompt(finding)
