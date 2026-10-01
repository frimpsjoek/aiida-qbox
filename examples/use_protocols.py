#!/usr/bin/env python3
"""Example: Using built-in protocols for Qbox calculations.

This example demonstrates how to use the predefined protocols
for common calculation types.
"""

from aiida import load_profile, orm
from aiida.engine import submit
from aiida.plugins import WorkflowFactory
from aiida_qbox.workflows.protocols import get_protocol, list_protocols

load_profile()

QboxRelaxWorkChain = WorkflowFactory('qbox.relax')

# List available protocols
print("Available protocols:")
for name, desc in list_protocols().items():
    print(f"  {name}: {desc}")

# Get a specific protocol
protocol = get_protocol('hybrid_relax')
print(f"\nUsing protocol: hybrid_relax")
print(f"Description: {protocol['description']}")
print(f"Parameters:")
for cmd, args in protocol['parameters'].items():
    if args:
        print(f"  {cmd} {args}")
    else:
        print(f"  {cmd}")

# Get the code
try:
    code = orm.Code.objects.get(label='qb-*@localhost')
except orm.exceptions.NotExistent:
    print("No Qbox code found. Run 'aiida-qbox setup-codes auto' first.")
    exit(1)

# Use protocol parameters with custom modifications
parameters = protocol['parameters'].copy()
# Override cell for a different system
parameters['set cell'] = '10.26 0 0  0 10.26 0  0 0 10.26'
parameters['species Si'] = 'Si_PBE.xml'
parameters['atom Si1 Si'] = '1.3575 1.3575 1.3575'
parameters['atom Si2 Si'] = '-1.3575 -1.3575 -1.3575'

# Submit workchain with protocol parameters
workchain_inputs = {
    'qbox': {
        'code': code,
        'parameters': orm.Dict(dict=parameters),
        'metadata': {
            'options': {
                'max_wallclock_seconds': 14400,  # 4 hours for hybrid
                'withmpi': True,
                'resources': {'num_machines': 1, 'num_mpiprocs_per_machine': 8},
            },
            'label': 'Si Hybrid Relax (protocol)',
            'description': 'Silicon geometry optimization with PBE0 using protocol',
        },
    },
    'max_iterations': orm.Int(10),
    'force_tolerance': orm.Float(1e-4),
    'clean_workdir': orm.Bool(False),
}

print("\nSubmitting Qbox Relax workchain with hybrid protocol...")
wc = submit(QboxRelaxWorkChain, **workchain_inputs)
print(f"Submitted workchain PK={wc.pk}")