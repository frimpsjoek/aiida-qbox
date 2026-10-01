"""Tests for Qbox parsers."""

import pytest
from aiida import orm
from aiida.common import exceptions

from aiida_qbox.parsers.base import QboxBaseParser
from aiida_qbox.parsers.server import QboxServerParser
from aiida_qbox.parsers.qbox_output import parse_qbox_xml, cpu_time_seconds, find_qbox_error, is_complete


SAMPLE_XML = """<?xml version="1.0"?>
<sample xmlns="http://www.quantum-simulation.org/ns/fpmd/fpmd-1.0">
  <etotal>-15.6789</etotal>
  <atomset>
    <unit_cell a="10.26 0 0" b="0 10.26 0" c="0 0 10.26"/>
    <species name="Si" mass="28.0855" pseudo="Si_PBE.xml"/>
    <atom name="Si1" species="Si">
      <position>1.3575 1.3575 1.3575</position>
      <force>0.001 -0.002 0.0005</force>
    </atom>
    <atom name="Si2" species="Si">
      <position>-1.3575 -1.3575 -1.3575</position>
      <force>-0.001 0.002 -0.0005</force>
    </atom>
  </atomset>
  <cputime>123.45</cputime>
  <walltime>456.78</walltime>
</sample>
"""

SAMPLE_STDOUT_COMPLETE = """
Qbox 1.0
Running SCF...
SCF converged in 45 iterations
cpu time: 123.45 s
wall time: 456.78 s
"""

SAMPLE_STDOUT_INCOMPLETE = """
Qbox 1.0
Running SCF...
SCF NOT converged after 100 iterations
"""

SAMPLE_STDOUT_ERROR = """
Qbox 1.0
ERROR: Failed to allocate memory
"""


def test_parse_qbox_xml():
    """Test XML parsing extracts key quantities."""
    parsed = parse_qbox_xml(SAMPLE_XML)

    assert 'etotal' in parsed
    assert parsed['etotal'] == -15.6789

    assert 'forces' in parsed
    assert 'Si1' in parsed['forces']
    assert parsed['forces']['Si1'] == [0.001, -0.002, 0.0005]

    assert 'positions' in parsed
    assert 'Si1' in parsed['positions']

    assert 'cell' in parsed
    assert len(parsed['cell']) == 3

    assert 'cpu_time' in parsed
    assert parsed['cpu_time'] == 123.45

    assert 'wall_time' in parsed
    assert parsed['wall_time'] == 456.78


def test_cpu_time_seconds():
    """Test CPU time extraction from stdout."""
    assert cpu_time_seconds('cpu time: 123.45 s') == 123.45
    assert cpu_time_seconds('CPU time: 100.0 s') == 100.0
    assert cpu_time_seconds('<cputime>200.0</cputime>') == 200.0
    assert cpu_time_seconds('no time here') is None


def test_find_qbox_error():
    """Test error detection in stdout."""
    assert find_qbox_error('ERROR: Something went wrong') == 'Something went wrong'
    assert find_qbox_error('qbox: error: File not found') == 'File not found'
    assert find_qbox_error('<error>Memory error</error>') == 'Memory error'
    assert find_qbox_error('No error here') is None


def test_is_complete():
    """Test completion detection."""
    assert is_complete('<status>completed</status>') is True
    assert is_complete('run 0 100 completed') is True
    assert is_complete('SCF converged\ncpu time: 100 s') is True
    assert is_complete('SCF NOT converged') is False
    assert is_complete('ERROR: Failed') is False


# Parser integration tests skipped - require proper FolderData setup with put_object_from_filelike
# @pytest.mark.skip(reason="Requires proper FolderData fixture setup")
# def test_qbox_base_parser_complete():
#     pass
# 
# @pytest.mark.skip(reason="Requires proper FolderData fixture setup")
# def test_qbox_base_parser_incomplete():
#     pass
# 
# @pytest.mark.skip(reason="Requires proper FolderData fixture setup")
# def test_qbox_base_parser_error():
#     pass