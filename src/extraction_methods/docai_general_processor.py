"""
Google Document AI General Processor implementation
Simplified extraction without overengineering - handles text, entities, and tables
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from google.api_core import retry
from google.api_core.exceptions import GoogleAPICallError

from ..config.docai_config import (
    DOCAI_CONFIG, 
    PROCESSING_CONFIG,
    get_processor_config,
    is_general_processor_configured,
    get_mime_type
)



class GeneralProcessorExtractor:
    """
    Document AI General Processor for universal document extraction
    Simplified implementation focused on core functionality
    """
    
    def __init__(self):
        """Initialize the general processor extractor"""
        self.config = get_processor_config("general_processor")
        self.client = None
        self.processor_name = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Document AI client with proper configuration"""
        if not is_general_processor_configured():
            print("  ⚠️ WARNING: General processor not configured - skipping initialization")
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
            print(f"  ✅ Initialized DocAI General Processor: {self.processor_name}")
            
        except Exception as e:
            print(f"  ❌ ERROR: Failed to initialize DocAI client: {e}")
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
            return {
                "success": False,
                "error": "Client not initialized - check processor configuration"
            }
        
        # Validate file
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config.get("max_file_size_mb", 20):
            return {
                "success": False,
                "error": f"File too large: {file_size_mb:.2f}MB > 20MB"
            }
        
        # Check file format
        if file_path.suffix.lower() not in self.config.get("supported_formats", []):
            return {
                "success": False,
                "error": f"Unsupported format: {file_path.suffix}"
            }
        
        try:
            # Process document (sync wrapper for async compatibility)
            document = await asyncio.get_event_loop().run_in_executor(
                None, self._process_document_sync, file_path
            )
            
            if not document:
                return {
                    "success": False,
                    "error": "Failed to process document"
                }
            
            # Extract all available data
            result = {
                "success": True,
                "text": document.text,
                "entities": self._extract_entities(document),
                "tables": self._extract_tables(document),
                "form_fields": self._extract_form_fields(document),
                "pages": len(document.pages) if document.pages else 0,
                "confidence": self._calculate_confidence(document),
                "metadata": {
                    "processor": "general_processor",
                    "file": file_path.name,
                    "pages_count": len(document.pages) if document.pages else 0,
                    "extraction_time": datetime.now().isoformat()
                }
            }
            
            print(f"  ✅ Successfully extracted data from {file_path.name}")
            return result
            
        except GoogleAPICallError as e:
            print(f"  ❌ ERROR: API error processing {file_path.name}: {e}")
            return {
                "success": False,
                "error": f"API error: {str(e)}",
                "error_code": e.code if hasattr(e, 'code') else None
            }
            
        except Exception as e:
            print(f"  ❌ ERROR: Unexpected error processing {file_path.name}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @retry.Retry(
        initial=PROCESSING_CONFIG["retry_initial"],
        maximum=PROCESSING_CONFIG["retry_maximum"],
        multiplier=PROCESSING_CONFIG["retry_multiplier"],
        deadline=PROCESSING_CONFIG["retry_deadline"]
    )
    def _process_document_sync(self, file_path: Path) -> Optional[documentai.Document]:
        """
        Process document synchronously with automatic retry on transient errors
        
        Args:
            file_path: Path to document
            
        Returns:
            Processed document object or None
        """
        try:
            # Read file content
            with open(file_path, "rb") as f:
                content = f.read()
            
            # Create request
            raw_document = documentai.RawDocument(
                content=content,
                mime_type=get_mime_type(file_path)
            )
            
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document
            )
            
            # Process document
            result = self.client.process_document(
                request=request,
                timeout=PROCESSING_CONFIG["timeout"]
            )
            
            return result.document
            
        except Exception as e:
            print(f"  ❌ ERROR: Error in document processing: {e}")
            raise
    
    def _extract_entities(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract entities from document"""
        entities = []
        
        for entity in document.entities:
            entity_dict = {
                "type": entity.type_,
                "text": entity.mention_text,
                "confidence": entity.confidence
            }
            
            # Add normalized value if available
            if entity.normalized_value:
                if entity.normalized_value.money_value:
                    entity_dict["normalized"] = {
                        "type": "money",
                        "amount": entity.normalized_value.money_value.amount,
                        "currency": entity.normalized_value.money_value.currency_code
                    }
                elif entity.normalized_value.date_value:
                    entity_dict["normalized"] = {
                        "type": "date",
                        "year": entity.normalized_value.date_value.year,
                        "month": entity.normalized_value.date_value.month,
                        "day": entity.normalized_value.date_value.day
                    }
                elif entity.normalized_value.text:
                    entity_dict["normalized"] = entity.normalized_value.text
            
            entities.append(entity_dict)
        
        return entities
    
    def _extract_tables(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """Extract tables from document"""
        tables = []
        
        for page_num, page in enumerate(document.pages):
            for table_num, table in enumerate(page.tables):
                # Extract header rows
                headers = []
                for row in table.header_rows:
                    header_row = []
                    for cell in row.cells:
                        header_row.append(self._get_cell_text(cell, document.text))
                    headers.append(header_row)
                
                # Extract body rows
                body = []
                for row in table.body_rows:
                    body_row = []
                    for cell in row.cells:
                        body_row.append(self._get_cell_text(cell, document.text))
                    body.append(body_row)
                
                # Create simplified table structure
                table_dict = {
                    "page": page_num + 1,
                    "table_index": table_num,
                    "headers": headers,
                    "body": body,
                    "rows": headers + body  # Combined view for easy access
                }
                
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
                        "confidence": field.field_name.confidence if field.field_name else 0.0
                    }
        
        return form_fields
    
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
        
        # Return average confidence or default
        if confidences:
            return sum(confidences) / len(confidences)
        return 0.85  # Default confidence for general processor