"""Implements the metzuda login command."""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import socket
import sys
import threading
from urllib.parse import parse_qs, urlparse
import webbrowser

import typer

from metzuda.cli.renderer import ErrorMessage, console
from metzuda.core.architecture_generator import ARCHITECTURE_FILE

app = typer.Typer()
CREDENTIALS_FILE = Path.home() / ".metzuda" / "credentials"

_PROVIDERS = [
    ("github",  "GitHub"),
    ("google",  "Google"),
]

# ── ANSI helpers (no Rich — raw mode + Rich don't mix) ───────────────────────
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_CYAN   = "\033[36m"
_WHITE  = "\033[97m"
_UP     = "\033[{}A"
_CLEAR  = "\033[2K"


def _draw_menu(options: list[tuple[str, str]], selected: int) -> int:
    """Print the menu lines and return the number of lines written."""
    lines = 0
    for i, (_, label) in enumerate(options):
        if i == selected:
            sys.stdout.write(f"{_CLEAR}{_BOLD}{_CYAN} ❯  {_WHITE}{label}{_RESET}\r\n")
        else:
            sys.stdout.write(f"{_CLEAR}{_DIM}    {label}{_RESET}\r\n")
        lines += 1
    hint = f"{_CLEAR}{_DIM}    ↑ ↓  to move · Enter to select · q to cancel{_RESET}\r\n"
    sys.stdout.write(hint)
    lines += 1
    sys.stdout.flush()
    return lines


def _erase_menu(n_lines: int) -> None:
    """Move cursor up n_lines and clear each line."""
    sys.stdout.write(f"\033[{n_lines}A")
    for _ in range(n_lines):
        sys.stdout.write(f"{_CLEAR}\r\n")
    sys.stdout.write(f"\033[{n_lines}A")
    sys.stdout.flush()


def _arrow_menu(label: str, options: list[tuple[str, str]]) -> str:
    """
    Interactive arrow-key menu.
    Returns the key of the chosen option.
    Falls back to a numbered prompt in non-TTY / non-Unix environments.
    """
    if not sys.stdin.isatty():
        return options[0][0]

    try:
        import termios
        import tty
    except ImportError:
        # Windows / no termios — numbered fallback
        return _numbered_fallback(label, options)

    selected = 0
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    console.print(f"  {label}")           # printed once, stays above the menu
    n_lines = _draw_menu(options, selected)

    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A":                                   # ↑
                    selected = (selected - 1) % len(options)
                elif seq == "[B":                                 # ↓
                    selected = (selected + 1) % len(options)
            elif ch in ("k", "K"):
                selected = (selected - 1) % len(options)
            elif ch in ("j", "J"):
                selected = (selected + 1) % len(options)
            elif ch in ("\r", "\n"):                              # Enter
                break
            elif ch in ("\x03", "q", "Q"):                       # Ctrl-C / q
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                _erase_menu(n_lines)
                raise typer.Abort()

            _erase_menu(n_lines)
            n_lines = _draw_menu(options, selected)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    _erase_menu(n_lines)
    return options[selected][0]


def _numbered_fallback(label: str, options: list[tuple[str, str]]) -> str:
    console.print(f"  {label}")
    for i, (_, name) in enumerate(options, 1):
        console.print(f"  [cyan]{i}[/cyan]  {name}")
    while True:
        raw = typer.prompt("  Choice", default="1")
        if raw.strip().isdigit() and 1 <= int(raw.strip()) <= len(options):
            return options[int(raw.strip()) - 1][0]
        console.print("  [red]Invalid choice.[/red]")


# ── Command ───────────────────────────────────────────────────────────────────

@app.command()
def login(
    key: str | None = typer.Option(None, "--key", "-k", help="API key for CI/CD (skips OAuth)")
) -> None:
    """Authenticate with Metzuda via OAuth or an API key."""

    if key:
        try:
            _save_credentials({"type": "api_key", "key": key, "provider": "api_key"})
            console.print("[green]✓[/green] API key saved.")
            _check_architecture_file()
            return
        except Exception as e:
            ErrorMessage.display(f"Failed to save API key: {e}")
            raise typer.Exit(code=1)

    try:
        provider = _arrow_menu("Login with:", _PROVIDERS)
    except typer.Abort:
        console.print("[dim]Login cancelled.[/dim]")
        raise typer.Exit(code=0)

    label = dict(_PROVIDERS)[provider]
    console.print(f"[green]✓[/green] {label} selected")
    _oauth_login(provider)


# ── OAuth flow ────────────────────────────────────────────────────────────────

def _oauth_login(provider: str) -> None:
    state = secrets.token_urlsafe(32)
    try:
        port = _find_free_port()
    except Exception as e:
        ErrorMessage.display(f"Could not bind local callback port: {e}")
        raise typer.Exit(code=1)

    redirect_uri = f"http://localhost:{port}/callback"
    received: dict = {}
    server_ready = threading.Event()

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            if qs.get("state", [None])[0] != state:
                self.send_error(400, "Invalid state")
                return
            token = qs.get("token", [None])[0]
            if token:
                received["token"] = token
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Metzuda — Authentication Successful</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: rgba(17, 24, 39, 0.8);
      --card-border: rgba(255, 255, 255, 0.1);
      --success: #10b981;
      --success-glow: rgba(16, 185, 129, 0.25);
      --text: #f9fafb;
      --muted: #9ca3af;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      background-image: 
        radial-gradient(circle at 50% 20%, rgba(0, 242, 254, 0.08) 0%, transparent 60%),
        radial-gradient(circle at 80% 80%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }
    .card {
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--card-border);
      border-radius: 24px;
      padding: 3rem 2.5rem;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 30px var(--success-glow);
      animation: popIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }
    .icon-box {
      width: 76px;
      height: 76px;
      background: radial-gradient(circle, var(--success-glow) 0%, transparent 70%);
      border: 2px solid rgba(16, 185, 129, 0.35);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem;
      color: var(--success);
      box-shadow: 0 0 20px var(--success-glow);
    }
    .icon-box svg {
      width: 38px;
      height: 38px;
      stroke-width: 2.5;
    }
    h1 {
      font-size: 1.75rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      margin-bottom: 0.75rem;
      background: linear-gradient(135deg, #ffffff 0%, #d1d5db 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    p {
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.6;
      margin-bottom: 1.75rem;
    }
    .terminal-badge {
      background: rgba(0, 0, 0, 0.45);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 12px;
      padding: 0.875rem 1.25rem;
      font-family: monospace;
      font-size: 0.875rem;
      color: #38bdf8;
      display: inline-block;
      width: 100%;
    }
    .hint {
      margin-top: 1.5rem;
      font-size: 0.8125rem;
      color: #6b7280;
    }
    @keyframes popIn {
      from { opacity: 0; transform: translateY(16px) scale(0.96); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon-box">
      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
      </svg>
    </div>
    <h1>Authentication Successful</h1>
    <p>You have successfully logged in to <strong>Metzuda</strong>. Your CLI session is now authenticated.</p>
    <div class="terminal-badge">$ metzuda scan</div>
    <div class="hint">You can close this window and return to your terminal.</div>
  </div>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, *_):
            pass

    try:
        httpd = HTTPServer(("localhost", port), _Handler)
    except Exception as e:
        ErrorMessage.display(f"Could not start local callback server: {e}")
        raise typer.Exit(code=1)

    thread = threading.Thread(
        target=lambda: (server_ready.set(), httpd.handle_request())
    )
    thread.daemon = True
    thread.start()
    server_ready.wait()

    from metzuda.infra.config import get_api_url

    label = dict(_PROVIDERS)[provider]
    url = f"{get_api_url()}/auth/{provider}?redirect_uri={redirect_uri}&state={state}"

    console.print(f"→ Opening browser for {label} login...")
    console.print(f"  [dim]If browser doesn't open:[/dim] {url}")

    try:
        webbrowser.open(url)
    except Exception:
        pass

    thread.join(timeout=120)
    try:
        httpd.server_close()
    except Exception:
        pass

    if "token" not in received:
        ErrorMessage.display(
            "Login timed out or was cancelled.\n"
            "  Check that the API server is running, or use:\n"
            "  metzuda login --key <API_KEY>"
        )
        raise typer.Exit(code=1)

    try:
        _save_credentials({"type": "jwt", "token": received["token"], "provider": provider})
        console.print("[green]✓[/green] Logged in successfully.")
        _check_architecture_file()
    except Exception as e:
        ErrorMessage.display(f"Failed to save credentials: {e}")
        raise typer.Exit(code=1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_architecture_file() -> None:
    if not ARCHITECTURE_FILE.exists():
        console.print(
            "[yellow]ℹ[/yellow] No ProjectArchitecture.md found. "
            "Run [bold]metzuda init[/bold] to create it."
        )


def _save_credentials(data: dict) -> None:
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data), encoding="utf-8")
    try:
        CREDENTIALS_FILE.chmod(0o600)
    except OSError:
        pass
    from metzuda.infra.config import sync_auth_state_to_config
    sync_auth_state_to_config()


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
