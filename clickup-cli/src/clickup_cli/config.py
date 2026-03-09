"""Configuration loading and saving.

Resolution order for token/workspace: CLI flag > env var > config file.
"""

import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "clickup-cli"
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
    return os.environ.get("CLICKUP_TOKEN")


def resolve_workspace(cli_workspace: str | None) -> str | None:
    if cli_workspace:
        return cli_workspace
    return os.environ.get("CLICKUP_WORKSPACE")


def resolve_project(cli_project: str | None) -> str | None:
    """Resolve project (ClickUp space) ID."""
    if cli_project:
        return cli_project
    return os.environ.get("CLICKUP_PROJECT")
