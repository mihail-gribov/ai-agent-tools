"""Tests for config commands."""

import json

from click.testing import CliRunner

from asana_cli.main import cli


def test_config_show(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_file.write_text('{"workspace": "ws1"}')
    monkeypatch.setattr("asana_cli.config.CONFIG_FILE", config_file)

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show"], catch_exceptions=False)
    assert result.exit_code == 0
    assert json.loads(result.output) == {"workspace": "ws1"}


def test_config_set(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    config_dir = tmp_path
    monkeypatch.setattr("asana_cli.config.CONFIG_FILE", config_file)
    monkeypatch.setattr("asana_cli.config.CONFIG_DIR", config_dir)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["config", "set", "--workspace", "ws999"], catch_exceptions=False
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["workspace"] == "ws999"
    # Verify file was written
    saved = json.loads(config_file.read_text())
    assert saved["workspace"] == "ws999"
