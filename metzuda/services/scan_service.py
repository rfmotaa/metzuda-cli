"""
metzuda/services/scan_service.py

Orquestra o caso de uso completo de scan de segurança.
Coordena Core e Infra sem conhecer nada do terminal (CLI).
Não imprime nada — retorna dados, lança exceções tipadas.
"""

from pathlib import Path

from metzuda.core.scanner import Scanner
from metzuda.core.walker import walk
from metzuda.exceptions import ConfigError, SemgrepNotFoundError
from metzuda.infra.config import load_config
from metzuda.infra.state_manager import get_files_for_static_scan, load_state, save_report, save_state
from metzuda.models.report import ScanReport


def run(
    path: Path | None = None,
    full: bool = False,
    run_ai: bool = True,
    ai_provider: str | None = None,
) -> tuple[ScanReport, list[Path]]:
    """
    Executa o pipeline de scan completo (Layer 1 + Layer 2 se aplicável).

    Args:
        path: Diretório raiz a escanear. Padrão: diretório atual.
        full: Se True, ignora cache e re-analisa todos os arquivos.
        run_ai: Se False, pula a análise de AI (Layer 2).
        ai_provider: Provider de AI a usar ('claude' | 'gemini'). None usa o default do servidor.

    Returns:
        Tupla (ScanReport, files_to_scan) — report completo e lista de arquivos escaneados.

    Raises:
        ConfigError: .metzuda/config.yml não encontrado. Usuário precisa rodar metzuda init.
        SemgrepNotFoundError: Semgrep não está instalado.
        QuotaExceededError: Quota de AI scans atingida.
        NetworkError: Falha de conexão com a API.
        UnauthorizedError: Token inválido ou expirado.
    """
    target = path or Path.cwd()

    try:
        config = load_config()
    except FileNotFoundError as exc:
        raise ConfigError("Config not found. Run: metzuda init") from exc

    state = load_state()
    all_files = walk(target, config.ignore_paths)
    files_to_scan = all_files if full else get_files_for_static_scan(all_files, state)

    scanner = Scanner(config)
    report, new_state = scanner.run(
        target,
        state,
        full,
        run_ai,
        ai_provider=ai_provider,
    )

    save_state(new_state)
    save_report(report)

    return report, files_to_scan
