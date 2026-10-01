#!/usr/bin/env python3
"""Example: Run a Qbox geometry optimization on silicon.

This example demonstrates how to submit a Qbox geometry optimization
using the aiida-qbox plugin with the relax workchain.

Usage:
    verdi run run_relax_silicon.py
"""

from aiida import load_profile, orm
from aiida.engine import submit
from aiida.plugins import WorkflowFactory

load_profile()

QboxRelaxWorkChain = WorkflowFactory('qbox.relax')

# Get the code
try:
    code = orm.Code.objects.get(label='qb-*@localhost')
except orm.exceptions.NotExistent:
    print("No Qbox code found. Run 'aiida-qbox setup-codes auto' first.")
    exit(1)

# Define silicon structure for relaxation
parameters = {
    'set cell': '10.26 0 0  0 10.26 0  0 0 10.26',
    'species Si': 'Si_PBE.xml',
    'atom Si1 Si': '1.3575 1.3575 1.3575',
    'atom Si2 Si': '-1.3575 -1.3575 -1.3575',
    'set ecut': '30',
    'set xc': 'PBE',
    'set wf_dyn': 'PSDA',
    'set scf_tol': '1e-8',
    'set max_scf': '100',
    'set atoms_dyn': 'CG',
    'set dt': '10',
    'randomize_wf': '',
    'run': '0 100',
    'save': 'si_relax.xml',
}

# Submit as relax workchain (handles restarts on convergence failure)
workchain_inputs = {
    'qbox': {
        'code': code,
        'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'max_wallclock_seconds': 7200,
                'withmpi': True,
                'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
            },
            'label': 'Si Relax',
            'description': 'Silicon geometry optimization with Qbox PBE',
        },
    },
    'max_iterations': orm.Int(10),
    'force_tolerance': orm.Float(1e-4),
    'clean_workdir': orm.Bool(False),
}

print("Submitting Qbox Relax workchain...")
wc = submit(QboxRelaxWorkChain, **workchain_inputs)
print(f"Submitted workchain PK={wc.pk}")