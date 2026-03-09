"""Tag commands."""

import click

from asana_cli.main import opt_fields_params, require_client, require_workspace
from asana_cli.output import output


@click.group("tag")
def tag_group() -> None:
    """Manage tags."""


@tag_group.command("list")
@click.pass_context
def tag_list(ctx: click.Context) -> None:
    """List tags in workspace."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    params = opt_fields_params(ctx, "gid,name,color")
    params["workspace"] = ws
    data = client.get_all("/tags", params, no_paginate=ctx.obj["no_paginate"])
    output(data, pretty=ctx.obj["pretty"])


@tag_group.command("create")
@click.option("--name", required=True, help="Tag name")
@click.option("--color", default=None, help="Tag color (e.g. light-green, dark-blue)")
@click.pass_context
def tag_create(ctx: click.Context, name: str, color: str | None) -> None:
    """Create a new tag."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    body: dict = {"name": name, "workspace": ws}
    if color:
        body["color"] = color
    data = client.post("/tags", body)
    output(data, pretty=ctx.obj["pretty"])


@tag_group.command("get")
@click.argument("gid")
@click.pass_context
def tag_get(ctx: click.Context, gid: str) -> None:
    """Get tag details."""
    client = require_client(ctx)
    params = opt_fields_params(ctx)
    data = client.get(f"/tags/{gid}", params)
    output(data, pretty=ctx.obj["pretty"])
