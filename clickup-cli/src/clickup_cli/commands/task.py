"""Task commands — CRUD, search, organization."""

import json
import sys

import click

from clickup_cli.config import resolve_project
from clickup_cli.main import require_client, require_workspace
from clickup_cli.output import output, output_error


def _date_to_ms(date_str: str) -> str:
    """Convert YYYY-MM-DD to Unix timestamp in milliseconds."""
    from datetime import datetime, timezone
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return str(int(dt.timestamp() * 1000))


def parse_custom_fields(values: tuple[str, ...]) -> list[dict]:
    """Parse --custom-field id=val pairs into ClickUp API format."""
    result = []
    for item in values:
        fid, _, val = item.partition("=")
        result.append({"id": fid, "value": val})
    return result


@click.group("task")
def task_group() -> None:
    """Manage tasks."""


@task_group.command("list")
@click.option("--project", "project_gid", default=None, help="Project (space) ID")
@click.option("--section", "section_gid", default=None, help="Section (list) ID")
@click.option("--assignee", default=None, help="Assignee user ID")
@click.option("--completed", is_flag=True, default=False, help="Include completed tasks")
@click.option("--limit", default=None, type=int, help="Max results")
@click.pass_context
def task_list(
    ctx: click.Context,
    project_gid: str | None,
    section_gid: str | None,
    assignee: str | None,
    completed: bool,
    limit: int | None,
) -> None:
    """List tasks by project, section, or assignee."""
    client = require_client(ctx)

    if section_gid:
        # List tasks in a specific list
        params: dict = {}
        if not completed:
            params["include_closed"] = "false"
        if assignee:
            params["assignees[]"] = assignee
        data = client.get_all(
            f"/list/{section_gid}/task", params,
            key="tasks", no_paginate=ctx.obj["no_paginate"],
        )
    elif project_gid or assignee:
        # Filtered team-level search
        ws = require_workspace(ctx)
        params = {}
        if project_gid:
            params["space_ids[]"] = project_gid
        if assignee:
            params["assignees[]"] = assignee
        if not completed:
            params["include_closed"] = "false"
        data = client.get_all(
            f"/team/{ws}/task", params,
            key="tasks", no_paginate=ctx.obj["no_paginate"],
        )
    else:
        click.echo(
            "Error: specify --project, --section, or --assignee", err=True
        )
        ctx.exit(1)
        return

    if limit:
        data = data[:limit]
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("search")
@click.option("--text", default=None, help="Filter by task name (client-side)")
@click.option("--assignee", default=None, help="Assignee user ID")
@click.option("--project", "project_gid", default=None, help="Project (space) ID")
@click.option("--section", "section_gid", default=None, help="Section (list) ID")
@click.option("--tag", default=None, help="Tag name")
@click.option("--completed", is_flag=True, default=False, help="Include completed")
@click.option("--due-before", default=None, help="Due date before (YYYY-MM-DD)")
@click.option("--due-after", default=None, help="Due date after (YYYY-MM-DD)")
@click.option("--modified-after", default=None, help="Modified after (YYYY-MM-DD)")
@click.option(
    "--sort-by",
    default=None,
    type=click.Choice(["due_date", "created", "updated"]),
    help="Sort order",
)
@click.option(
    "--custom-field",
    "custom_fields",
    multiple=True,
    help="Filter by custom field: id=value (repeatable)",
)
@click.option("--status", default=None, help="Filter by status name")
@click.pass_context
def task_search(
    ctx: click.Context,
    text: str | None,
    assignee: str | None,
    project_gid: str | None,
    section_gid: str | None,
    tag: str | None,
    completed: bool,
    due_before: str | None,
    due_after: str | None,
    modified_after: str | None,
    sort_by: str | None,
    custom_fields: tuple[str, ...],
    status: str | None,
) -> None:
    """Search tasks in workspace."""
    client = require_client(ctx)
    ws = require_workspace(ctx)

    params: dict = {}
    if assignee:
        params["assignees[]"] = assignee
    if project_gid:
        params["space_ids[]"] = project_gid
    if section_gid:
        params["list_ids[]"] = section_gid
    if tag:
        params["tags[]"] = tag
    if status:
        params["statuses[]"] = status
    if not completed:
        params["include_closed"] = "false"
    if due_before:
        params["due_date_lt"] = _date_to_ms(due_before)
    if due_after:
        params["due_date_gt"] = _date_to_ms(due_after)
    if modified_after:
        params["date_updated_gt"] = _date_to_ms(modified_after)
    if sort_by:
        params["order_by"] = sort_by
    if custom_fields:
        cf_filters = []
        for cf in custom_fields:
            fid, _, val = cf.partition("=")
            cf_filters.append({"field_id": fid, "operator": "=", "value": val})
        params["custom_fields"] = json.dumps(cf_filters)

    data = client.get_all(
        f"/team/{ws}/task", params,
        key="tasks", no_paginate=ctx.obj["no_paginate"],
    )

    # Client-side text filter (ClickUp v2 has no server-side text search)
    if text:
        text_lower = text.lower()
        data = [t for t in data if text_lower in t.get("name", "").lower()]

    output(data, pretty=ctx.obj["pretty"])


@task_group.command("get")
@click.argument("gid")
@click.option("--history", is_flag=True, default=False, help="(not supported in ClickUp)")
@click.pass_context
def task_get(ctx: click.Context, gid: str, history: bool) -> None:
    """Get full task details."""
    client = require_client(ctx)
    params: dict = {"include_subtasks": "true"}
    data = client.get(f"/task/{gid}", params)
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("create")
@click.option("--name", required=True, help="Task name")
@click.option("--notes", default=None, help="Task description (use '-' for stdin)")
@click.option("--assignee", default=None, help="Assignee user ID")
@click.option("--project", "project_gid", default=None, help="Project (space) ID (unused, use --section)")
@click.option("--section", "section_gid", default=None, help="Section (list) ID — required")
@click.option("--parent", "parent_gid", default=None, help="Parent task ID (for subtasks)")
@click.option("--due-on", default=None, help="Due date (YYYY-MM-DD)")
@click.option("--start-on", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--tags", default=None, help="Comma-separated tag names")
@click.option("--status", default=None, help="Task status name")
@click.option(
    "--custom-field",
    "custom_fields",
    multiple=True,
    help="Custom field id=value (repeatable)",
)
@click.pass_context
def task_create(
    ctx: click.Context,
    name: str,
    notes: str | None,
    assignee: str | None,
    project_gid: str | None,
    section_gid: str | None,
    parent_gid: str | None,
    due_on: str | None,
    start_on: str | None,
    tags: str | None,
    status: str | None,
    custom_fields: tuple[str, ...],
) -> None:
    """Create a new task."""
    client = require_client(ctx)

    if notes == "-":
        notes = sys.stdin.read()

    if not section_gid and not parent_gid:
        output_error(
            "Task creation requires --section (list ID) or --parent (for subtasks).",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    body: dict = {"name": name}
    if notes is not None:
        body["markdown_description"] = notes
    if assignee:
        body["assignees"] = [int(assignee)]
    if parent_gid:
        body["parent"] = parent_gid
    if due_on:
        body["due_date"] = int(_date_to_ms(due_on))
    if start_on:
        body["start_date"] = int(_date_to_ms(start_on))
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if status:
        body["status"] = status
    if custom_fields:
        body["custom_fields"] = parse_custom_fields(custom_fields)

    # Create in list or as subtask
    if parent_gid and not section_gid:
        # Get parent's list to create subtask
        parent = client.get(f"/task/{parent_gid}")
        section_gid = parent.get("list", {}).get("id")
        if not section_gid:
            output_error("Cannot determine list from parent task.", pretty=ctx.obj["pretty"])
            sys.exit(1)

    data = client.post(f"/list/{section_gid}/task", body)
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("update")
@click.argument("gid")
@click.option("--name", default=None, help="New name")
@click.option("--notes", default=None, help="New description (use '-' for stdin)")
@click.option("--assignee", default=None, help="Assignee user ID")
@click.option("--due-on", default=None, help="Due date (YYYY-MM-DD)")
@click.option("--start-on", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--completed/--no-completed", default=None, help="Mark completed/incomplete")
@click.option("--status", default=None, help="Set task status name")
@click.option(
    "--custom-field",
    "custom_fields",
    multiple=True,
    help="Custom field id=value (repeatable) — uses separate API calls",
)
@click.option(
    "--archive-notes",
    is_flag=True,
    default=False,
    help="Save current description as a comment before replacing",
)
@click.pass_context
def task_update(
    ctx: click.Context,
    gid: str,
    name: str | None,
    notes: str | None,
    assignee: str | None,
    due_on: str | None,
    start_on: str | None,
    completed: bool | None,
    status: str | None,
    custom_fields: tuple[str, ...],
    archive_notes: bool,
) -> None:
    """Update a task."""
    client = require_client(ctx)

    if notes == "-":
        notes = sys.stdin.read()

    # Archive current description as a comment before overwriting
    if archive_notes and notes is not None:
        task = client.get(f"/task/{gid}")
        old_desc = (task.get("description") or "").strip()
        if old_desc:
            comment = f"Description archived before update:\n\n{old_desc}"
            client.post(f"/task/{gid}/comment", {"comment_text": comment})

    body: dict = {}
    if name is not None:
        body["name"] = name
    if notes is not None:
        body["markdown_description"] = notes
    if assignee is not None:
        body["assignees"] = {"add": [int(assignee)]}
    if due_on is not None:
        body["due_date"] = int(_date_to_ms(due_on))
    if start_on is not None:
        body["start_date"] = int(_date_to_ms(start_on))
    if completed is True:
        body["status"] = "complete"
    elif completed is False:
        body["status"] = "to do"
    if status is not None:
        body["status"] = status

    data = client.put(f"/task/{gid}", body)

    # Custom fields require separate API calls
    for cf in custom_fields:
        fid, _, val = cf.partition("=")
        parsed: object = val
        if val.lower() == "true":
            parsed = True
        elif val.lower() == "false":
            parsed = False
        else:
            try:
                parsed = int(val)
            except ValueError:
                try:
                    parsed = float(val)
                except ValueError:
                    pass
        client.post(f"/task/{gid}/field/{fid}", {"value": parsed})

    output(data, pretty=ctx.obj["pretty"])


@task_group.command("complete")
@click.argument("gid")
@click.pass_context
def task_complete(ctx: click.Context, gid: str) -> None:
    """Mark a task as complete."""
    client = require_client(ctx)
    data = client.put(f"/task/{gid}", {"status": "complete"})
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("delete")
@click.argument("gid")
@click.pass_context
def task_delete(ctx: click.Context, gid: str) -> None:
    """Delete a task."""
    client = require_client(ctx)
    client.delete(f"/task/{gid}")
    output({"deleted": True, "gid": gid}, pretty=ctx.obj["pretty"])


@task_group.command("subtasks")
@click.argument("gid")
@click.pass_context
def task_subtasks(ctx: click.Context, gid: str) -> None:
    """List subtasks of a task."""
    client = require_client(ctx)
    params: dict = {"include_subtasks": "true"}
    data = client.get(f"/task/{gid}", params)
    subtasks = data.get("subtasks", []) if isinstance(data, dict) else []
    output(subtasks, pretty=ctx.obj["pretty"])


@task_group.command("add-project")
@click.argument("gid")
@click.option("--project", "project_gid", required=True, help="Project (space) ID")
@click.option("--section", "section_gid", default=None, help="Section (list) ID")
@click.pass_context
def task_add_project(
    ctx: click.Context, gid: str, project_gid: str, section_gid: str | None
) -> None:
    """Add a task to a list (move to list)."""
    client = require_client(ctx)
    if section_gid:
        # Move to specific list
        data = client.put(f"/task/{gid}", {"list_id": section_gid})
    else:
        output_error(
            "ClickUp requires a specific list (--section) to add task to.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("remove-project")
@click.argument("gid")
@click.option("--project", "project_gid", required=True, help="Project (space) ID")
@click.pass_context
def task_remove_project(ctx: click.Context, gid: str, project_gid: str) -> None:
    """Remove a task from a project (not supported in ClickUp — tasks must belong to a list)."""
    output_error(
        "ClickUp tasks must belong to a list. Use 'task move' to relocate.",
        pretty=ctx.obj["pretty"],
    )
    sys.exit(1)


@task_group.command("move")
@click.argument("gid")
@click.option("--section", "section_gid", required=True, help="Target section (list) ID")
@click.pass_context
def task_move(ctx: click.Context, gid: str, section_gid: str) -> None:
    """Move a task to a different section (list)."""
    client = require_client(ctx)
    data = client.put(f"/task/{gid}", {"list_id": section_gid})
    output({"ok": True}, pretty=ctx.obj["pretty"])


# -- Dependencies --


@task_group.command("dependencies")
@click.argument("gid")
@click.pass_context
def task_dependencies(ctx: click.Context, gid: str) -> None:
    """List tasks this task is waiting on (depends on)."""
    client = require_client(ctx)
    data = client.get(f"/task/{gid}")
    deps = data.get("dependencies", []) if isinstance(data, dict) else []
    output(deps, pretty=ctx.obj["pretty"])


@task_group.command("dependents")
@click.argument("gid")
@click.pass_context
def task_dependents(ctx: click.Context, gid: str) -> None:
    """List tasks that are waiting on (blocked by) this task."""
    client = require_client(ctx)
    data = client.get(f"/task/{gid}")
    deps = data.get("dependents", []) if isinstance(data, dict) else []
    output(deps, pretty=ctx.obj["pretty"])


@task_group.command("add-dependency")
@click.argument("gid")
@click.option("--dependency", required=True, help="ID of the task this task depends on")
@click.pass_context
def task_add_dependency(ctx: click.Context, gid: str, dependency: str) -> None:
    """Mark that this task depends on (is waiting on) another task."""
    client = require_client(ctx)
    client.post(f"/task/{gid}/dependency", {"depends_on": dependency})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("remove-dependency")
@click.argument("gid")
@click.option("--dependency", required=True, help="ID of the dependency to remove")
@click.pass_context
def task_remove_dependency(ctx: click.Context, gid: str, dependency: str) -> None:
    """Remove a dependency from this task."""
    client = require_client(ctx)
    client.delete(f"/task/{gid}/dependency", {"depends_on": dependency})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("add-dependent")
@click.argument("gid")
@click.option("--dependent", required=True, help="ID of the task blocked by this task")
@click.pass_context
def task_add_dependent(ctx: click.Context, gid: str, dependent: str) -> None:
    """Mark that another task is blocked by (waiting on) this task."""
    client = require_client(ctx)
    client.post(f"/task/{gid}/dependency", {"dependency_of": dependent})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("remove-dependent")
@click.argument("gid")
@click.option("--dependent", required=True, help="ID of the dependent to remove")
@click.pass_context
def task_remove_dependent(ctx: click.Context, gid: str, dependent: str) -> None:
    """Remove a dependent from this task."""
    client = require_client(ctx)
    client.delete(f"/task/{gid}/dependency", {"dependency_of": dependent})
    output({"ok": True}, pretty=ctx.obj["pretty"])


# -- Smart commands --


@task_group.command("next")
@click.option("--project", "project_gid", default=None, help="Project (space) ID")
@click.option("--status", "status_name", default="to do", help="Status name to look for (default: to do)")
@click.option("--assignee", default=None, help="Assignee user ID")
@click.pass_context
def task_next(
    ctx: click.Context,
    project_gid: str | None,
    status_name: str,
    assignee: str | None,
) -> None:
    """Find the next actionable task: matching status and not blocked by incomplete tasks."""
    client = require_client(ctx)
    ws = require_workspace(ctx)

    project_gid = resolve_project(project_gid)
    if not project_gid:
        output_error(
            "No project configured. Use --project or CLICKUP_PROJECT env var.",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    params: dict = {
        "space_ids[]": project_gid,
        "statuses[]": status_name,
        "include_closed": "false",
        "order_by": "created",
    }
    if assignee:
        params["assignees[]"] = assignee

    candidates = client.get_all(
        f"/team/{ws}/task", params, key="tasks",
    )

    # Filter out tasks blocked by incomplete dependencies
    for task in candidates:
        task_detail = client.get(f"/task/{task['id']}")
        deps = task_detail.get("dependencies", [])
        if not deps:
            output(task, pretty=ctx.obj["pretty"])
            return
        # Check if all dependencies are resolved
        all_resolved = True
        for dep in deps:
            dep_id = dep.get("task_id") or dep.get("id")
            if dep_id:
                dep_task = client.get(f"/task/{dep_id}")
                dep_status = dep_task.get("status", {})
                if dep_status.get("type") != "closed":
                    all_resolved = False
                    break
        if all_resolved:
            output(task, pretty=ctx.obj["pretty"])
            return

    output(None, pretty=ctx.obj["pretty"])
