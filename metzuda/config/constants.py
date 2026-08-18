"""
metzuda/config/constants.py

Constantes do projeto — limites, timeouts, extensões suportadas.
Nenhum módulo deve usar magic numbers ou magic strings — importe daqui.
"""

from typing import Final

PLAN_LIMITS: Final[dict[str, dict[str, int]]] = {
    "FREE":  {"scans_per_month": 0},
    "SOLO":  {"scans_per_month": 50},
    "DEV":   {"scans_per_month": 200},
    "TEAM":  {"scans_per_month": 1_000},
}

MAX_FILES_PER_SCAN: Final[int] = 30
MAX_FILE_SIZE_BYTES: Final[int] = 100_000
OAUTH_CALLBACK_TIMEOUT_SECONDS: Final[int] = 120
HTTP_TIMEOUT_SECONDS: Final[int] = 120
SEMGREP_CHUNK_SIZE: Final[int] = 100

SUPPORTED_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".kt"}
)

HASH_PREFIX: Final[str] = "sha256:"
