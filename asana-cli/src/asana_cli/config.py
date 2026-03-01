"""Configuration loading and saving.

Resolution order for token/workspace: CLI flag > env var > config file.
"""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "asana-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def resolve_token(cli_token: str | None) -> str | None:
    if cli_token:
        return cli_token
    env_token = os.environ.get("ASANA_TOKEN")
    if env_token:
        return env_token
    return load_config().get("token")


def resolve_workspace(cli_workspace: str | None) -> str | None:
    if cli_workspace:
        return cli_workspace
    env_ws = os.environ.get("ASANA_WORKSPACE")
    if env_ws:
        return env_ws
    return load_config().get("workspace")


def resolve_project(cli_project: str | None) -> str | None:
    if cli_project:
        return cli_project
    env_proj = os.environ.get("ASANA_PROJECT")
    if env_proj:
        return env_proj
    return load_config().get("project")


def get_project_cache(project_gid: str) -> dict | None:
    """Get cached custom field settings for a project."""
    config = load_config()
    return config.get("projects", {}).get(project_gid)


def save_project_cache(project_gid: str, data: dict) -> None:
    """Cache custom field settings for a project."""
    config = load_config()
    config.setdefault("projects", {})[project_gid] = data
    save_config(config)
