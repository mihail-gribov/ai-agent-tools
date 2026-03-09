"""Tag commands."""

import click

from clickup_cli.main import require_client
from clickup_cli.config import resolve_project
from clickup_cli.output import output, output_error
import sys


@click.group("tag")
def tag_group() -> None:
    """Manage tags."""


@tag_group.command("list")
@click.option("--project", "project_gid", default=None, help="Project (space) ID")
@click.pass_context
def tag_list(ctx: click.Context, project_gid: str | None) -> None:
    """List tags in a project (space)."""
    client = require_client(ctx)
    project_gid = resolve_project(project_gid)
    if not project_gid:
        output_error(
            "No project configured. Use --project or CLICKUP_PROJECT env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    data = client.get(f"/space/{project_gid}/tag")
    tags = data.get("tags", []) if isinstance(data, dict) else data
    output(tags, pretty=ctx.obj["pretty"])


@tag_group.command("create")
@click.option("--name", required=True, help="Tag name")
@click.option("--color", default=None, help="Tag color hex (e.g. #7B68EE)")
@click.option("--project", "project_gid", default=None, help="Project (space) ID")
@click.pass_context
def tag_create(ctx: click.Context, name: str, color: str | None, project_gid: str | None) -> None:
    """Create a new tag."""
    client = require_client(ctx)
    project_gid = resolve_project(project_gid)
    if not project_gid:
        output_error(
            "No project configured. Use --project or CLICKUP_PROJECT env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    body: dict = {"tag": {"name": name}}
    if color:
        body["tag"]["tag_bg"] = color
        body["tag"]["tag_fg"] = color
    data = client.post(f"/space/{project_gid}/tag", body)
    output(data, pretty=ctx.obj["pretty"])


@tag_group.command("get")
@click.argument("gid")
@click.option("--project", "project_gid", default=None, help="Project (space) ID")
@click.pass_context
def tag_get(ctx: click.Context, gid: str, project_gid: str | None) -> None:
    """Get tag details (finds by name in space tags)."""
    client = require_client(ctx)
    project_gid = resolve_project(project_gid)
    if not project_gid:
        output_error(
            "No project configured. Use --project or CLICKUP_PROJECT env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    # ClickUp has no get-tag-by-id; list all and filter
    data = client.get(f"/space/{project_gid}/tag")
    tags = data.get("tags", []) if isinstance(data, dict) else data
    for tag in tags:
        if tag.get("name") == gid:
            output(tag, pretty=ctx.obj["pretty"])
            return
    output_error(f"Tag '{gid}' not found", pretty=ctx.obj["pretty"])
    sys.exit(1)
