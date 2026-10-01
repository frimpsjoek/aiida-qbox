"""Calculation plugins for Qbox."""

from .base import QboxBaseCalculation
from .server import QboxServerCalculation

__all__ = ('QboxBaseCalculation', 'QboxServerCalculation')