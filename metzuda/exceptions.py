"""
metzuda/exceptions.py

Hierarquia de exceções tipadas do Metzuda.
Todas as exceções de negócio devem herdar de MetzudaError.
A CLI captura essas exceções e exibe mensagens amigáveis ao usuário.
"""


class MetzudaError(Exception):
    """Classe base para todos os erros do Metzuda."""


class NetworkError(MetzudaError):
    """Falha de conexão com a API Metzuda."""


class UnauthorizedError(MetzudaError):
    """Token inválido, expirado ou ausente. Usuário precisa fazer login."""


class QuotaExceededError(MetzudaError):
    """Quota mensal de AI scans atingida. Usuário precisa fazer upgrade."""


class ConfigError(MetzudaError):
    """Configuração local ausente ou inválida. Usuário precisa rodar metzuda init."""


class SemgrepNotFoundError(MetzudaError):
    """Semgrep não está instalado ou não está no PATH."""


class RateLimitError(MetzudaError):
    """Limite de taxa da API excedido. Tentar novamente em breve."""
