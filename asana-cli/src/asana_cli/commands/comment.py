"""Comment (story) commands."""

import sys

import click

from asana_cli.rich_text import md_to_html
from asana_cli.commands.task import _get_status_info
from asana_cli.config import resolve_project
from asana_cli.main import opt_fields_params, require_client, require_workspace
from asana_cli.output import output, output_error


@click.group("comment")
def comment_group() -> None:
    """Manage task comments."""


@comment_group.command("list")
@click.argument("task_gid")
@click.pass_context
def comment_list(ctx: click.Context, task_gid: str) -> None:
    """List comments/stories on a task."""
    client = require_client(ctx)
    params = opt_fields_params(ctx, "gid,text,created_by.name,created_at,type")
    data = client.get_all(
        f"/tasks/{task_gid}/stories",
        params,
        no_paginate=ctx.obj["no_paginate"],
    )
    # Filter to only comment-type stories
    comments = [s for s in data if s.get("type") == "comment"]
    output(comments, pretty=ctx.obj["pretty"])


@comment_group.command("add")
@click.argument("task_gid")
@click.option("--text", required=True, help="Comment text (use '-' for stdin)")
@click.pass_context
def comment_add(ctx: click.Context, task_gid: str, text: str) -> None:
    """Add a comment to a task."""
    if text == "-":
        text = sys.stdin.read()

    client = require_client(ctx)
    data = client.post(f"/tasks/{task_gid}/stories", {"html_text": md_to_html(text)})
    output(data, pretty=ctx.obj["pretty"])


@comment_group.command("check")
@click.option(
    "--status", "status_name", default="Need info",
    help="Status to filter tasks by (default: Need info)",
)
@click.pass_context
def comment_check(
    ctx: click.Context,
    status_name: str,
) -> None:
    """Find tasks needing a comment response.

    Searches the configured project for tasks with the given status where
    the last comment is not from the current user (agent).
    """
    client = require_client(ctx)
    ws = require_workspace(ctx)

    project_gid = resolve_project(None)
    if not project_gid:
        output_error(
            "No project configured. Use 'asana config set --project <gid>'.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    info = _get_status_info(client, project_gid)
    status_field = info.get("status_field")
    if not status_field:
        output_error(
            f"No status enum field found in project {project_gid}.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    status_value = info.get("statuses", {}).get(status_name)
    if not status_value:
        available = ", ".join(info.get("statuses", {}).keys())
        output_error(
            f"Status '{status_name}' not found. Available: {available}",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    me = client.get("/users/me", {"opt_fields": "gid"})
    my_gid = me["gid"]

    tasks = client.get(
        f"/workspaces/{ws}/tasks/search",
        {
            "opt_fields": "gid,name,assignee.name,due_on",
            "projects.any": project_gid,
            "completed": "false",
            f"custom_fields.{status_field}.value": status_value,
            "sort_by": "created_at",
        },
    )
    if not isinstance(tasks, list):
        tasks = [tasks] if tasks else []

    results = []
    for task in tasks:
        stories = client.get_all(
            f"/tasks/{task['gid']}/stories",
            {"opt_fields": "gid,text,created_by.gid,created_by.name,created_at,type"},
        )
        comments = [s for s in stories if s.get("type") == "comment"]
        if not comments:
            continue
        last = comments[-1]
        if last.get("created_by", {}).get("gid") != my_gid:
            results.append({"task": task, "comment": last})

    output(results, pretty=ctx.obj["pretty"])
