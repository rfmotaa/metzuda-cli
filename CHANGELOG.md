# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-08-16

### Added
- **Layer 1 (Static Analysis)**: Bundled Semgrep security rules for JavaScript/TypeScript, Python, and Java (vulnerability checks for cookies, passwords, uploads, headers, access control, validation, and payments).
- **Layer 2 (Semantic AI Analysis)**: Deep semantic security analysis with context awareness via Metzuda API or local Anthropic provider.
- **CLI Commands**:
  - `init`: Initialize repository configuration and `.metzuda` state directory.
  - `scan`: Execute incremental or full static and semantic security scans.
  - `report`: Display summary or detailed findings from the last scan with SARIF export support.
  - `fix`: Interactive menu and LLM prompt generation to fix detected vulnerabilities.
  - `config`: View and modify project configuration (`.metzuda/config.yml`).
  - `login` / `logout`: Authentication via OAuth (GitHub / Google) or API Key (`sk-mtz-*`).
  - `status`: Display CLI auth status, plan limits, and current quota consumption.
  - `upgrade` / `billing`: Stripe checkout upgrade flow and customer billing portal integration.
- **Context & Architecture**: Automatic generation and diff tracking of `ProjectArchitecture.md`.
- **Integrations**:
  - Pre-commit hook support (`.pre-commit-hooks.yaml`).
  - GitHub Actions action (`metzuda-action/action.yml`).
