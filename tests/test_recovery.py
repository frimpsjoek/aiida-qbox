"""Tests for recovery utilities."""

import pytest

from aiida_qbox.workchains.recovery import (
    find_fatal_marker,
    scheduler_stderr,
    abort,
    next_max_scf,
    made_scf_progress,
    FATAL_MARKERS,
    SCHEDULER_STDERR,
)


class MockCalculation:
    """Mock calculation for testing."""
    def __init__(self, retrieved_content=None):
        from aiida.orm import FolderData
        from io import BytesIO
        self.outputs = type('Outputs', (), {})()
        if retrieved_content:
            retrieved = FolderData()
            for fname, content in retrieved_content.items():
                retrieved.put_object_from_filelike(BytesIO(content.encode()), fname)
            self.outputs.retrieved = retrieved
        else:
            self.outputs.retrieved = None


def test_find_fatal_marker_all():
    """Test all fatal markers are detected."""
    for marker in FATAL_MARKERS:
        assert find_fatal_marker(marker) == marker
        assert find_fatal_marker(marker.upper()) == marker
        assert find_fatal_marker(f'Some text {marker} more text') == marker


def test_find_fatal_marker_none():
    """Test no false positives."""
    assert find_fatal_marker('Normal calculation output') is None
    assert find_fatal_marker('Memory usage: 50%') is None
    assert find_fatal_marker('') is None


def test_scheduler_stderr_with_file():
    """Test scheduler stderr retrieval."""
    calc = MockCalculation({
        '_scheduler-stderr.txt': 'slurmstepd: error: Out of memory\nJob terminated'
    })
    result = scheduler_stderr(calc)
    assert 'Out of memory' in result


def test_scheduler_stderr_without_file():
    """Test scheduler stderr when file not retrieved."""
    calc = MockCalculation()
    result = scheduler_stderr(calc)
    assert result == ''


def test_scheduler_stderr_no_retrieved():
    """Test scheduler stderr when no retrieved folder."""
    calc = MockCalculation()
    calc.outputs.retrieved = None
    result = scheduler_stderr(calc)
    assert result == ''


def test_abort_returns_handler_report():
    """Test abort returns correct ProcessHandlerReport."""
    class MockWC:
        def __init__(self):
            self.msgs = []
        def report(self, msg):
            self.msgs.append(msg)
        exit_codes = type('EC', (), {'ERROR_UNRECOVERABLE_FAILURE': 403})()

    wc = MockWC()
    report = abort(wc, 'Test abort message')

    from aiida.engine import ProcessHandlerReport
    assert isinstance(report, ProcessHandlerReport)
    assert report.do_break is True
    assert report.exit_code == 403
    assert 'Test abort message' in wc.msgs


def test_next_max_scf():
    """Test next_max_scf calculation."""
    assert next_max_scf(50, 100) == 150
    assert next_max_scf(10, 50) == 60
    assert next_max_scf(0, 100) == 100
    assert next_max_scf('50', '100') == 150  # String inputs


def test_made_scf_progress():
    """Test made_scf_progress logic."""
    assert made_scf_progress(None, 10) is True
    assert made_scf_progress(5, 10) is True
    assert made_scf_progress(10, 10) is False
    assert made_scf_progress(10, 5) is False
    assert made_scf_progress(5, None) is False
    assert made_scf_progress(None, None) is False