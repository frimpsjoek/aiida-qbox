"""Pytest configuration for aiida-qbox tests."""

import pytest

# Use the modern pytest fixtures from aiida.tools
pytest_plugins = ['aiida.tools.pytest_fixtures']


# The aiida_profile fixture is provided by aiida.tools.pytest_fixtures
# No need to define our own