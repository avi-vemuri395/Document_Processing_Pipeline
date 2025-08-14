"""
Template-based extraction system for loan application documents.
"""

from .registry import TemplateRegistry
from .extractors.base import BaseExtractor, ExtractionResult
from .orchestrator import ExtractionOrchestrator

__all__ = [
    'TemplateRegistry',
    'BaseExtractor',
    'ExtractionResult',
    'ExtractionOrchestrator',
]