"""Task commands — CRUD, search, organization."""

import sys

import click

from asana_cli.config import (
    get_project_cache,
    load_config,
    resolve_project,
    save_project_cache,
)
from asana_cli.main import opt_fields_params, require_client, require_workspace
from asana_cli.output import output, output_error


# Known names for the status field (case-insensitive matching)
_STATUS_FIELD_NAMES = {"status", "статус"}


def parse_custom_fields(values: tuple[str, ...]) -> dict:
    """Parse --custom-field gid=val pairs into API format."""
    result = {}
    for item in values:
        gid, _, val = item.partition("=")
        result[gid] = val
    return result


@click.group("task")
def task_group() -> None:
    """Manage tasks."""


@task_group.command("list")
@click.option("--project", "project_gid", default=None, help="Project GID")
@click.option("--section", "section_gid", default=None, help="Section GID")
@click.option("--assignee", default=None, help="Assignee GID or 'me'")
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
    defaults = "gid,name,completed,assignee.name,due_on"
    params = opt_fields_params(ctx, defaults)

    if section_gid:
        path = f"/sections/{section_gid}/tasks"
    elif project_gid:
        path = "/tasks"
        params["project"] = project_gid
    elif assignee:
        path = "/tasks"
        params["assignee"] = assignee
        ws = require_workspace(ctx)
        params["workspace"] = ws
    else:
        click.echo(
            "Error: specify --project, --section, or --assignee", err=True
        )
        ctx.exit(1)
        return

    if not completed:
        params["completed_since"] = "now"
    if limit:
        params["limit"] = limit

    data = client.get_all(path, params, no_paginate=ctx.obj["no_paginate"])
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("search")
@click.option("--text", default=None, help="Full-text search")
@click.option("--assignee", default=None, help="Assignee GID or 'me'")
@click.option("--project", "project_gid", default=None, help="Project GID")
@click.option("--section", "section_gid", default=None, help="Section GID")
@click.option("--tag", default=None, help="Tag GID")
@click.option("--completed", is_flag=True, default=False, help="Include completed")
@click.option("--due-before", default=None, help="Due date before (YYYY-MM-DD)")
@click.option("--due-after", default=None, help="Due date after (YYYY-MM-DD)")
@click.option("--modified-after", default=None, help="Modified after (ISO datetime)")
@click.option(
    "--sort-by",
    default=None,
    type=click.Choice(["due_date", "created_at", "completed_at", "modified_at"]),
    help="Sort order",
)
@click.option(
    "--custom-field",
    "custom_fields",
    multiple=True,
    help="Filter by custom field: gid=value (repeatable). For enum fields use the enum option GID as value.",
)
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
) -> None:
    """Search tasks in workspace."""
    client = require_client(ctx)
    ws = require_workspace(ctx)
    defaults = "gid,name,completed,assignee.name,due_on,custom_fields"
    params = opt_fields_params(ctx, defaults)

    if text:
        params["text"] = text
    if assignee:
        params["assignee.any"] = assignee
    if project_gid:
        params["projects.any"] = project_gid
    if section_gid:
        params["sections.any"] = section_gid
    if tag:
        params["tags.any"] = tag
    if not completed:
        params["completed"] = "false"
    if due_before:
        params["due_on.before"] = due_before
    if due_after:
        params["due_on.after"] = due_after
    if modified_after:
        params["modified_at.after"] = modified_after
    if sort_by:
        params["sort_by"] = sort_by
    for cf in custom_fields:
        gid, _, val = cf.partition("=")
        params[f"custom_fields.{gid}.value"] = val

    # Search API doesn't paginate the same way; use get() directly
    data = client.get(f"/workspaces/{ws}/tasks/search", params)
    if not isinstance(data, list):
        data = [data] if data else []
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("get")
@click.argument("gid")
@click.pass_context
def task_get(ctx: click.Context, gid: str) -> None:
    """Get full task details."""
    client = require_client(ctx)
    params = opt_fields_params(ctx)
    data = client.get(f"/tasks/{gid}", params)
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("create")
@click.option("--name", required=True, help="Task name")
@click.option("--notes", default=None, help="Task description (use '-' for stdin)")
@click.option("--assignee", default=None, help="Assignee GID or 'me'")
@click.option("--project", "project_gid", default=None, help="Project GID")
@click.option("--section", "section_gid", default=None, help="Section GID")
@click.option("--parent", "parent_gid", default=None, help="Parent task GID")
@click.option("--due-on", default=None, help="Due date (YYYY-MM-DD)")
@click.option("--start-on", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--tags", default=None, help="Comma-separated tag GIDs")
@click.option(
    "--custom-field",
    "custom_fields",
    multiple=True,
    help="Custom field gid=value (repeatable)",
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
    custom_fields: tuple[str, ...],
) -> None:
    """Create a new task."""
    client = require_client(ctx)

    if notes == "-":
        notes = sys.stdin.read()

    body: dict = {"name": name}
    if notes is not None:
        body["notes"] = notes
    if assignee:
        body["assignee"] = assignee
    if project_gid:
        body["projects"] = [project_gid]
    if section_gid:
        body["memberships"] = [{"project": project_gid, "section": section_gid}] if project_gid else []
    if parent_gid:
        body["parent"] = parent_gid
    if due_on:
        body["due_on"] = due_on
    if start_on:
        body["start_on"] = start_on
    if tags:
        body["tags"] = [t.strip() for t in tags.split(",")]
    if custom_fields:
        body["custom_fields"] = parse_custom_fields(custom_fields)

    # If workspace needed and no project specified
    if not project_gid and not parent_gid:
        ws = require_workspace(ctx)
        body["workspace"] = ws

    data = client.post("/tasks", body)
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("update")
@click.argument("gid")
@click.option("--name", default=None, help="New name")
@click.option("--notes", default=None, help="New description (use '-' for stdin)")
@click.option("--assignee", default=None, help="Assignee GID or 'me'")
@click.option("--due-on", default=None, help="Due date (YYYY-MM-DD)")
@click.option("--start-on", default=None, help="Start date (YYYY-MM-DD)")
@click.option("--completed/--no-completed", default=None, help="Mark completed/incomplete")
@click.option(
    "--custom-field",
    "custom_fields",
    multiple=True,
    help="Custom field gid=value (repeatable)",
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
    custom_fields: tuple[str, ...],
) -> None:
    """Update a task."""
    client = require_client(ctx)

    if notes == "-":
        notes = sys.stdin.read()

    body: dict = {}
    if name is not None:
        body["name"] = name
    if notes is not None:
        body["notes"] = notes
    if assignee is not None:
        body["assignee"] = assignee
    if due_on is not None:
        body["due_on"] = due_on
    if start_on is not None:
        body["start_on"] = start_on
    if completed is not None:
        body["completed"] = completed
    if custom_fields:
        body["custom_fields"] = parse_custom_fields(custom_fields)

    data = client.put(f"/tasks/{gid}", body)
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("complete")
@click.argument("gid")
@click.pass_context
def task_complete(ctx: click.Context, gid: str) -> None:
    """Mark a task as complete."""
    client = require_client(ctx)
    data = client.put(f"/tasks/{gid}", {"completed": True})
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("delete")
@click.argument("gid")
@click.pass_context
def task_delete(ctx: click.Context, gid: str) -> None:
    """Delete a task."""
    client = require_client(ctx)
    client.delete(f"/tasks/{gid}")
    output({"deleted": True, "gid": gid}, pretty=ctx.obj["pretty"])


@task_group.command("subtasks")
@click.argument("gid")
@click.pass_context
def task_subtasks(ctx: click.Context, gid: str) -> None:
    """List subtasks of a task."""
    client = require_client(ctx)
    defaults = "gid,name,completed,assignee.name,due_on"
    params = opt_fields_params(ctx, defaults)
    data = client.get_all(
        f"/tasks/{gid}/subtasks", params, no_paginate=ctx.obj["no_paginate"]
    )
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("add-project")
@click.argument("gid")
@click.option("--project", "project_gid", required=True, help="Project GID")
@click.option("--section", "section_gid", default=None, help="Section GID")
@click.pass_context
def task_add_project(
    ctx: click.Context, gid: str, project_gid: str, section_gid: str | None
) -> None:
    """Add a task to a project."""
    client = require_client(ctx)
    body: dict = {"project": project_gid}
    if section_gid:
        body["section"] = section_gid
    client.post(f"/tasks/{gid}/addProject", body)
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("remove-project")
@click.argument("gid")
@click.option("--project", "project_gid", required=True, help="Project GID")
@click.pass_context
def task_remove_project(ctx: click.Context, gid: str, project_gid: str) -> None:
    """Remove a task from a project."""
    client = require_client(ctx)
    client.post(f"/tasks/{gid}/removeProject", {"project": project_gid})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("move")
@click.argument("gid")
@click.option("--section", "section_gid", required=True, help="Target section GID")
@click.pass_context
def task_move(ctx: click.Context, gid: str, section_gid: str) -> None:
    """Move a task to a section."""
    client = require_client(ctx)
    client.post(f"/sections/{section_gid}/addTask", {"task": gid})
    output({"ok": True}, pretty=ctx.obj["pretty"])


# -- Dependencies --


@task_group.command("dependencies")
@click.argument("gid")
@click.pass_context
def task_dependencies(ctx: click.Context, gid: str) -> None:
    """List tasks this task is waiting on (depends on)."""
    client = require_client(ctx)
    defaults = "gid,name,completed,assignee.name,due_on"
    params = opt_fields_params(ctx, defaults)
    data = client.get_all(
        f"/tasks/{gid}/dependencies", params, no_paginate=ctx.obj["no_paginate"]
    )
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("dependents")
@click.argument("gid")
@click.pass_context
def task_dependents(ctx: click.Context, gid: str) -> None:
    """List tasks that are waiting on (blocked by) this task."""
    client = require_client(ctx)
    defaults = "gid,name,completed,assignee.name,due_on"
    params = opt_fields_params(ctx, defaults)
    data = client.get_all(
        f"/tasks/{gid}/dependents", params, no_paginate=ctx.obj["no_paginate"]
    )
    output(data, pretty=ctx.obj["pretty"])


@task_group.command("add-dependency")
@click.argument("gid")
@click.option("--dependency", required=True, help="GID of the task this task depends on (waits for)")
@click.pass_context
def task_add_dependency(ctx: click.Context, gid: str, dependency: str) -> None:
    """Mark that this task depends on (is waiting on) another task."""
    client = require_client(ctx)
    client.post(f"/tasks/{gid}/addDependencies", {"dependencies": [dependency]})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("remove-dependency")
@click.argument("gid")
@click.option("--dependency", required=True, help="GID of the dependency to remove")
@click.pass_context
def task_remove_dependency(ctx: click.Context, gid: str, dependency: str) -> None:
    """Remove a dependency from this task."""
    client = require_client(ctx)
    client.post(f"/tasks/{gid}/removeDependencies", {"dependencies": [dependency]})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("add-dependent")
@click.argument("gid")
@click.option("--dependent", required=True, help="GID of the task that is blocked by this task")
@click.pass_context
def task_add_dependent(ctx: click.Context, gid: str, dependent: str) -> None:
    """Mark that another task is blocked by (waiting on) this task."""
    client = require_client(ctx)
    client.post(f"/tasks/{gid}/addDependents", {"dependents": [dependent]})
    output({"ok": True}, pretty=ctx.obj["pretty"])


@task_group.command("remove-dependent")
@click.argument("gid")
@click.option("--dependent", required=True, help="GID of the dependent to remove")
@click.pass_context
def task_remove_dependent(ctx: click.Context, gid: str, dependent: str) -> None:
    """Remove a dependent from this task."""
    client = require_client(ctx)
    client.post(f"/tasks/{gid}/removeDependents", {"dependents": [dependent]})
    output({"ok": True}, pretty=ctx.obj["pretty"])


# -- Smart commands --


def _discover_project_fields(client, project_gid: str) -> dict:
    """Fetch project custom fields and build a cache entry."""
    data = client.get(
        f"/projects/{project_gid}",
        {
            "opt_fields": (
                "custom_field_settings.custom_field.gid,"
                "custom_field_settings.custom_field.name,"
                "custom_field_settings.custom_field.type,"
                "custom_field_settings.custom_field.enum_options.gid,"
                "custom_field_settings.custom_field.enum_options.name"
            )
        },
    )
    result: dict = {"statuses": {}}
    for setting in data.get("custom_field_settings", []):
        cf = setting.get("custom_field", {})
        if cf.get("type") == "enum" and cf.get("name", "").lower() in _STATUS_FIELD_NAMES:
            result["status_field"] = cf["gid"]
            for opt in cf.get("enum_options", []):
                result["statuses"][opt["name"]] = opt["gid"]
            break
    return result


def _get_status_info(client, project_gid: str) -> dict:
    """Get status field info from cache or auto-discover and cache."""
    cached = get_project_cache(project_gid)
    if cached and "status_field" in cached:
        return cached
    discovered = _discover_project_fields(client, project_gid)
    if "status_field" in discovered:
        save_project_cache(project_gid, discovered)
    return discovered


@task_group.command("next")
@click.option("--project", "project_gid", default=None, help="Project GID (or use config)")
@click.option("--status", "status_name", default="New", help="Status name to look for (default: New)")
@click.pass_context
def task_next(
    ctx: click.Context,
    project_gid: str | None,
    status_name: str,
) -> None:
    """Find the next actionable task: status=New and not blocked by incomplete tasks.

    Auto-discovers the status custom field from the project and caches it.
    A dependency is considered resolved if the blocking task is completed.
    """
    client = require_client(ctx)
    ws = require_workspace(ctx)

    project_gid = resolve_project(project_gid)
    if not project_gid:
        output_error(
            "No project configured. Use --project or 'asana config set --project <gid>'.",
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

    # Search for tasks with the target status
    params: dict = {
        "opt_fields": "gid,name,completed,assignee.name,due_on,custom_fields",
        "projects.any": project_gid,
        "completed": "false",
        f"custom_fields.{status_field}.value": status_value,
        "sort_by": "created_at",
    }
    candidates = client.get(f"/workspaces/{ws}/tasks/search", params)
    if not isinstance(candidates, list):
        candidates = [candidates] if candidates else []

    # Filter out tasks blocked by incomplete dependencies
    for task in candidates:
        deps = client.get_all(
            f"/tasks/{task['gid']}/dependencies",
            {"opt_fields": "gid,completed"},
        )
        has_incomplete_blocker = any(not d.get("completed", False) for d in deps)
        if not has_incomplete_blocker:
            output(task, pretty=ctx.obj["pretty"])
            return

    output(None, pretty=ctx.obj["pretty"])
