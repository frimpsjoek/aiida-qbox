#!/usr/bin/env python3
"""Example: Run a Qbox Born-Oppenheimer MD simulation of water.

This example demonstrates how to submit a Qbox MD calculation
using the aiida-qbox plugin with the MD workchain.

Usage:
    verdi run run_md_water.py
"""

from aiida import load_profile, orm
from aiida.engine import submit
from aiida.plugins import WorkflowFactory

load_profile()

QboxMDWorkChain = WorkflowFactory('qbox.md')

# Get the code
try:
    code = orm.Code.objects.get(label='qb-*@localhost')
except orm.exceptions.NotExistent:
    print("No Qbox code found. Run 'aiida-qbox setup-codes auto' first.")
    exit(1)

# Define water box for MD (simplified - in practice use a proper water box)
parameters = {
    'set cell': '15.0 0 0  0 15.0 0  0 0 15.0',
    'species O': 'O_HSCV_PBE.xml',
    'species H': 'H_HSCV_PBE.xml',
    # Add water molecules here - simplified for example
    'atom O1 O': '7.5 7.5 7.5',
    'atom H1 H': '8.0 7.5 7.5',
    'atom H2 H': '7.5 8.0 7.5',
    'set ecut': '50',
    'set xc': 'PBE',
    'set wf_dyn': 'PSDA',
    'set scf_tol': '1e-6',
    'set max_scf': '50',
    'set atoms_dyn': 'MD',
    'set dt': '5',
    'randomize_wf': '',
    'run': '1000 1000',  # 1000 MD steps
    'save': 'water_md.xml',
}

# Submit as MD workchain
workchain_inputs = {
    'qbox': {
        'code': code,
        'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'max_wallclock_seconds': 86400,  # 24 hours
                'withmpi': True,
                'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 8},
            },
            'label': 'Water MD',
            'description': 'Water Born-Oppenheimer MD with Qbox PBE',
        },
    },
    'max_iterations': orm.Int(5),
    'target_md_steps': orm.Int(1000),
    'clean_workdir': orm.Bool(False),
}

print("Submitting Qbox MD workchain...")
wc = submit(QboxMDWorkChain, **workchain_inputs)
print(f"Submitted workchain PK={wc.pk}")