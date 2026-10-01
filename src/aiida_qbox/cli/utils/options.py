"""CLI options for aiida-qbox commands."""

import click
from aiida.cmdline.params.types import CodeParamType, ComputerParamType
from aiida.cmdline.utils.decorators import with_dbenv


# Reusable option decorators
code_option = click.option(
    '--code',
    'code',
    type=CodeParamType(),
    required=True,
    help='Code to use for the calculation.'
)

computer_option = click.option(
    '--computer',
    'computer',
    type=ComputerParamType(),
    default='localhost',
    help='Computer to run on (default: localhost).'
)

walltime_option = click.option(
    '--walltime',
    'walltime',
    type=int,
    default=3600,
    help='Walltime in seconds (default: 3600).'
)

mpiprocs_option = click.option(
    '--mpiprocs',
    'mpiprocs',
    type=int,
    default=1,
    help='Number of MPI processes per machine (default: 1).'
)

dry_run_option = click.option(
    '--dry-run',
    'dry_run',
    is_flag=True,
    help='Show what would be submitted without actually submitting.'
)