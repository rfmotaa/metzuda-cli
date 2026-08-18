"""
metzuda/infra/backend_client.py

Cliente HTTP para enviar requests de análise à Metzuda API.
Usa endpoints centralizados de metzuda.config.endpoints.
Lança exceções tipadas de metzuda.exceptions.
"""

from pathlib import Path
import uuid

import httpx

from metzuda.cli.renderer import console
from metzuda.config.endpoints import endpoints
from metzuda.config.settings import settings
from metzuda.exceptions import NetworkError, QuotaExceededError, RateLimitError, UnauthorizedError
from metzuda.infra.auth import get_auth_header, is_logged_in
from metzuda.models.finding import Finding, Severity, Source


class BackendClient:
    """
    Cliente para comunicação com a Metzuda API.

    Centraliza todas as chamadas HTTP autenticadas ao backend.
    A URL da API é lida de settings.api_url (configurável via METZUDA_API_URL).
    """

    def __init__(self, api_url: str | None = None) -> None:
        self.api_url = (api_url or settings.api_url).rstrip("/")

    def is_available(self) -> bool:
        """Retorna True se o usuário está autenticado e pode usar o backend."""
        return is_logged_in()

    def analyze(
        self,
        files: list[Path],
        static_findings: list[Finding] | None = None,
        architecture: str | None = None,
        architecture_changed: bool = False,
        language: str = "javascript",
        ai_provider: str | None = None,
    ) -> list[Finding]:
        """
        Envia arquivos para análise de AI no backend.

        Returns:
            Lista de findings encontrados pelo backend.

        Raises:
            QuotaExceededError: Quota mensal atingida.
            RateLimitError: Rate limit da API.
        """
        auth_header = get_auth_header()
        if not auth_header:
            return []

        if not files:
            return []

        project_files = []
        for f in files:
            try:
                rel_path = str(f.relative_to(Path.cwd()))
            except ValueError:
                rel_path = str(f)

            try:
                content = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            category = "other"
            name_lower = rel_path.lower()
            if "route" in name_lower:
                category = "routes"
            elif "controller" in name_lower:
                category = "controllers"
            elif "middleware" in name_lower:
                category = "middleware"
            elif "auth" in name_lower:
                category = "auth"
            elif "model" in name_lower:
                category = "models"
            elif "config" in name_lower:
                category = "config"
            elif "util" in name_lower:
                category = "utils"

            project_files.append({
                "path": rel_path,
                "content": content,
                "category": category,
                "priority": 1 if category in ("routes", "controllers") else 3,
            })

        if not project_files:
            return []

        converted_static = []
        if static_findings:
            for sf in static_findings:
                converted_static.append({
                    "file": sf.file,
                    "line": sf.line,
                    "type": sf.type,
                    "severity": sf.severity.value if hasattr(sf.severity, "value") else str(sf.severity),
                    "rule_id": sf.rule_id,
                })

        # Ensure language matches API schema enum
        valid_lang = language.lower()
        if valid_lang not in ("javascript", "typescript", "python", "java"):
            valid_lang = "javascript"

        payload: dict = {
            "scan_id": str(uuid.uuid4()),
            "language": valid_lang,
            "project_files": project_files,
            "static_findings": converted_static,
            "architecture": architecture,
            "architecture_changed": architecture_changed,
        }
        if ai_provider and ai_provider.lower() in ("claude", "gemini"):
            payload["ai_provider"] = ai_provider.lower()

        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    endpoints.analyze,
                    json=payload,
                    headers={"Authorization": auth_header},
                )
                response.raise_for_status()
                data = response.json()
                findings = []
                for i, f in enumerate(data.get("findings", []), 1):
                    try:
                        sev = Severity(f.get("severity", "HIGH").upper())
                    except ValueError:
                        sev = Severity.HIGH

                    findings.append(Finding(
                        id=f"MTZ-SEM-{i:03d}",
                        type=f.get("type", "UNKNOWN"),
                        severity=sev,
                        source=Source.SEMANTIC,
                        file=f.get("file", ""),
                        line=f.get("line", 0),
                        explanation=f.get("explanation", ""),
                    ))
                return findings
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                err_data: dict = {}
                try:
                    err_data = e.response.json()
                except Exception:
                    pass
                if err_data.get("error") == "QUOTA_EXCEEDED":
                    raise QuotaExceededError("AI quota exceeded for this month.")
                console.print("[yellow]⚠ Quota or rate limit exceeded. AI scan skipped.[/yellow]")
                raise RateLimitError("Rate limit exceeded.")
            elif e.response.status_code == 401:
                console.print("[yellow]⚠ Session expired. Run: metzuda login[/yellow]")
            return []
        except (QuotaExceededError, RateLimitError):
            raise
        except Exception:
            return []  # never crash the scan

    def create_checkout_session(self, plan: str) -> dict:
        """
        Cria uma sessão de checkout Stripe para o plano especificado.

        Raises:
            UnauthorizedError: Usuário não autenticado.
            NetworkError: Falha de conexão.
        """
        auth_header = get_auth_header()
        if not auth_header:
            raise UnauthorizedError("Not authenticated. Run: metzuda login")
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    endpoints.billing_checkout,
                    json={"plan": plan},
                    headers={"Authorization": auth_header},
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            raise NetworkError(f"Could not connect to {endpoints.billing_checkout}") from exc

    def open_billing_portal(self) -> dict:
        """
        Abre o portal de billing do Stripe para o usuário autenticado.

        Raises:
            UnauthorizedError: Usuário não autenticado.
            NetworkError: Falha de conexão.
        """
        auth_header = get_auth_header()
        if not auth_header:
            raise UnauthorizedError("Not authenticated. Run: metzuda login")
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    endpoints.billing_portal,
                    headers={"Authorization": auth_header},
                )
                response.raise_for_status()
                return response.json()
        except httpx.RequestError as exc:
            raise NetworkError(f"Could not connect to {endpoints.billing_portal}") from exc
