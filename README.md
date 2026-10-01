# aiida-qbox

AiiDA plugin for the Qbox code (FPMD/DFT with hybrid functionals, client-server for WEST) — https://qboxcode.org

**Developed under the [Midwest Integrated Center for Computational Materials (MICCoM)](https://miccom.org/), a DOE Computational Materials Sciences center.**

See the [WEST code documentation](https://west-code.org) for information on the finite-field coupling approach used in the client-server mode.

## Features

- **Calculations**: Single-point SCF, geometry optimization, Born-Oppenheimer MD, Car-Parrinello MD
- **Hybrid functionals**: PBE0, HSE with recursive subspace bisection
- **Client-server mode**: Finite-field coupling with WEST
- **Error handling**: Automatic restarts on SCF convergence failure, walltime killed, retrieve failures
- **OOM detection**: Reads scheduler stderr to detect out-of-memory kills
- **Protocols**: Predefined parameter sets for common calculation types
- **CLI tools**: Code setup, data inspection

## Installation

```bash
# From source (editable)
cd aiida-qbox
pip install -e .

# Or with uv (recommended)
uv pip install -e .
```

## Quick Start

```bash
# Set up AiiDA profile (if not done)
verdi quicksetup

# Auto-detect and set up Qbox codes
aiida-qbox setup-codes auto

# List available protocols
aiida-qbox data show-protocols

# Run an example
verdi run examples/run_scf_silicon.py
```

## Plugin Structure

```
aiida_qbox/
├── calculations/     # CalcJob plugins
│   ├── base.py       # Standard Qbox runs (SCF, relax, MD)
│   └── server.py     # Client-server mode for WEST
├── parsers/          # Output parsers
│   ├── base.py       # Parser for standard runs
│   ├── server.py     # Parser for server mode
│   └── qbox_output.py # Shared XML/stdout parsing utilities
├── workchains/       # WorkChains with error handling
│   ├── base.py       # Base SCF workchain
│   ├── relax.py      # Geometry optimization
│   ├── md.py         # Molecular dynamics
│   ├── server.py     # Server mode
│   └── recovery.py   # Shared error recovery utilities
├── workflows/        # Protocols
│   └── protocols/    # YAML protocol definitions
├── cli/              # Command-line tools
│   ├── setup/        # Code/computer setup
│   └── data.py       # Data inspection
└── utils/            # Utility functions
```

## Workchain Error Handling

All workchains inherit from `BaseRestartWorkChain` and provide:

| Error Type | Handler | Action |
|------------|---------|--------|
| SCF not converged | `handle_convergence_failure` | Restart with increased `max_scf` |
| Walltime killed | `handle_killed` | Double walltime, restart |
| OOM killed | `handle_killed` | Abort (resource change needed) |
| Qbox error | `handle_qbox_error` | Abort (input/environment issue) |
| Retrieve failure | `handle_retrieve_failure` | Retry once from remote folder |

Maximum restart attempts controlled by `max_iterations` input (default: 5).

## Protocols

Built-in protocols for common calculations:

```python
from aiida_qbox.workflows.protocols import get_protocol, list_protocols

# List protocols
list_protocols()
# {'scf': 'Single-point SCF calculation',
#  'relax': 'Geometry optimization with CG',
#  'md': 'Born-Oppenheimer MD',
#  'cpmd': 'Car-Parrinello MD',
#  'hybrid': 'Hybrid functional (PBE0) SCF',
#  'hybrid_relax': 'Geometry optimization with hybrid functional',
#  'server_init': 'Server initialization for WEST'}

# Use a protocol
protocol = get_protocol('hybrid_relax')
parameters = protocol['parameters']
```

## Client-Server Mode (WEST Coupling)

For finite-field WEST calculations:

1. Run a converged ground-state Qbox calculation
2. Start Qbox server with `qbox.server` workchain
3. WEST acts as client, sends perturbations via lock files
4. Server computes response and returns XML output

```python
# Server initialization (ground state)
server_inputs = {
    'qbox': {
        'code': code,
        'parent_folder': gs_calc.outputs.remote_folder,
        'parameters': orm.Dict(dict={...}),
    },
    'max_iterations': orm.Int(3),
}

wc = submit(QboxServerWorkChain, **server_inputs)
```

## CLI Commands

```bash
# Set up codes
aiida-qbox setup-codes qbox "qb-1.0@localhost" --computer localhost
aiida-qbox setup-codes auto

# Inspect calculation data
aiida-qbox data parse-xml <node_pk>
aiida-qbox data show-params <node_pk>
aiida-qbox data show-output <node_pk>
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=aiida_qbox tests/
```

## Requirements

- AiiDA >= 2.5
- aiida-quantumespresso >= 4.0
- lxml (for XML parsing)
- Qbox executable (qb or qb.x)

## License

MIT License - see LICENSE file

## Acknowledgments

Developed under the [Midwest Integrated Center for Computational Materials (MICCoM)](https://miccom.org/), a DOE Computational Materials Sciences center.

See the [WEST code documentation](https://west-code.org) and [Qbox code documentation](https://qboxcode.org) for information on the finite-field coupling approach used in the client-server mode.