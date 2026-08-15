"""Implements the Anthropic-based semantic analyzer for Metzuda."""

import os
import json
from pathlib import Path
from metzuda.analyzers.base import BaseAnalyzer
from metzuda.models.finding import Finding, Severity, Source

SECURITY_SYSTEM_PROMPT = """
You are a security code reviewer specializing in vulnerabilities introduced by
AI coding tools (Cursor, Claude Code, GitHub Copilot).

Your task: analyze the provided code snippet and identify security vulnerabilities
that static analysis tools commonly miss in AI-generated code:
- IDOR (Insecure Direct Object Reference): endpoint returns data without verifying
  the requested ID belongs to the authenticated user
- Missing authentication: route exists but no auth check before accessing data
- Business logic flaws: auth check exists but is incorrectly implemented
- Async race conditions: shared state modified without proper synchronization
- Privilege escalation: user can access resources belonging to other users

The code has already been flagged by static analysis for: {static_finding_type}

Return ONLY a valid JSON object. No markdown, no explanation outside the JSON.
If you find no additional vulnerabilities beyond what static analysis found, return:
{{"vulnerabilities": [], "assessment": "No additional issues found."}}

Required JSON schema:
{{
  "vulnerabilities": [
    {{
      "type": "IDOR|MISSING_AUTH|BUSINESS_LOGIC|RACE_CONDITION|PRIVILEGE_ESCALATION",
      "severity": "CRITICAL|HIGH|LOW",
      "line": <integer>,
      "explanation": "<plain English, 1-2 sentences, no jargon>",
      "confidence": "HIGH|MEDIUM|LOW"
    }}
  ],
  "assessment": "<1-2 sentence overall summary>"
}}
"""

class SemanticAnalyzer(BaseAnalyzer):
    def __init__(self):
        # Import here to avoid hard dependency when not using AI
        try:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
            self._available = True
        except (ImportError, Exception):
            self._available = False

    def is_available(self) -> bool:
        return self._available and bool(os.environ.get("ANTHROPIC_API_KEY"))

    def analyze(self, files: list[Path], static_findings: list[Finding] = None) -> list[Finding]:
        # files here are only the ones flagged CRITICAL/HIGH by static analyzer
        # The scanner.py is responsible for this filtering
        findings = []
        static_findings = static_findings or []
        
        # Group static findings by file to pass the most severe one
        findings_by_file = {}
        for sf in static_findings:
            findings_by_file.setdefault(sf.file, []).append(sf)

        for f in files:
            try:
                # Find relative path matching f.file
                try:
                    rel_path = str(f.relative_to(Path.cwd()))
                except ValueError:
                    rel_path = str(f)
                
                file_static_findings = findings_by_file.get(rel_path, [])
                most_severe = None
                if file_static_findings:
                    severity_scores = {
                        Severity.CRITICAL: 3,
                        Severity.HIGH: 2,
                        Severity.LOW: 1
                    }
                    most_severe = max(file_static_findings, key=lambda sf: severity_scores.get(sf.severity, 0))
                
                findings.extend(self._analyze_file(f, most_severe))
            except Exception as e:
                # NEVER crash the scan — log and continue
                import sys
                print(f"[metzuda] semantic analysis skipped for {f}: {e}", file=sys.stderr)
        return findings

    def _analyze_file(self, file: Path, static_finding: Finding = None) -> list[Finding]:
        context = self._extract_context(file, static_finding)
        
        finding_type = static_finding.type if static_finding else "UNKNOWN"
        system = SECURITY_SYSTEM_PROMPT.format(static_finding_type=finding_type)
        
        response = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": context}]
        )
        
        raw = response.content[0].text.strip()
        # Strip markdown fences if model wraps in ```json
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            if raw.endswith("```"):
                raw = raw[:-3].strip()
        
        data = json.loads(raw.strip())
        
        results = []
        for i, v in enumerate(data.get("vulnerabilities", [])):
            if v.get("confidence") == "LOW":
                continue  # skip low confidence to reduce false positives
            
            try:
                vuln_severity = Severity(v["severity"])
            except ValueError:
                vuln_severity = Severity.HIGH
                
            results.append(Finding(
                id=f"MTZ-SEM-{i+1:03d}",
                type=v["type"],
                severity=vuln_severity,
                source=Source.SEMANTIC,
                file=str(file),
                line=v.get("line", static_finding.line if static_finding else 0),
                explanation=v.get("explanation", ""),
            ))
        return results

    def _extract_context(self, file: Path, finding: Finding = None, max_lines: int = 100) -> str:
        lines = file.read_text(errors="replace").splitlines()
        
        if not finding or len(lines) <= max_lines:
            code = "\n".join(lines)
        else:
            center = finding.line - 1  # 0-indexed
            half = max_lines // 2
            start = max(0, center - half)
            end = min(len(lines), center + half)
            code = "\n".join(lines[start:end])
            header = f"# Lines {start+1}-{end} of {len(lines)} total\n"
            code = header + code
        
        prefix = f"# File: {file}\n"
        if finding:
            prefix += f"# Static analysis flagged: {finding.type} at line {finding.line}\n"
        prefix += "\n"
        
        return prefix + code
