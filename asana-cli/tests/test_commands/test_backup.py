"""Tests for backup and restore commands."""

import json
import os
import tempfile
from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

import pytest

from asana_cli.main import cli


@pytest.fixture(autouse=True)
def _no_throttle():
    with patch("asana_cli.commands.backup._throttle"):
        yield


def make_ctx(workspace="ws123"):
    return {
        "client": MagicMock(),
        "pretty": False,
        "fields": None,
        "no_paginate": False,
        "workspace_gid": workspace,
    }


def invoke(args, obj=None):
    runner = CliRunner()
    obj = obj or make_ctx()
    return runner.invoke(cli, args, obj=obj, catch_exceptions=False)


# -- Export tests --

def _setup_export_mocks(client):
    """Set up mock responses for a minimal export."""
    client.get.side_effect = lambda path, params=None: {
        "/projects/proj1": {
            "gid": "proj1",
            "name": "Test Project",
            "color": "light-green",
            "default_view": "board",
            "custom_field_settings": [
                {"custom_field": {"gid": "cf1", "name": "Status", "type": "enum"}},
            ],
        },
        "/custom_fields/cf1": {
            "gid": "cf1",
            "name": "Status",
            "type": "enum",
            "enum_options": [
                {"gid": "opt1", "name": "New", "color": "blue", "enabled": True},
            ],
        },
        "/tasks/t1": {
            "gid": "t1",
            "name": "Task One",
            "notes": "Hello",
            "html_notes": "<body>Hello</body>",
            "completed": False,
            "assignee": {"gid": "u1", "name": "Alice"},
            "due_on": "2026-03-15",
            "start_on": None,
            "custom_fields": [],
            "tags": [{"gid": "tag1", "name": "urgent", "color": "red"}],
            "memberships": [
                {"section": {"gid": "sec1", "name": "Backlog"}, "project": {"gid": "proj1"}},
            ],
            "parent": None,
        },
    }.get(path, {})

    client.get_all.side_effect = lambda path, params=None, **kw: {
        "/projects/proj1/sections": [
            {"gid": "sec1", "name": "Backlog"},
            {"gid": "sec2", "name": "Done"},
        ],
        "/tasks": [{"gid": "t1"}],
        "/tasks/t1/subtasks": [],
        "/tasks/t1/dependencies": [],
        "/tasks/t1/stories": [
            {
                "gid": "s1",
                "text": "Great work",
                "html_text": "<body>Great work</body>",
                "type": "comment",
                "created_by": {"gid": "u1", "name": "Alice"},
                "created_at": "2026-03-01T10:00:00Z",
            },
        ],
    }.get(path, [])


def test_backup_export():
    obj = make_ctx()
    _setup_export_mocks(obj["client"])

    with tempfile.TemporaryDirectory() as tmpdir:
        outfile = os.path.join(tmpdir, "backup.json")
        result = invoke(["backup", "export", "proj1", "-o", outfile], obj)
        assert result.exit_code == 0

        with open(outfile) as f:
            data = json.load(f)

        assert data["version"] == 1
        assert data["project"]["gid"] == "proj1"
        assert data["project"]["name"] == "Test Project"
        assert len(data["sections"]) == 2
        assert len(data["custom_fields"]) == 1
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["task"]["name"] == "Task One"
        assert len(data["tasks"][0]["stories"]) == 1
        assert data["tags"][0]["name"] == "urgent"


def test_backup_export_default_filename():
    obj = make_ctx()
    _setup_export_mocks(obj["client"])

    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(
            cli, ["backup", "export", "proj1"], obj=obj, catch_exceptions=False
        )
        assert result.exit_code == 0
        output = json.loads(result.output.strip().split("\n")[-1])
        assert output["file"].startswith("Test_Project_")
        assert output["tasks"] == 1


# -- Restore tests --

def _make_backup_data():
    return {
        "version": 1,
        "exported_at": "2026-03-09T12:00:00Z",
        "project": {
            "gid": "old_proj",
            "name": "Restored Project",
            "color": "light-green",
            "default_view": "board",
        },
        "sections": [
            {"gid": "old_sec1", "name": "Untitled section"},
            {"gid": "old_sec2", "name": "In Progress"},
        ],
        "custom_fields": [
            {
                "gid": "cf1",
                "name": "Status",
                "type": "enum",
                "enum_options": [
                    {"gid": "old_opt1", "name": "New", "color": "blue"},
                ],
            },
        ],
        "tags": [
            {"gid": "old_tag1", "name": "urgent", "color": "red"},
        ],
        "tasks": [
            {
                "task": {
                    "gid": "old_t1",
                    "name": "Task One",
                    "notes": "Hello",
                    "html_notes": "<body>Hello</body>",
                    "completed": False,
                    "assignee": {"gid": "u1", "name": "Alice"},
                    "due_on": "2026-03-15",
                    "start_on": None,
                    "custom_fields": [
                        {
                            "gid": "cf1",
                            "type": "enum",
                            "enum_value": {"gid": "old_opt1", "name": "New"},
                        },
                    ],
                    "tags": [{"gid": "old_tag1", "name": "urgent"}],
                    "memberships": [
                        {
                            "section": {"gid": "old_sec2", "name": "In Progress"},
                            "project": {"gid": "old_proj"},
                        },
                    ],
                },
                "subtasks": [],
                "dependencies": [],
                "stories": [
                    {
                        "gid": "s1",
                        "text": "Great work",
                        "html_text": "<body>Great work</body>",
                        "type": "comment",
                        "created_by": {"gid": "u1", "name": "Alice"},
                        "created_at": "2026-03-01T10:00:00Z",
                    },
                ],
            },
        ],
    }


def test_backup_restore():
    obj = make_ctx()
    client = obj["client"]

    # Mock responses for restore
    client.post.side_effect = lambda path, body=None: {
        "/projects": {"gid": "new_proj"},
        f"/projects/new_proj/sections": {"gid": "new_sec2"},
        "/tasks": {"gid": "new_t1"},
        "/tags": {"gid": "new_tag1"},
    }.get(path, {"gid": "unknown"})

    client.get.side_effect = lambda path, params=None: {
        "/custom_fields/cf1": {
            "gid": "cf1",
            "enum_options": [{"gid": "existing_opt1", "name": "New"}],
        },
    }.get(path, {})

    client.get_all.side_effect = lambda path, params=None, **kw: {
        "/projects/new_proj/sections": [
            {"gid": "default_sec", "name": "Untitled section"},
        ],
        "/tags": [{"gid": "existing_tag", "name": "urgent"}],
    }.get(path, [])

    data = _make_backup_data()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        f.flush()
        backup_file = f.name

    try:
        result = invoke(["backup", "restore", backup_file], obj)
        assert result.exit_code == 0

        output = json.loads(result.output.strip().split("\n")[-1])
        assert output["project"] == "new_proj"

        # Verify project was created
        project_create_call = client.post.call_args_list[0]
        assert project_create_call[0][0] == "/projects"
        assert project_create_call[0][1]["name"] == "Restored Project"

    finally:
        os.unlink(backup_file)


def test_backup_restore_with_dependencies():
    obj = make_ctx()
    client = obj["client"]

    data = _make_backup_data()
    # Add a second task and dependency
    data["tasks"].append({
        "task": {
            "gid": "old_t2",
            "name": "Task Two",
            "completed": False,
            "custom_fields": [],
            "tags": [],
            "memberships": [],
        },
        "subtasks": [],
        "dependencies": ["old_t1"],
        "stories": [],
    })

    client.post.side_effect = lambda path, body=None: {
        "/projects": {"gid": "new_proj"},
        f"/projects/new_proj/sections": {"gid": "new_sec2"},
    }.get(path, {"gid": f"new_{path.split('/')[-1]}"})

    # Track all post calls to verify dependencies
    post_calls = []
    original_post = client.post.side_effect

    def track_post(path, body=None):
        post_calls.append((path, body))
        if path == "/projects":
            return {"gid": "new_proj"}
        if "sections" in path:
            return {"gid": "new_sec2"}
        if path == "/tasks":
            name = (body or {}).get("name", "")
            if name == "Task One":
                return {"gid": "new_t1"}
            if name == "Task Two":
                return {"gid": "new_t2"}
        if path == "/tags":
            return {"gid": "new_tag1"}
        return {"gid": "unknown"}

    client.post.side_effect = track_post

    client.get.side_effect = lambda path, params=None: {
        "/custom_fields/cf1": {
            "gid": "cf1",
            "enum_options": [{"gid": "existing_opt1", "name": "New"}],
        },
    }.get(path, {})

    client.get_all.side_effect = lambda path, params=None, **kw: {
        "/projects/new_proj/sections": [
            {"gid": "default_sec", "name": "Untitled section"},
        ],
        "/tags": [{"gid": "existing_tag", "name": "urgent"}],
    }.get(path, [])

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        f.flush()
        backup_file = f.name

    try:
        result = invoke(["backup", "restore", backup_file], obj)
        assert result.exit_code == 0

        # Verify addDependencies was called
        dep_calls = [
            (p, b) for p, b in post_calls if "addDependencies" in p
        ]
        assert len(dep_calls) == 1
        assert dep_calls[0][0] == "/tasks/new_t2/addDependencies"
        assert dep_calls[0][1] == {"dependencies": ["new_t1"]}
    finally:
        os.unlink(backup_file)
