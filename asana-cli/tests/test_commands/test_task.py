"""Tests for task commands using Click's test runner and mocked client."""

import json

from click.testing import CliRunner
from unittest.mock import MagicMock

from asana_cli.main import cli


def make_ctx(workspace="ws123"):
    """Create a mock context obj dict."""
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
    result = runner.invoke(cli, args, obj=obj, catch_exceptions=False)
    return result


def test_task_get():
    obj = make_ctx()
    obj["client"].get.return_value = {"gid": "123", "name": "Test Task"}
    result = invoke(["task", "get", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "123"
    obj["client"].get.assert_called_once()


def test_task_get_without_history_flag():
    obj = make_ctx()
    obj["client"].get.return_value = {"gid": "123", "name": "Test Task"}
    result = invoke(["task", "get", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "status_history" not in data
    obj["client"].get_all.assert_not_called()


def test_task_get_with_history():
    obj = make_ctx()
    obj["client"].get.return_value = {"gid": "123", "name": "Test Task"}
    obj["client"].get_all.return_value = [
        {
            "resource_subtype": "enum_custom_field_changed",
            "custom_field": {"gid": "CF1", "name": "Status"},
            "old_enum_value": {"gid": "E1", "name": "New"},
            "new_enum_value": {"gid": "E2", "name": "In progress"},
            "created_at": "2026-01-15T10:00:00.000Z",
            "created_by": {"gid": "USER1"},
        },
        {
            "resource_subtype": "enum_custom_field_changed",
            "custom_field": {"gid": "CF1", "name": "Status"},
            "old_enum_value": {"gid": "E2", "name": "In progress"},
            "new_enum_value": {"gid": "E3", "name": "Need info"},
            "created_at": "2026-01-16T12:00:00.000Z",
            "created_by": {"gid": "USER2"},
        },
        {
            "resource_subtype": "comment_added",
            "text": "Some comment",
            "created_at": "2026-01-16T13:00:00.000Z",
        },
    ]
    result = invoke(["task", "get", "123", "--history"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "123"
    assert len(data["status_history"]) == 2
    assert data["status_history"][0] == {
        "from": "New",
        "to": "In progress",
        "at": "2026-01-15T10:00:00.000Z",
        "by": "USER1",
    }
    assert data["status_history"][1]["from"] == "In progress"
    assert data["status_history"][1]["to"] == "Need info"
    assert data["status_history"][1]["by"] == "USER2"


def test_task_get_history_empty():
    obj = make_ctx()
    obj["client"].get.return_value = {"gid": "123", "name": "Test Task"}
    obj["client"].get_all.return_value = []
    result = invoke(["task", "get", "123", "--history"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status_history"] == []


def test_task_list_by_project():
    obj = make_ctx()
    obj["client"].get_all.return_value = [
        {"gid": "1", "name": "Task 1"},
        {"gid": "2", "name": "Task 2"},
    ]
    result = invoke(["task", "list", "--project", "proj1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


def test_task_list_by_section():
    obj = make_ctx()
    obj["client"].get_all.return_value = [{"gid": "1", "name": "Task 1"}]
    result = invoke(["task", "list", "--section", "sec1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


def test_task_create():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "999", "name": "New"}
    result = invoke(
        ["task", "create", "--name", "New", "--project", "proj1", "--due-on", "2026-03-15"],
        obj,
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "999"
    call_args = obj["client"].post.call_args
    assert call_args[0][0] == "/tasks"
    body = call_args[0][1]
    assert body["name"] == "New"
    assert body["due_on"] == "2026-03-15"


def test_task_update():
    obj = make_ctx()
    obj["client"].put.return_value = {"gid": "123", "name": "Updated"}
    result = invoke(["task", "update", "123", "--name", "Updated"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Updated"


def test_task_update_archive_notes():
    obj = make_ctx()
    obj["client"].get.return_value = {"notes": "Old description"}
    obj["client"].post.return_value = {"gid": "comment1"}
    obj["client"].put.return_value = {"gid": "123", "notes": "New description"}
    result = invoke(
        ["task", "update", "123", "--notes", "New description", "--archive-notes"],
        obj,
    )
    assert result.exit_code == 0
    # Should have fetched old notes, posted comment, then updated
    obj["client"].get.assert_called_once()
    obj["client"].post.assert_called_once_with(
        "/tasks/123/stories",
        {"html_text": "<body>📋 Description archived before update:Old description</body>"},
    )
    obj["client"].put.assert_called_once_with(
        "/tasks/123", {"html_notes": "<body>New description</body>"}
    )


def test_task_update_archive_notes_empty():
    """Skip archiving when current description is empty."""
    obj = make_ctx()
    obj["client"].get.return_value = {"notes": ""}
    obj["client"].put.return_value = {"gid": "123", "notes": "New description"}
    result = invoke(
        ["task", "update", "123", "--notes", "New description", "--archive-notes"],
        obj,
    )
    assert result.exit_code == 0
    obj["client"].post.assert_not_called()


def test_task_complete():
    obj = make_ctx()
    obj["client"].put.return_value = {"gid": "123", "completed": True}
    result = invoke(["task", "complete", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["completed"] is True


def test_task_delete():
    obj = make_ctx()
    obj["client"].delete.return_value = {}
    result = invoke(["task", "delete", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["deleted"] is True


def test_task_subtasks():
    obj = make_ctx()
    obj["client"].get_all.return_value = [{"gid": "sub1", "name": "Subtask"}]
    result = invoke(["task", "subtasks", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


def test_task_add_project():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "add-project", "123", "--project", "proj1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True


def test_task_remove_project():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "remove-project", "123", "--project", "proj1"], obj)
    assert result.exit_code == 0


def test_task_move():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "move", "123", "--section", "sec1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ok"] is True


def test_task_search():
    obj = make_ctx()
    obj["client"].get.return_value = [{"gid": "1", "name": "Found"}]
    result = invoke(["task", "search", "--text", "hello"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


def test_task_create_with_custom_fields():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "999", "name": "CF Task"}
    result = invoke(
        [
            "task", "create", "--name", "CF Task",
            "--project", "proj1",
            "--custom-field", "111=High",
            "--custom-field", "222=42",
        ],
        obj,
    )
    assert result.exit_code == 0
    body = obj["client"].post.call_args[0][1]
    assert body["custom_fields"] == {"111": "High", "222": "42"}


def test_task_search_by_custom_field():
    obj = make_ctx()
    obj["client"].get.return_value = [{"gid": "1", "name": "Status match"}]
    result = invoke(
        [
            "task", "search",
            "--custom-field", "111111=AAA",
            "--custom-field", "222222=BBB",
            "--project", "proj1",
        ],
        obj,
    )
    assert result.exit_code == 0
    call_args = obj["client"].get.call_args
    params = call_args[1].get("params") or call_args[0][1]
    assert params["custom_fields.111111.value"] == "AAA"
    assert params["custom_fields.222222.value"] == "BBB"


def test_task_search_by_section():
    obj = make_ctx()
    obj["client"].get.return_value = [{"gid": "1", "name": "In section"}]
    result = invoke(["task", "search", "--section", "sec1"], obj)
    assert result.exit_code == 0
    call_args = obj["client"].get.call_args
    params = call_args[1].get("params") or call_args[0][1]
    assert params["sections.any"] == "sec1"


def test_task_dependencies():
    obj = make_ctx()
    obj["client"].get_all.return_value = [{"gid": "dep1", "name": "Blocker"}]
    result = invoke(["task", "dependencies", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["gid"] == "dep1"


def test_task_dependents():
    obj = make_ctx()
    obj["client"].get_all.return_value = [{"gid": "w1", "name": "Waiting"}]
    result = invoke(["task", "dependents", "123"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


def test_task_add_dependency():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "add-dependency", "123", "--dependency", "456"], obj)
    assert result.exit_code == 0
    call_args = obj["client"].post.call_args
    assert call_args[0][0] == "/tasks/123/addDependencies"
    assert call_args[0][1] == {"dependencies": ["456"]}


def test_task_remove_dependency():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "remove-dependency", "123", "--dependency", "456"], obj)
    assert result.exit_code == 0
    call_args = obj["client"].post.call_args
    assert call_args[0][0] == "/tasks/123/removeDependencies"


def test_task_add_dependent():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "add-dependent", "123", "--dependent", "789"], obj)
    assert result.exit_code == 0
    call_args = obj["client"].post.call_args
    assert call_args[0][0] == "/tasks/123/addDependents"
    assert call_args[0][1] == {"dependents": ["789"]}


def test_task_remove_dependent():
    obj = make_ctx()
    obj["client"].post.return_value = {}
    result = invoke(["task", "remove-dependent", "123", "--dependent", "789"], obj)
    assert result.exit_code == 0
    call_args = obj["client"].post.call_args
    assert call_args[0][0] == "/tasks/123/removeDependents"


_CACHED_INFO = {"status_field": "SF1", "statuses": {"New": "SV1", "Done": "SV2"}}


def _patch_next(monkeypatch, project="proj1", cached=None):
    """Patch resolve_project and _get_status_info for task next tests."""
    monkeypatch.setattr(
        "asana_cli.commands.task.resolve_project",
        lambda p: p or project,
    )
    info = cached or _CACHED_INFO
    monkeypatch.setattr(
        "asana_cli.commands.task._get_status_info",
        lambda client, pid: info,
    )


def test_task_next_returns_unblocked(monkeypatch):
    _patch_next(monkeypatch)
    obj = make_ctx()
    # Search returns two candidates
    obj["client"].get.return_value = [
        {"gid": "t1", "name": "Blocked task"},
        {"gid": "t2", "name": "Free task"},
    ]
    # First task has incomplete dep, second has none
    obj["client"].get_all.side_effect = [
        [{"gid": "dep1", "completed": False}],  # t1 blocked
        [],                                       # t2 free
    ]
    result = invoke(["task", "next"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "t2"


def test_task_next_skips_completed_deps(monkeypatch):
    _patch_next(monkeypatch)
    obj = make_ctx()
    obj["client"].get.return_value = [
        {"gid": "t1", "name": "Has resolved dep"},
    ]
    # Dependency is completed — should not block
    obj["client"].get_all.return_value = [{"gid": "dep1", "completed": True}]
    result = invoke(["task", "next"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "t1"


def test_task_next_none_available(monkeypatch):
    _patch_next(monkeypatch)
    obj = make_ctx()
    obj["client"].get.return_value = []
    result = invoke(["task", "next"], obj)
    assert result.exit_code == 0
    assert json.loads(result.output) is None


def test_task_next_all_blocked(monkeypatch):
    _patch_next(monkeypatch)
    obj = make_ctx()
    obj["client"].get.return_value = [
        {"gid": "t1", "name": "Blocked"},
    ]
    obj["client"].get_all.return_value = [{"gid": "dep1", "completed": False}]
    result = invoke(["task", "next"], obj)
    assert result.exit_code == 0
    assert json.loads(result.output) is None


def test_task_next_custom_status(monkeypatch):
    _patch_next(monkeypatch, cached={
        "status_field": "SF1",
        "statuses": {"New": "SV1", "Planning": "SV3"},
    })
    obj = make_ctx()
    obj["client"].get.return_value = [{"gid": "t1", "name": "Planning task"}]
    obj["client"].get_all.return_value = []
    result = invoke(["task", "next", "--status", "Planning"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "t1"


def test_task_next_auto_discovers(monkeypatch):
    """Test that _get_status_info is called with the right project."""
    calls = []

    def fake_get_status_info(client, project_gid):
        calls.append(project_gid)
        return {"status_field": "SF1", "statuses": {"New": "SV1"}}

    monkeypatch.setattr(
        "asana_cli.commands.task.resolve_project",
        lambda p: p or "proj1",
    )
    monkeypatch.setattr(
        "asana_cli.commands.task._get_status_info",
        fake_get_status_info,
    )
    obj = make_ctx()
    obj["client"].get.return_value = []
    result = invoke(["task", "next", "--project", "proj99"], obj)
    assert result.exit_code == 0
    assert calls == ["proj99"]


def test_task_next_assignee_filter(monkeypatch):
    _patch_next(monkeypatch)
    obj = make_ctx()
    obj["client"].get.return_value = [{"gid": "t1", "name": "My task"}]
    obj["client"].get_all.return_value = []
    result = invoke(["task", "next", "--assignee", "user1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "t1"
    # Verify assignee.any was passed in search params
    call_args = obj["client"].get.call_args
    params = call_args[0][1]
    assert params["assignee.any"] == "user1"
