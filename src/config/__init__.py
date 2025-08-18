"""Configuration module for Document Processing Pipeline"""

from .docai_config import (
    DOCAI_CONFIG,
    PROCESSING_CONFIG,
    get_processor_config,
    is_general_processor_configured,
    get_mime_type
)

__all__ = [
    "DOCAI_CONFIG",
    "PROCESSING_CONFIG",
    "get_processor_config", 
    "is_general_processor_configured",
    "get_mime_type"
]