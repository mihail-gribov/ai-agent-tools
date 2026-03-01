"""Section commands."""

import click

from asana_cli.main import opt_fields_params, require_client
from asana_cli.output import output


@click.group("section")
def section_group() -> None:
    """Manage sections."""


@section_group.command("list")
@click.option("--project", "project_gid", required=True, help="Project GID")
@click.pass_context
def section_list(ctx: click.Context, project_gid: str) -> None:
    """List sections in a project."""
    client = require_client(ctx)
    params = opt_fields_params(ctx, "gid,name")
    data = client.get_all(
        f"/projects/{project_gid}/sections",
        params,
        no_paginate=ctx.obj["no_paginate"],
    )
    output(data, pretty=ctx.obj["pretty"])


@section_group.command("get")
@click.argument("gid")
@click.pass_context
def section_get(ctx: click.Context, gid: str) -> None:
    """Get section details."""
    client = require_client(ctx)
    params = opt_fields_params(ctx)
    data = client.get(f"/sections/{gid}", params)
    output(data, pretty=ctx.obj["pretty"])
