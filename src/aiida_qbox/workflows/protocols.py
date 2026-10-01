"""Protocol definitions for Qbox workflows.

Protocols provide predefined parameter sets for common calculation types.
Based on Qbox tutorial notes (Galli/Govoni/MICCoM group).
"""

import yaml
from pathlib import Path
from typing import Dict, Any


# Built-in protocol definitions
BUILTIN_PROTOCOLS = {
    'scf': {
        'description': 'Single-point SCF calculation',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '100',
            'randomize_wf': '',
            'run': '0 100',
        },
    },
    'relax': {
        'description': 'Geometry optimization with CG',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '100',
            'set atoms_dyn': 'CG',
            'set dt': '10',
            'randomize_wf': '',
            'run': '0 100',
        },
    },
    'md': {
        'description': 'Born-Oppenheimer MD',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-6',
            'set max_scf': '50',
            'set atoms_dyn': 'MD',
            'set dt': '5',
            'randomize_wf': '',
            'run': '1000 1000',
        },
    },
    'cpmd': {
        'description': 'Car-Parrinello MD',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'MD',
            'set scf_tol': '1e-6',
            'set max_scf': '50',
            'set atoms_dyn': 'MD',
            'set dt': '3',
            'set mass': '400',
            'randomize_wf': '',
            'run': '1000 1000',
        },
    },
    'hybrid': {
        'description': 'Hybrid functional (PBE0) SCF with recursive subspace bisection',
        'parameters': {
            'set ecut': '40',
            'set xc': 'PBE0',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '150',
            'set blHF': '3 3 3',
            'set btHF': '0.01',
            'randomize_wf': '',
            'run': '0 150',
        },
    },
    'hybrid_relax': {
        'description': 'Geometry optimization with hybrid functional (PBE0)',
        'parameters': {
            'set ecut': '40',
            'set xc': 'PBE0',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '150',
            'set blHF': '3 3 3',
            'set btHF': '0.01',
            'set atoms_dyn': 'CG',
            'set dt': '10',
            'randomize_wf': '',
            'run': '0 150',
        },
    },
    'hse': {
        'description': 'Range-separated hybrid (HSE06) SCF',
        'parameters': {
            'set ecut': '40',
            'set xc': 'HSE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '150',
            'set muRSH': '0.2',  # screening parameter (default 0.2 for HSE06)
            'set alphaRSH': '0.25',  # SR HF exchange fraction
            'set betaRSH': '0.0',   # LR HF exchange fraction
            'set blHF': '3 3 3',
            'set btHF': '0.01',
            'randomize_wf': '',
            'run': '0 150',
        },
    },
    'hse_relax': {
        'description': 'Geometry optimization with HSE06',
        'parameters': {
            'set ecut': '40',
            'set xc': 'HSE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '150',
            'set muRSH': '0.2',
            'set alphaRSH': '0.25',
            'set betaRSH': '0.0',
            'set blHF': '3 3 3',
            'set btHF': '0.01',
            'set atoms_dyn': 'CG',
            'set dt': '10',
            'randomize_wf': '',
            'run': '0 150',
        },
    },
    'ddh': {
        'description': 'Dielectric-dependent hybrid (DDH) SCF: alpha_PBE0 = 1/eps_inf',
        'parameters': {
            'set ecut': '40',
            'set xc': 'PBE0',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '150',
            'set alpha_PBE0': '0.25',  # user must set to 1/eps_inf (e.g., 0.2 for Si eps_inf=5)
            'set blHF': '3 3 3',
            'set btHF': '0.01',
            'randomize_wf': '',
            'run': '0 150',
        },
    },
    'ddh_relax': {
        'description': 'Geometry optimization with DDH',
        'parameters': {
            'set ecut': '40',
            'set xc': 'PBE0',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '150',
            'set alpha_PBE0': '0.25',  # set to 1/eps_inf
            'set blHF': '3 3 3',
            'set btHF': '0.01',
            'set atoms_dyn': 'CG',
            'set dt': '10',
            'randomize_wf': '',
            'run': '0 150',
        },
    },
    'finite_field': {
        'description': 'Finite-field calculation for polarization/response',
        'parameters': {
            'set ecut': '40',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '100',
            'set e_field': '0 0 0.001',  # perturbative field along z
            'randomize_wf': '',
            'run': '0 100',
        },
    },
    'thermostat_md': {
        'description': 'MD with Nosé-Hoover thermostat',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-6',
            'set max_scf': '50',
            'set atoms_dyn': 'MD',
            'set dt': '5',
            'set thermostat': 'NOSE',
            'set th_temp': '300',
            'set th_time': '100',
            'set th_width': '0.1',
            'randomize_wf': '',
            'run': '1000 1000',
        },
    },
    'polarization': {
        'description': 'Berry-phase polarization calculation',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '100',
            'set polarization': 'BERRY',
            'randomize_wf': '',
            'run': '0 100',
        },
    },
    'cell_relax': {
        'description': 'Cell shape/volume relaxation (variable cell CG)',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '100',
            'set atoms_dyn': 'CG',
            'set cell_dyn': 'CG',
            'set dt': '10',
            'set stress': 'ON',
            'randomize_wf': '',
            'run': '0 100',
        },
    },
    'server_init': {
        'description': 'Server initialization for WEST finite-field coupling',
        'parameters': {
            'set ecut': '30',
            'set xc': 'PBE',
            'set wf_dyn': 'PSDA',
            'set scf_tol': '1e-8',
            'set max_scf': '100',
            'randomize_wf': '',
            'run': '0 100',
        },
    },
}


def list_protocols() -> Dict[str, str]:
    """List available built-in protocols with descriptions."""
    return {name: proto['description'] for name, proto in BUILTIN_PROTOCOLS.items()}


def get_protocol(name: str) -> Dict[str, Any]:
    """Get a protocol by name.

    Args:
        name: Protocol name

    Returns:
        Protocol dictionary with 'description' and 'parameters'

    Raises:
        ValueError: If protocol not found
    """
    if name not in BUILTIN_PROTOCOLS:
        available = ', '.join(BUILTIN_PROTOCOLS.keys())
        raise ValueError(f"Unknown protocol '{name}'. Available: {available}")

    return BUILTIN_PROTOCOLS[name].copy()


def load_protocol_file(filepath: str) -> Dict[str, Any]:
    """Load a protocol from a YAML file.

    Args:
        filepath: Path to YAML file

    Returns:
        Protocol dictionary
    """
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def save_protocol(protocol: Dict[str, Any], filepath: str):
    """Save a protocol to a YAML file.

    Args:
        protocol: Protocol dictionary
        filepath: Path to save YAML file
    """
    with open(filepath, 'w') as f:
        yaml.dump(protocol, f, default_flow_style=False)