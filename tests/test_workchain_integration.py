"""Integration tests for Qbox workchain error handlers.

These tests require proper AiiDA test infrastructure (pgtest fixtures) to create
mock calculation nodes. Skipped for now - see unit tests in test_recovery.py,
test_workchains.py, test_parsers.py for working tests.
"""

import pytest

# Integration tests skipped - they require pgtest fixtures and proper AiiDA test
# infrastructure to create mock calculation nodes with outputs.
# The unit tests in test_recovery.py, test_workchains.py, test_parsers.py
# cover the handler logic and recovery utilities.

# @pytest.mark.skip(reason="Requires pgtest fixtures for proper mock nodes")
# def test_handler_integration():
#     pass