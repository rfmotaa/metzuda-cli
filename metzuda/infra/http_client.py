"""
metzuda/infra/http_client.py

Wrapper centralizado para todas as chamadas HTTP à Metzuda API.
Nenhuma outra camada deve usar httpx diretamente.
Lança exceções tipadas de metzuda.exceptions.
"""

import httpx

from metzuda.config.endpoints import endpoints
from metzuda.config.constants import HTTP_TIMEOUT_SECONDS
from metzuda.exceptions import NetworkError, QuotaExceededError, RateLimitError, UnauthorizedError
from metzuda.infra.auth import get_auth_header


def _get_headers(extra: dict | None = None) -> dict[str, str]:
    """Retorna headers padrão com Authorization se disponível."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    auth = get_auth_header()
    if auth:
        headers["Authorization"] = auth
    if extra:
        headers.update(extra)
    return headers


def _handle_response(resp: httpx.Response) -> dict:
    """Valida o status HTTP e retorna o JSON, ou lança exceção tipada."""
    if resp.status_code == 401:
        raise UnauthorizedError("Session expired. Run: metzuda login")
    if resp.status_code == 429:
        raise RateLimitError("Rate limit exceeded. Please wait and try again.")
    if resp.status_code == 402:
        raise QuotaExceededError("Quota exceeded. Run: metzuda upgrade")
    resp.raise_for_status()
    return resp.json()


def get(path: str, params: dict | None = None) -> dict:
    """
    GET autenticado para a Metzuda API.

    Args:
        path: Caminho completo da URL (use endpoints.<nome>).
        params: Query parameters opcionais.

    Returns:
        Resposta JSON como dict.

    Raises:
        NetworkError: Falha de conexão.
        UnauthorizedError: Token inválido.
        QuotaExceededError: Quota mensal excedida.
        RateLimitError: Rate limit da API.
    """
    try:
        resp = httpx.get(
            path,
            params=params,
            headers=_get_headers(),
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        raise NetworkError(f"Could not connect to {path}") from exc

    return _handle_response(resp)


def post(path: str, payload: dict | None = None) -> dict:
    """
    POST autenticado para a Metzuda API.

    Args:
        path: Caminho completo da URL (use endpoints.<nome>).
        payload: Body JSON opcional.

    Returns:
        Resposta JSON como dict.

    Raises:
        NetworkError: Falha de conexão.
        UnauthorizedError: Token inválido.
        QuotaExceededError: Quota mensal excedida.
        RateLimitError: Rate limit da API.
    """
    try:
        resp = httpx.post(
            path,
            json=payload or {},
            headers=_get_headers(),
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except httpx.RequestError as exc:
        raise NetworkError(f"Could not connect to {path}") from exc

    return _handle_response(resp)
