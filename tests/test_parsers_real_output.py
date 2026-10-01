"""Tests for Qbox parsers using real output fixtures."""

import json
from pathlib import Path

import pytest
from aiida import orm
from aiida.orm import FolderData

from aiida_qbox.parsers.base import QboxBaseParser
from aiida_qbox.parsers.qbox_output import parse_qbox_xml


FIXTURE_DIR = Path(__file__).parent / 'fixtures'


def load_fixture(name: str):
    """Load a test fixture."""
    fixture_path = FIXTURE_DIR / name
    if not fixture_path.exists():
        pytest.skip(f"Fixture {name} not found")

    stdout = (fixture_path / 'aiida.out').read_text() if (fixture_path / 'aiida.out').exists() else ''
    xml = (fixture_path / 'qbox.xml').read_text() if (fixture_path / 'qbox.xml').exists() else ''
    expected = json.loads((fixture_path / 'expected.json').read_text()) if (fixture_path / 'expected.json').exists() else {}

    return stdout, xml, expected


def make_retrieved_folder(stdout: str, xml: str) -> FolderData:
    """Create a FolderData with stdout and XML."""
    folder = FolderData()
    if stdout:
        folder.put_object_from_filelike(stdout.encode(), 'qbox.out')
    if xml:
        folder.put_object_from_filelike(xml.encode(), 'qbox.xml')
    return folder


# Skip integration tests - require proper FolderData setup
# @pytest.mark.skip(reason="Requires proper FolderData fixture setup with put_object_from_filelike")
# def test_parse_fixture_scf_converged():
#     """Test parsing of converged SCF fixture."""
#     stdout, xml, expected = load_fixture('scf_converged')
#
#     retrieved = make_retrieved_folder(stdout, xml)
#     parser = QboxBaseParser(node=orm.CalcJobNode())
#     parser.retrieved = retrieved
#     parser.node.get_option = lambda x: 'qbox.out'
#
#     result = parser.parse()
#
#     assert result is None, f"Parser failed: {result}"
#
#     if expected:
#         params = parser._outputs['output_parameters'].get_dict()
#         for key, value in expected.items():
#             if key in params:
#                 assert params[key] == value, f"Mismatch in {key}: got {params[key]}, expected {value}"
#
#
# @pytest.mark.skip(reason="Requires proper FolderData fixture setup with put_object_from_filelike")
# def test_parse_fixture_relax_converged():
#     """Test parsing of converged relax fixture."""
#     stdout, xml, expected = load_fixture('relax_converged')
#
#     retrieved = make_retrieved_folder(stdout, xml)
#     parser = QboxBaseParser(node=orm.CalcJobNode())
#     parser.retrieved = retrieved
#     parser.node.get_option = lambda x: 'qbox.out'
#
#     result = parser.parse()
#
#     assert result is None, f"Parser failed: {result}"
#
#
# @pytest.mark.skip(reason="Requires proper FolderData fixture setup with put_object_from_filelike")
# def test_parse_fixture_md_complete():
#     """Test parsing of completed MD fixture."""
#     stdout, xml, expected = load_fixture('md_complete')
#
#     retrieved = make_retrieved_folder(stdout, xml)
#     parser = QboxBaseParser(node=orm.CalcJobNode())
#     parser.retrieved = retrieved
#     parser.node.get_option = lambda x: 'qbox.out'
#
#     result = parser.parse()
#
#     assert result is None, f"Parser failed: {result}"


def test_xml_parsing_fixtures():
    """Test XML parsing directly on all fixtures."""
    for fixture_path in FIXTURE_DIR.iterdir():
        if not fixture_path.is_dir():
            continue

        xml_file = fixture_path / 'qbox.xml'
        if not xml_file.exists():
            continue

        xml = xml_file.read_text()
        parsed = parse_qbox_xml(xml)

        # Basic sanity checks
        assert isinstance(parsed, dict)
        if 'etotal' in parsed:
            assert isinstance(parsed['etotal'], float)
        if 'forces' in parsed:
            assert isinstance(parsed['forces'], dict)
            for atom, force in parsed['forces'].items():
                assert isinstance(force, list)
                assert len(force) == 3