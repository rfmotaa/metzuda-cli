"""
metzuda/cli/commands/status.py

Implementa o comando metzuda status.
Exibe informações de autenticação, quota e estatísticas do repositório.
"""

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from metzuda.config.endpoints import endpoints
from metzuda.infra.auth import get_auth_header, get_login_method, get_user_email, is_logged_in
from metzuda.infra.config import load_config, save_config
from metzuda.infra.state_manager import load_report, load_state
from metzuda.models.finding import Severity

console = Console()
app = typer.Typer()


@app.command()
def status() -> None:
    """
    [bold green]Display Metzuda status[/bold green], including authentication, quota usage, and repository stats.
    """
    logged_in = is_logged_in()
    email = get_user_email() or "N/A"
    login_method = get_login_method()

    # Load cached values from config (available offline)
    try:
        cfg = load_config()
        plan_name = cfg.plan.capitalize() if cfg.plan else "Free"
        if cfg.email and email == "N/A":
            email = cfg.email
    except Exception:
        cfg = None
        plan_name = "Free"

    scans_used = 0
    scans_limit = "Unlimited (Local Layer 1)"
    tokens_used = 0
    api_online = False

    if logged_in:
        auth_header = get_auth_header()
        if auth_header:
            try:
                with httpx.Client(timeout=5) as client:
                    me_res = client.get(endpoints.users_me, headers={"Authorization": auth_header})
                    if me_res.status_code == 200:
                        user_data = me_res.json()
                        api_online = True
                        plan_name = user_data.get("plan", plan_name).capitalize()
                        if "email" in user_data:
                            email = user_data["email"]

                        # Cache plan in config for offline access
                        if cfg:
                            cfg.plan = plan_name.lower()
                            cfg.email = email
                            try:
                                save_config(cfg)
                            except Exception:
                                pass

                    usage_res = client.get(endpoints.users_usage, headers={"Authorization": auth_header})
                    if usage_res.status_code == 200:
                        usage_data = usage_res.json()
                        scans_used = usage_data.get("scansUsed", 0)
                        scans_limit = str(usage_data.get("scansLimit", 500))
                        tokens_used = usage_data.get("tokensUsed", 0)
            except Exception:
                pass  # Graceful offline fallback

    # Repo stats from local state & report
    tracked_files = 0
    last_scan = "Never"
    critical_count = 0
    high_count = 0
    low_count = 0

    try:
        state = load_state()
        tracked_files = len(state.get("files", {}))
    except Exception:
        pass

    try:
        report = load_report()
        last_scan = report.timestamp
        for f in report.findings:
            if f.severity == Severity.CRITICAL:
                critical_count += 1
            elif f.severity == Severity.HIGH:
                high_count += 1
            else:
                low_count += 1
    except Exception:
        pass

    # Build Rich output
    console.print()

    auth_table = Table(show_header=False, box=None, padding=(0, 1))
    auth_table.add_column("Key", style="bold white", width=20)
    auth_table.add_column("Value")

    auth_table.add_row("Logged In", "[green]Yes[/green]" if logged_in else "[yellow]No[/yellow]")
    auth_table.add_row("User Email", email)
    auth_table.add_row("Login Method", login_method)

    plan_display = plan_name
    if logged_in and not api_online:
        plan_display += " [dim](cached — offline)[/dim]"
    auth_table.add_row("Current Plan", plan_display)
    auth_table.add_row("Scans (Month)", f"{scans_used} / {scans_limit}")
    auth_table.add_row("Tokens Used", f"{tokens_used:,}")

    console.print(Panel(auth_table, title="[bold cyan]Metzuda Status[/bold cyan]", expand=False))

    if isinstance(scans_limit, int) and scans_used >= scans_limit:
        console.print("  [yellow]⚠[/yellow]  AI quota reached for this month.")
        console.print("     Run [bold]metzuda upgrade[/bold] to increase your quota.")

    repo_table = Table(show_header=False, box=None, padding=(0, 1))
    repo_table.add_column("Key", style="bold white", width=20)
    repo_table.add_column("Value")

    repo_table.add_row("Tracked Files", str(tracked_files))
    repo_table.add_row("Last Scan", last_scan)
    findings_str = (
        f"[bold red]{critical_count} CRITICAL[/bold red], "
        f"[bold yellow]{high_count} HIGH[/bold yellow], "
        f"[dim]{low_count} LOW[/dim]"
    )
    repo_table.add_row("Open Findings", findings_str)

    console.print(Panel(repo_table, title="[bold cyan]Repository Status[/bold cyan]", expand=False))
    console.print()
