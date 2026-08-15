"""Provides functionality to walk the workspace and list files to scan, respecting ignore lists."""

import fnmatch
from pathlib import Path


def should_ignore(path: Path, root: Path, ignore_patterns: list[str]) -> bool:
    """Returns True if the given path matches any of the ignore patterns."""
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        rel_path = path

    rel_path_str = str(rel_path).replace("\\", "/")

    for pattern in ignore_patterns:
        clean_pat = pattern.rstrip("/")
        # Match full relative path or component parts
        if fnmatch.fnmatch(rel_path_str, clean_pat) or fnmatch.fnmatch(rel_path_str, pattern):
            return True
        for part in rel_path.parts:
            if fnmatch.fnmatch(part, clean_pat) or fnmatch.fnmatch(part, pattern):
                return True
    return False


def load_metzudaignore(root: Path) -> list[str]:
    """Loads ignore patterns from .metzudaignore if it exists."""
    ignore_file = root / ".metzudaignore"
    if not ignore_file.exists():
        return []
    with ignore_file.open("r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]


def walk(root: Path, ignore_patterns: list[str]) -> list[Path]:
    """Recursively walks repository paths and returns all non-ignored files."""
    combined_patterns = list(ignore_patterns) + load_metzudaignore(root)
    files = []

    def _walk_dir(current_dir: Path):
        for path in current_dir.iterdir():
            if should_ignore(path, root, combined_patterns):
                continue
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                _walk_dir(path)

    if root.exists():
        if root.is_file():
            if not should_ignore(root, root.parent, combined_patterns):
                files.append(root)
        else:
            _walk_dir(root)

    return sorted(files)
