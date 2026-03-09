"""Section commands. Maps to ClickUp Lists (where tasks live)."""

import click

from clickup_cli.main import require_client
from clickup_cli.output import output


@click.group("section")
def section_group() -> None:
    """Manage sections (ClickUp lists)."""


@section_group.command("list")
@click.option("--project", "project_gid", required=True, help="Project (space) ID")
@click.pass_context
def section_list(ctx: click.Context, project_gid: str) -> None:
    """List sections in a project.

    Returns all lists: folderless lists directly under the space,
    plus lists inside folders.
    """
    client = require_client(ctx)
    results = []

    # Folderless lists
    data = client.get(f"/space/{project_gid}/list")
    lists = data.get("lists", []) if isinstance(data, dict) else data
    results.extend(lists)

    # Lists inside folders
    folders_data = client.get(f"/space/{project_gid}/folder")
    folders = folders_data.get("folders", []) if isinstance(folders_data, dict) else folders_data
    for folder in folders:
        folder_lists = folder.get("lists", [])
        for lst in folder_lists:
            lst["folder"] = {"id": folder.get("id"), "name": folder.get("name")}
        results.extend(folder_lists)

    output(results, pretty=ctx.obj["pretty"])


@section_group.command("create")
@click.option("--project", "project_gid", required=True, help="Project (space) ID")
@click.option("--name", required=True, help="Section name")
@click.option("--folder", "folder_id", default=None, help="Folder ID (creates inside folder)")
@click.pass_context
def section_create(
    ctx: click.Context,
    project_gid: str,
    name: str,
    folder_id: str | None,
) -> None:
    """Create a new section (ClickUp list)."""
    client = require_client(ctx)
    body: dict = {"name": name}
    if folder_id:
        data = client.post(f"/folder/{folder_id}/list", body)
    else:
        data = client.post(f"/space/{project_gid}/list", body)
    output(data, pretty=ctx.obj["pretty"])


@section_group.command("get")
@click.argument("gid")
@click.pass_context
def section_get(ctx: click.Context, gid: str) -> None:
    """Get section details."""
    client = require_client(ctx)
    data = client.get(f"/list/{gid}")
    output(data, pretty=ctx.obj["pretty"])
