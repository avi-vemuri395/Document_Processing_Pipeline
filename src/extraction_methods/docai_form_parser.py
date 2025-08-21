"""
Google Document AI Form Parser implementation
Extracts structured data including key-value pairs, tables, entities, and checkboxes
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
    is_form_parser_configured,
    get_mime_type
)


def _should_retry_docai_error_static(exception: Exception) -> bool:
    """
    Static function to determine if a DocAI error should be retried.
    
    Returns True only for transient errors that might succeed on retry.
    Returns False for deterministic failures like validation errors.
    """
    if not isinstance(exception, GoogleAPICallError):
        return False
    
    # Get error code if available
    error_code = getattr(exception, 'code', None)
    
    # Don't retry client errors (4xx) except rate limiting
    if error_code:
        if error_code == 429:  # Rate limit - should retry
            print(f"     • Rate limit error (429) - will retry")
            return True
        if 400 <= error_code < 500:  # Client errors - don't retry
            print(f"     • Client error ({error_code}) - not retrying")
            return False
        if 500 <= error_code < 600:  # Server errors - retry
            print(f"     • Server error ({error_code}) - will retry")
            return True
    
    # Default to no retry for unknown errors
    return False



class FormParserExtractor:
    """
    Document AI Form Parser for structured document extraction
    Extracts key-value pairs, tables, entities, and checkboxes
    """
    
    def __init__(self):
        """Initialize the form parser extractor"""
        self.config = get_processor_config("form_parser")
        self.client = None
        self.processor_name = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Document AI client with proper configuration"""
        if not is_form_parser_configured():
            print("  ⚠️ WARNING: Form parser not configured - skipping initialization")
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
            print(f"  ✅ Initialized DocAI Form Parser: {self.processor_name}")
            
        except Exception as e:
            print(f"  ❌ ERROR: Failed to initialize DocAI client: {e}")
            self.client = None
    
    async def extract(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract structured data from document using form parser
        
        Args:
            file_path: Path to document file
            
        Returns:
            Extracted data with form fields, tables, entities, and metadata
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
        
        # Check file size and skip if too large for reliable processing
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        max_size = self.config.get("max_file_size_mb", 40)
        
        # Skip files that are likely to exceed page limits
        # Form Parser has a hard limit of 15 pages
        # Rough estimate: 100KB per page average
        if file_size_mb > 1.5:  # ~15 pages at 100KB/page
            return {
                "success": False,
                "error": f"File likely exceeds 15-page limit: {file_size_mb:.2f}MB (fallback to Claude Vision)"
            }
        
        if file_size_mb > max_size:
            return {
                "success": False,
                "error": f"File too large: {file_size_mb:.2f}MB > {max_size}MB"
            }
        
        # Check file format
        if file_path.suffix.lower() not in self.config.get("supported_formats", []):
            return {
                "success": False,
                "error": f"Unsupported format: {file_path.suffix}"
            }
        
        try:
            print(f"  📄 Starting DocAI processing for {file_path.name}")
            
            # Process document with proper async handling and timeout
            document = await self._process_document_async_safe(file_path)
            
            if not document:
                return {
                    "success": False,
                    "error": "Failed to process document"
                }
            
            print(f"  ✅ DocAI processing completed for {file_path.name}, extracting structured data...")
            
            # Extract all structured data
            result = {
                "success": True,
                "text": document.text,
                "form_fields": self._extract_form_fields(document),
                "tables": self._extract_tables(document),
                "entities": self._extract_entities(document),
                "checkboxes": self._extract_checkboxes(document),
                "pages": len(document.pages) if document.pages else 0,
                "confidence": self._calculate_confidence(document),
                "metadata": {
                    "processor": "form_parser",
                    "file": file_path.name,
                    "pages_count": len(document.pages) if document.pages else 0,
                    "extraction_time": datetime.now().isoformat()
                }
            }
            
            print(f"  ✅ Successfully extracted structured data from {file_path.name}")
            print(f"     • Form fields: {len(result['form_fields'])}")
            print(f"     • Tables: {len(result['tables'])}")
            print(f"     • Entities: {len(result['entities'])}")
            print(f"     • Checkboxes: {len(result['checkboxes'])}")
            
            return result
            
        except asyncio.TimeoutError:
            print(f"  ❌ ERROR: Timeout processing {file_path.name} - DocAI request exceeded timeout")
            return {
                "success": False,
                "error": "Processing timeout - document may be too complex or service unavailable"
            }
            
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
    
    async def _process_document_async_safe(self, file_path: Path) -> Optional[documentai.Document]:
        """
        Safely process document with proper async handling and timeout.
        Uses asyncio.wait_for to prevent indefinite hanging.
        
        Args:
            file_path: Path to document file
            
        Returns:
            Processed document or None if failed
        """
        try:
            # Calculate appropriate timeout based on file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            # More reasonable timeout: 30s base + 10s per MB
            base_timeout = 30  # Reduced from 120
            extra_timeout = int(file_size_mb * 10)
            timeout = base_timeout + extra_timeout
            
            # Cap at 60 seconds to fail fast and use fallback
            timeout = min(timeout, 60)
            
            print(f"     • Processing document with {timeout}s timeout (file: {file_size_mb:.1f}MB)")
            
            # Run the sync method in executor with timeout
            loop = asyncio.get_running_loop()
            
            # Use asyncio.wait_for to enforce timeout on the executor
            document = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    self._process_document_sync, 
                    file_path
                ),
                timeout=timeout
            )
            
            print(f"     • DocAI processing completed successfully for {file_path.name}")
            return document
            
        except asyncio.TimeoutError:
            print(f"  ⚠️ DocAI processing timeout for {file_path.name} (>{timeout}s)")
            # Return None to trigger fallback instead of raising
            return None
            
        except Exception as e:
            print(f"  ⚠️ Error in async document processing for {file_path.name}: {e}")
            # Return None to trigger fallback instead of raising
            return None
    
    @retry.Retry(
        initial=PROCESSING_CONFIG["retry_initial"],
        maximum=PROCESSING_CONFIG["retry_maximum"],
        multiplier=PROCESSING_CONFIG["retry_multiplier"],
        timeout=PROCESSING_CONFIG["timeout"],
        predicate=_should_retry_docai_error_static
    )
    def _process_document_sync(self, file_path: Path) -> Optional[documentai.Document]:
        """
        Synchronously process document with Form Parser
        
        Args:
            file_path: Path to document file
            
        Returns:
            Processed document or None if failed
        """
        try:
            print(f"     • Reading file: {file_path.name}")
            
            # Read file content
            with open(file_path, "rb") as f:
                content = f.read()
            
            print(f"     • File content read: {len(content)} bytes")
            
            # Determine MIME type
            mime_type = get_mime_type(file_path)
            print(f"     • Detected MIME type: {mime_type}")
            
            # Create document request
            raw_document = documentai.RawDocument(
                content=content,
                mime_type=mime_type
            )
            
            # Configure process options with OCR settings
            process_options = None
            
            # Configure OCR options - always enable native PDF parsing for better quality
            ocr_config = documentai.OcrConfig(
                enable_native_pdf_parsing=True
            )
            
            # Create process options with OCR config
            process_options = documentai.ProcessOptions(
                ocr_config=ocr_config
            )
            
            # Log imageless mode status
            if self.config.get("use_imageless_mode", False):
                print("     • Imageless mode enabled (30-page limit)")
            else:
                print("     • Using standard mode (15-page limit)")
            
            # Create request with process options and imageless mode parameter
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=raw_document,
                process_options=process_options,
                imageless_mode=self.config.get("use_imageless_mode", False)
            )
            
            print(f"     • Sending request to DocAI processor: {self.processor_name}")
            print("     • Waiting for DocAI response...")
            
            # Process document with explicit timeout to prevent hanging
            timeout_seconds = 30  # Fixed 30s timeout for individual API call
            print(f"     • Using API timeout: {timeout_seconds} seconds")
            result = self.client.process_document(request=request, timeout=timeout_seconds)
            
            print(f"     • DocAI response received successfully")
            
            if result and result.document:
                print(f"     • Document processed: {len(result.document.pages) if result.document.pages else 0} pages")
                return result.document
            else:
                print("  ⚠️ WARNING: DocAI returned empty result")
                return None
            
        except Exception as e:
            print(f"  ❌ ERROR: Error in document processing: {e}")
            print(f"     • Error type: {type(e).__name__}")
            if hasattr(e, 'code'):
                print(f"     • Error code: {e.code}")
            raise
    
    def _extract_form_fields(self, document: documentai.Document) -> Dict[str, Any]:
        """
        Extract key-value pairs from form fields
        
        Returns:
            Dictionary of field names to values
        """
        form_fields = {}
        
        for page in document.pages:
            for field in page.form_fields:
                # Extract field name (key)
                field_name = self._get_text(field.field_name, document)
                
                # Extract field value
                field_value = self._get_text(field.field_value, document)
                
                if field_name:
                    # Clean up the field name and value
                    field_name = field_name.strip().replace(":", "").replace("\n", " ")
                    field_value = field_value.strip() if field_value else ""
                    
                    # Store with confidence score
                    form_fields[field_name] = {
                        "value": field_value,
                        "confidence": field.field_name.confidence
                    }
        
        return form_fields
    
    def _extract_tables(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """
        Extract tables from document
        
        Returns:
            List of tables with headers and rows
        """
        tables = []
        
        for page_num, page in enumerate(document.pages):
            for table_num, table in enumerate(page.tables):
                table_data = {
                    "page": page_num + 1,
                    "table_index": table_num,
                    "headers": [],
                    "rows": []
                }
                
                # Extract headers
                if table.header_rows:
                    for header_row in table.header_rows:
                        header_cells = []
                        for cell in header_row.cells:
                            cell_text = self._get_text(cell.layout, document)
                            header_cells.append(cell_text.strip() if cell_text else "")
                        table_data["headers"].append(header_cells)
                
                # Extract body rows
                for row in table.body_rows:
                    row_cells = []
                    for cell in row.cells:
                        cell_text = self._get_text(cell.layout, document)
                        row_cells.append(cell_text.strip() if cell_text else "")
                    table_data["rows"].append(row_cells)
                
                tables.append(table_data)
        
        return tables
    
    def _extract_entities(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """
        Extract generic entities (email, phone, address, etc.)
        
        Returns:
            List of entities with type, text, and confidence
        """
        entities = []
        
        for entity in document.entities:
            entity_data = {
                "type": entity.type_,
                "text": entity.mention_text,
                "confidence": entity.confidence
            }
            
            # Add page reference if available
            if entity.page_anchor and entity.page_anchor.page_refs:
                entity_data["pages"] = [ref.page + 1 for ref in entity.page_anchor.page_refs]
            
            entities.append(entity_data)
        
        return entities
    
    def _extract_checkboxes(self, document: documentai.Document) -> List[Dict[str, Any]]:
        """
        Extract checkboxes and selection marks
        
        Returns:
            List of checkboxes with their state
        """
        checkboxes = []
        
        for page_num, page in enumerate(document.pages):
            for field in page.form_fields:
                # Check if this is a checkbox field
                if field.value_type and "checkbox" in field.value_type.lower():
                    field_name = self._get_text(field.field_name, document)
                    field_value = self._get_text(field.field_value, document)
                    
                    checkbox_data = {
                        "page": page_num + 1,
                        "label": field_name.strip() if field_name else "",
                        "checked": field_value.lower() in ["true", "yes", "checked", "x"] if field_value else False,
                        "confidence": field.field_value.confidence if field.field_value else 0
                    }
                    
                    checkboxes.append(checkbox_data)
        
        return checkboxes
    
    def _get_text(self, layout: documentai.Document.Page.Layout, document: documentai.Document) -> str:
        """
        Extract text from a layout element
        
        Args:
            layout: Layout element containing text anchor
            document: The document containing the text
            
        Returns:
            Extracted text string
        """
        if not layout or not layout.text_anchor or not layout.text_anchor.text_segments:
            return ""
        
        text_segments = []
        for segment in layout.text_anchor.text_segments:
            start = segment.start_index if segment.start_index else 0
            end = segment.end_index if segment.end_index else len(document.text)
            text_segments.append(document.text[start:end])
        
        return "".join(text_segments)
    
    def _calculate_confidence(self, document: documentai.Document) -> float:
        """
        Calculate overall confidence score for the document
        
        Returns:
            Average confidence score (0-1)
        """
        confidences = []
        
        # Collect confidence scores from various elements
        for page in document.pages:
            # Form fields confidence
            for field in page.form_fields:
                if field.field_name and field.field_name.confidence:
                    confidences.append(field.field_name.confidence)
                if field.field_value and field.field_value.confidence:
                    confidences.append(field.field_value.confidence)
            
            # Tables confidence
            for table in page.tables:
                # Combine header and body rows properly
                all_rows = list(table.header_rows) + list(table.body_rows)
                for row in all_rows:
                    for cell in row.cells:
                        if cell.layout and cell.layout.confidence:
                            confidences.append(cell.layout.confidence)
        
        # Entities confidence
        for entity in document.entities:
            if entity.confidence:
                confidences.append(entity.confidence)
        
        # Calculate average
        if confidences:
            return sum(confidences) / len(confidences)
        else:
            # Default confidence if no elements found
            return 0.85