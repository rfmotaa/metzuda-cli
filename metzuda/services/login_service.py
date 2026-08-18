"""
metzuda/services/login_service.py

Orquestra o fluxo de autenticação OAuth do CLI.
Constrói URLs de autenticação usando endpoints centralizados.
Não imprime nada — retorna dados, lança exceções tipadas.
"""

from metzuda.config.endpoints import endpoints
from metzuda.config.settings import settings


def build_oauth_url(provider: str, redirect_uri: str, state: str) -> str:
    """
    Constrói a URL de redirecionamento OAuth para o provider especificado.

    Args:
        provider: 'github' ou 'google'.
        redirect_uri: URI local de callback (servidor HTTP temporário).
        state: Token anti-CSRF gerado aleatoriamente.

    Returns:
        URL completa para abertura no browser.
    """
    base = endpoints.auth_github if provider == "github" else endpoints.auth_google
    return f"{base}?redirect_uri={redirect_uri}&state={state}"
