"""Workspace commands."""

import click

from asana_cli.main import opt_fields_params, require_client
from asana_cli.output import output


@click.group("workspace")
def workspace_group() -> None:
    """Manage workspaces."""


@workspace_group.command("list")
@click.pass_context
def workspace_list(ctx: click.Context) -> None:
    """List accessible workspaces."""
    client = require_client(ctx)
    params = opt_fields_params(ctx, "gid,name")
    data = client.get_all("/workspaces", params, no_paginate=ctx.obj["no_paginate"])
    output(data, pretty=ctx.obj["pretty"])
