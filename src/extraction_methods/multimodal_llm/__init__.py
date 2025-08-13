"""
Multi-modal LLM extraction method using vision-language models.
"""

from .core.base_llm_extractor import (
    BaseLLMExtractor,
    ExtractionResult,
    FieldExtraction,
    ExtractionConfidence
)
from .core.schema_generator import PrismaSchemaGenerator
from .core.confidence_aggregator import ConfidenceAggregator

# Import providers if available
try:
    from .providers.claude_extractor import ClaudeExtractor
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False
    ClaudeExtractor = None

__all__ = [
    "BaseLLMExtractor",
    "ExtractionResult",
    "FieldExtraction",
    "ExtractionConfidence",
    "PrismaSchemaGenerator",
    "ConfidenceAggregator",
    "ClaudeExtractor",
    "CLAUDE_AVAILABLE"
]