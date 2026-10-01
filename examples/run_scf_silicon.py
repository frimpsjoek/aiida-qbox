#!/usr/bin/env python3
"""Example: Run a Qbox SCF calculation on silicon.

This example demonstrates how to submit a Qbox SCF calculation
using the aiida-qbox plugin.

Usage:
    verdi run run_scf_silicon.py
"""

from aiida import load_profile, orm
from aiida.engine import submit
from aiida.plugins import CalculationFactory, WorkflowFactory

load_profile()

QboxBaseCalculation = CalculationFactory('qbox.base')
QboxBaseWorkChain = WorkflowFactory('qbox.base')

# Get the code (adjust label as needed)
try:
    code = orm.Code.objects.get(label='qb-*@localhost')
except orm.exceptions.NotExistent:
    print("No Qbox code found. Run 'aiida-qbox setup-codes auto' first.")
    exit(1)

# For a first SCF, we need a parent folder from a previous calculation
# or we can create an input file with atomic positions
# Here we demonstrate using the workchain with a simple input

# Define silicon structure (diamond, 2 atoms in primitive cell)
# Using Qbox input format directly
parameters = {
    'set cell': '10.26 0 0  0 10.26 0  0 0 10.26',  # Diamond Si, a=5.43 Ang
    'species Si': 'Si_PBE.xml',  # Pseudopotential file (must be available)
    'atom Si1 Si': '1.3575 1.3575 1.3575',
    'atom Si2 Si': '-1.3575 -1.3575 -1.3575',
    'set ecut': '30',
    'set xc': 'PBE',
    'set wf_dyn': 'PSDA',
    'set scf_tol': '1e-8',
    'set max_scf': '100',
    'randomize_wf': '',
    'run': '0 100',
    'save': 'si_scf.xml',
}

# Submit as a calculation (direct)
calc_inputs = {
    'code': code,
    'parameters': orm.Dict(dict=parameters),
    'metadata': {
        'options': {
            'max_wallclock_seconds': 3600,
            'withmpi': True,
            'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 4},
        },
        'label': 'Si SCF',
        'description': 'Silicon SCF with Qbox PBE',
    },
}

print("Submitting Qbox SCF calculation...")
calc = submit(QboxBaseCalculation, **calc_inputs)
print(f"Submitted calculation PK={calc.pk}")


# Alternatively, submit as a workchain with error handling
# This requires a parent folder, so typically used for restarts
# workchain_inputs = {
#     'qbox': calc_inputs,
#     'max_iterations': orm.Int(5),
#     'clean_workdir': orm.Bool(False),
# }
# wc = submit(QboxBaseWorkChain, **workchain_inputs)
# print(f"Submitted workchain PK={wc.pk}")