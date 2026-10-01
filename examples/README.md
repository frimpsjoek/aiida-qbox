# aiida-qbox Examples

This directory contains example scripts for running Qbox calculations
using the aiida-qbox plugin.

## Examples

| Script | Description |
|--------|-------------|
| `run_scf_silicon.py` | Single-point SCF calculation on silicon |
| `run_relax_silicon.py` | Geometry optimization with error handling |
| `run_md_water.py` | Born-Oppenheimer MD of water |
| `run_server_west.py` | Qbox server for WEST finite-field coupling |
| `use_protocols.py` | Using built-in protocols |

## Running Examples

```bash
# Load AiiDA profile
verdi run examples/run_scf_silicon.py

# Or with explicit profile
AIIDA_PROFILE=myprofile verdi run examples/run_scf_silicon.py
```

## Prerequisites

1. Qbox code installed and accessible
2. AiiDA profile configured
3. Qbox code set up in AiiDA:

```bash
# Auto-detect and set up Qbox codes
aiida-qbox setup-codes auto

# Or manually
aiida-qbox setup-codes qbox "qb-1.0@localhost" --computer localhost
```

4. Pseudopotential files available (`.xml` format) in the working directory
   or accessible via the code's prepend_text.

## Using Protocols

```python
from aiida_qbox.workflows.protocols import get_protocol

# Get built-in protocol
protocol = get_protocol('relax')
parameters = protocol['parameters']

# Use in calculation inputs
inputs = {
    'qbox': {
        'parameters': orm.Dict(dict=parameters),
        ...
    }
}
```

## Workchain Features

All workchains include automated error handling:

- **SCF convergence failure**: Restarts with increased `max_scf`
- **Walltime killed**: Doubles walltime and restarts
- **Out of memory**: Aborts with clear message
- **Qbox errors**: Aborts with Qbox's error message
- **Retrieve failures**: Retries once from remote folder