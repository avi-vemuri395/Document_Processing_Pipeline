"""
Multi-modal LLM extraction method using vision-language models.
Simplified benchmark implementation for unstructured extraction and form filling.
"""

from .core.schema_generator import PrismaSchemaGenerator
from .providers import (
    BenchmarkExtractor,
    LLMFormFiller,
    LLMFormFillerWithPDF,
    PDFFormGenerator
)

__all__ = [
    "PrismaSchemaGenerator",
    "BenchmarkExtractor",
    "LLMFormFiller",
    "LLMFormFillerWithPDF",
    "PDFFormGenerator"
]