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

# Batch processing configuration
BATCH_CONFIG = {
    "enabled": os.getenv("DOCAI_BATCH_ENABLED", "true").lower() == "true",
    "threshold_mb": float(os.getenv("DOCAI_BATCH_THRESHOLD_MB", "2.0")),
    "timeout_minutes": int(os.getenv("DOCAI_BATCH_TIMEOUT_MINUTES", "10")),
    "temp_bucket_suffix": os.getenv("DOCAI_BATCH_BUCKET_SUFFIX", "docai-batch-temp"),
    "cleanup_hours": int(os.getenv("DOCAI_BATCH_CLEANUP_HOURS", "24")),
    "poll_interval_seconds": int(os.getenv("DOCAI_BATCH_POLL_INTERVAL", "10")),
    "max_poll_interval_seconds": int(os.getenv("DOCAI_BATCH_MAX_POLL_INTERVAL", "60"))
}

# Document routing configuration for intelligent processing
DOCUMENT_ROUTING = {
    "enable_smart_routing": os.getenv("ENABLE_SMART_ROUTING", "true").lower() == "true",
    "skip_docai_for_narrative": os.getenv("SKIP_DOCAI_FOR_NARRATIVE", "true").lower() == "true", 
    "enable_rate_limiting": os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true",
    "rate_limit_docai_rps": int(os.getenv("RATE_LIMIT_DOCAI_RPS", "10")),  # 10 req/s
    "rate_limit_claude_rps": int(os.getenv("RATE_LIMIT_CLAUDE_RPS", "5"))  # 5 req/s
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
        },
        "batch_processor": {
            "id": os.getenv("DOCAI_FORM_PARSER_ID", "").strip(),  # Uses same processor as Form Parser
            "type": "FORM_PARSER_BATCH",
            "display_name": "Form Parser (Batch)",
            "description": "Batch processing for large documents using Form Parser",
            "capabilities": {
                "text_extraction": True,
                "key_value_extraction": True,
                "table_extraction": True,
                "entity_recognition": True,
                "checkbox_detection": True,
                "form_parsing": True,
                "layout_analysis": True,
                "async_processing": True
            },
            "supported_formats": [".pdf", ".tiff", ".png", ".jpg", ".jpeg"],
            "max_file_size_mb": 200,  # Much higher limit for batch processing
            "max_pages_batch": 200,   # Up to 200 pages in batch mode
            "min_threshold_mb": 2.0,  # Minimum file size for batch processing
            "best_for": ["large_documents", "multi_page_forms", "complex_layouts"],
            "enabled": bool(os.getenv("DOCAI_FORM_PARSER_ID", "").strip() and 
                          not os.getenv("DOCAI_FORM_PARSER_ID", "").strip().startswith('#') and
                          BATCH_CONFIG["enabled"]),
            "pricing_per_1000": 30.00,  # Same pricing as sync Form Parser
            "confidence_threshold": 0.75,
            "processing_time_estimate_minutes": "2-10",
            "requires_gcs": True
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

def get_batch_config() -> Dict[str, Any]:
    """Get batch processing configuration"""
    return BATCH_CONFIG

def is_batch_processor_configured() -> bool:
    """Check if batch processor is properly configured"""
    # Batch processor uses same ID as Form Parser
    if not is_form_parser_configured():
        return False
    
    # Check if batch processing is enabled
    if not BATCH_CONFIG["enabled"]:
        return False
    
    # Verify required environment
    try:
        import google.cloud.storage
        return True
    except ImportError:
        print(f"  ⚠️ WARNING: google-cloud-storage not available - batch processing disabled")
        return False

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

def get_temp_bucket_name() -> str:
    """Get the temporary bucket name for batch processing"""
    project_id = DOCAI_CONFIG["project_id"]
    suffix = BATCH_CONFIG["temp_bucket_suffix"]
    return f"{project_id}-{suffix}"

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

def get_batch_threshold_mb() -> float:
    """Get the current batch processing threshold in MB"""
    return BATCH_CONFIG["threshold_mb"]

def should_use_batch_processing(file_size_mb: float) -> bool:
    """Determine if a file should use batch processing based on size and configuration"""
    if not is_batch_processor_configured():
        return False
    
    return file_size_mb >= get_batch_threshold_mb()

def get_mime_type(file_path: Path) -> str:
    """Get MIME type for a file based on extension"""
    suffix = file_path.suffix.lower()
    return DOCAI_CONFIG["mime_type_mapping"].get(suffix, "application/octet-stream")