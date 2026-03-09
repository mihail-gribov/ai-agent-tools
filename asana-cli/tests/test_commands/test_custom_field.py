"""Tests for custom-field commands."""

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


def test_cf_get():
    obj = make_ctx()
    obj["client"].get.return_value = {
        "gid": "cf1",
        "name": "Status",
        "type": "enum",
        "enum_options": [
            {"gid": "o1", "name": "New", "color": "cool-gray", "enabled": True},
        ],
    }
    result = invoke(["custom-field", "get", "cf1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["gid"] == "cf1"
    assert len(data["enum_options"]) == 1


def test_cf_list_options():
    obj = make_ctx()
    obj["client"].get.return_value = {
        "enum_options": [
            {"gid": "o1", "name": "New", "color": "cool-gray", "enabled": True},
            {"gid": "o2", "name": "Done", "color": "green", "enabled": True},
        ],
    }
    result = invoke(["custom-field", "list-options", "cf1"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2
    assert data[0]["name"] == "New"


def test_cf_add_option():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "o3", "name": "Canceled", "color": "cool-gray"}
    result = invoke(["custom-field", "add-option", "cf1", "--name", "Canceled", "--color", "cool-gray"], obj)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Canceled"
    obj["client"].post.assert_called_once_with(
        "/custom_fields/cf1/enum_options",
        {"name": "Canceled", "color": "cool-gray"},
    )


def test_cf_add_option_no_color():
    obj = make_ctx()
    obj["client"].post.return_value = {"gid": "o3", "name": "Test"}
    result = invoke(["custom-field", "add-option", "cf1", "--name", "Test"], obj)
    assert result.exit_code == 0
    obj["client"].post.assert_called_once_with(
        "/custom_fields/cf1/enum_options",
        {"name": "Test"},
    )


def test_cf_update_option():
    obj = make_ctx()
    obj["client"].put.return_value = {"gid": "o1", "name": "New", "color": "red"}
    result = invoke(["custom-field", "update-option", "o1", "--color", "red"], obj)
    assert result.exit_code == 0
    obj["client"].put.assert_called_once_with(
        "/enum_options/o1",
        {"color": "red"},
    )


def test_cf_update_option_disable():
    obj = make_ctx()
    obj["client"].put.return_value = {"gid": "o1", "name": "Old", "enabled": False}
    result = invoke(["custom-field", "update-option", "o1", "--disabled"], obj)
    assert result.exit_code == 0
    obj["client"].put.assert_called_once_with(
        "/enum_options/o1",
        {"enabled": False},
    )
