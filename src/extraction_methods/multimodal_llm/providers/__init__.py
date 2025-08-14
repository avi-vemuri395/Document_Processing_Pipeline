"""
Document extraction providers.
BenchmarkExtractor is the new simplified approach for unstructured extraction.
LLMFormFiller handles form filling using extracted data.
DynamicFormMapper can extract fields from any PDF form.
"""

from .benchmark_extractor import BenchmarkExtractor, SimpleFormFiller
from .form_filler import LLMFormFiller, LLMFormFillerWithPDF, SimpleLoanApplicationProcessor
from .pdf_form_generator import AcroFormFiller, PDFFormGenerator
from .dynamic_form_mapper import DynamicFormMapper

__all__ = [
    'BenchmarkExtractor',
    'SimpleFormFiller',
    'LLMFormFiller',
    'LLMFormFillerWithPDF',
    'SimpleLoanApplicationProcessor',
    'AcroFormFiller',
    'PDFFormGenerator',
    'DynamicFormMapper'
]