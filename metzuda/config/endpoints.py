"""
metzuda/config/endpoints.py

Todos os endpoints da API construídos a partir do settings.api_url.
Nunca use strings de URL hardcoded em outros módulos — use endpoints.<nome>.
"""

from metzuda.config.settings import settings


class Endpoints:
    """Centraliza todos os paths da Metzuda API. Instanciar via singleton `endpoints`."""

    @property
    def analyze(self) -> str:
        return f"{settings.api_url}/v1/analyze"

    @property
    def auth_github(self) -> str:
        return f"{settings.api_url}/auth/github"

    @property
    def auth_google(self) -> str:
        return f"{settings.api_url}/auth/google"

    @property
    def auth_done(self) -> str:
        return f"{settings.api_url}/auth/done"

    @property
    def api_keys(self) -> str:
        return f"{settings.api_url}/auth/api-keys"

    @property
    def billing_checkout(self) -> str:
        return f"{settings.api_url}/billing/checkout"

    @property
    def billing_portal(self) -> str:
        return f"{settings.api_url}/billing/portal"

    @property
    def users_me(self) -> str:
        return f"{settings.api_url}/users/me"

    @property
    def users_usage(self) -> str:
        return f"{settings.api_url}/users/me/usage"


# Singleton — importado por qualquer módulo que precise de uma URL
endpoints = Endpoints()
