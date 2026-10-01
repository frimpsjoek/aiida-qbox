"""CLI command to set up Qbox codes."""

import click
from aiida import load_profile
from aiida.orm import Code, Computer, InstalledCode
from aiida.common.exceptions import NotExistent


@click.group()
def setup_codes():
    """Set up Qbox codes on the current computer."""
    pass


@setup_codes.command('qbox')
@click.argument('label')
@click.option('--computer', default='localhost', help='Computer name (default: localhost)')
@click.option('--prepend-text', default='', help='Text to prepend to the command (e.g., module load)')
@click.option('--append-text', default='', help='Text to append to the command')
@click.option('--mpirun', default='mpirun', help='MPI launcher command (default: mpirun)')
def setup_qbox_code(label, computer, prepend_text, append_text, mpirun):
    """Set up a Qbox code (qb executable).

    LABEL: Label for the code (e.g., 'qb-1.0@localhost')
    """
    load_profile()

    try:
        comp = Computer.objects.get(label=computer)
    except NotExistent:
        click.echo(f"Computer '{computer}' not found. Create it first with 'verdi computer setup'.")
        return

    # Check if code already exists
    try:
        existing = Code.objects.get(label=label)
        click.echo(f"Code '{label}' already exists (PK={existing.pk}). Use a different label or delete the existing one.")
        return
    except NotExistent:
        pass

    # Create the code
    # Qbox executable is typically 'qb' or 'qb.x'
    executable = 'qb'

    code = InstalledCode(
        label=label,
        computer=comp,
        filepath_executable=executable,
        prepend_text=prepend_text,
        append_text=append_text,
        default_mpiprocs_per_machine=1,
    )
    code.store()
    click.echo(f"Created code '{label}' (PK={code.pk})")


@setup_codes.command('list')
def list_codes():
    """List all Qbox codes."""
    load_profile()

    codes = Code.objects.all()
    qbox_codes = [c for c in codes if 'qbox' in c.label.lower() or 'qb' in c.label.lower()]

    if not qbox_codes:
        click.echo("No Qbox codes found.")
        return

    for code in qbox_codes:
        click.echo(f"  {code.label} (PK={code.pk}) - {code.computer.label} - {code.filepath_executable}")


@setup_codes.command('auto')
@click.option('--computer', default='localhost', help='Computer name (default: localhost)')
@click.option('--prefix', default='qb', help='Prefix for code labels (default: qb)')
def auto_setup(computer, prefix):
    """Automatically detect and set up Qbox codes.

    Searches for qb/qb.x executables in common locations.
    """
    load_profile()

    try:
        comp = Computer.objects.get(label=computer)
    except NotExistent:
        click.echo(f"Computer '{computer}' not found.")
        return

    # Common locations to search
    import os
    search_paths = [
        '/usr/local/bin',
        '/opt/bin',
        '/opt/qbox/bin',
        os.path.expanduser('~/qbox-public/build'),
        os.path.expanduser('~/qbox/bin'),
    ]

    found = False
    for path in search_paths:
        for exe in ['qb', 'qb.x']:
            exe_path = os.path.join(path, exe)
            if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                # Get version
                import subprocess
                try:
                    result = subprocess.run([exe_path, '--version'], capture_output=True, text=True, timeout=10)
                    version = result.stdout.strip() or result.stderr.strip() or 'unknown'
                except Exception:
                    version = 'unknown'

                label = f"{prefix}-{version}@{computer}"
                # Sanitize version for label
                label = label.replace(' ', '-').replace('.', '-')

                try:
                    existing = Code.objects.get(label=label)
                    click.echo(f"Code '{label}' already exists (PK={existing.pk})")
                except NotExistent:
                    code = InstalledCode(
                        label=label,
                        computer=comp,
                        filepath_executable=exe_path,
                        default_mpiprocs_per_machine=1,
                    )
                    code.store()
                    click.echo(f"Created code '{label}' (PK={code.pk}) - {exe_path}")
                found = True

    if not found:
        click.echo("No Qbox executables found in common locations.")
        click.echo("Try specifying the path manually with 'aiida-qbox setup-codes qbox LABEL'")