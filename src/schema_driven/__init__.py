"""
Schema-Driven Form Extraction Module

This module implements OpenAI structured outputs to replace string-based 
field mapping with semantic understanding.
"""

from .form_schema_extractor import FormSchemaExtractor
from .openai_form_mapper import OpenAIFormMapper

__all__ = ['FormSchemaExtractor', 'OpenAIFormMapper']