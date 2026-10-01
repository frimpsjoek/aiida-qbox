"""CLI commands for aiida-qbox."""

import click

from .setup.codes import setup_codes
from .data import data_cmd


@click.group()
def cmd_root():
    """AiiDA-Qbox command line interface."""
    pass


cmd_root.add_command(setup_codes)
cmd_root.add_command(data_cmd)