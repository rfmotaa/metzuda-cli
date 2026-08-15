"""Wraps state comparison logic for incremental scanning."""

from pathlib import Path

from metzuda.infra.state_manager import get_changed_files, update_state


def get_incremental_files(all_files: list[Path], state: dict) -> list[Path]:
    """Returns the list of files that have changed since the last scan."""
    return get_changed_files(all_files, state)


def update_scan_state(files: list[Path], state: dict) -> None:
    """Updates the scan state dict in-memory with current hashes."""
    update_state(files, state)
