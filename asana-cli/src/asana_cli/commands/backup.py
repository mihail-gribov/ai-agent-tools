"""Backup and restore Asana projects."""

import json
import random
import sys
import time
from datetime import datetime, timezone

import click

from asana_cli.client import AsanaClient
from asana_cli.main import require_client, require_workspace
from asana_cli.output import output_error

BACKUP_VERSION = 1

# Fields to request when fetching full task data
_TASK_FIELDS = (
    "gid,name,notes,html_notes,completed,completed_at,created_at,modified_at,"
    "assignee,assignee.name,assignee.email,"
    "due_on,start_on,parent,parent.name,"
    "custom_fields,tags,tags.name,tags.color,"
    "followers,followers.name,followers.email,"
    "memberships.section.gid,memberships.section.name,"
    "memberships.project.gid,memberships.project.name,"
    "permalink_url"
)

# Fields for stories (comments + history)
_STORY_FIELDS = (
    "gid,text,html_text,type,resource_subtype,created_at,"
    "created_by.gid,created_by.name,created_by.email,"
    "custom_field.gid,custom_field.name,"
    "old_enum_value.gid,old_enum_value.name,"
    "new_enum_value.gid,new_enum_value.name"
)


def _throttle(lo: float = 0.2, hi: float = 0.6) -> None:
    """Random delay between API calls to avoid rate limits."""
    time.sleep(random.uniform(lo, hi))


def _log(msg: str) -> None:
    click.echo(msg, err=True)


def _collect_project(client: AsanaClient, project_gid: str) -> dict:
    """Collect full project backup data."""
    _log(f"Fetching project {project_gid}...")
    project = client.get(f"/projects/{project_gid}", {
        "opt_fields": (
            "gid,name,color,default_view,archived,public,notes,html_notes,"
            "custom_field_settings.custom_field.gid,"
            "custom_field_settings.custom_field.name,"
            "custom_field_settings.custom_field.type,"
            "custom_field_settings.custom_field.enum_options.gid,"
            "custom_field_settings.custom_field.enum_options.name,"
            "custom_field_settings.custom_field.enum_options.color,"
            "custom_field_settings.custom_field.enum_options.enabled"
        ),
    })

    # Sections
    _log("Fetching sections...")
    sections = client.get_all(
        f"/projects/{project_gid}/sections",
        {"opt_fields": "gid,name"},
    )

    # Custom fields (full definitions)
    custom_fields = []
    cf_settings = project.get("custom_field_settings", [])
    for cfs in cf_settings:
        cf = cfs.get("custom_field", {})
        if cf.get("gid"):
            _throttle()
            _log(f"  Fetching custom field: {cf.get('name', cf['gid'])}")
            cf_full = client.get(f"/custom_fields/{cf['gid']}", {
                "opt_fields": "gid,name,type,enum_options.gid,enum_options.name,"
                              "enum_options.color,enum_options.enabled",
            })
            custom_fields.append(cf_full)

    # All tasks in project (including completed)
    _log("Fetching tasks...")
    tasks_list = client.get_all(
        f"/tasks", {"project": project_gid, "opt_fields": "gid"},
    )
    task_gids = [t["gid"] for t in tasks_list]
    _log(f"  Found {len(task_gids)} tasks")

    # Collect full data for each task
    tasks = []
    tags_seen = {}
    for i, gid in enumerate(task_gids):
        _throttle()
        _log(f"  [{i+1}/{len(task_gids)}] Fetching task {gid}...")
        task = client.get(f"/tasks/{gid}", {"opt_fields": _TASK_FIELDS})

        # Subtasks
        subtasks = client.get_all(
            f"/tasks/{gid}/subtasks", {"opt_fields": "gid"},
        )
        subtask_gids = [s["gid"] for s in subtasks]

        # Fetch full data for each subtask
        full_subtasks = []
        for sgid in subtask_gids:
            _throttle()
            st = client.get(f"/tasks/{sgid}", {"opt_fields": _TASK_FIELDS})
            # Subtask stories
            st_stories = client.get_all(
                f"/tasks/{sgid}/stories", {"opt_fields": _STORY_FIELDS},
            )
            # Subtask dependencies
            st_deps = client.get_all(
                f"/tasks/{sgid}/dependencies", {"opt_fields": "gid"},
            )
            full_subtasks.append({
                "task": st,
                "stories": st_stories,
                "dependencies": [d["gid"] for d in st_deps],
            })

        # Dependencies
        deps = client.get_all(
            f"/tasks/{gid}/dependencies", {"opt_fields": "gid"},
        )

        # Stories (comments + history)
        stories = client.get_all(
            f"/tasks/{gid}/stories", {"opt_fields": _STORY_FIELDS},
        )

        # Collect unique tags
        for tag in task.get("tags", []):
            if tag["gid"] not in tags_seen:
                tags_seen[tag["gid"]] = tag

        tasks.append({
            "task": task,
            "subtasks": full_subtasks,
            "dependencies": [d["gid"] for d in deps],
            "stories": stories,
        })

    return {
        "version": BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "sections": sections,
        "custom_fields": custom_fields,
        "tags": list(tags_seen.values()),
        "tasks": tasks,
    }


def _restore_project(
    client: AsanaClient,
    workspace_gid: str,
    data: dict,
    token_map: dict[str, AsanaClient] | None = None,
) -> dict:
    """Restore project from backup data. Returns GID mapping."""
    gid_map: dict[str, str] = {}
    token_map = token_map or {}

    proj = data["project"]

    # 1. Create project
    _log(f"Creating project: {proj['name']}...")
    body: dict = {
        "name": proj["name"],
        "workspace": workspace_gid,
        "default_view": proj.get("default_view", "board"),
    }
    if proj.get("color"):
        body["color"] = proj["color"]
    if proj.get("notes"):
        body["html_notes"] = proj.get("html_notes", f"<body>{proj['notes']}</body>")
    if proj.get("public"):
        body["public"] = True
    new_proj = client.post("/projects", body)
    new_proj_gid = new_proj["gid"]
    gid_map[proj["gid"]] = new_proj_gid
    _log(f"  Created: {new_proj_gid}")

    # 2. Create sections (skip "Untitled section" — Asana creates it automatically)
    _log("Creating sections...")
    for sec in data.get("sections", []):
        name = sec["name"]
        if name == "Untitled section":
            # Map to the auto-created default section
            new_sections = client.get_all(
                f"/projects/{new_proj_gid}/sections",
                {"opt_fields": "gid,name"},
            )
            default = next(
                (s for s in new_sections if s["name"] == "Untitled section"), None
            )
            if default:
                gid_map[sec["gid"]] = default["gid"]
                continue
        _throttle()
        new_sec = client.post(f"/projects/{new_proj_gid}/sections", {"name": name})
        gid_map[sec["gid"]] = new_sec["gid"]
        _log(f"  Section '{name}': {new_sec['gid']}")

    # 3. Ensure custom field enum options exist and build option GID mapping
    _log("Mapping custom fields...")
    for cf in data.get("custom_fields", []):
        if cf.get("type") != "enum":
            continue
        # Fetch current state of the field
        current = client.get(f"/custom_fields/{cf['gid']}", {
            "opt_fields": "gid,enum_options.gid,enum_options.name",
        })
        existing_names = {
            opt["name"]: opt["gid"]
            for opt in current.get("enum_options", [])
        }
        for opt in cf.get("enum_options", []):
            if opt["name"] in existing_names:
                gid_map[opt["gid"]] = existing_names[opt["name"]]
            else:
                _throttle()
                _log(f"  Adding enum option: {opt['name']} to {cf['name']}")
                new_opt = client.post(
                    f"/custom_fields/{cf['gid']}/enum_options",
                    {"name": opt["name"], "color": opt.get("color", "")},
                )
                gid_map[opt["gid"]] = new_opt["gid"]

    # 4. Create tags
    _log("Creating tags...")
    for tag in data.get("tags", []):
        # Try to find existing tag by name
        existing_tags = client.get_all(
            "/tags", {"workspace": workspace_gid, "opt_fields": "gid,name"},
        )
        found = next((t for t in existing_tags if t["name"] == tag["name"]), None)
        if found:
            gid_map[tag["gid"]] = found["gid"]
            _log(f"  Tag '{tag['name']}' exists: {found['gid']}")
        else:
            body = {"name": tag["name"], "workspace": workspace_gid}
            if tag.get("color"):
                body["color"] = tag["color"]
            new_tag = client.post("/tags", body)
            gid_map[tag["gid"]] = new_tag["gid"]
            _log(f"  Tag '{tag['name']}' created: {new_tag['gid']}")

    # 5. Create tasks (top-level only, subtasks will be created nested)
    _log("Creating tasks...")
    all_task_entries = data.get("tasks", [])

    for i, entry in enumerate(all_task_entries):
        _create_task_entry(
            client, entry, new_proj_gid, gid_map, token_map,
            prefix=f"  [{i+1}/{len(all_task_entries)}]",
        )

    # 6. Set dependencies (all tasks created, GIDs mapped)
    _log("Setting dependencies...")
    dep_count = 0
    for entry in all_task_entries:
        dep_count += _set_dependencies(client, entry, gid_map)
    _log(f"  Set {dep_count} dependencies")

    _log(f"Restore complete. Project: {new_proj_gid}")
    return gid_map


def _create_task_entry(
    client: AsanaClient,
    entry: dict,
    project_gid: str,
    gid_map: dict,
    token_map: dict[str, AsanaClient],
    parent_gid: str | None = None,
    prefix: str = "",
) -> None:
    """Create a task and its subtasks, add comments."""
    task = entry["task"]
    old_gid = task["gid"]

    body: dict = {"name": task["name"]}

    if task.get("html_notes"):
        body["html_notes"] = task["html_notes"]
    elif task.get("notes"):
        body["notes"] = task["notes"]

    if task.get("assignee", {}).get("gid"):
        body["assignee"] = task["assignee"]["gid"]
    if task.get("due_on"):
        body["due_on"] = task["due_on"]
    if task.get("start_on"):
        body["start_on"] = task["start_on"]
    if task.get("completed"):
        body["completed"] = True

    # Tags
    tag_gids = [gid_map.get(t["gid"], t["gid"]) for t in task.get("tags", [])]
    if tag_gids:
        body["tags"] = tag_gids

    # Custom fields — remap enum option GIDs
    if task.get("custom_fields"):
        cf_values = {}
        for cf in task["custom_fields"]:
            if cf.get("type") == "enum" and cf.get("enum_value"):
                old_opt_gid = cf["enum_value"]["gid"]
                cf_values[cf["gid"]] = gid_map.get(old_opt_gid, old_opt_gid)
            elif cf.get("type") == "text" and cf.get("text_value") is not None:
                cf_values[cf["gid"]] = cf["text_value"]
            elif cf.get("type") == "number" and cf.get("number_value") is not None:
                cf_values[cf["gid"]] = cf["number_value"]
        if cf_values:
            body["custom_fields"] = cf_values

    # Placement
    if parent_gid:
        body["parent"] = parent_gid
    else:
        body["projects"] = [project_gid]
        # Place in correct section
        memberships = task.get("memberships", [])
        for m in memberships:
            sec = m.get("section", {})
            if sec.get("gid") and sec["gid"] in gid_map:
                body["memberships"] = [{
                    "project": project_gid,
                    "section": gid_map[sec["gid"]],
                }]
                break

    _throttle()
    new_task = client.post("/tasks", body)
    gid_map[old_gid] = new_task["gid"]
    _log(f"{prefix} Task '{task['name']}': {new_task['gid']}")

    # Create subtasks
    for sub_entry in entry.get("subtasks", []):
        _create_task_entry(
            client, sub_entry, project_gid, gid_map, token_map,
            parent_gid=new_task["gid"],
            prefix=f"{prefix}  ",
        )

    # Add comments (preserving authorship via token_map)
    comments = [
        s for s in entry.get("stories", [])
        if s.get("type") == "comment"
    ]
    for comment in comments:
        text = comment.get("html_text") or comment.get("text", "")
        if not text:
            continue
        author_gid = comment.get("created_by", {}).get("gid")
        comment_client = token_map.get(author_gid, client)
        _throttle()
        comment_client.post(
            f"/tasks/{new_task['gid']}/stories",
            {"html_text": text},
        )


def _set_dependencies(
    client: AsanaClient, entry: dict, gid_map: dict
) -> int:
    """Set dependencies for a task and its subtasks. Returns count."""
    count = 0
    old_gid = entry["task"]["gid"]
    new_gid = gid_map.get(old_gid)
    if not new_gid:
        return 0

    deps = entry.get("dependencies", [])
    mapped_deps = [gid_map[d] for d in deps if d in gid_map]
    if mapped_deps:
        _throttle()
        client.post(
            f"/tasks/{new_gid}/addDependencies",
            {"dependencies": mapped_deps},
        )
        count += len(mapped_deps)

    for sub_entry in entry.get("subtasks", []):
        count += _set_dependencies(client, sub_entry, gid_map)
    return count


@click.group("backup")
def backup_group() -> None:
    """Backup and restore Asana projects."""


@backup_group.command("export")
@click.argument("project_gid")
@click.option("--output", "-o", "output_file", default=None, help="Output file path")
@click.pass_context
def backup_export(ctx: click.Context, project_gid: str, output_file: str | None) -> None:
    """Export a project to a JSON backup file."""
    client = require_client(ctx)
    data = _collect_project(client, project_gid)

    if not output_file:
        safe_name = data["project"]["name"].replace(" ", "_").replace("/", "_")
        date = datetime.now().strftime("%Y%m%d")
        output_file = f"{safe_name}_{date}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _log(f"Backup saved to {output_file}")
    # Output the file path as JSON for programmatic use
    click.echo(json.dumps({"file": output_file, "tasks": len(data["tasks"])}))


@backup_group.command("restore")
@click.argument("backup_file")
@click.option(
    "--token-map", "token_map_file", default=None,
    help="JSON file mapping user GIDs to their Asana tokens",
)
@click.pass_context
def backup_restore(
    ctx: click.Context,
    backup_file: str,
    token_map_file: str | None,
) -> None:
    """Restore a project from a JSON backup file.

    TOKEN_MAP is an optional JSON file: {"user_gid": "asana_token", ...}
    to restore comments with original authorship.
    """
    client = require_client(ctx)
    ws = require_workspace(ctx)

    with open(backup_file, encoding="utf-8") as f:
        data = json.load(f)

    if data.get("version", 0) > BACKUP_VERSION:
        output_error(
            f"Backup version {data['version']} is newer than supported ({BACKUP_VERSION})",
            pretty=ctx.obj["pretty"],
        )
        sys.exit(1)

    # Build token map: user_gid -> AsanaClient
    token_map: dict[str, AsanaClient] = {}
    if token_map_file:
        with open(token_map_file, encoding="utf-8") as f:
            raw_map = json.load(f)
        for user_gid, token in raw_map.items():
            token_map[user_gid] = AsanaClient(token)

    gid_map = _restore_project(client, ws, data, token_map)

    # Output mapping for programmatic use
    click.echo(json.dumps({
        "project": gid_map.get(data["project"]["gid"]),
        "tasks_restored": sum(1 for v in gid_map.values()),
    }))
