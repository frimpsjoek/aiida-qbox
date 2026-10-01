"""Setup tools for aiida-qbox."""

from aiida import load_profile
from aiida.orm import Computer, Code, InstalledCode
from aiida.common.exceptions import NotExistent


def setup_computer(label: str = 'localhost', hostname: str = 'localhost', workdir: str = None):
    """Set up a computer for Qbox calculations.

    Args:
        label: Computer label
        hostname: Hostname
        workdir: Working directory (optional)

    Returns:
        Computer node
    """
    load_profile()

    try:
        computer = Computer.objects.get(label=label)
        print(f"Computer '{label}' already exists (PK={computer.pk})")
        return computer
    except NotExistent:
        pass

    computer = Computer(
        label=label,
        description=f'{label} computer for Qbox',
        hostname=hostname,
        transport_type='ssh',
        scheduler_type='slurm',
        workdir=workdir or f'/tmp/aiida-{label}',
    )
    computer.store()
    computer.configure()
    print(f"Created computer '{label}' (PK={computer.pk})")
    return computer


def setup_codes(computer_label: str = 'localhost', qbox_path: str = 'qb'):
    """Set up Qbox codes on a computer.

    Args:
        computer_label: Label of the computer
        qbox_path: Path to Qbox executable (qb or qb.x)

    Returns:
        Dictionary of created code labels and PKs
    """
    load_profile()

    try:
        computer = Computer.objects.get(label=computer_label)
    except NotExistent:
        print(f"Computer '{computer_label}' not found. Run setup_computer first.")
        return {}

    import os
    if not os.path.isabs(qbox_path):
        # Search in common locations
        search_paths = [
            '/usr/local/bin',
            '/opt/bin',
            '/opt/qbox/bin',
            os.path.expanduser('~/qbox-public/build'),
            os.path.expanduser('~/qbox/bin'),
        ]
        found_path = None
        for path in search_paths:
            for exe in [qbox_path, 'qb', 'qb.x']:
                exe_path = os.path.join(path, exe)
                if os.path.isfile(exe_path) and os.access(exe_path, os.X_OK):
                    found_path = exe_path
                    break
            if found_path:
                break
        if found_path:
            qbox_path = found_path
            print(f"Found Qbox at: {qbox_path}")
        else:
            print(f"Qbox executable not found at {qbox_path} or common locations")
            return {}

    # Get version
    import subprocess
    try:
        result = subprocess.run([qbox_path, '--version'], capture_output=True, text=True, timeout=10)
        version = result.stdout.strip() or result.stderr.strip() or 'unknown'
    except Exception:
        version = 'unknown'

    # Create code
    label = f"qb-{version}@{computer_label}".replace(' ', '-').replace('.', '-')

    try:
        existing = Code.objects.get(label=label)
        print(f"Code '{label}' already exists (PK={existing.pk})")
        return {label: existing.pk}
    except NotExistent:
        pass

    code = InstalledCode(
        label=label,
        computer=computer,
        filepath_executable=qbox_path,
        default_mpiprocs_per_machine=1,
    )
    code.store()
    print(f"Created code '{label}' (PK={code.pk})")
    return {label: code.pk}