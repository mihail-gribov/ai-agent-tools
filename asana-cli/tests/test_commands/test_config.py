"""Tests for config commands."""

import json

from click.testing import CliRunner

from asana_cli.main import cli


def test_config_show(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"projects": {"p1": {"status_field": "SF1"}}}')
    monkeypatch.setattr("asana_cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["projects"]["p1"]["status_field"] == "SF1"


def test_config_show_empty(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setattr("asana_cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"], catch_exceptions=False)
    assert result.exit_code == 0
    assert json.loads(result.output) == {}
