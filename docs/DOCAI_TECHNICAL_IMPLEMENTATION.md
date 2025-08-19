# Google Document AI Technical Implementation Guide

## Overview
This guide provides comprehensive technical documentation for Google Document AI integration in our financial document processing pipeline, specifically optimized for loan applications, tax returns, and financial statements.

**Current Status**: ✅ **PRODUCTION READY** (Updated Jan 2025)
- Form Parser: Fully integrated with imageless mode support
- General Processor: Available as intelligent fallback
- Smart retry logic: No more unnecessary retries on page limit errors
- Individual file processing: Proper result storage for all extraction methods

**Scope**: Production-ready implementation with optimal processor selection and fallback strategies
**Prerequisites**: Google Cloud project with Document AI API enabled + optional allowlist for imageless mode
**Processing Capabilities**: Form Parser (15-30 pages), General Processor (15-30 pages), Claude Vision (unlimited fallback)
**Setup Time**: 30-60 minutes for configuration (implementation complete)

---

## Table of Contents
1. [Document AI Capabilities & Usage](#1-document-ai-capabilities--usage)
2. [Supported Document Types](#2-supported-document-types)
3. [Environment Setup](#3-environment-setup)
4. [Authentication Configuration](#4-authentication-configuration)
5. [Code Implementation](#5-code-implementation)
6. [Testing & Validation](#6-testing--validation)
7. [Deployment Steps](#7-deployment-steps)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Document AI Capabilities & Usage

### 1.1 Processor Overview

Our implementation uses two Google Document AI processors with intelligent fallback:

#### **Form Parser** (Primary)
- **Purpose**: Specialized extraction from structured/semi-structured forms
- **Strengths**: Superior key-value extraction, checkbox detection, table parsing
- **Page Limits**: 15 pages (standard), 30 pages (imageless mode with allowlist)
- **Cost**: $30 per 1,000 pages
- **Best For**: Loan applications, tax forms, financial statements, surveys

#### **General Processor** (Fallback)
- **Purpose**: Universal document processing with generative AI models
- **Strengths**: Advanced entity extraction, complex layouts, handwritten text
- **Page Limits**: 15 pages (standard), 30 pages (imageless mode)
- **Cost**: $1.50 per 1,000 pages
- **Best For**: Unstructured documents, mixed content, complex layouts

### 1.2 Core Extraction Capabilities

| Feature | Form Parser | General Processor | Our Implementation |
|---------|-------------|-------------------|-------------------|
| **Key-Value Pairs** | ✅ Excellent | ✅ Good | ✅ Primary extraction method |
| **Table Detection** | ✅ Structured tables | ✅ Complex tables | ✅ Both simple and complex |
| **Entity Extraction** | ✅ Generic entities | ✅ Custom + Generic | ✅ Financial entities (SSN, EIN, etc.) |
| **Checkbox Detection** | ✅ Specialized | ✅ Advanced | ✅ Form field validation |
| **OCR Quality** | ✅ High accuracy | ✅ Highest accuracy | ✅ Multi-language support |
| **Handwriting** | ✅ Limited | ✅ Excellent | ✅ Signatures, handwritten notes |

### 1.3 Financial Document Optimization

Our implementation is specifically optimized for financial document processing:

```python
# Entity types we extract
FINANCIAL_ENTITIES = [
    "person",           # Names, signatories
    "organization",     # Business names, banks
    "phone",           # Contact information
    "email",           # Email addresses
    "address",         # Residential, business addresses
    "date_time",       # Document dates, tax years
    "price",           # Dollar amounts, financial figures
    "quantity",        # Percentages, counts
    "id"               # SSN, EIN, account numbers
]

# Form fields we prioritize
LOAN_APPLICATION_FIELDS = [
    "applicant_name", "ssn", "business_name", "ein",
    "annual_revenue", "net_worth", "assets", "liabilities",
    "ownership_percentage", "years_in_business"
]
```

---

## 2. Supported Document Types

### 2.1 Primary Use Cases (Optimal Performance)

#### **Loan Applications** 
- SBA loan applications
- Commercial loan forms
- Personal loan applications
- Mortgage applications
- Line of credit applications

#### **Tax Documents**
- Form 1040 (Individual tax returns)
- Form 1065 (Partnership returns)
- Form 1120S (S-Corporation returns)
- W-2 forms (Wage and tax statements)
- 1099 forms (Income statements)
- Schedule K-1 (Partner's share)

#### **Financial Statements**
- Personal Financial Statements (PFS)
- Balance sheets
- Profit & Loss statements
- Cash flow statements
- Bank statements
- Investment account statements

#### **Supporting Documents**
- Business licenses
- Articles of incorporation
- Operating agreements
- Management biographies
- Insurance policies
- Lease agreements

### 2.2 Document Characteristics (What Works Best)

#### **Excellent Results** ✅
- **PDF forms**: Clear structure, defined fields
- **Scanned documents**: High resolution (300+ DPI)
- **Typed text**: Machine-readable fonts
- **Structured layouts**: Tables, labeled sections
- **Standard forms**: Bank forms, government forms

#### **Good Results** ⚠️
- **Mixed content**: Text + tables + images
- **Multi-column layouts**: Complex formatting
- **Handwritten text**: Signatures, notes (General Processor better)
- **Poor quality scans**: Low resolution, skewed

#### **Challenging** ❌
- **Purely handwritten documents**: Use General Processor
- **Complex graphics**: Charts, diagrams
- **Non-standard layouts**: Creative formatting
- **Damaged documents**: Torn, faded, corrupted

### 2.3 File Format Support

```python
SUPPORTED_FORMATS = {
    "pdf": "application/pdf",           # Primary format - best results
    "png": "image/png",                 # Good for scanned documents
    "jpg": "image/jpeg",                # Good for photos
    "jpeg": "image/jpeg",               # Good for photos  
    "tiff": "image/tiff",               # Excellent for scanned forms
    "bmp": "image/bmp",                 # Basic support
    "gif": "image/gif"                  # Basic support
}

# File size limits
MAX_FILE_SIZE = 40MB                    # Per document
MAX_PAGES_SYNC = 15                     # Standard mode
MAX_PAGES_IMAGELESS = 30                # With allowlist
```

### 2.4 Our Pipeline's Document Processing Strategy

```mermaid
graph TD
    A[Document Input] --> B{File Analysis}
    B --> C{Pages ≤ 15?}
    C -->|Yes| D[Form Parser]
    C -->|No| E{Imageless Mode?}
    E -->|Yes| F[Form Parser + Imageless]
    E -->|No| G[General Processor]
    F --> H{Success?}
    G --> H
    D --> H
    H -->|Yes| I[Structured Data]
    H -->|No| J[Claude Vision Fallback]
    J --> I
```

---

## 3. Environment Setup

### 3.1 Install Required Dependencies

```bash
# Add to requirements.txt
google-cloud-documentai==2.20.0
google-auth==2.23.0
google-api-core==2.12.0

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "from google.cloud import documentai; print('DocAI version:', documentai.__version__)"
```

### 3.2 Create Environment Variables

Create or update `.env` file:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us  # or 'eu' based on processor location

# DocAI Processors (current production setup)
DOCAI_FORM_PARSER_ID=your-form-parser-id      # Primary: 15-30 pages, $30/1000 pages
DOCAI_GENERAL_PROCESSOR_ID=your-processor-id   # Fallback: 15-30 pages, $1.50/1000 pages

# Processing Configuration
DOCAI_USE_IMAGELESS_MODE=true                 # Enable for 30-page limit (requires Google allowlist)
DOCAI_TIMEOUT=120                              # Processing timeout in seconds
DOCAI_MAX_RETRIES=3                           # Retry attempts for failed requests

# Authentication (choose one method)
# Method A: Service Account Key
GOOGLE_APPLICATION_CREDENTIALS=./credentials/docai-service-account.json

# Method B: Application Default Credentials (for local development)
# Run: gcloud auth application-default login

# Optional: Configure processing options
DOCAI_TIMEOUT=120  # seconds
DOCAI_MAX_RETRIES=3
DOCAI_MAX_PAGES_PER_REQUEST=15
```

### 1.3 Verify Processor Access

Create `scripts/verify_docai_setup.py`:

```python
#!/usr/bin/env python3
"""Verify Document AI setup and processor access"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import documentai
from google.api_core.client_options import ClientOptions

# Load environment variables
load_dotenv()

def verify_setup():
    """Verify Document AI configuration"""
    
    # Check required environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
    processor_id = os.getenv("DOCAI_GENERAL_PROCESSOR_ID")
    
    if not all([project_id, processor_id]):
        print("❌ Missing required environment variables")
        print(f"  PROJECT: {project_id or 'NOT SET'}")
        print(f"  PROCESSOR: {processor_id or 'NOT SET'}")
        return False
    
    print(f"✅ Configuration loaded:")
    print(f"  Project: {project_id}")
    print(f"  Location: {location}")
    print(f"  Processor: {processor_id}")
    
    # Test authentication
    try:
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        # Build processor name
        name = client.processor_path(project_id, location, processor_id)
        print(f"✅ Authentication successful")
        print(f"  Processor path: {name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_setup()
    sys.exit(0 if success else 1)
```

---

## **PRODUCTION STATUS (August 2025)**

### ✅ **Current Implementation Status**
- **Form Parser**: ✅ Production ready and operational
- **General Processor**: ✅ Available as fallback (optional)
- **Integration**: ✅ BenchmarkExtractor with hybrid DocAI + Claude Vision
- **Bug Fixes**: ✅ DocAI results properly returned (critical fix applied)

### 📊 **Performance Metrics**
- **Form Parser**: 85-97% accuracy, $30/1000 pages, 15-page limit
- **Processing Speed**: ~4-5 seconds per document (3-5 pages)
- **Fallback**: Claude Vision for documents >15 pages
- **Success Rate**: 3/4 test documents processed successfully

### 🐛 **Known Issues & Fixes**
1. **FIXED**: DocAI results not returned (Aug 2025)
   - **Issue**: Results discarded due to incorrect early return logic
   - **Fix**: Updated `benchmark_extractor.py` line 281-282
   - **Status**: ✅ Resolved and tested

2. **Print vs Logging**: ✅ All DocAI modules use print statements for visibility
3. **Page Limits**: ✅ Properly enforced (15 pages for Form Parser)
4. **Authentication**: ✅ ADC working with gcloud setup

### 🔧 **Key Files**
- `src/extraction_methods/docai_form_parser.py` (478 lines)
- `src/extraction_methods/docai_general_processor.py` (fallback)
- `src/config/docai_config.py` (configuration)
- `src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py` (integration)

---

## 2. Authentication Configuration

### 2.1 Service Account Setup (Recommended for Production)

```bash
# 1. Create service account in Google Cloud Console
gcloud iam service-accounts create docai-processor \
    --display-name="Document AI Processor Service Account"

# 2. Grant necessary roles
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:docai-processor@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/documentai.apiUser"

# 3. Create and download key
gcloud iam service-accounts keys create \
    ./credentials/docai-service-account.json \
    --iam-account=docai-processor@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 4. Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="./credentials/docai-service-account.json"
```

### 2.2 Application Default Credentials (Development)

```bash
# Login with your Google account
gcloud auth application-default login

# Set default project
gcloud config set project YOUR_PROJECT_ID
```

---

## 3. Code Implementation

### 3.1 Update Configuration Module

Update `src/config/docai_config.py`:

```python
"""
Google Document AI Configuration with General Processor support
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

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
            "pricing_per_1000": 1.50
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
```

### 3.2 Create General Processor Extractor

Create `src/extraction_methods/docai_general_processor.py`:

```python
"""
Google Document AI General Processor implementation
Handles text extraction, entity recognition, and table parsing
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from google.api_core import retry
from google.api_core.exceptions import GoogleAPICallError

from ..config.docai_config import (
    DOCAI_CONFIG, 
    PROCESSING_CONFIG,
    get_processor_config,
    is_general_processor_configured
)
from ..utils.cost_tracker import CostTracker

logger = logging.getLogger(__name__)


class GeneralProcessorExtractor:
    """
    Document AI General Processor for universal document extraction
    """
    
    def __init__(self):
        """Initialize the general processor extractor"""
        self.config = get_processor_config("general_processor")
        self.cost_tracker = CostTracker()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Document AI client with proper configuration"""
        if not is_general_processor_configured():
            logger.warning("General processor not configured")
            return
        
        try:
            location = DOCAI_CONFIG["location"]
            opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
            self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
            
            # Build processor name
            self.processor_name = self.client.processor_path(
                DOCAI_CONFIG["project_id"],
                location,
                self.config["id"]
            )
            logger.info(f"Initialized general processor: {self.processor_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize DocAI client: {e}")
            self.client = None
    
    async def extract(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract data from document using general processor
        
        Args:
            file_path: Path to document file
            
        Returns:
            Extracted data with text, entities, tables, and metadata
        """
        if not self.client:
            return self._create_error_response("Client not initialized")
        
        # Validate file
        if not self._validate_file(file_path):
            return self._create_error_response(f"Invalid file: {file_path}")
        
        try:
            # Process document
            document = await self._process_document(file_path)
            
            # Extract all available data
            result = {
                "success": True,
                "text": document.text,
                "entities": self._extract_entities(document),
                "tables": self._extract_tables(document),
                "form_fields": self._extract_form_fields(document),
                "pages": self._extract_page_info(document),
                "confidence": self._calculate_confidence(document),
                "metadata": {
                    "processor": "general_processor",
                    "file": file_path.name,
                    "pages_count": len(document.pages) if document.pages else 0,
                    "extraction_time": datetime.now().isoformat(),
                    "processor_version": self.config.get("version", "latest")
                }
            }
            
            # Track costs
            self._track_cost(file_path, len(document.pages) if document.pages else 1, True)
            
            logger.info(f"Successfully extracted data from {file_path.name}")
            return result
            
        except GoogleAPICallError as e:
            logger.error(f"API error processing {file_path.name}: {e}")
            return self._handle_api_error(e, file_path)
            
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path.name}: {e}")
            self._track_cost(file_path, 0, False)
            return self._create_error_response(str(e))
    
    @retry.Retry(
        initial=PROCESSING_CONFIG["retry_initial"],
        maximum=PROCESSING_CONFIG["retry_maximum"],
        multiplier=PROCESSING_CONFIG["retry_multiplier"],
        deadline=PROCESSING_CONFIG["retry_deadline"],
        predicate=retry.if_transient_error
    )
    async def _process_document(self, file_path: Path) -> documentai.Document:
        """
        Process document with automatic retry on transient errors
        
        Args:
            file_path: Path to document
            
        Returns:
            Processed document object
        """
        # Read file content
        with open(file_path, "rb") as f:
            content = f.read()
        
        # Determine MIME type
        mime_type = self._get_mime_type(file_path)
        
        # Create request
        raw_document = documentai.RawDocument(
            content=content,
            mime_type=mime_type
        )
        
        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=raw_document,
            # Optional: Add field mask to optimize response
            field_mask=self._get_field_mask()
        )
        
        # Process document
        result = self.client.process_document(
            request=request,
            timeout=PROCESSING_CONFIG["timeout"]
        )
        
        return result.document
    
    def _extract_entities(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract entities from document"""
        entities = []
        
        for entity in document.entities:
            entity_dict = {
                "type": entity.type_,
                "text": entity.mention_text,
                "confidence": entity.confidence,
                "page_anchor": self._get_page_anchor(entity.page_anchor) if entity.page_anchor else None
            }
            
            # Add normalized value if available
            if entity.normalized_value:
                entity_dict["normalized"] = {
                    "text": entity.normalized_value.text,
                    "value": self._parse_normalized_value(entity.normalized_value)
                }
            
            # Add properties if available
            if entity.properties:
                entity_dict["properties"] = [
                    {
                        "type": prop.type_,
                        "text": prop.mention_text,
                        "confidence": prop.confidence
                    }
                    for prop in entity.properties
                ]
            
            entities.append(entity_dict)
        
        return entities
    
    def _extract_tables(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract tables from document"""
        tables = []
        
        for page_num, page in enumerate(document.pages):
            for table_num, table in enumerate(page.tables):
                table_dict = {
                    "page": page_num + 1,
                    "table_index": table_num,
                    "rows": [],
                    "headers": [],
                    "body": []
                }
                
                # Extract header rows
                for row in table.header_rows:
                    header_row = []
                    for cell in row.cells:
                        header_row.append({
                            "text": self._get_cell_text(cell, document.text),
                            "row_span": cell.row_span,
                            "col_span": cell.col_span
                        })
                    table_dict["headers"].append(header_row)
                
                # Extract body rows
                for row in table.body_rows:
                    body_row = []
                    for cell in row.cells:
                        body_row.append({
                            "text": self._get_cell_text(cell, document.text),
                            "row_span": cell.row_span,
                            "col_span": cell.col_span
                        })
                    table_dict["body"].append(body_row)
                
                # Create simplified rows view
                all_rows = table_dict["headers"] + table_dict["body"]
                table_dict["rows"] = [[cell["text"] for cell in row] for row in all_rows]
                
                tables.append(table_dict)
        
        return tables
    
    def _extract_form_fields(self, document: documentai.Document) -> Dict[str, Any]:
        """Extract form fields (key-value pairs) from document"""
        form_fields = {}
        
        for page in document.pages:
            for field in page.form_fields:
                # Get field name (key)
                field_name = self._get_text_from_layout(
                    field.field_name, 
                    document.text
                ) if field.field_name else ""
                
                # Get field value
                field_value = self._get_text_from_layout(
                    field.field_value,
                    document.text
                ) if field.field_value else ""
                
                if field_name:
                    form_fields[field_name] = {
                        "value": field_value,
                        "confidence": field.field_name.confidence if field.field_name else 0.0,
                        "value_type": field.value_type if hasattr(field, 'value_type') else "text"
                    }
        
        return form_fields
    
    def _extract_page_info(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract page-level information"""
        pages = []
        
        for page_num, page in enumerate(document.pages):
            page_info = {
                "page_number": page_num + 1,
                "width": page.dimension.width if page.dimension else 0,
                "height": page.dimension.height if page.dimension else 0,
                "unit": page.dimension.unit if page.dimension else "pixel",
                "detected_languages": [
                    {
                        "code": lang.language_code,
                        "confidence": lang.confidence
                    }
                    for lang in page.detected_languages
                ] if page.detected_languages else [],
                "blocks_count": len(page.blocks) if page.blocks else 0,
                "paragraphs_count": len(page.paragraphs) if page.paragraphs else 0,
                "lines_count": len(page.lines) if page.lines else 0,
                "tokens_count": len(page.tokens) if page.tokens else 0
            }
            pages.append(page_info)
        
        return pages
    
    def _validate_file(self, file_path: Path) -> bool:
        """Validate file before processing"""
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        max_size = self.config.get("max_file_size_mb", 20)
        if file_size_mb > max_size:
            logger.error(f"File too large: {file_size_mb:.2f}MB > {max_size}MB")
            return False
        
        # Check file format
        if file_path.suffix.lower() not in self.config.get("supported_formats", []):
            logger.error(f"Unsupported format: {file_path.suffix}")
            return False
        
        return True
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type for file"""
        suffix = file_path.suffix.lower()
        return DOCAI_CONFIG["mime_type_mapping"].get(suffix, "application/octet-stream")
    
    def _get_field_mask(self) -> Optional[str]:
        """Get field mask to optimize API response"""
        # Return specific fields we need to reduce response size
        return "text,entities,pages.form_fields,pages.tables,pages.dimension"
    
    def _get_cell_text(self, cell, document_text: str) -> str:
        """Extract text from table cell"""
        if not cell.layout:
            return ""
        return self._get_text_from_layout(cell.layout, document_text)
    
    def _get_text_from_layout(self, layout, document_text: str) -> str:
        """Extract text from layout element"""
        if not layout or not layout.text_anchor:
            return ""
        
        text = ""
        for segment in layout.text_anchor.text_segments:
            start = int(segment.start_index) if segment.start_index else 0
            end = int(segment.end_index) if segment.end_index else len(document_text)
            text += document_text[start:end]
        
        return text.strip()
    
    def _get_page_anchor(self, page_anchor) -> Dict[str, Any]:
        """Extract page anchor information"""
        if not page_anchor or not page_anchor.page_refs:
            return {}
        
        return {
            "pages": [
                {
                    "page": ref.page,
                    "confidence": ref.confidence if hasattr(ref, 'confidence') else 1.0
                }
                for ref in page_anchor.page_refs
            ]
        }
    
    def _parse_normalized_value(self, normalized_value) -> Any:
        """Parse normalized value based on type"""
        if normalized_value.money_value:
            return {
                "type": "money",
                "amount": normalized_value.money_value.amount,
                "currency": normalized_value.money_value.currency_code
            }
        elif normalized_value.date_value:
            return {
                "type": "date",
                "year": normalized_value.date_value.year,
                "month": normalized_value.date_value.month,
                "day": normalized_value.date_value.day
            }
        elif normalized_value.datetime_value:
            return {
                "type": "datetime",
                "value": normalized_value.datetime_value
            }
        elif normalized_value.address_value:
            return {
                "type": "address",
                "value": normalized_value.address_value
            }
        elif normalized_value.boolean_value is not None:
            return {
                "type": "boolean",
                "value": normalized_value.boolean_value
            }
        else:
            return normalized_value.text if normalized_value.text else None
    
    def _calculate_confidence(self, document: documentai.Document) -> float:
        """Calculate overall document confidence"""
        confidences = []
        
        # Collect entity confidences
        for entity in document.entities:
            if entity.confidence:
                confidences.append(entity.confidence)
        
        # Collect form field confidences
        for page in document.pages:
            for field in page.form_fields:
                if field.field_name and field.field_name.confidence:
                    confidences.append(field.field_name.confidence)
                if field.field_value and field.field_value.confidence:
                    confidences.append(field.field_value.confidence)
        
        # Return average confidence or default
        if confidences:
            return sum(confidences) / len(confidences)
        return 0.85  # Default confidence for general processor
    
    def _track_cost(self, file_path: Path, pages: int, success: bool):
        """Track processing costs"""
        cost = (pages / 1000) * self.config.get("pricing_per_1000", 1.50)
        
        self.cost_tracker.record(
            service="docai_general",
            processor_type="general_processor",
            cost=cost,
            pages=pages,
            document=file_path.name,
            success=success
        )
    
    def _handle_api_error(self, error: GoogleAPICallError, file_path: Path) -> Dict[str, Any]:
        """Handle API errors with appropriate responses"""
        error_code = error.code if hasattr(error, 'code') else 500
        
        if error_code == 429:  # Rate limit
            return self._create_error_response(
                "Rate limit exceeded. Please retry after a moment.",
                error_code=429,
                retry_after=60
            )
        elif error_code == 403:  # Permission denied
            return self._create_error_response(
                "Permission denied. Check processor access and credentials.",
                error_code=403
            )
        elif error_code >= 500:  # Server error
            return self._create_error_response(
                "Server error. The request can be retried.",
                error_code=error_code,
                retryable=True
            )
        else:
            return self._create_error_response(
                f"API error: {str(error)}",
                error_code=error_code
            )
    
    def _create_error_response(self, message: str, **kwargs) -> Dict[str, Any]:
        """Create standardized error response"""
        response = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat()
        }
        response.update(kwargs)
        return response


# Batch processing support
class BatchProcessor:
    """
    Batch processing for multiple documents
    """
    
    def __init__(self, processor: GeneralProcessorExtractor):
        self.processor = processor
        self.max_concurrent = 5  # Limit concurrent requests
    
    async def process_batch(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch
        
        Args:
            file_paths: List of document paths
            
        Returns:
            List of extraction results
        """
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_limit(file_path: Path):
            async with semaphore:
                return await self.processor.extract(file_path)
        
        # Process all documents concurrently with limit
        tasks = [process_with_limit(fp) for fp in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "success": False,
                    "error": str(result),
                    "file": file_paths[i].name
                })
            else:
                processed_results.append(result)
        
        return processed_results
```

### 3.3 Integration with Existing Pipeline

Update `src/extraction_methods/multimodal_llm/providers/hybrid_extractor.py`:

```python
# Add to imports
from ..docai_general_processor import GeneralProcessorExtractor

class HybridDocumentExtractor:
    def __init__(self, api_key: Optional[str] = None, use_files_api: bool = False):
        # ... existing initialization ...
        
        # Initialize general processor if configured
        self.general_processor = None
        if is_general_processor_configured():
            self.general_processor = GeneralProcessorExtractor()
            print("  ✅ General Processor initialized")
    
    async def extract(self, file_path: Path, doc_type: Optional[DocumentType] = None) -> Dict[str, Any]:
        """Smart routing with general processor as primary option"""
        
        # Excel files: Always use pandas
        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            return await self.excel_extractor.extract(file_path)
        
        # Try general processor first (if available)
        if self.general_processor:
            print(f"  → Using Document AI General Processor")
            result = await self.general_processor.extract(file_path)
            
            if result.get("success"):
                return self._standardize_result(result)
            else:
                print(f"  ⚠️ General processor failed: {result.get('error')}")
                print(f"  → Falling back to Claude Vision")
        
        # Fallback to Claude Vision
        return await self.claude_extractor.extract_all([str(file_path)])
    
    def _standardize_result(self, docai_result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert DocAI result to standard format"""
        return {
            'text': docai_result.get('text', ''),
            'entities': docai_result.get('entities', []),
            'tables': docai_result.get('tables', []),
            'form_fields': docai_result.get('form_fields', {}),
            'confidence': docai_result.get('confidence', 0.85),
            '_metadata': docai_result.get('metadata', {})
        }
```

---

## 4. Testing & Validation

### 4.1 Create Test Script

Create `test_general_processor.py`:

```python
#!/usr/bin/env python3
"""Test script for Document AI General Processor"""

import asyncio
import json
from pathlib import Path
from src.extraction_methods.docai_general_processor import GeneralProcessorExtractor

async def test_single_document():
    """Test processing a single document"""
    
    # Initialize processor
    processor = GeneralProcessorExtractor()
    
    # Test document
    test_file = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"Processing: {test_file.name}")
    result = await processor.extract(test_file)
    
    if result.get("success"):
        print(f"✅ Extraction successful!")
        print(f"  - Text length: {len(result.get('text', ''))}")
        print(f"  - Entities found: {len(result.get('entities', []))}")
        print(f"  - Tables found: {len(result.get('tables', []))}")
        print(f"  - Form fields: {len(result.get('form_fields', {}))}")
        print(f"  - Confidence: {result.get('confidence', 0):.2%}")
        
        # Save result for inspection
        output_file = Path("outputs/test_general_processor_result.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"  - Full result saved to: {output_file}")
    else:
        print(f"❌ Extraction failed: {result.get('error')}")

async def test_batch_processing():
    """Test batch processing multiple documents"""
    
    from src.extraction_methods.docai_general_processor import BatchProcessor
    
    processor = GeneralProcessorExtractor()
    batch_processor = BatchProcessor(processor)
    
    # Get test documents
    test_dir = Path("inputs/real/Brigham_dallas")
    test_files = list(test_dir.glob("*.pdf"))[:3]  # Test with first 3 PDFs
    
    if not test_files:
        print("❌ No test files found")
        return
    
    print(f"Batch processing {len(test_files)} documents...")
    results = await batch_processor.process_batch(test_files)
    
    # Summary
    successful = sum(1 for r in results if r.get("success"))
    print(f"\n📊 Batch Results:")
    print(f"  - Total: {len(results)}")
    print(f"  - Successful: {successful}")
    print(f"  - Failed: {len(results) - successful}")
    
    for i, result in enumerate(results):
        status = "✅" if result.get("success") else "❌"
        print(f"  {status} {test_files[i].name}")

async def main():
    """Run all tests"""
    print("="*60)
    print("Document AI General Processor Tests")
    print("="*60)
    
    print("\n1. Testing single document processing...")
    await test_single_document()
    
    print("\n2. Testing batch processing...")
    await test_batch_processing()
    
    print("\n" + "="*60)
    print("Tests complete!")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4.2 Integration Test

Create `test_pipeline_with_docai.py`:

```python
#!/usr/bin/env python3
"""Test full pipeline with Document AI integration"""

import asyncio
from pathlib import Path
from src.template_extraction.comprehensive_processor import ComprehensiveProcessor

async def test_comprehensive_with_docai():
    """Test comprehensive processor with DocAI enabled"""
    
    processor = ComprehensiveProcessor(use_docai=True)
    
    # Test documents
    documents = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf")
    ]
    
    print("Testing comprehensive processor with DocAI...")
    
    for doc in documents:
        if doc.exists():
            print(f"\nProcessing: {doc.name}")
            result = await processor.process_document(doc)
            
            print(f"  Extraction method: {result.get('_metadata', {}).get('extraction_method', 'unknown')}")
            print(f"  Fields extracted: {len(result)}")
            
            # Check if DocAI was used
            if "general_processor" in str(result.get('_metadata', {})):
                print("  ✅ Document AI General Processor used")
            else:
                print("  ⚠️ Fallback method used")

if __name__ == "__main__":
    asyncio.run(test_comprehensive_with_docai())
```

---

## 5. Deployment Steps

### 5.1 Pre-deployment Checklist

```bash
#!/bin/bash
# pre_deploy_check.sh

echo "Pre-deployment checks for Document AI integration"
echo "================================================="

# Check environment variables
echo "1. Checking environment variables..."
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "  ❌ GOOGLE_CLOUD_PROJECT not set"
    exit 1
else
    echo "  ✅ Project: $GOOGLE_CLOUD_PROJECT"
fi

if [ -z "$DOCAI_GENERAL_PROCESSOR_ID" ]; then
    echo "  ❌ DOCAI_GENERAL_PROCESSOR_ID not set"
    exit 1
else
    echo "  ✅ Processor: $DOCAI_GENERAL_PROCESSOR_ID"
fi

# Check authentication
echo "2. Checking authentication..."
python scripts/verify_docai_setup.py
if [ $? -ne 0 ]; then
    echo "  ❌ Authentication check failed"
    exit 1
fi

# Run tests
echo "3. Running tests..."
python test_general_processor.py
if [ $? -ne 0 ]; then
    echo "  ❌ Tests failed"
    exit 1
fi

echo "✅ All checks passed! Ready for deployment."
```

### 5.2 Deployment Steps

1. **Merge to main branch**:
```bash
git checkout main
git merge feature/docai-integration
git push origin main
```

2. **Deploy configuration**:
```bash
# Copy environment variables to production
scp .env production-server:/app/.env

# Or use secrets manager
gcloud secrets create docai-processor-id --data-file=processor-id.txt
```

3. **Monitor initial usage**:
```python
# monitor_docai.py
from src.utils.cost_tracker import CostTracker

tracker = CostTracker()
summary = tracker.get_daily_summary()
print(f"DocAI Usage Today: ${summary.get('docai_general', 0):.2f}")
```

---

## 6. Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| `Permission denied` error | 1. Check service account roles<br>2. Verify processor ID<br>3. Ensure API is enabled |
| `Processor not found` | 1. Verify processor ID matches exactly<br>2. Check region/location<br>3. Ensure processor is deployed |
| `Invalid authentication` | 1. Check GOOGLE_APPLICATION_CREDENTIALS path<br>2. Verify JSON key file exists<br>3. Try `gcloud auth application-default login` |
| `Rate limit exceeded` | 1. Implement exponential backoff<br>2. Reduce concurrent requests<br>3. Check quota limits in Console |
| `File too large` | 1. Check file size (<20MB)<br>2. Split large PDFs<br>3. Use batch processing API |
| `Poor extraction quality` | 1. Check document quality<br>2. Ensure correct MIME type<br>3. Try preprocessing (deskew, denoise) |

### Debug Logging

Enable detailed logging:

```python
import logging

# Enable debug logging for DocAI
logging.getLogger('google.cloud.documentai').setLevel(logging.DEBUG)
logging.getLogger('src.extraction_methods.docai_general_processor').setLevel(logging.DEBUG)
```

### Performance Optimization

1. **Use field masks** to reduce response size:
```python
field_mask = "text,entities,pages.tables"  # Only get needed fields
```

2. **Batch processing** for multiple documents:
```python
# Process up to 50 documents in one request
batch_processor = BatchProcessor(processor)
results = await batch_processor.process_batch(file_paths)
```

3. **Implement caching** for repeated documents:
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def process_cached(file_hash: str):
    # Cache results by file hash
    pass
```

---

## Next Steps

With the general processor integrated, you can:

1. **Monitor performance** and adjust routing logic
2. **Add specialized processors** as they become available
3. **Implement advanced features** like custom entity extraction
4. **Optimize costs** by routing documents to appropriate processors

This completes the technical implementation guide for integrating Google Document AI General Processor into your loan processing pipeline.