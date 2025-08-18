"""
Google Document AI Configuration
Handles processor setup and configuration for document extraction
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Core configuration
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us")

# Processing options
PROCESSING_CONFIG = {
    "timeout": int(os.getenv("DOCAI_TIMEOUT", "120")),
    "max_retries": int(os.getenv("DOCAI_MAX_RETRIES", "3")),
    "max_pages_per_request": int(os.getenv("DOCAI_MAX_PAGES_PER_REQUEST", "15")),
    "retry_initial": 1.0,
    "retry_maximum": 60.0,
    "retry_multiplier": 2.0,
    "retry_deadline": 300.0
}

# Processor configurations
DOCAI_CONFIG: Dict[str, Any] = {
    "project_id": PROJECT_ID,
    "location": LOCATION,
    "processors": {
        "general_processor": {
            "id": os.getenv("DOCAI_GENERAL_PROCESSOR_ID", ""),
            "type": "GENERAL_PROCESSOR",
            "display_name": "General Processor",
            "description": "Universal document processor for text, entities, and tables",
            "capabilities": {
                "text_extraction": True,
                "entity_recognition": True,
                "table_extraction": True,
                "form_parsing": True,
                "layout_analysis": True,
                "ocr": True
            },
            "supported_formats": [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif"],
            "max_file_size_mb": 20,
            "best_for": ["general", "unknown", "mixed_content", "fallback"],
            "enabled": bool(os.getenv("DOCAI_GENERAL_PROCESSOR_ID")),
            "pricing_per_1000": 1.50,
            "confidence_threshold": 0.70
        }
    },
    "mime_type_mapping": {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
        ".gif": "image/gif"
    }
}

def get_processor_config(processor_type: str = "general_processor") -> Dict[str, Any]:
    """Get configuration for specific processor"""
    return DOCAI_CONFIG["processors"].get(processor_type, {})

def is_general_processor_configured() -> bool:
    """Check if general processor is properly configured"""
    config = get_processor_config("general_processor")
    return bool(PROJECT_ID and config.get("enabled"))

def get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file based on extension"""
    suffix = file_path.suffix.lower()
    return DOCAI_CONFIG["mime_type_mapping"].get(suffix, "application/octet-stream")