"""
Template-based extraction system for loan application documents.
"""

from .registry import TemplateRegistry
from .extractors.base import BaseExtractor, ExtractionResult
from .orchestrator import ExtractionOrchestrator
from .pipeline_orchestrator import PipelineOrchestrator

__all__ = [
    'TemplateRegistry',
    'BaseExtractor',
    'ExtractionResult',
    'ExtractionOrchestrator',
    'PipelineOrchestrator',
]