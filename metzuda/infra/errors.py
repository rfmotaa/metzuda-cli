"""
metzuda/infra/errors.py

Re-exports de metzuda.exceptions para compatibilidade retroativa.
Novos módulos devem importar diretamente de metzuda.exceptions.
"""

# Re-export para manter compatibilidade com imports existentes
from metzuda.exceptions import (  # noqa: F401
    MetzudaError,
    NetworkError,
    UnauthorizedError,
    QuotaExceededError,
    ConfigError,
    SemgrepNotFoundError,
    RateLimitError,
)
