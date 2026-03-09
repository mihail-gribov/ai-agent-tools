"""Custom field commands — enum options management."""

import click

from asana_cli.main import opt_fields_params, require_client
from asana_cli.output import output


@click.group("custom-field")
def custom_field_group() -> None:
    """Manage custom fields."""


@custom_field_group.command("get")
@click.argument("gid")
@click.pass_context
def cf_get(ctx: click.Context, gid: str) -> None:
    """Get custom field details with enum options."""
    client = require_client(ctx)
    defaults = (
        "gid,name,type,enum_options.gid,enum_options.name,"
        "enum_options.color,enum_options.enabled"
    )
    params = opt_fields_params(ctx, defaults)
    data = client.get(f"/custom_fields/{gid}", params)
    output(data, pretty=ctx.obj["pretty"])


@custom_field_group.command("list-options")
@click.argument("gid")
@click.pass_context
def cf_list_options(ctx: click.Context, gid: str) -> None:
    """List enum options of a custom field."""
    client = require_client(ctx)
    defaults = "gid,name,color,enabled"
    params = opt_fields_params(ctx, defaults)
    data = client.get(f"/custom_fields/{gid}", {
        "opt_fields": "enum_options.gid,enum_options.name,enum_options.color,enum_options.enabled",
    })
    options = data.get("enum_options", [])
    output(options, pretty=ctx.obj["pretty"])


@custom_field_group.command("add-option")
@click.argument("gid")
@click.option("--name", required=True, help="Option display name")
@click.option("--color", default=None, help="Option color (e.g. cool-gray, red, blue, green)")
@click.pass_context
def cf_add_option(ctx: click.Context, gid: str, name: str, color: str | None) -> None:
    """Add an enum option to a custom field."""
    client = require_client(ctx)
    body: dict = {"name": name}
    if color:
        body["color"] = color
    data = client.post(f"/custom_fields/{gid}/enum_options", body)
    output(data, pretty=ctx.obj["pretty"])


@custom_field_group.command("update-option")
@click.argument("option_gid")
@click.option("--name", default=None, help="New display name")
@click.option("--color", default=None, help="New color")
@click.option("--enabled/--disabled", default=None, help="Enable or disable option")
@click.pass_context
def cf_update_option(
    ctx: click.Context,
    option_gid: str,
    name: str | None,
    color: str | None,
    enabled: bool | None,
) -> None:
    """Update an enum option (name, color, enabled)."""
    client = require_client(ctx)
    body: dict = {}
    if name is not None:
        body["name"] = name
    if color is not None:
        body["color"] = color
    if enabled is not None:
        body["enabled"] = enabled
    if not body:
        click.echo("Error: specify at least one of --name, --color, --enabled/--disabled", err=True)
        ctx.exit(1)
        return
    data = client.put(f"/enum_options/{option_gid}", body)
    output(data, pretty=ctx.obj["pretty"])
