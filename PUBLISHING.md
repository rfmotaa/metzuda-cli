# metzuda-cli — Mapa de Arquivos e Guia de Publicação no PyPI

> Documento interno. Explica o papel de cada arquivo e o checklist completo para a primeira publicação pública.

---

## 1. Estrutura do projeto

```
metzuda-cli/
│
├── metzuda/                       ← Pacote Python instalável (o que vai ao PyPI)
│   ├── __init__.py                ← load_dotenv() na inicialização
│   ├── exceptions.py              ← Hierarquia de exceções tipadas
│   │
│   ├── cli/                       ← Camada de interface com o terminal
│   │   ├── main.py                ← Typer app + registro de subcomandos + entrypoint()
│   │   ├── renderer.py            ← Todo output visual passa aqui (nunca print() direto)
│   │   └── commands/
│   │       ├── init.py            ← metzuda init
│   │       ├── scan.py            ← metzuda scan
│   │       ├── login.py           ← metzuda login (OAuth GitHub/Google + API key)
│   │       ├── logout.py          ← metzuda logout
│   │       ├── status.py          ← metzuda status
│   │       ├── upgrade.py         ← metzuda upgrade (Stripe checkout)
│   │       ├── billing.py         ← metzuda billing (Stripe portal)
│   │       ├── fix.py             ← metzuda fix (gera prompts de correção)
│   │       ├── report.py          ← metzuda report (exibe último scan)
│   │       └── config.py          ← metzuda config (lê/escreve config.yml)
│   │
│   ├── services/                  ← Orquestração de casos de uso
│   │   ├── scan_service.py        ← Pipeline completo de scan
│   │   ├── login_service.py       ← Construção de URLs OAuth
│   │   └── upgrade_service.py     ← Checkout e portal Stripe
│   │
│   ├── core/                      ← Lógica de análise pura (sem I/O)
│   │   ├── scanner.py             ← Orquestra Walker → Static → AI → Aggregator
│   │   ├── walker.py              ← Percorre arquivos respeitando ignores
│   │   ├── aggregator.py          ← Merge e deduplicação de findings
│   │   ├── prompt_builder.py      ← Constrói prompts de contexto para a AI
│   │   ├── architecture_generator.py ← Cria e lê ProjectArchitecture.md
│   │   └── state.py               ← Thin wrapper para scan incremental
│   │
│   ├── analyzers/                 ← Motores de análise
│   │   ├── base.py                ← ABC com interface analyze()
│   │   ├── static.py              ← Layer 1: Semgrep + parse do JSON de saída
│   │   └── semantic.py            ← Layer 2: Anthropic API direta (análise local)
│   │
│   ├── infra/                     ← I/O: disco, rede, credenciais
│   │   ├── auth.py                ← ~/.metzuda/credentials (lê/escreve/deleta)
│   │   ├── config.py              ← .metzuda/config.yml (lê/escreve)
│   │   ├── state_manager.py       ← .metzuda/state.json e last-report.json
│   │   ├── backend_client.py      ← Cliente HTTP para a Metzuda API
│   │   ├── http_client.py         ← Wrapper centralizado sobre httpx
│   │   └── errors.py              ← Re-exports de exceptions.py (retrocompat)
│   │
│   ├── models/                    ← Dataclasses puros (zero I/O, zero lógica)
│   │   ├── finding.py             ← Finding, Severity (LOW/HIGH/CRITICAL), Source
│   │   ├── report.py              ← ScanReport com findings + is_safe()
│   │   └── config.py              ← MetzudaConfig (linguagem, auth, plano, etc.)
│   │
│   ├── config/                    ← Configuração centralizada de ambiente
│   │   ├── settings.py            ← Singleton settings (METZUDA_API_URL, METZUDA_ENV)
│   │   ├── endpoints.py           ← Singleton endpoints (todas as URLs da API)
│   │   └── constants.py           ← MAX_FILES_PER_SCAN, PLAN_LIMITS, timeouts, etc.
│   │
│   └── rules/                     ← Regras Semgrep (bundled dentro do wheel)
│       ├── javascript/            ← auth, cors, eval, secrets, sql-injection
│       ├── python/                ← auth, eval, secrets, sql-injection
│       └── java/                  ← auth, secrets, sql-injection
│
├── repoTests/
│   └── tests/                     ← Suite de testes pytest
│       ├── fixtures/safe/         ← Código seguro (não deve gerar findings)
│       ├── fixtures/vulnerable/   ← Código vulnerável (deve gerar findings)
│       ├── vulnerable_project_sim/ ← Projeto simulado para testes E2E
│       └── test_*.py              ← 76 testes (unit + integration)
│
├── metzuda-action/                ← GitHub Action para uso em CI/CD
│   ├── action.yml
│   └── README.md
│
├── pyproject.toml                 ← Source of truth: build, deps, entry point, ferramentas
├── Makefile                       ← make dev | test | lint | format | check
├── README.md                      ← Documentação pública (aparece na página do PyPI)
├── REFACTOR.md                    ← Guia interno de arquitetura em camadas
├── .pre-commit-hooks.yaml         ← Hook para pre-commit framework
├── .semgrepignore                 ← Vazio: sobrescreve defaults do Semgrep
├── .env.example                   ← Documenta METZUDA_API_URL e METZUDA_ENV
├── requirements.txt               ← ⚠️ LEGADO — ver seção 4.1
└── dist/                          ← ⚠️ Builds locais — não versionar (ver seção 4.2)
```

---

## 2. Utilidade de cada arquivo (detalhado)

### Raiz

| Arquivo | O que faz |
|---------|-----------|
| `pyproject.toml` | **Source of truth** do pacote. Nome, versão, deps, entry point, ruff, mypy, pytest. |
| `README.md` | Exibido na página do PyPI. Deve ter instalação, quickstart e exemplos claros. |
| `Makefile` | Atalhos de dev. Não entra no wheel. |
| `.pre-commit-hooks.yaml` | Permite que outros projetos rodem `metzuda scan --no-ai` como pre-commit hook. Estratégia de adoção viral. |
| `.semgrepignore` | Arquivo vazio proposital — garante que o Semgrep não ignore arquivos durante o próprio scan do Metzuda. |
| `REFACTOR.md` | Guia de arquitetura em camadas. Referência para contribuidores. |
| `requirements.txt` | ⚠️ Gerado por `pip freeze` em algum momento. Não é a source of truth — pode confundir. |
| `dist/` | ⚠️ Build artefacts gerados localmente. Não devem ser versionados. |

### `metzuda/config/` — novos módulos

**`settings.py`**: Singleton `settings` lido do ambiente na primeira importação. Todo módulo que precisa da URL da API importa `settings.api_url` — ninguém chama `os.getenv()` diretamente.

**`endpoints.py`**: Singleton `endpoints` com todas as URLs construídas a partir de `settings.api_url`. Mudar de `api.metzuda.dev` para outro domínio requer alterar apenas a variável de ambiente — todos os endpoints atualizam automaticamente.

**`constants.py`**: Centraliza magic numbers: `MAX_FILES_PER_SCAN = 30`, `HTTP_TIMEOUT_SECONDS = 120`, `PLAN_LIMITS`, `SUPPORTED_EXTENSIONS`. Nenhum módulo usa literais numéricos avulsos.

### `metzuda/analyzers/semantic.py`

Layer 2 **local** via Anthropic API direta. Usado como alternativa ao backend Metzuda quando o usuário tem uma chave Anthropic própria. O fluxo padrão vai pelo backend (`backend_client.py`).

### `metzuda/core/state.py`

Thin wrapper sobre `infra/state_manager`. Existiu antes da refatoração em camadas para desacoplar o Core do Infra. Pode ser integrado ao `scan_service` futuramente.

---

## 3. O que já está pronto para o PyPI

- ✅ `pyproject.toml` completo com metadados, classifiers, entry point e build config
- ✅ Dependências declaradas com versões mínimas
- ✅ Regras Semgrep bundled via `[tool.hatch.build.targets.wheel.force-include]`
- ✅ Entry point: `metzuda = "metzuda.cli.main:entrypoint"`
- ✅ `README.md` com exemplos e output de terminal
- ✅ Licença MIT declarada
- ✅ `requires-python = ">=3.11"`
- ✅ Classifiers corretos (Development Status, Environment, License, etc.)
- ✅ Build system configurado (hatchling)
- ✅ Builds antigos já gerados em `dist/`

---

## 4. O que falta antes de publicar

### 4.1 Remover `requirements.txt` (bloqueador de clareza)

O arquivo é um `pip freeze` desatualizado que não reflete as dependências reais do projeto.
Isso confunde contribuidores sobre o que instalar.

```bash
rm requirements.txt
# As dependências estão em pyproject.toml — é tudo que precisa.
```

### 4.2 Adicionar `dist/` ao `.gitignore`

Builds locais não devem ser versionados. Editar `.gitignore`:

```
dist/
*.egg-info/
```

### 4.3 Adicionar `[project.urls]` ao `pyproject.toml`

Aparece na sidebar da página do PyPI. Aumenta confiança e discoverability:

```toml
[project.urls]
Homepage = "https://metzuda.dev"
Repository = "https://github.com/rfmota/metzuda"
Documentation = "https://docs.metzuda.dev"
"Bug Tracker" = "https://github.com/rfmota/metzuda/issues"
Changelog = "https://github.com/rfmota/metzuda/blob/main/CHANGELOG.md"
```

### 4.4 Implementar `metzuda --version`

Todo CLI precisa de `--version`. Adicionar em `cli/main.py`:

```python
from importlib.metadata import version as _pkg_version

def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"metzuda {_pkg_version('metzuda')}")
        raise typer.Exit()

@app.callback()
def _main(
    version: bool = typer.Option(
        None, "--version", "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass
```

### 4.5 Criar `CHANGELOG.md`

Necessário para comunicar breaking changes entre versões.
Formato: [Keep a Changelog](https://keepachangelog.com).

```markdown
# Changelog

## [0.1.0] — 2026-08-16
### Added
- Layer 1: Semgrep static analysis (JS, Python, Java)
- Layer 2: AI semantic analysis via Metzuda API
- Commands: init, scan, login, logout, status, upgrade, billing, fix, report, config
- pre-commit hook support
- GitHub Action
```

### 4.6 Considerar `anthropic` como dependência opcional

`anthropic` é pesado e só é necessário para quem quiser Layer 2 **local**.
O fluxo padrão usa o backend Metzuda. Isso reduz o tamanho da instalação:

```toml
# pyproject.toml
dependencies = [
    "typer[all]>=0.12.0",
    "rich>=13.0.0",
    "semgrep>=1.70.0",
    "pyyaml>=6.0",
    "pyperclip>=1.8.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
    # anthropic removido daqui
]

[project.optional-dependencies]
anthropic = ["anthropic>=0.25.0"]
dev = ["pytest>=8.0", ...]
```

Instalação para quem quiser análise local: `pip install metzuda[anthropic]`

### 4.7 Criar conta no PyPI e gerar API Token

1. Criar conta em [pypi.org](https://pypi.org/account/register/)
2. Ir em Account Settings → API Tokens
3. Gerar token com escopo "Entire account" para o primeiro upload
4. Guardar o token — aparece uma só vez

---

## 5. Checklist de publicação — passo a passo

```bash
# Pré-requisitos
pip install build twine

# 1. Limpar builds antigos
rm -rf dist/ metzuda.egg-info/

# 2. Garantir que testes passam
make test

# 3. Confirmar versão em pyproject.toml
grep '^version' pyproject.toml   # deve ser "0.1.0"

# 4. Build
python -m build
# Gera:
#   dist/metzuda-0.1.0.tar.gz          ← source distribution
#   dist/metzuda-0.1.0-py3-none-any.whl ← wheel

# 5. Verificar que as regras Semgrep estão dentro do wheel
unzip -l dist/metzuda-0.1.0-py3-none-any.whl | grep rules
# Deve listar: metzuda/rules/javascript/secrets.yml etc.

# 6. Publicar no TestPyPI primeiro
twine upload --repository testpypi dist/*
# Acessa: https://test.pypi.org/project/metzuda/

# 7. Instalar do TestPyPI e validar
pip install \
  --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ \
  metzuda
metzuda --help
metzuda --version  # após implementar 4.4

# 8. Se tudo OK: publicar no PyPI real
twine upload dist/*
# Acessa: https://pypi.org/project/metzuda/

# 9. Criar git tag
git tag v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

---

## 6. CI/CD para publicação automática (quando estável)

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  push:
    tags: ["v*.*.*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # Trusted Publisher OIDC — sem token armazenado no repo
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Configurar Trusted Publisher em pypi.org → Project → Publishing → Add publisher.
Isso elimina a necessidade de armazenar tokens PyPI como secrets do GitHub.

---

## 7. Após a publicação

```bash
# Verificar instalação limpa
pip install metzuda==0.1.0
metzuda --help

# Verificar que as regras funcionam (precisa de semgrep no PATH)
mkdir /tmp/test-repo && cd /tmp/test-repo
echo "const key = 'sk_live_abc123'" > index.js
metzuda init && metzuda scan --no-ai
# Deve detectar HARDCODED_SECRET
```

---

*Documento interno — não remover do repo.*
