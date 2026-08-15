"""Orchestrates the security scanning pipeline."""

import datetime
import inspect
import logging
from pathlib import Path
import time
import uuid

from metzuda.analyzers.static import StaticAnalyzer
from metzuda.core.aggregator import aggregate
from metzuda.core.prompt_builder import update_findings_prompts
from metzuda.core.walker import walk
from metzuda.infra.backend_client import BackendClient
from metzuda.infra.errors import QuotaExceededError
from metzuda.infra.state_manager import (
    file_hash,
    get_files_for_ai_scan,
    get_files_for_static_scan,
    update_architecture_hash,
    update_state_after_ai,
    update_state_after_static,
)
from metzuda.models.config import MetzudaConfig
from metzuda.models.report import ScanReport

logger = logging.getLogger("metzuda")


def get_architecture_context(root: Path, state: dict) -> tuple[str | None, bool]:
    arch_file = root / "ProjectArchitecture.md"
    if not arch_file.exists():
        return None, False
    try:
        content = arch_file.read_text(encoding="utf-8")
        curr_hash = file_hash(arch_file)
        arch_changed = state.get("architecture_hash") != curr_hash
        return content, arch_changed
    except Exception:
        return None, False


class Scanner:
    def __init__(self, config: MetzudaConfig):
        self.config = config
        self.static = StaticAnalyzer()
        self.backend_client = BackendClient()
        self.semantic = self.backend_client

    def run(
        self,
        root: Path,
        state: dict,
        full_scan: bool = False,
        run_ai: bool = True,
        ai_provider: str | None = None,
    ) -> tuple[ScanReport, dict]:
        """
        Executes the full scan pipeline.
        Returns (report, updated_state).
        The caller is responsible for persisting the updated state.
        """

        start_time = time.time()

        # 1. Walk the repo to get all files respecting config.ignore_paths
        all_files = walk(root, self.config.ignore_paths)

        # 2. Select files for static and AI scan layers
        if full_scan:
            static_files = all_files
            ai_files = all_files
        else:
            static_files = get_files_for_static_scan(all_files, state)
            ai_files = get_files_for_ai_scan(all_files, state)

        # 3. Check if StaticAnalyzer is available
        if static_files and not self.static.is_available():
            raise RuntimeError("Semgrep not found. Install with: pip install semgrep")

        static_findings = []
        if static_files:
            try:
                static_findings = self.static.analyze(static_files)
                state = update_state_after_static(static_files, state)
            except Exception as e:
                logger.exception(f"StaticAnalyzer error during analysis: {e}")

        # 4. Layer 2 — AI Semantic Analysis
        semantic_findings = []
        api_calls_made = 0
        backend = getattr(self, "backend_client", getattr(self, "semantic", None))

        if run_ai and self.config.ai_analysis and backend and backend.is_available():
            architecture, arch_changed = get_architecture_context(root, state)
            files_for_ai = all_files if full_scan else ai_files

            # Prioritize files by architecture category rules (routes, middleware, models, controllers first)
            def category_priority(p: Path) -> int:
                name_lower = p.name.lower()
                if any(k in name_lower for k in ("route", "controller")):
                    return 1
                if any(k in name_lower for k in ("middleware", "auth")):
                    return 2
                if any(k in name_lower for k in ("model", "repo", "db")):
                    return 3
                return 4

            sorted_ai_files = sorted(files_for_ai, key=category_priority)[:30]

            if sorted_ai_files:
                api_calls_made = 1
                try:
                    sig = inspect.signature(backend.analyze)
                    kwargs = {
                        "files": sorted_ai_files,
                        "static_findings": static_findings,
                    }
                    if "architecture" in sig.parameters:
                        kwargs["architecture"] = architecture
                        kwargs["architecture_changed"] = arch_changed
                    if "language" in sig.parameters:
                        kwargs["language"] = self.config.language
                    if "ai_provider" in sig.parameters and ai_provider:
                        kwargs["ai_provider"] = ai_provider

                    semantic_findings = backend.analyze(**kwargs)

                    state = update_state_after_ai(sorted_ai_files, state)
                    if architecture:
                        arch_file = root / "ProjectArchitecture.md"
                        state = update_architecture_hash(arch_file, state)
                except QuotaExceededError:
                    from metzuda.cli.renderer import console
                    console.print("\n  [yellow]⚠[/yellow]  AI quota exceeded for this month.")
                    console.print("     Run [bold]metzuda upgrade[/bold] to increase your quota.\n")
                except Exception as e:
                    logger.exception(f"Error during AI analysis: {e}")
                    from metzuda.cli.renderer import console
                    console.print(f"[yellow]Warning: AI call failed ({e}). Skipping AI layer.[/yellow]")

        # 5. Load historical findings for files NOT scanned in this static run
        historical_findings = []
        if not full_scan:
            scanned_files_rel = set()
            for f_path in static_files:
                try:
                    rel_path = str(f_path.relative_to(Path.cwd()))
                except ValueError:
                    rel_path = str(f_path)
                scanned_files_rel.add(rel_path)

            try:
                from metzuda.infra.state_manager import load_report
                prev_report = load_report()
                for f in prev_report.findings:
                    if f.file not in scanned_files_rel:
                        historical_findings.append(f)
            except Exception:
                pass

        # 6. Aggregate findings from both layers and historical findings
        findings = aggregate(static_findings + historical_findings, semantic_findings)

        # 7. Update fix prompts
        update_findings_prompts(findings)

        # 8. Build and return ScanReport
        duration_seconds = time.time() - start_time
        report = ScanReport(
            scan_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            findings=findings,
            files_scanned=len(static_files),
            api_calls_made=api_calls_made,
            duration_seconds=duration_seconds,
        )

        return report, state
