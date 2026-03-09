"""Tests for project commands."""

import json

from click.testing import CliRunner
from unittest.mock import MagicMock

from asana_cli.main import cli


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


def test_project_create_minimal():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "p1", "name": "My Project"}
    result = invoke(["project", "create", "--name", "My Project"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "p1"
    obj["client"].post.assert_called_once_with(
        "/projects",
        {"name": "My Project", "workspace": "ws123", "default_view": "board"},
    )


def test_project_create_all_options():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "p2", "name": "Full Project"}
    result = invoke(
        [
            "project", "create",
            "--name", "Full Project",
            "--color", "light-green",
            "--layout", "list",
            "--public",
        ],
        obj,
    )
    assert result.exit_code == 0
    obj["client"].post.assert_called_once_with(
        "/projects",
        {
            "name": "Full Project",
            "workspace": "ws123",
            "default_view": "list",
            "color": "light-green",
            "public": True,
        },
    )


def test_project_create_requires_name():
    result = invoke(["project", "create"])
    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()
