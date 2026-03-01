"""CLI entrypoint with global options and error handling."""

import sys

import click

from asana_cli.client import AsanaAPIError, AsanaClient
from asana_cli.config import resolve_token, resolve_workspace
from asana_cli.output import output_error


class AsanaCLI(click.Group):
    """Custom group that catches AsanaAPIError and outputs JSON errors."""

    def invoke(self, ctx: click.Context) -> None:
        try:
            super().invoke(ctx)
        except AsanaAPIError as e:
            output_error(e.message, pretty=ctx.params.get("pretty", False))
            ctx.exit(1)


@click.group(cls=AsanaCLI)
@click.option("--token", envvar="ASANA_TOKEN", default=None, help="Asana PAT")
@click.option("--workspace", default=None, help="Workspace GID")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output")
@click.option("--fields", default=None, help="Comma-separated opt_fields override")
@click.option("--no-paginate", is_flag=True, help="Disable auto-pagination")
@click.pass_context
def cli(
    ctx: click.Context,
    token: str | None,
    workspace: str | None,
    pretty: bool,
    fields: str | None,
    no_paginate: bool,
) -> None:
    """Asana CLI for AI agents."""
    ctx.ensure_object(dict)
    ctx.obj.setdefault("pretty", pretty)
    ctx.obj.setdefault("fields", fields)
    ctx.obj.setdefault("no_paginate", no_paginate)
    ctx.obj.setdefault("workspace_gid", resolve_workspace(workspace))

    if "client" not in ctx.obj:
        resolved_token = resolve_token(token)
        if resolved_token:
            ctx.obj["client"] = AsanaClient(resolved_token)
        else:
            ctx.obj["client"] = None


def require_client(ctx: click.Context) -> AsanaClient:
    client = ctx.obj.get("client")
    if client is None:
        output_error(
            "No token configured. Use --token, ASANA_TOKEN env var, "
            "or 'asana config set --token <pat>'.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    return client


def require_workspace(ctx: click.Context) -> str:
    ws = ctx.obj.get("workspace_gid")
    if not ws:
        output_error(
            "No workspace configured. Use --workspace, ASANA_WORKSPACE env var, "
            "or 'asana config set --workspace <gid>'.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    return ws


def opt_fields_params(
    ctx: click.Context, defaults: str | None = None
) -> dict:
    """Build opt_fields query params from --fields override or defaults."""
    fields = ctx.obj.get("fields") or defaults
    if fields:
        return {"opt_fields": fields}
    return {}


# Register command groups
from asana_cli.commands.config_cmd import config_group  # noqa: E402
from asana_cli.commands.workspace import workspace_group  # noqa: E402
from asana_cli.commands.project import project_group  # noqa: E402
from asana_cli.commands.section import section_group  # noqa: E402
from asana_cli.commands.task import task_group  # noqa: E402
from asana_cli.commands.comment import comment_group  # noqa: E402
from asana_cli.commands.tag import tag_group  # noqa: E402

cli.add_command(config_group, "config")
cli.add_command(workspace_group, "workspace")
cli.add_command(project_group, "project")
cli.add_command(section_group, "section")
cli.add_command(task_group, "task")
cli.add_command(comment_group, "comment")
cli.add_command(tag_group, "tag")
