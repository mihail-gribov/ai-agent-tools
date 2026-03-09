"""Project commands."""

import click

from asana_cli.main import opt_fields_params, require_client, require_workspace
from asana_cli.output import output


@click.group("project")
def project_group() -> None:
    """Manage projects."""


@project_group.command("list")
@click.option("--archived", is_flag=True, help="Include archived projects")
@click.pass_context
def project_list(ctx: click.Context, archived: bool) -> None:
    """List projects in workspace."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    params = opt_fields_params(ctx, "gid,name,archived,color")
    params["workspace"] = ws
    params["archived"] = str(archived).lower()
    data = client.get_all("/projects", params, no_paginate=ctx.obj["no_paginate"])
    output(data, pretty=ctx.obj["pretty"])


@project_group.command("create")
@click.option("--name", required=True, help="Project name")
@click.option("--color", default=None, help="Project color (e.g. light-green, dark-blue)")
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
    """Create a new project."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    body: dict = {"name": name, "workspace": ws, "default_view": layout}
    if color:
        body["color"] = color
    if public:
        body["public"] = True
    data = client.post("/projects", body)
    output(data, pretty=ctx.obj["pretty"])


@project_group.command("get")
@click.argument("gid")
@click.pass_context
def project_get(ctx: click.Context, gid: str) -> None:
    """Get project details."""
    client = require_client(ctx)
    params = opt_fields_params(ctx)
    data = client.get(f"/projects/{gid}", params)
    output(data, pretty=ctx.obj["pretty"])
