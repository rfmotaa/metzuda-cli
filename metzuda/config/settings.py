"""
metzuda/config/settings.py

Settings singleton lido do ambiente.
Nenhum módulo deve usar os.getenv() diretamente — importe settings aqui.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Configurações imutáveis lidas do ambiente na inicialização."""

    api_url: str
    env: str
    credentials_file: Path
    metzuda_dir: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            api_url=os.getenv("METZUDA_API_URL", "https://api.metzuda.dev").rstrip("/"),
            env=os.getenv("METZUDA_ENV", "production"),
            credentials_file=Path.home() / ".metzuda" / "credentials",
            metzuda_dir=".metzuda",
        )

    @property
    def is_dev(self) -> bool:
        return self.env in ("development", "test")


# Singleton — importado por qualquer módulo que precise de configuração
settings = Settings.from_env()
