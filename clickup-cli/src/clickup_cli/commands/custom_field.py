"""Custom field commands."""

import click

from clickup_cli.main import require_client
from clickup_cli.output import output, output_error
import sys


@click.group("custom-field")
def custom_field_group() -> None:
    """Manage custom fields."""


@custom_field_group.command("get")
@click.argument("gid")
@click.option("--section", "list_id", required=True, help="Section (list) ID to look up field")
@click.pass_context
def cf_get(ctx: click.Context, gid: str, list_id: str) -> None:
    """Get custom field details with options."""
    client = require_client(ctx)
    data = client.get(f"/list/{list_id}/field")
    fields = data.get("fields", []) if isinstance(data, dict) else data
    for field in fields:
        if field.get("id") == gid:
            output(field, pretty=ctx.obj["pretty"])
            return
    output_error(f"Field '{gid}' not found in list {list_id}", pretty=ctx.obj["pretty"])
    sys.exit(1)


@custom_field_group.command("list-options")
@click.argument("gid")
@click.option("--section", "list_id", required=True, help="Section (list) ID to look up field")
@click.pass_context
def cf_list_options(ctx: click.Context, gid: str, list_id: str) -> None:
    """List dropdown/label options of a custom field."""
    client = require_client(ctx)
    data = client.get(f"/list/{list_id}/field")
    fields = data.get("fields", []) if isinstance(data, dict) else data
    for field in fields:
        if field.get("id") == gid:
            type_config = field.get("type_config", {})
            options = type_config.get("options", [])
            output(options, pretty=ctx.obj["pretty"])
            return
    output_error(f"Field '{gid}' not found in list {list_id}", pretty=ctx.obj["pretty"])
    sys.exit(1)


@custom_field_group.command("set")
@click.argument("task_id")
@click.option("--field", "field_id", required=True, help="Custom field ID")
@click.option("--value", required=True, help="Value to set")
@click.pass_context
def cf_set(ctx: click.Context, task_id: str, field_id: str, value: str) -> None:
    """Set a custom field value on a task."""
    client = require_client(ctx)
    # Try to parse as number/bool for non-string fields
    parsed: object = value
    if value.lower() == "true":
        parsed = True
    elif value.lower() == "false":
        parsed = False
    else:
        try:
            parsed = int(value)
        except ValueError:
            try:
                parsed = float(value)
            except ValueError:
                pass
    data = client.post(f"/task/{task_id}/field/{field_id}", {"value": parsed})
    output(data, pretty=ctx.obj["pretty"])


@custom_field_group.command("remove")
@click.argument("task_id")
@click.option("--field", "field_id", required=True, help="Custom field ID")
@click.pass_context
def cf_remove(ctx: click.Context, task_id: str, field_id: str) -> None:
    """Remove a custom field value from a task."""
    client = require_client(ctx)
    data = client.delete(f"/task/{task_id}/field/{field_id}")
    output(data or {"ok": True}, pretty=ctx.obj["pretty"])
