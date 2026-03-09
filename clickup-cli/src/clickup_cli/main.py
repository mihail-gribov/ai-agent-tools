"""CLI entrypoint with global options and error handling."""

import sys

import click

from importlib.metadata import version

from clickup_cli.client import ClickUpAPIError, ClickUpClient
from clickup_cli.config import resolve_token, resolve_workspace
from clickup_cli.output import output_error


class ClickUpCLI(click.Group):
    """Custom group that catches ClickUpAPIError and outputs JSON errors."""

    def invoke(self, ctx: click.Context) -> None:
        try:
            super().invoke(ctx)
        except ClickUpAPIError as e:
            output_error(e.message, pretty=ctx.params.get("pretty", False))
            ctx.exit(1)


@click.group(cls=ClickUpCLI)
@click.version_option(version=version("clickup-cli"), prog_name="clickup-cli")
@click.option("--token", envvar="CLICKUP_TOKEN", default=None, help="ClickUp API token")
@click.option("--workspace", default=None, help="Workspace (team) ID")
@click.option("--pretty", is_flag=True, help="Pretty-print JSON output")
@click.option("--fields", default=None, help="Comma-separated fields filter (client-side)")
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
    """ClickUp CLI for AI agents."""
    ctx.ensure_object(dict)
    ctx.obj.setdefault("pretty", pretty)
    ctx.obj.setdefault("fields", fields)
    ctx.obj.setdefault("no_paginate", no_paginate)
    ctx.obj.setdefault("workspace_gid", resolve_workspace(workspace))

    if "client" not in ctx.obj:
        resolved_token = resolve_token(token)
        if resolved_token:
            ctx.obj["client"] = ClickUpClient(resolved_token)
        else:
            ctx.obj["client"] = None


def require_client(ctx: click.Context) -> ClickUpClient:
    client = ctx.obj.get("client")
    if client is None:
        output_error(
            "No token configured. Use --token or CLICKUP_TOKEN env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    return client


def require_workspace(ctx: click.Context) -> str:
    ws = ctx.obj.get("workspace_gid")
    if not ws:
        output_error(
            "No workspace configured. Use --workspace or CLICKUP_WORKSPACE env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    return ws


# Register command groups
from clickup_cli.commands.config_cmd import config_group  # noqa: E402
from clickup_cli.commands.workspace import workspace_group  # noqa: E402
from clickup_cli.commands.project import project_group  # noqa: E402
from clickup_cli.commands.section import section_group  # noqa: E402
from clickup_cli.commands.folder import folder_group  # noqa: E402
from clickup_cli.commands.task import task_group  # noqa: E402
from clickup_cli.commands.comment import comment_group  # noqa: E402
from clickup_cli.commands.tag import tag_group  # noqa: E402
from clickup_cli.commands.custom_field import custom_field_group  # noqa: E402

cli.add_command(config_group, "config")
cli.add_command(workspace_group, "workspace")
cli.add_command(project_group, "project")
cli.add_command(section_group, "section")
cli.add_command(folder_group, "folder")
cli.add_command(task_group, "task")
cli.add_command(comment_group, "comment")
cli.add_command(tag_group, "tag")
cli.add_command(custom_field_group, "custom-field")
