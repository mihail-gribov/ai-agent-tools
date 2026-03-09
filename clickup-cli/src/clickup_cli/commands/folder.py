"""Folder commands. ClickUp-specific organizational layer."""

import click

from clickup_cli.main import require_client
from clickup_cli.output import output


@click.group("folder")
def folder_group() -> None:
    """Manage folders (ClickUp-specific, groups lists)."""


@folder_group.command("list")
@click.option("--project", "project_gid", required=True, help="Project (space) ID")
@click.option("--archived", is_flag=True, help="Include archived folders")
@click.pass_context
def folder_list(ctx: click.Context, project_gid: str, archived: bool) -> None:
    """List folders in a project."""
    client = require_client(ctx)
    params = {"archived": str(archived).lower()}
    data = client.get(f"/space/{project_gid}/folder", params)
    folders = data.get("folders", []) if isinstance(data, dict) else data
    output(folders, pretty=ctx.obj["pretty"])


@folder_group.command("create")
@click.option("--project", "project_gid", required=True, help="Project (space) ID")
@click.option("--name", required=True, help="Folder name")
@click.pass_context
def folder_create(ctx: click.Context, project_gid: str, name: str) -> None:
    """Create a new folder."""
    client = require_client(ctx)
    data = client.post(f"/space/{project_gid}/folder", {"name": name})
    output(data, pretty=ctx.obj["pretty"])


@folder_group.command("get")
@click.argument("gid")
@click.pass_context
def folder_get(ctx: click.Context, gid: str) -> None:
    """Get folder details."""
    client = require_client(ctx)
    data = client.get(f"/folder/{gid}")
    output(data, pretty=ctx.obj["pretty"])
