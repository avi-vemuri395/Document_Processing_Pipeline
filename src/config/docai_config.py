"""
Google Document AI Configuration
Handles processor setup and configuration for document extraction
"""

import os
import re
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
        },
        "form_parser": {
            "id": os.getenv("DOCAI_FORM_PARSER_ID", "").strip(),
            "type": "FORM_PARSER",
            "display_name": "Form Parser",
            "description": "Specialized processor for extracting key-value pairs, tables, and entities from forms",
            "capabilities": {
                "text_extraction": True,
                "key_value_extraction": True,
                "table_extraction": True,
                "entity_recognition": True,
                "checkbox_detection": True,
                "form_parsing": True,
                "layout_analysis": True
            },
            "supported_formats": [".pdf", ".tiff", ".png", ".jpg", ".jpeg"],
            "max_file_size_mb": 40,
            "max_pages_sync": 15,  # 30 with imageless mode
            "use_imageless_mode": os.getenv("DOCAI_USE_IMAGELESS_MODE", "false").lower() == "true",
            "best_for": ["loan_applications", "financial_statements", "tax_forms", "structured_forms"],
            "enabled": bool(os.getenv("DOCAI_FORM_PARSER_ID", "").strip() and 
                          not os.getenv("DOCAI_FORM_PARSER_ID", "").strip().startswith('#')),
            "pricing_per_1000": 30.00,
            "confidence_threshold": 0.75,
            "entities_supported": [
                "email", "phone", "url", "date_time", "address",
                "person", "organization", "quantity", "price", "id", "page_number"
            ]
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

def validate_processor_id(processor_id: str) -> bool:
    """
    Validate processor ID format
    Google Document AI processor IDs are typically 16 hex characters
    """
    if not processor_id:
        return False
    
    # Strip whitespace
    processor_id = processor_id.strip()
    
    # Check for comment-like strings
    if processor_id.startswith('#'):
        return False
    
    # Basic format validation (16 hex chars is typical, but can vary)
    # Allow alphanumeric characters, typical length is 16
    if not re.match(r'^[a-f0-9]{16}$', processor_id):
        # Also allow other formats that Google might use
        if not re.match(r'^[a-zA-Z0-9]{8,32}$', processor_id):
            return False
    
    return True

def get_processor_config(processor_type: str = "general_processor") -> Dict[str, Any]:
    """Get configuration for specific processor"""
    return DOCAI_CONFIG["processors"].get(processor_type, {})

def is_general_processor_configured() -> bool:
    """Check if general processor is properly configured"""
    processor_id = os.getenv("DOCAI_GENERAL_PROCESSOR_ID", "").strip()
    
    # Skip if empty or looks like a comment
    if not processor_id or processor_id.startswith('#'):
        return False
    
    # Validate format
    if not validate_processor_id(processor_id):
        print(f"  ⚠️ WARNING: Invalid General Processor ID format: {processor_id[:20]}...")
        return False
    
    config = get_processor_config("general_processor")
    return bool(PROJECT_ID and config.get("enabled"))

def is_form_parser_configured() -> bool:
    """Check if form parser is properly configured"""
    processor_id = os.getenv("DOCAI_FORM_PARSER_ID", "").strip()
    
    # Skip if empty or looks like a comment
    if not processor_id or processor_id.startswith('#'):
        return False
    
    # Validate format
    if not validate_processor_id(processor_id):
        print(f"  ⚠️ WARNING: Invalid Form Parser ID format: {processor_id[:20]}...")
        return False
    
    config = get_processor_config("form_parser")
    return bool(PROJECT_ID and config.get("enabled"))

def get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file based on extension"""
    suffix = file_path.suffix.lower()
    return DOCAI_CONFIG["mime_type_mapping"].get(suffix, "application/octet-stream")