"""
metzuda/analyzers/static.py

Layer 1: Semgrep static analyzer.
Carrega todas as regras de metzuda/rules/ e converte resultados em Finding objects.
"""

import json
from pathlib import Path
import shutil
import subprocess

from metzuda.analyzers.base import BaseAnalyzer
from metzuda.models.finding import Finding, Severity, Source


# Mapeamento de fragmentos de check_id para tipo de finding legível
_TYPE_MAP: list[tuple[str, str]] = [
    # Existentes
    ("sql", "SQL_INJECTION"),
    ("secret", "HARDCODED_SECRET"),
    ("cors", "CORS_WILDCARD"),
    ("eval", "EVAL"),
    # Autenticação e sessão
    ("auth", "AUTH"),
    ("session", "SESSION"),
    ("cookie", "INSECURE_COOKIE"),
    ("csrf", "CSRF"),
    ("login-no-rate", "RATE_LIMIT"),
    ("rate-limit", "RATE_LIMIT"),
    ("lockout", "ACCOUNT_LOCKOUT"),
    ("no-account-lockout", "ACCOUNT_LOCKOUT"),
    ("password-reset-no-rate", "RATE_LIMIT"),
    ("session-not-regen", "SESSION_FIXATION"),
    ("session-not-invalidated", "SESSION_FIXATION"),
    # Senhas e hashing
    ("plaintext-password", "PLAINTEXT_PASSWORD"),
    ("weak-hash", "WEAK_HASH"),
    ("weak-password-hash", "WEAK_HASH"),
    # Controle de acesso
    ("idor", "IDOR"),
    ("mass-assignment", "MASS_ASSIGNMENT"),
    ("auth-from-client", "BROKEN_AUTH"),
    ("auth-from-request", "BROKEN_AUTH"),
    ("user-enumeration", "USER_ENUMERATION"),
    ("reset-token-no-expiry", "INSECURE_RESET_TOKEN"),
    ("reset-token-expiry", "INSECURE_RESET_TOKEN"),
    ("no-reset-token-expiry", "INSECURE_RESET_TOKEN"),
    # Validação e XSS
    ("no-input-validation", "MISSING_INPUT_VALIDATION"),
    ("xss", "XSS"),
    ("innerhtml", "XSS"),
    ("dangerouslysetinnerhtml", "XSS"),
    ("unsanitized", "UNSANITIZED_INPUT"),
    ("no-request-size", "MISSING_SIZE_LIMIT"),
    ("no-max-content", "MISSING_SIZE_LIMIT"),
    ("no-max-upload", "MISSING_SIZE_LIMIT"),
    ("unsanitized-html", "XSS"),
    # Uploads
    ("unrestricted-file-upload", "UNRESTRICTED_UPLOAD"),
    ("file-upload-no-extension", "UNRESTRICTED_UPLOAD"),
    ("file-upload-no-mimetype", "UNRESTRICTED_UPLOAD"),
    ("file-upload", "UNRESTRICTED_UPLOAD"),
    # Respostas / exposição de dados
    ("password-in-api", "SENSITIVE_DATA_EXPOSURE"),
    ("password-in-response", "SENSITIVE_DATA_EXPOSURE"),
    ("sensitive-field-in-response", "SENSITIVE_DATA_EXPOSURE"),
    ("sensitive-field-exposed", "SENSITIVE_DATA_EXPOSURE"),
    ("sensitive-field", "SENSITIVE_DATA_EXPOSURE"),
    # Headers e infra
    ("no-helmet", "MISSING_SECURITY_HEADERS"),
    ("no-talisman", "MISSING_SECURITY_HEADERS"),
    ("spring-no-security-headers", "MISSING_SECURITY_HEADERS"),
    ("http-server", "INSECURE_HTTP"),
    ("no-https-redirect", "INSECURE_HTTP"),
    ("no-hsts", "MISSING_HSTS"),
    ("spring-no-hsts", "MISSING_HSTS"),
    ("directory-listing", "DIRECTORY_LISTING"),
    ("default-admin-route", "EXPOSED_ADMIN"),
    ("admin-route", "EXPOSED_ADMIN"),
    ("spring-csrf-disabled", "CSRF"),
    # Pagamentos e AI
    ("stripe-webhook", "UNVERIFIED_WEBHOOK"),
    ("price-from-client", "CLIENT_SIDE_PRICING"),
    ("prompt-injection", "PROMPT_INJECTION"),
    ("ai-no-usage", "UNCAPPED_AI_USAGE"),
    ("no-security-logging", "MISSING_SECURITY_LOGGING"),
    # Runtime code exec
    ("runtime-exec", "COMMAND_INJECTION"),
    # Python específicos
    ("jinja2-autoescape", "XSS"),
    ("flask-markup", "XSS"),
    ("flask-session", "INSECURE_SESSION"),
    ("flask-debug", "DEBUG_ENABLED"),
    ("bare-except", "SWALLOWED_EXCEPTION"),
    ("no-csrf-protection", "CSRF"),
    ("cors-wildcard", "CORS_WILDCARD"),
]


def _map_type(check_id: str) -> str:
    """Maps Semgrep check IDs to Metzuda finding types."""
    check_lower = check_id.lower()
    for fragment, finding_type in _TYPE_MAP:
        if fragment in check_lower:
            return finding_type
    return "STATIC_VULNERABILITY"


def _map_severity(semgrep_sev: str, check_id: str) -> Severity:
    """
    Maps Semgrep severity + metadata to Metzuda Severity.

    Priority order:
    1. Rule metadata metzuda-severity (via check_id naming convention)
    2. Semgrep severity field
    """
    check_lower = check_id.lower()

    # CRITICAL patterns — any of these is always CRITICAL regardless of Semgrep severity
    critical_fragments = (
        "plaintext-password", "weak-hash", "mass-assignment",
        "auth-from-client", "stripe-webhook", "price-from-client",
        "password-in-api", "sensitive-field", "xss-innerhtml",
        "jinja2-autoescape", "flask-debug", "hardcoded-secret",
        "sql-concat",
    )
    if any(f in check_lower for f in critical_fragments):
        return Severity.CRITICAL

    # Semgrep ERROR → HIGH
    if semgrep_sev.upper() == "ERROR":
        return Severity.HIGH

    # Semgrep WARNING → HIGH
    if semgrep_sev.upper() == "WARNING":
        return Severity.HIGH

    # Semgrep INFO → LOW
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
