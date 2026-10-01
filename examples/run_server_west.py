#!/usr/bin/env python3
"""Example: Run a Qbox server for WEST finite-field coupling.

This example demonstrates how to submit a Qbox server calculation
for client-server coupling with WEST.

Usage:
    verdi run run_server_west.py
"""

from aiida import load_profile, orm
from aiida.engine import submit
from aiida.plugins import WorkflowFactory

load_profile()

QboxServerWorkChain = WorkflowFactory('qbox.server')

# Get the code
try:
    code = orm.Code.objects.get(label='qb-*@localhost')
except orm.exceptions.NotExistent:
    print("No Qbox code found. Run 'aiida-qbox setup-codes auto' first.")
    exit(1)

# For server mode, we need a parent folder from a previous Qbox calculation
# This would typically come from a converged ground state calculation
# For this example, we show the structure - you'd need to provide the parent_folder

# Server initialization parameters (ground state setup)
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
    'randomize_wf': '',
    'run': '0 100',
}

# NOTE: You need to provide a parent_folder from a previous calculation
# parent_folder = orm.load_node(PK_OF_CONVERGED_CALC).outputs.remote_folder

workchain_inputs = {
    'qbox': {
        'code': code,
        # 'parent_folder': parent_folder,  # Required for server mode
        'parameters': orm.Dict(dict=parameters),
        'server_input_file': orm.Str('qb_in'),
        'server_output_file': orm.Str('qb_out'),
        'metadata': {
            'options': {
                'max_wallclock_seconds': 86400,  # Long-running server
                'withmpi': True,
                'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
            },
            'label': 'Qbox Server for WEST',
            'description': 'Qbox finite-field server for WEST coupling',
        },
    },
    'max_iterations': orm.Int(3),
    'max_walltime_factor': orm.Float(1.5),
    'clean_workdir': orm.Bool(False),
}

# Uncomment and provide parent_folder to actually submit
# print("Submitting Qbox Server workchain...")
# wc = submit(QboxServerWorkChain, **workchain_inputs)
# print(f"Submitted workchain PK={wc.pk}")

print("Example server workchain inputs prepared.")
print("To submit, provide a parent_folder from a converged Qbox calculation.")