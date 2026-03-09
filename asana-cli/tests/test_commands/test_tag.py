"""Tests for tag commands."""

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


def test_tag_create_minimal():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "t1", "name": "urgent"}
    result = invoke(["tag", "create", "--name", "urgent"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "t1"
    obj["client"].post.assert_called_once_with(
        "/tags",
        {"name": "urgent", "workspace": "ws123"},
    )


def test_tag_create_with_color():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "t2", "name": "bug"}
    result = invoke(["tag", "create", "--name", "bug", "--color", "dark-red"], obj)
    assert result.exit_code == 0
    obj["client"].post.assert_called_once_with(
        "/tags",
        {"name": "bug", "workspace": "ws123", "color": "dark-red"},
    )


def test_tag_create_requires_name():
    result = invoke(["tag", "create"])
    assert result.exit_code != 0
