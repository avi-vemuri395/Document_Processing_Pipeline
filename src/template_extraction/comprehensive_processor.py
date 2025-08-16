"""
Comprehensive Document Processor - Part 1 of Two-Part Pipeline
Extracts data ONCE from documents comprehensively (not using form templates)
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..extraction_methods.multimodal_llm.providers import BenchmarkExtractor
from .incremental_utils import merge_extractions


class ComprehensiveProcessor:
    """
    Correctly implements Part 1: Extract data ONCE from documents.
    
    This processor extracts ALL available data from documents without
    using form templates. Form templates are for FILLING forms, not
    for EXTRACTING from documents.
    """
    
    def __init__(self):
        """Initialize with comprehensive extractor"""
        self.extractor = BenchmarkExtractor()
        self.output_base = Path("outputs/applications")
    
    async def process_document(
        self, 
        document_path: Path, 
        application_id: str
    ) -> Dict[str, Any]:
        """
        Process a single document and extract ALL data comprehensively.
        
        Args:
            document_path: Path to document to process
            application_id: Unique application identifier
            
        Returns:
            Updated master data after merging this document's extraction
        """
        print(f"\n📄 Processing document: {document_path.name}")
        
        # Ensure output directory exists
        app_dir = self.output_base / application_id / "part1_document_processing"
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Extract ALL data from document (unstructured)
        print("  ⚙️  Extracting data comprehensively...")
        try:
            raw_extraction = await self.extractor.extract_all([str(document_path)])
        except Exception as e:
            print(f"  ❌ Extraction failed: {e}")
            return {}
        
        # 2. Structure the extracted data
        structured_data = self._structure_extracted_data(
            raw_extraction, 
            document_path.name
        )
        
        # 3. Save individual extraction
        extraction_path = app_dir / "extractions" / f"{document_path.stem}_extraction.json"
        extraction_path.parent.mkdir(exist_ok=True)
        with open(extraction_path, 'w') as f:
            json.dump(structured_data, f, indent=2, default=str)
        print(f"  ✅ Saved extraction to {extraction_path.name}")
        
        # 4. Load existing master data
        master_path = app_dir / "master_data.json"
        existing_master = self._load_master_data(master_path)
        
        # 5. Merge with existing data
        updated_master = self._merge_with_master(
            existing_master, 
            structured_data,
            application_id
        )
        
        # 6. Save updated master data
        with open(master_path, 'w') as f:
            json.dump(updated_master, f, indent=2, default=str)
        print(f"  ✅ Updated master data with {len(structured_data)} categories")
        
        # 7. Update processing state
        self._update_state(app_dir, document_path.name, updated_master)
        
        return updated_master
    
    async def process_documents(
        self,
        document_paths: List[Path],
        application_id: str
    ) -> Dict[str, Any]:
        """
        Process multiple documents for an application.
        
        Args:
            document_paths: List of document paths to process
            application_id: Unique application identifier
            
        Returns:
            Final master data after processing all documents
        """
        print(f"\n{'='*70}")
        print(f"  PART 1: COMPREHENSIVE DOCUMENT PROCESSING")
        print(f"  Application ID: {application_id}")
        print(f"  Documents to process: {len(document_paths)}")
        print(f"{'='*70}")
        
        master_data = {}
        for doc_path in document_paths:
            if doc_path.exists():
                master_data = await self.process_document(doc_path, application_id)
            else:
                print(f"  ⚠️  Document not found: {doc_path}")
        
        print(f"\n✅ Part 1 Complete: Extracted data from {len(document_paths)} documents")
        return master_data
    
    def _structure_extracted_data(
        self, 
        raw_data: Dict[str, Any], 
        source_document: str
    ) -> Dict[str, Any]:
        """
        Map extraction results to pipeline categories.
        
        Handles two formats:
        1. PDF/Image extraction: Has keys like personal, addresses, business, financials
        2. Excel extraction: Has file paths as keys with nested data structure
        
        Pipeline expects:
        - personal_info: personal data + addresses
        - business_info: business entities and ownership
        - financial_data: all financial statements and metrics
        - tax_data: tax return information
        - debt_schedules: loans and debt details
        
        Args:
            raw_data: Raw extraction from BenchmarkExtractor
            source_document: Name of source document
            
        Returns:
            Structured data organized by pipeline categories
        """
        # Initialize categories
        structured = {
            "personal_info": {},
            "business_info": {},
            "financial_data": {},
            "tax_data": {},
            "debt_schedules": {},
            "other_data": {},
            "metadata": {
                "source_document": source_document,
                "extraction_timestamp": datetime.now().isoformat(),
                "extraction_method": "unknown"  # Will be updated based on actual method
            }
        }
        
        # Check if this is Excel extraction format (has file paths as keys)
        is_excel_format = False
        for key in raw_data.keys():
            if key not in ['_metadata', 'error'] and '/' in str(key):
                is_excel_format = True
                break
        
        if is_excel_format:
            # Handle Excel extraction format
            for file_path, excel_data in raw_data.items():
                if file_path == '_metadata':
                    structured["metadata"]["extraction_metadata"] = excel_data
                    continue
                    
                if isinstance(excel_data, dict):
                    # Set extraction method from Excel data
                    if 'extraction_method' in excel_data:
                        structured["metadata"]["extraction_method"] = excel_data['extraction_method']
                    
                    # Store document type and confidence
                    if 'document_type' in excel_data:
                        structured["metadata"]["document_type"] = excel_data['document_type']
                    if 'confidence' in excel_data:
                        structured["metadata"]["confidence"] = excel_data['confidence']
                    
                    # Map financial data from Excel
                    if 'data' in excel_data and isinstance(excel_data['data'], dict):
                        data = excel_data['data']
                        
                        if 'financial_data' in data:
                            structured["financial_data"].update(data['financial_data'])
                        
                        # Store any metadata from Excel
                        if 'metadata' in data:
                            structured["other_data"]["excel_metadata"] = data['metadata']
        else:
            # Handle standard PDF/image extraction format
            structured["metadata"]["extraction_method"] = "comprehensive_llm"
            
            # Map personal data
            if "personal" in raw_data and raw_data["personal"]:
                structured["personal_info"]["personal"] = raw_data["personal"]
            
            # Map addresses (combine with personal_info)
            if "addresses" in raw_data and raw_data["addresses"]:
                structured["personal_info"]["addresses"] = raw_data["addresses"]
            
            # Map business information
            if "business" in raw_data and raw_data["business"]:
                structured["business_info"]["business"] = raw_data["business"]
            
            # Map financial data
            if "financials" in raw_data and raw_data["financials"]:
                structured["financial_data"] = raw_data["financials"]
            
            # Map tax information
            if "tax_information" in raw_data and raw_data["tax_information"]:
                structured["tax_data"] = raw_data["tax_information"]
            elif "tax_data" in raw_data and raw_data["tax_data"]:
                structured["tax_data"] = raw_data["tax_data"]
            
            # Map debt schedules
            if "debt_details" in raw_data and raw_data["debt_details"]:
                structured["debt_schedules"] = raw_data["debt_details"]
            elif "liabilities" in raw_data and raw_data["liabilities"]:
                structured["debt_schedules"]["liabilities"] = raw_data["liabilities"]
            
            # Map checkboxes and questions (often important for forms)
            if "checkboxes_and_questions" in raw_data and raw_data["checkboxes_and_questions"]:
                structured["other_data"]["checkboxes_and_questions"] = raw_data["checkboxes_and_questions"]
            
            # Store any other top-level keys in other_data
            skip_keys = {
                "personal", "addresses", "business", "financials", 
                "tax_information", "tax_data", "debt_details", "liabilities",
                "checkboxes_and_questions", "metadata", "_metadata",
                "_extraction_failed", "error", "raw_text"
            }
            
            for key, value in raw_data.items():
                if key not in skip_keys and value:
                    # Check if it's substantial data (not empty dict/list/string)
                    if isinstance(value, dict) and value:
                        structured["other_data"][key] = value
                    elif isinstance(value, list) and value:
                        structured["other_data"][key] = value
                    elif isinstance(value, (str, int, float, bool)) and value != "":
                        structured["other_data"][key] = value
            
            # Add extraction metadata if present
            if "_metadata" in raw_data:
                structured["metadata"]["extraction_metadata"] = raw_data["_metadata"]
        
        return structured
    
    def _load_master_data(self, master_path: Path) -> Dict[str, Any]:
        """Load existing master data or return empty structure"""
        if master_path.exists():
            with open(master_path, 'r') as f:
                return json.load(f)
        
        return {
            "personal_info": {},
            "business_info": {},
            "financial_data": {},
            "tax_data": {},
            "debt_schedules": {},
            "other_data": {},
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "documents_processed": []
            }
        }
    
    def _deep_merge_dicts(self, existing: Any, new: Any) -> Any:
        """
        Deep merge two dictionaries, preserving existing non-null values.
        
        Rules:
        - For dicts: Recursively merge
        - For lists: Append new items if not already present
        - For primitives: New value wins only if it's not null/empty
        - Empty strings, None, empty lists/dicts don't override existing values
        """
        # If new value is None or empty string, keep existing
        if new is None or new == "":
            return existing
            
        # If existing is None or empty string, take new value
        if existing is None or existing == "":
            return new
            
        # Both are dicts - merge recursively
        if isinstance(existing, dict) and isinstance(new, dict):
            result = existing.copy()
            for key, new_value in new.items():
                if key in result:
                    result[key] = self._deep_merge_dicts(result[key], new_value)
                else:
                    # Only add if new value is substantial
                    if new_value not in [None, "", [], {}]:
                        result[key] = new_value
            return result
            
        # Both are lists - combine unique items
        if isinstance(existing, list) and isinstance(new, list):
            # For lists of dicts (like addresses, co_applicants), append new items
            # For simple lists, combine unique values
            result = existing.copy()
            for item in new:
                if item not in result and item not in [None, "", [], {}]:
                    result.append(item)
            return result
            
        # For primitives (strings, numbers, booleans)
        # New value wins only if it's not empty/null
        if new not in [None, "", [], {}]:
            return new
        else:
            return existing
    
    def _merge_with_master(
        self,
        existing_master: Dict[str, Any],
        new_data: Dict[str, Any],
        application_id: str
    ) -> Dict[str, Any]:
        """
        Merge new extraction with existing master data using deep merge.
        
        Preserves existing data while adding new information.
        Empty/null values in new data won't override existing values.
        """
        # Start with existing master structure
        merged = existing_master.copy()
        
        # Deep merge each category
        for category in ["personal_info", "business_info", "financial_data", 
                        "tax_data", "debt_schedules", "other_data"]:
            if category in new_data:
                if category not in merged:
                    merged[category] = {}
                
                # Use deep merge instead of shallow replacement
                merged[category] = self._deep_merge_dicts(
                    merged.get(category, {}),
                    new_data[category]
                )
        
        # Update metadata
        merged["metadata"]["last_updated"] = datetime.now().isoformat()
        merged["metadata"]["application_id"] = application_id
        
        # Track processed documents
        if "documents_processed" not in merged["metadata"]:
            merged["metadata"]["documents_processed"] = []
        
        source_doc = new_data.get("metadata", {}).get("source_document", "unknown")
        if source_doc not in merged["metadata"]["documents_processed"]:
            merged["metadata"]["documents_processed"].append(source_doc)
        
        return merged
    
    def _update_state(
        self, 
        app_dir: Path, 
        document_name: str,
        master_data: Dict[str, Any]
    ):
        """Update processing state for tracking"""
        state_dir = app_dir / "state"
        state_dir.mkdir(exist_ok=True)
        
        state = {
            "last_document_processed": document_name,
            "processing_timestamp": datetime.now().isoformat(),
            "documents_processed": master_data.get("metadata", {}).get("documents_processed", []),
            "field_counts": {
                category: len(fields)
                for category, fields in master_data.items()
                if isinstance(fields, dict) and category != "metadata"
            },
            "total_fields": sum(
                len(fields) for category, fields in master_data.items()
                if isinstance(fields, dict) and category != "metadata"
            )
        }
        
        state_path = state_dir / "current_state.json"
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)