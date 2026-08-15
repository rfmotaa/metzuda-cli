"""Implements the metzuda init command for setting up configuration and state."""

from pathlib import Path
import shutil
import click
from rich.console import Console
import typer

from metzuda.core.architecture_generator import ARCHITECTURE_FILE, create_architecture_file
from metzuda.infra.auth import logout
from metzuda.infra.config import save_config
from metzuda.infra.state_manager import save_state
from metzuda.models.config import MetzudaConfig

console = Console()
app = typer.Typer()


def detect_language() -> str:
    """Detects the primary language of the project by counting file extensions in CWD."""
    cwd = Path.cwd()
    counts = {"javascript": 0, "python": 0, "java": 0}
    ignore = {".git", "node_modules", ".venv", "dist", "build", "__pycache__", ".metzuda"}

    for path in cwd.rglob("*"):
        if any(part in ignore for part in path.parts):
            continue
        if path.is_file():
            ext = path.suffix.lower()
            if ext in (".js", ".jsx", ".ts", ".tsx"):
                counts["javascript"] += 1
            elif ext == ".py":
                counts["python"] += 1
            elif ext == ".java":
                counts["java"] += 1

    max_lang = "python"  # Default fallback if no files are found
    max_count = -1
    for lang, count in counts.items():
        if count > max_count:
            max_count = count
            max_lang = lang
    return max_lang


def update_gitignore() -> None:
    """Appends Metzuda ignore paths to .gitignore if not already present."""
    gitignore = Path.cwd() / ".gitignore"
    required_lines = [
        ".metzuda/state.json",
        ".metzuda/last-report.json",
        ".metzuda/fixes/",
    ]
    lines = []
    if gitignore.exists():
        with gitignore.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f]

    modified = False
    for item in required_lines:
        if item not in lines:
            lines.append(item)
            modified = True

    if modified or not gitignore.exists():
        with gitignore.open("w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")


@app.command()
def init(
    lang: str = typer.Option(
        "auto",
        "--lang",
        click_type=click.Choice(["auto", "javascript", "python", "java"], case_sensitive=False),
        help="Primary programming language. If [italic]auto[/italic], Metzuda will count file extensions to auto-detect. [bold](auto | javascript | python | java)[/bold]",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip reinitialization warning prompts and accept defaults.",
    ),
) -> None:
    """
    [bold green]Initialize[/bold green] Metzuda configuration and state in the current repository.
    """
    metzuda_dir = Path.cwd() / ".metzuda"
    arch_file = Path.cwd() / "ProjectArchitecture.md"

    if (metzuda_dir.exists() or arch_file.exists()) and not yes:
        confirm = typer.confirm("Reinitialize?", default=False)
        if not confirm:
            raise typer.Exit()

    # 1. Logout the user
    logout()

    # 2. Clear existing configuration & state
    if metzuda_dir.exists():
        shutil.rmtree(metzuda_dir)

    # 3. Remove old ProjectArchitecture.md file if present
    if arch_file.exists():
        try:
            arch_file.unlink()
        except OSError:
            pass

    # Detect language if auto
    lang_lower = lang.lower()
    detected_lang = lang_lower
    if lang_lower == "auto":
        detected_lang = detect_language()
        console.print(f"[dim]  Auto-detected language: [cyan]{detected_lang}[/cyan][/dim]")

    # Create .metzuda/ directory
    metzuda_dir.mkdir(exist_ok=True)

    # Save fresh config without user info and empty state
    cfg = MetzudaConfig(
        language=detected_lang,
        logged_in=False,
        login_method="none",
        email=None,
    )
    save_config(cfg)
    save_state({})

    # Update .gitignore
    update_gitignore()

    # Recreate fresh ProjectArchitecture.md template
    arch_path = create_architecture_file(cfg)

    # Report what was created
    console.print()
    console.print("[green]✓[/green] Metzuda initialized:")
    console.print(f"  [cyan].metzuda/config.yml[/cyan]        — project config (language: {detected_lang})")
    console.print( "  [cyan].metzuda/state.json[/cyan]       — file hash cache (empty)")
    console.print(f"  [cyan]{arch_path.name}[/cyan]  — architecture context for AI analysis")
    console.print( "  [cyan].gitignore[/cyan]                — updated with .metzuda/ entries")
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print("  1. Edit [bold]ProjectArchitecture.md[/bold] — describe your stack, auth rules, and trust boundaries")
    console.print("  2. Run [bold cyan]metzuda scan[/bold cyan] — start scanning")
    console.print("  3. Run [bold cyan]metzuda login[/bold cyan] — enable Layer 2 AI analysis")