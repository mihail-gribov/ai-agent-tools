"""Config show command."""

import click

from asana_cli.config import load_config
from asana_cli.output import output


@click.group("config")
def config_group() -> None:
    """Show CLI configuration (project field cache)."""


@config_group.command("show")
@click.pass_context
def config_show(ctx: click.Context) -> None:
    """Show current configuration."""
    config = load_config()
    output(config, pretty=ctx.obj["pretty"])
