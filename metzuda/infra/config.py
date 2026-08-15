"""Manages project configuration file operations for Metzuda."""

import os
from pathlib import Path
import yaml

from metzuda.models.config import MetzudaConfig
from metzuda.models.finding import Severity


def get_api_url() -> str:
    """Returns the Metzuda API URL from environment variable or default localhost:3000."""
    return os.getenv("METZUDA_API_URL", "http://localhost:3000").rstrip("/")


def load_config() -> MetzudaConfig:
    """Loads configuration settings from the project's .metzuda/config.yml file."""
    path = Path.cwd() / ".metzuda" / "config.yml"
    if not path.exists():
        raise FileNotFoundError("Config not found. Run: metzuda init")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    language = data.get("language")
    if language is None:
        language = data.get("project", {}).get("language", "auto")

    severity_threshold_str = data.get("severity_threshold")
    if severity_threshold_str is None:
        severity_threshold_str = data.get("scan", {}).get("severity_threshold", "HIGH")

    sev_map = {
        "LEVE": "LOW",
        "GRAVE": "HIGH",
        "GRAVÍSSIMO": "CRITICAL",
        "GRAVISSIMO": "CRITICAL",
    }
    severity_threshold_str = sev_map.get(severity_threshold_str.upper(), severity_threshold_str)
    severity_threshold = Severity(severity_threshold_str.upper())

    ai_analysis = data.get("ai_analysis")
    if ai_analysis is None:
        ai_analysis = data.get("scan", {}).get("ai_analysis", True)

    max_context_lines = data.get("max_context_lines")
    if max_context_lines is None:
        max_context_lines = data.get("scan", {}).get("max_context_lines", 150)

    ignore_paths = data.get("ignore_paths")
    if ignore_paths is None:
        ignore_paths = data.get("ignore", {}).get("paths")

    from metzuda.infra.auth import is_logged_in, get_login_method, get_user_email

    auth_data = data.get("auth", {})
    logged_in = auth_data.get("logged_in")
    if logged_in is None:
        logged_in = is_logged_in()
        login_method = get_login_method()
        email = get_user_email()
    else:
        login_method = auth_data.get("login_method")
        if login_method is None:
            login_method = get_login_method() if logged_in else "none"
        email = auth_data.get("email")
        if email is None and logged_in:
            email = get_user_email()

    plan = auth_data.get("plan", "free")

    kwargs = {}
    if language is not None:
        kwargs["language"] = language
    if severity_threshold is not None:
        kwargs["severity_threshold"] = severity_threshold
    if ai_analysis is not None:
        kwargs["ai_analysis"] = ai_analysis
    if max_context_lines is not None:
        kwargs["max_context_lines"] = max_context_lines
    if ignore_paths is not None:
        kwargs["ignore_paths"] = ignore_paths
    kwargs["logged_in"] = logged_in
    kwargs["login_method"] = login_method
    kwargs["email"] = email
    kwargs["plan"] = plan

    return MetzudaConfig(**kwargs)



def save_config(cfg: MetzudaConfig) -> None:
    """Saves the provided MetzudaConfig object to .metzuda/config.yml."""
    path = Path.cwd() / ".metzuda" / "config.yml"
    path.parent.mkdir(exist_ok=True)

    data = {
        "version": "1",
        "project": {
            "language": cfg.language,
        },
        "auth": {
            "logged_in": cfg.logged_in,
            "login_method": cfg.login_method,
            "email": cfg.email,
            "plan": cfg.plan,
        },

        "scan": {
            "severity_threshold": cfg.severity_threshold.value,
            "ai_analysis": cfg.ai_analysis,
            "max_context_lines": cfg.max_context_lines,
        },
        "ignore": {
            "paths": cfg.ignore_paths,
        },
    }

    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def sync_auth_state_to_config() -> None:
    """Synchronizes current authentication state to local .metzuda/config.yml if it exists."""
    path = Path.cwd() / ".metzuda" / "config.yml"
    if not path.exists():
        return
    try:
        from metzuda.infra.auth import is_logged_in, get_login_method, get_user_email
        cfg = load_config()
        cfg.logged_in = is_logged_in()
        cfg.login_method = get_login_method()
        cfg.email = get_user_email()
        save_config(cfg)
    except Exception:
        pass
