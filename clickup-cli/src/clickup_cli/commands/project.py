"""Project commands. Maps to ClickUp Spaces."""

import click

from clickup_cli.main import require_client, require_workspace
from clickup_cli.output import output


@click.group("project")
def project_group() -> None:
    """Manage projects (ClickUp spaces)."""


@project_group.command("list")
@click.option("--archived", is_flag=True, help="Include archived spaces")
@click.pass_context
def project_list(ctx: click.Context, archived: bool) -> None:
    """List projects in workspace."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    params = {"archived": str(archived).lower()}
    data = client.get(f"/team/{ws}/space", params)
    spaces = data.get("spaces", []) if isinstance(data, dict) else data
    output(spaces, pretty=ctx.obj["pretty"])


@project_group.command("create")
@click.option("--name", required=True, help="Project name")
@click.option("--color", default=None, help="Project color hex (e.g. #7B68EE)")
@click.option("--layout", default="board", help="Layout: board or list (default: board)")
@click.option("--public", is_flag=True, default=False, help="Make project public")
@click.pass_context
def project_create(
    ctx: click.Context,
    name: str,
    color: str | None,
    layout: str,
    public: bool,
) -> None:
    """Create a new project (ClickUp space)."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    body: dict = {
        "name": name,
        "multiple_assignees": True,
        "features": {
            "due_dates": {"enabled": True, "start_date": True},
            "tags": {"enabled": True},
            "custom_fields": {"enabled": True},
        },
    }
    if color:
        body["color"] = color
    if public:
        body["admin_can_manage"] = False
    data = client.post(f"/team/{ws}/space", body)
    output(data, pretty=ctx.obj["pretty"])


@project_group.command("get")
@click.argument("gid")
@click.pass_context
def project_get(ctx: click.Context, gid: str) -> None:
    """Get project details."""
    client = require_client(ctx)
    data = client.get(f"/space/{gid}")
    output(data, pretty=ctx.obj["pretty"])
