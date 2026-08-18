"""
metzuda/services/upgrade_service.py

Orquestra o fluxo de upgrade de plano via Stripe.
Não imprime nada — retorna dados, lança exceções tipadas.
"""

from metzuda.exceptions import NetworkError, QuotaExceededError, UnauthorizedError
from metzuda.infra.backend_client import BackendClient


def get_checkout_url(plan: str) -> str:
    """
    Cria uma sessão de checkout Stripe para o plano especificado.

    Args:
        plan: Nome do plano em maiúsculas ('SOLO' | 'DEV' | 'TEAM').

    Returns:
        URL da sessão de checkout Stripe.

    Raises:
        UnauthorizedError: Usuário não autenticado.
        NetworkError: Falha de conexão com a API.
        ValueError: URL não retornada pela API.
    """
    client = BackendClient()
    result = client.create_checkout_session(plan=plan)
    url = result.get("url")
    if not url:
        raise ValueError("Failed to create checkout session: no URL returned.")
    return url


def get_portal_url() -> str:
    """
    Abre o portal de billing do Stripe para o usuário autenticado.

    Returns:
        URL do Stripe Customer Portal.

    Raises:
        UnauthorizedError: Usuário não autenticado.
        NetworkError: Falha de conexão com a API.
        ValueError: URL não retornada pela API.
    """
    client = BackendClient()
    result = client.open_billing_portal()
    url = result.get("url")
    if not url:
        raise ValueError("Failed to open billing portal: no URL returned.")
    return url
