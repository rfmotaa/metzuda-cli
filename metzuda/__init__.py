"""
metzuda — Security scanner for AI-generated code.

Loads .env on startup so that METZUDA_API_URL and METZUDA_ENV can be
set in a local .env file without modifying shell configuration.
"""

from dotenv import load_dotenv

load_dotenv()  # noqa: E402 — carrega .env da raiz do projeto se existir
