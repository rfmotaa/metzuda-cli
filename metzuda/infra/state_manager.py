"""Manages file hashing, state storage, and report caching for Metzuda."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from metzuda.models.finding import Finding, Severity, Source
from metzuda.models.report import ScanReport


def file_hash(path: Path) -> str:
    """Computes the SHA-256 hash of a file's content."""
    sha256 = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()}"


def load_state() -> dict:
    """Loads the scan state dictionary from .metzuda/state.json and migrates v1 -> v2 if needed."""
    path = Path.cwd() / ".metzuda" / "state.json"
    if not path.exists():
        return {"version": "2", "files": {}}
    with path.open("r", encoding="utf-8") as f:
        try:
            state = json.load(f)
        except json.JSONDecodeError:
            return {"version": "2", "files": {}}

    # Migrate old-format state.json if needed
    files = state.get("files", {})
    for file_key, file_entry in files.items():
        if isinstance(file_entry, dict):
            if "hash" in file_entry and "static_hash" not in file_entry:
                file_entry["static_hash"] = file_entry.pop("hash")
                file_entry["static_scanned_at"] = file_entry.pop("last_scanned", None)
                file_entry["ai_hash"] = None
                file_entry["ai_scanned_at"] = None

    state["version"] = "2"
    return state


def save_state(state: dict) -> None:
    """Saves the scan state dictionary to .metzuda/state.json with indent=2."""
    path = Path.cwd() / ".metzuda" / "state.json"
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _hash_changed(file: Path, state: dict, key: str) -> bool:
    """Checks whether current file hash differs from saved state hash for key."""
    if not file.exists():
        return False
    current = file_hash(file)
    try:
        rel_path = str(file.relative_to(Path.cwd()))
    except ValueError:
        rel_path = str(file)

    files_state = state.get("files", {})
    file_info = files_state.get(rel_path)
    if not isinstance(file_info, dict):
        return True

    saved = file_info.get(key)
    return current != saved


def get_files_for_static_scan(all_files: list[Path], state: dict) -> list[Path]:
    """Files that changed since last Semgrep scan."""
    return [f for f in all_files if _hash_changed(f, state, key="static_hash")]


def get_files_for_ai_scan(all_files: list[Path], state: dict) -> list[Path]:
    """Files that changed since last AI scan (or never sent to AI)."""
    return [f for f in all_files if _hash_changed(f, state, key="ai_hash")]


def get_changed_files(all_files: list[Path], state: dict) -> list[Path]:
    """Alias for get_files_for_static_scan for backward compatibility."""
    return get_files_for_static_scan(all_files, state)


def update_state_after_static(files: list[Path], state: dict) -> dict:
    """Update static_hash after Semgrep scan."""
    if "files" not in state:
        state["files"] = {}
    state["version"] = "2"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for f in files:
        try:
            rel_path = str(f.relative_to(Path.cwd()))
        except ValueError:
            rel_path = str(f)

        entry = state["files"].setdefault(
            rel_path,
            {
                "static_hash": None,
                "static_scanned_at": None,
                "ai_hash": None,
                "ai_scanned_at": None,
            },
        )
        if f.exists():
            entry["static_hash"] = file_hash(f)
            entry["static_scanned_at"] = now_str

    return state


def update_state_after_ai(files: list[Path], state: dict) -> dict:
    """Update ai_hash after successful AI scan."""
    if "files" not in state:
        state["files"] = {}
    state["version"] = "2"
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for f in files:
        try:
            rel_path = str(f.relative_to(Path.cwd()))
        except ValueError:
            rel_path = str(f)

        entry = state["files"].setdefault(
            rel_path,
            {
                "static_hash": None,
                "static_scanned_at": None,
                "ai_hash": None,
                "ai_scanned_at": None,
            },
        )
        if f.exists():
            entry["ai_hash"] = file_hash(f)
            entry["ai_scanned_at"] = now_str

    return state


def update_architecture_hash(arch_file: Path, state: dict) -> dict:
    """Update architecture hash after reading ProjectArchitecture.md."""
    if arch_file.exists():
        state["architecture_hash"] = file_hash(arch_file)
    else:
        state["architecture_hash"] = None
    return state


def update_state(files: list[Path], state: dict) -> dict:
    """Alias for update_state_after_static for backward compatibility."""
    return update_state_after_static(files, state)


def load_report() -> ScanReport:
    """Loads the last ScanReport from .metzuda/last-report.json."""
    path = Path.cwd() / ".metzuda" / "last-report.json"
    if not path.exists():
        raise FileNotFoundError("No scan report found. Run: metzuda scan")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    findings = []
    for f_data in data.get("findings", []):
        findings.append(
            Finding(
                id=f_data["id"],
                type=f_data["type"],
                severity=Severity(f_data["severity"]),
                source=Source(f_data["source"]),
                file=f_data["file"],
                line=f_data["line"],
                column=f_data.get("column", 0),
                rule_id=f_data.get("rule_id"),
                explanation=f_data.get("explanation", ""),
                fix_prompt=f_data.get("fix_prompt", ""),
                code_snippet=f_data.get("code_snippet", ""),
            )
        )

    return ScanReport(
        scan_id=data["scan_id"],
        timestamp=data["timestamp"],
        project=data.get("project", ""),
        findings=findings,
        files_scanned=data.get("files_scanned", 0),
        api_calls_made=data.get("api_calls_made", 0),
        api_tokens_used=data.get("api_tokens_used", 0),
        duration_seconds=data.get("duration_seconds", 0.0),
        git_commit=data.get("git_commit", ""),
        git_branch=data.get("git_branch", ""),
    )


def save_report(report: ScanReport, fix_prompts: bool = True) -> None:
    """Saves a ScanReport object to .metzuda/last-report.json and individual fixes."""
    metzuda_dir = Path.cwd() / ".metzuda"
    path = metzuda_dir / "last-report.json"
    metzuda_dir.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)

    # Save fix prompts to .metzuda/fixes/
    fixes_dir = metzuda_dir / "fixes"
    if fixes_dir.exists():
        # Clean up old fixes
        for f_path in fixes_dir.glob("*.md"):
            try:
                f_path.unlink()
            except Exception:
                pass
    else:
        fixes_dir.mkdir(exist_ok=True)

    if fix_prompts:
        for finding in report.findings:
            if finding.fix_prompt:
                # Extract number from ID (e.g. MTZ-001 -> 001)
                num_part = finding.id.split("-")[-1] if "-" in finding.id else finding.id
                fix_path = fixes_dir / f"fix-{num_part}.md"
                with fix_path.open("w", encoding="utf-8") as f:
                    f.write(finding.fix_prompt)
