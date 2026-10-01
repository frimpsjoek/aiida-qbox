"""Tests for Qbox workchains."""

import pytest
from aiida import orm
from aiida.engine import ProcessHandlerReport

from aiida_qbox.workchains.base import QboxBaseWorkChain
from aiida_qbox.workchains.relax import QboxRelaxWorkChain
from aiida_qbox.workchains.md import QboxMDWorkChain
from aiida_qbox.workchains.server import QboxServerWorkChain
from aiida_qbox.workchains.recovery import (
    find_fatal_marker,
    scheduler_stderr,
    abort,
    next_max_scf,
    made_scf_progress,
)


def test_find_fatal_marker():
    """Test OOM marker detection."""
    assert find_fatal_marker('Out of memory') == 'out of memory'
    assert find_fatal_marker('OOM-Kill') == 'oom-kill'
    assert find_fatal_marker('Memory allocation failed') == 'memory allocation failed'
    assert find_fatal_marker('Segmentation fault') == 'segmentation fault'
    assert find_fatal_marker('Normal output') is None
    assert find_fatal_marker('') is None


def test_next_max_scf():
    """Test max_scf calculation for restart."""
    assert next_max_scf(50, 100) == 150
    assert next_max_scf(10, 50) == 60
    assert next_max_scf(0, 100) == 100


def test_made_scf_progress():
    """Test SCF progress detection."""
    assert made_scf_progress(None, 10) is True
    assert made_scf_progress(5, 10) is True
    assert made_scf_progress(10, 10) is False
    assert made_scf_progress(10, 5) is False
    assert made_scf_progress(5, None) is False
    assert made_scf_progress(None, None) is False


def test_abort():
    """Test abort helper."""
    class MockWorkChain:
        def __init__(self):
            self.messages = []
            self.exit_codes = type('ExitCodes', (), {
                'ERROR_UNRECOVERABLE_FAILURE': 403
            })()

        def report(self, msg):
            self.messages.append(msg)

    wc = MockWorkChain()
    report = abort(wc, 'Test abort message')

    assert isinstance(report, ProcessHandlerReport)
    assert report.do_break is True
    assert report.exit_code == 403
    assert 'Test abort message' in wc.messages


def test_qbox_base_workchain_define():
    """Test base workchain spec."""
    spec = QboxBaseWorkChain.spec()

    # Check inputs
    assert 'qbox' in spec.inputs
    assert 'max_iterations' in spec.inputs
    assert 'clean_workdir' in spec.inputs

    # Check exit codes - new AiiDA uses string names
    exit_codes = list(spec.exit_codes.keys())
    assert 'ERROR_MAXIMUM_ITERATIONS_EXCEEDED' in exit_codes
    assert 'ERROR_PARENT_FOLDER_INVALID' in exit_codes
    assert 'ERROR_UNRECOVERABLE_FAILURE' in exit_codes


def test_qbox_relax_workchain_define():
    """Test relax workchain spec."""
    spec = QboxRelaxWorkChain.spec()

    assert 'force_tolerance' in spec.inputs
    assert 'max_force' in spec.inputs

    exit_codes = list(spec.exit_codes.keys())
    assert 'ERROR_FORCES_NOT_CONVERGED' in exit_codes


def test_qbox_md_workchain_define():
    """Test MD workchain spec."""
    spec = QboxMDWorkChain.spec()

    assert 'target_md_steps' in spec.inputs

    exit_codes = list(spec.exit_codes.keys())
    assert 'ERROR_MD_INCOMPLETE' in exit_codes


def test_qbox_server_workchain_define():
    """Test server workchain spec."""
    spec = QboxServerWorkChain.spec()

    assert 'max_walltime_factor' in spec.inputs


# Handler tests skipped - require proper workchain fixture setup
# @pytest.mark.skip(reason="Requires proper workchain fixture setup")
# def test_handle_convergence_failure(...):
#     pass
# 
# @pytest.mark.skip(reason="Requires proper workchain fixture setup")
# def test_handle_killed(...):
#     pass