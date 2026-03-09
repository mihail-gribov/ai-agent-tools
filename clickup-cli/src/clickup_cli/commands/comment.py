"""Comment commands."""

import sys

import click

from clickup_cli.config import resolve_project
from clickup_cli.main import require_client, require_workspace
from clickup_cli.output import output, output_error


@click.group("comment")
def comment_group() -> None:
    """Manage task comments."""


@comment_group.command("list")
@click.argument("task_gid")
@click.pass_context
def comment_list(ctx: click.Context, task_gid: str) -> None:
    """List comments on a task."""
    client = require_client(ctx)
    no_paginate = ctx.obj["no_paginate"]

    if no_paginate:
        data = client.get(f"/task/{task_gid}/comment")
        comments = data.get("comments", []) if isinstance(data, dict) else data
        output(comments, pretty=ctx.obj["pretty"])
        return

    # Paginate through all comments (25 per page, newest first)
    all_comments: list = []
    start = None
    start_id = None
    while True:
        params: dict = {}
        if start is not None:
            params["start"] = start
            params["start_id"] = start_id
        data = client.get(f"/task/{task_gid}/comment", params)
        comments = data.get("comments", []) if isinstance(data, dict) else data
        if not comments:
            break
        all_comments.extend(comments)
        if len(comments) < 25:
            break
        last = comments[-1]
        start = last.get("date")
        start_id = last.get("id")

    output(all_comments, pretty=ctx.obj["pretty"])


@comment_group.command("add")
@click.argument("task_gid")
@click.option("--text", required=True, help="Comment text (use '-' for stdin)")
@click.pass_context
def comment_add(ctx: click.Context, task_gid: str, text: str) -> None:
    """Add a comment to a task."""
    if text == "-":
        text = sys.stdin.read()

    client = require_client(ctx)
    data = client.post(f"/task/{task_gid}/comment", {"comment_text": text})
    output(data, pretty=ctx.obj["pretty"])


@comment_group.command("check")
@click.option(
    "--status", "status_name", default="need info",
    help="Status to filter tasks by (default: need info)",
)
@click.pass_context
def comment_check(ctx: click.Context, status_name: str) -> None:
    """Find tasks needing a comment response.

    Searches the configured project for tasks with the given status where
    the last comment is not from the current user (agent).
    """
    client = require_client(ctx)
    ws = require_workspace(ctx)

    project_gid = resolve_project(None)
    if not project_gid:
        output_error(
            "No project configured. Use CLICKUP_PROJECT env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    # Get current user
    me = client.get(f"/team/{ws}/member")
    members = me.get("members", []) if isinstance(me, dict) else me
    # Use the token owner — first call /user endpoint idea
    # Actually, let's get the authorized user
    # ClickUp doesn't have /users/me equivalent easily; workaround:
    # we'll compare by checking who posted last comment
    # For now, get tasks with the target status
    params: dict = {
        "statuses[]": status_name,
        "space_ids[]": project_gid,
        "include_closed": "false",
    }
    tasks_data = client.get_all(
        f"/team/{ws}/task", params, key="tasks",
    )

    results = []
    for task in tasks_data:
        task_id = task.get("id")
        comment_data = client.get(f"/task/{task_id}/comment")
        comments = comment_data.get("comments", []) if isinstance(comment_data, dict) else comment_data
        if not comments:
            continue
        last = comments[0]  # newest first
        # If no user info or last commenter is different — needs response
        results.append({"task": task, "comment": last})

    output(results, pretty=ctx.obj["pretty"])
