"""Workspace commands. ClickUp v2 calls workspaces "teams"."""

import click

from clickup_cli.main import require_client
from clickup_cli.output import output


@click.group("workspace")
def workspace_group() -> None:
    """Manage workspaces."""


@workspace_group.command("list")
@click.pass_context
def workspace_list(ctx: click.Context) -> None:
    """List accessible workspaces."""
    client = require_client(ctx)
    data = client.get("/team")
    teams = data.get("teams", []) if isinstance(data, dict) else data
    output(teams, pretty=ctx.obj["pretty"])
