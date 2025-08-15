"""
Extraction modules for template-based extraction.
"""

from .base import BaseExtractor, ExtractionResult
from .acroform import AcroFormExtractor
from .anchor import AnchorExtractor
from .checkbox import CheckboxExtractor
from .date import DateExtractor
from .table import TableExtractor

__all__ = [
    'BaseExtractor',
    'ExtractionResult',
    'AcroFormExtractor',
    'AnchorExtractor',
    'CheckboxExtractor',
    'DateExtractor',
    'TableExtractor',
]