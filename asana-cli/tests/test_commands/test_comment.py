"""Tests for comment commands."""

import json

from click.testing import CliRunner
from unittest.mock import MagicMock

from asana_cli.main import cli


_CACHED_INFO = {
    "status_field": "SF1",
    "statuses": {"Need info": "NI1", "New": "SV1"},
}


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


def _patch_check(monkeypatch, project="proj1", cached=None):
    """Patch resolve_project and _get_status_info for comment check tests."""
    monkeypatch.setattr(
        "asana_cli.commands.comment.resolve_project",
        lambda p: project,
    )
    monkeypatch.setattr(
        "asana_cli.commands.comment._get_status_info",
        lambda client, pid: cached or _CACHED_INFO,
    )


def test_comment_list():
    obj = make_ctx()
    obj["client"].get_all.return_value = [
        {"gid": "s1", "text": "Hello", "type": "comment"},
        {"gid": "s2", "text": "assigned", "type": "system"},
        {"gid": "s3", "text": "World", "type": "comment"},
    ]
    result = invoke(["comment", "list", "task1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["gid"] == "s1"
    assert data[1]["gid"] == "s3"


def test_comment_add():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "s10", "text": "Nice"}
    result = invoke(["comment", "add", "task1", "--text", "Nice"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["text"] == "Nice"
    call_args = obj["client"].post.call_args
    assert call_args[0][0] == "/tasks/task1/stories"
    assert call_args[0][1] == {"text": "Nice"}


def test_comment_check_finds_unresponded(monkeypatch):
    _patch_check(monkeypatch)
    obj = make_ctx()

    # /users/me
    obj["client"].get.side_effect = [
        {"gid": "agent1"},
        # search results
        [{"gid": "t1", "name": "Task 1"}],
    ]
    # stories for t1: last comment is from another user
    obj["client"].get_all.return_value = [
        {"gid": "s1", "text": "I did X", "type": "comment",
         "created_by": {"gid": "agent1", "name": "Agent"}, "created_at": "2026-01-01T00:00:00Z"},
        {"gid": "s2", "text": "Please clarify", "type": "comment",
         "created_by": {"gid": "user1", "name": "Mike"}, "created_at": "2026-01-02T00:00:00Z"},
    ]

    result = invoke(["comment", "check"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["task"]["gid"] == "t1"
    assert data[0]["comment"]["gid"] == "s2"


def test_comment_check_skips_already_responded(monkeypatch):
    _patch_check(monkeypatch)
    obj = make_ctx()

    obj["client"].get.side_effect = [
        {"gid": "agent1"},
        [{"gid": "t1", "name": "Task 1"}],
    ]
    # last comment is from agent itself
    obj["client"].get_all.return_value = [
        {"gid": "s1", "text": "Please clarify", "type": "comment",
         "created_by": {"gid": "user1", "name": "Mike"}, "created_at": "2026-01-01T00:00:00Z"},
        {"gid": "s2", "text": "Here is the answer", "type": "comment",
         "created_by": {"gid": "agent1", "name": "Agent"}, "created_at": "2026-01-02T00:00:00Z"},
    ]

    result = invoke(["comment", "check"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 0


def test_comment_check_skips_tasks_without_comments(monkeypatch):
    _patch_check(monkeypatch)
    obj = make_ctx()

    obj["client"].get.side_effect = [
        {"gid": "agent1"},
        [{"gid": "t1", "name": "No comments task"}],
    ]
    # only system stories, no comments
    obj["client"].get_all.return_value = [
        {"gid": "s1", "text": "assigned", "type": "system"},
    ]

    result = invoke(["comment", "check"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 0


def test_comment_check_no_tasks_found(monkeypatch):
    _patch_check(monkeypatch)
    obj = make_ctx()

    obj["client"].get.side_effect = [
        {"gid": "agent1"},
        [],
    ]

    result = invoke(["comment", "check"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 0


def test_comment_check_multiple_tasks(monkeypatch):
    _patch_check(monkeypatch)
    obj = make_ctx()

    obj["client"].get.side_effect = [
        {"gid": "agent1"},
        [
            {"gid": "t1", "name": "Needs response"},
            {"gid": "t2", "name": "Already answered"},
        ],
    ]
    obj["client"].get_all.side_effect = [
        # t1: last comment from user
        [
            {"gid": "s1", "text": "Question?", "type": "comment",
             "created_by": {"gid": "user1", "name": "Mike"}, "created_at": "2026-01-01T00:00:00Z"},
        ],
        # t2: last comment from agent
        [
            {"gid": "s2", "text": "Question?", "type": "comment",
             "created_by": {"gid": "user1", "name": "Mike"}, "created_at": "2026-01-01T00:00:00Z"},
            {"gid": "s3", "text": "Answer.", "type": "comment",
             "created_by": {"gid": "agent1", "name": "Agent"}, "created_at": "2026-01-02T00:00:00Z"},
        ],
    ]

    result = invoke(["comment", "check"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["task"]["gid"] == "t1"


def test_comment_check_custom_status(monkeypatch):
    _patch_check(monkeypatch, cached={
        "status_field": "SF1",
        "statuses": {"Need info": "NI1", "Planning": "PL1"},
    })
    obj = make_ctx()

    obj["client"].get.side_effect = [
        {"gid": "agent1"},
        [{"gid": "t1", "name": "Planning task"}],
    ]
    obj["client"].get_all.return_value = [
        {"gid": "s1", "text": "What about X?", "type": "comment",
         "created_by": {"gid": "user1", "name": "Mike"}, "created_at": "2026-01-01T00:00:00Z"},
    ]

    result = invoke(["comment", "check", "--status", "Planning"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
