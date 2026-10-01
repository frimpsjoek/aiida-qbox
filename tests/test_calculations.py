"""Tests for Qbox calculation plugins."""

import pytest
from aiida import orm
from aiida.common import datastructures
from aiida.engine import run
from pathlib import Path

from aiida_qbox.calculations.base import QboxBaseCalculation
from aiida_qbox.calculations.server import QboxServerCalculation


def test_qbox_base_calculation_define():
    """Test that QboxBaseCalculation defines inputs/outputs correctly."""
    spec = QboxBaseCalculation.spec()

    # Check required inputs
    assert 'parameters' in spec.inputs
    assert spec.inputs['parameters'].required
    assert 'parent_folder' in spec.inputs
    assert not spec.inputs['parent_folder'].required

    # Check outputs
    assert 'output_parameters' in spec.outputs
    assert spec.outputs['output_parameters'].required
    assert 'remote_folder' in spec.outputs
    assert spec.outputs['remote_folder'].required
    assert 'output_xml' in spec.outputs
    assert not spec.outputs['output_xml'].required

    # Check exit codes - new AiiDA uses string names
    exit_codes = list(spec.exit_codes.keys())
    assert 'ERROR_NO_RETRIEVED_FOLDER' in exit_codes
    assert 'ERROR_OUTPUT_STDOUT_INCOMPLETE' in exit_codes
    assert 'ERROR_OUTPUT_XML_MISSING' in exit_codes
    assert 'ERROR_QBOX' in exit_codes
    assert 'ERROR_CONVERGENCE_NOT_REACHED' in exit_codes


def test_qbox_server_calculation_define():
    """Test that QboxServerCalculation defines inputs/outputs correctly."""
    spec = QboxServerCalculation.spec()

    # Check required inputs
    assert 'parameters' in spec.inputs
    assert spec.inputs['parameters'].required
    assert 'parent_folder' in spec.inputs
    assert spec.inputs['parent_folder'].required
    assert 'server_input_file' in spec.inputs
    assert 'server_output_file' in spec.inputs

    # Check outputs
    assert 'output_parameters' in spec.outputs
    assert spec.outputs['output_parameters'].required
    assert 'remote_folder' in spec.outputs
    assert spec.outputs['remote_folder'].required

    exit_codes = list(spec.exit_codes.keys())
    assert 'ERROR_NO_RETRIEVED_FOLDER' in exit_codes
    assert 'ERROR_OUTPUT_STDOUT_MISSING' in exit_codes
    assert 'ERROR_OUTPUT_STDOUT_INCOMPLETE' in exit_codes
    assert 'ERROR_OUTPUT_XML_MISSING' in exit_codes
    assert 'ERROR_OUTPUT_XML_PARSE' in exit_codes
    assert 'ERROR_QBOX' in exit_codes
    assert 'ERROR_OUT_OF_WALLTIME' in exit_codes
    assert 'ERROR_UNKNOWN' in exit_codes


# Skip the prepare_for_submission tests for now as they require more complex fixture setup
# These would need a proper ProcessBuilder or run() call
# @pytest.mark.skip(reason="Requires proper CalcJob fixture setup")
# def test_qbox_base_prepare_for_submission(...):
#     pass