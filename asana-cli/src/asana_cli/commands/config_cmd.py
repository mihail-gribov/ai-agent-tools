"""Config show/set commands."""

import click

from asana_cli.config import load_config, save_config
from asana_cli.output import output


@click.group("config")
def config_group() -> None:
    """Manage CLI configuration."""


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show current configuration."""
    config = load_config()
    output(config, pretty=ctx.obj["pretty"])


@config_group.command("set")
@click.option("--workspace", default=None, help="Default workspace GID")
@click.option("--token", default=None, help="Asana PAT")
@click.option("--project", default=None, help="Default project GID")
@click.pass_context
def config_set(
    ctx: click.Context,
    workspace: str | None,
    token: str | None,
    project: str | None,
) -> None:
    """Save configuration values."""
    config = load_config()
    if workspace is not None:
        config["workspace"] = workspace
    if token is not None:
        config["token"] = token
    if project is not None:
        config["project"] = project
    save_config(config)
    output(config, pretty=ctx.obj["pretty"])
