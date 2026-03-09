"""Tests for section commands."""

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


def test_section_create():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "sec1", "name": "Backlog"}
    result = invoke(
        ["section", "create", "--project", "proj1", "--name", "Backlog"], obj
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "sec1"
    obj["client"].post.assert_called_once_with(
        "/projects/proj1/sections",
        {"name": "Backlog"},
    )


def test_section_create_requires_project():
    result = invoke(["section", "create", "--name", "Backlog"])
    assert result.exit_code != 0


def test_section_create_requires_name():
    result = invoke(["section", "create", "--project", "proj1"])
    assert result.exit_code != 0
