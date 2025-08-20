"""
Google Document AI Batch Processing implementation
Handles large documents using asynchronous batch processing with Google Cloud Storage
"""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from google.cloud import documentai
from google.cloud import storage
from google.api_core.client_options import ClientOptions
from google.api_core import retry
from google.api_core.exceptions import GoogleAPICallError
from google.api_core import operation

from ..config.docai_config import (
    DOCAI_CONFIG, 
    PROCESSING_CONFIG,
    get_processor_config,
    is_form_parser_configured,
    get_mime_type
)


class BatchDocumentProcessor:
    """
    Document AI Batch Processor for large documents (>2MB)
    
    Uses Google Cloud Storage for temporary file management and 
    asynchronous batch processing via Long Running Operations (LRO).
    
    Features:
    - Conservative threshold-based routing (2MB default)
    - GCS temporary file management with auto-cleanup
    - LRO polling with exponential backoff
    - Same output format as Form Parser for seamless integration
    - Graceful error handling with fallback support
    """
    
    def __init__(self):
        """Initialize batch processor with GCS and DocAI clients"""
        self.config = get_processor_config("form_parser")
        self.client = None
        self.storage_client = None
        self.processor_name = None
        self.temp_bucket_name = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize Document AI and Cloud Storage clients"""
        if not is_form_parser_configured():
            print("  ⚠️ WARNING: Form parser not configured - batch processor disabled")
            return
        
        try:
            # Initialize Document AI client
            location = DOCAI_CONFIG["location"]
            opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
            self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
            
            # Build processor name (use Form Parser for batch processing)
            self.processor_name = self.client.processor_path(
                DOCAI_CONFIG["project_id"],
                location,
                self.config["id"]
            )
            
            # Initialize Cloud Storage client
            self.storage_client = storage.Client(project=DOCAI_CONFIG["project_id"])
            
            # Set up temporary bucket name
            self.temp_bucket_name = f"{DOCAI_CONFIG['project_id']}-docai-batch-temp"
            
            print(f"  ✅ Initialized DocAI Batch Processor")
            print(f"     • Processor: {self.processor_name}")
            print(f"     • Temp bucket: {self.temp_bucket_name}")
            
        except Exception as e:
            print(f"  ❌ ERROR: Failed to initialize batch processor: {e}")
            self.client = None
            self.storage_client = None
    
    async def process_large_document(
        self, 
        file_path: Path, 
        threshold_mb: float = 2.0
    ) -> Dict[str, Any]:
        """
        Process large document using batch API
        
        Args:
            file_path: Path to document file
            threshold_mb: Minimum file size in MB to use batch processing
            
        Returns:
            Extracted data in same format as Form Parser, or error dict
        """
        if not self.client or not self.storage_client:
            return {
                "success": False,
                "error": "Batch processor not initialized - check configuration"
            }
        
        # Validate file exists
        if not file_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        # Check if file meets threshold
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb < threshold_mb:
            return {
                "success": False,
                "error": f"File too small for batch processing: {file_size_mb:.2f}MB < {threshold_mb}MB"
            }
        
        # Check file format
        if file_path.suffix.lower() not in self.config.get("supported_formats", []):
            return {
                "success": False,
                "error": f"Unsupported format for batch processing: {file_path.suffix}"
            }
        
        print(f"\n🔄 STARTING BATCH PROCESSING")
        print(f"  • File: {file_path.name}")
        print(f"  • Size: {file_size_mb:.2f} MB")
        print(f"  • Threshold: {threshold_mb} MB")
        
        try:
            # Step 1: Upload to GCS
            print(f"\n📤 Step 1: Uploading to GCS...")
            gcs_uri = await self._upload_to_gcs(file_path)
            if not gcs_uri:
                return {
                    "success": False,
                    "error": "Failed to upload file to GCS"
                }
            
            # Step 2: Submit batch processing request
            print(f"\n🚀 Step 2: Submitting batch request...")
            operation_future = await self._submit_batch_request(gcs_uri, file_path.name)
            if not operation_future:
                await self._cleanup_gcs_file(gcs_uri)
                return {
                    "success": False,
                    "error": "Failed to submit batch processing request"
                }
            
            # Step 3: Poll for completion
            print(f"\n⏳ Step 3: Polling for completion...")
            batch_result = await self._poll_operation(operation_future)
            
            # Step 4: Cleanup GCS file
            print(f"\n🧹 Step 4: Cleaning up temporary files...")
            await self._cleanup_gcs_file(gcs_uri)
            
            if not batch_result:
                return {
                    "success": False,
                    "error": "Batch processing failed or timed out"
                }
            
            # Step 5: Convert to standard format
            print(f"\n✅ Step 5: Converting to standard format...")
            standardized_result = self._convert_to_standard_format(batch_result, file_path)
            
            print(f"\n✅ BATCH PROCESSING COMPLETE")
            print(f"  • File: {file_path.name}")
            print(f"  • Pages processed: {standardized_result.get('pages', 0)}")
            print(f"  • Form fields: {len(standardized_result.get('form_fields', {}))}")
            print(f"  • Tables: {len(standardized_result.get('tables', []))}")
            print(f"  • Entities: {len(standardized_result.get('entities', []))}")
            
            return standardized_result
            
        except Exception as e:
            print(f"\n❌ BATCH PROCESSING FAILED: {e}")
            return {
                "success": False,
                "error": f"Batch processing exception: {str(e)}"
            }
    
    async def _upload_to_gcs(self, file_path: Path) -> Optional[str]:
        """Upload file to GCS and return URI"""
        try:
            # Ensure bucket exists
            bucket = await self._get_or_create_temp_bucket()
            if not bucket:
                return None
            
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            blob_name = f"batch_input/{timestamp}_{unique_id}_{file_path.name}"
            
            print(f"  • Uploading to: gs://{self.temp_bucket_name}/{blob_name}")
            
            # Upload file
            blob = bucket.blob(blob_name)
            
            # Run upload in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, 
                lambda: blob.upload_from_filename(str(file_path))
            )
            
            gcs_uri = f"gs://{self.temp_bucket_name}/{blob_name}"
            print(f"  ✅ Upload complete: {gcs_uri}")
            
            return gcs_uri
            
        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
            return None
    
    async def _get_or_create_temp_bucket(self):
        """Get or create the temporary bucket for batch processing"""
        try:
            # Try to get existing bucket
            loop = asyncio.get_running_loop()
            bucket = await loop.run_in_executor(
                None,
                lambda: self.storage_client.get_bucket(self.temp_bucket_name)
            )
            print(f"  • Using existing bucket: {self.temp_bucket_name}")
            return bucket
            
        except Exception:
            # Bucket doesn't exist, try to create it
            try:
                print(f"  • Creating temporary bucket: {self.temp_bucket_name}")
                bucket = await loop.run_in_executor(
                    None,
                    lambda: self.storage_client.create_bucket(
                        self.temp_bucket_name,
                        location=DOCAI_CONFIG["location"].upper()
                    )
                )
                
                # Set lifecycle rule for auto-cleanup (24 hours)
                lifecycle_rule = {
                    "action": {"type": "Delete"},
                    "condition": {"age": 1}  # Delete after 1 day
                }
                bucket.lifecycle_rules = [lifecycle_rule]
                await loop.run_in_executor(None, bucket.patch)
                
                print(f"  ✅ Created bucket with 24h auto-cleanup")
                return bucket
                
            except Exception as create_error:
                print(f"  ❌ Failed to create bucket: {create_error}")
                return None
    
    async def _submit_batch_request(self, gcs_input_uri: str, file_name: str) -> Optional[operation.Operation]:
        """Submit batch processing request and return operation future"""
        try:
            # Generate output URI
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            output_prefix = f"batch_output/{timestamp}_{unique_id}"
            gcs_output_uri = f"gs://{self.temp_bucket_name}/{output_prefix}/"
            
            print(f"  • Input: {gcs_input_uri}")
            print(f"  • Output: {gcs_output_uri}")
            
            # Create batch process request
            input_config = documentai.BatchDocumentsInputConfig(
                gcs_documents=documentai.GcsDocuments(
                    documents=[
                        documentai.GcsDocument(
                            gcs_uri=gcs_input_uri,
                            mime_type=get_mime_type(Path(file_name))
                        )
                    ]
                )
            )
            
            output_config = documentai.DocumentOutputConfig(
                gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                    gcs_uri=gcs_output_uri
                )
            )
            
            # Configure OCR options (same as sync processing)
            process_options = documentai.ProcessOptions(
                ocr_config=documentai.OcrConfig(
                    enable_native_pdf_parsing=True
                )
            )
            
            request = documentai.BatchProcessRequest(
                name=self.processor_name,
                input_documents=input_config,
                document_output_config=output_config,
                process_options=process_options
            )
            
            print(f"  • Submitting to processor: {self.processor_name}")
            
            # Submit batch request
            loop = asyncio.get_running_loop()
            operation_future = await loop.run_in_executor(
                None,
                lambda: self.client.batch_process_documents(request=request)
            )
            
            print(f"  ✅ Batch request submitted")
            print(f"     • Operation name: {operation_future.operation.name}")
            print(f"     • Output location: {gcs_output_uri}")
            
            # Store output URI for later retrieval
            operation_future._gcs_output_uri = gcs_output_uri
            
            return operation_future
            
        except Exception as e:
            print(f"  ❌ Failed to submit batch request: {e}")
            return None
    
    async def _poll_operation(self, operation_future, timeout_minutes: int = 10) -> Optional[Dict[str, Any]]:
        """Poll LRO until completion with exponential backoff"""
        timeout_seconds = timeout_minutes * 60
        start_time = time.time()
        poll_interval = 10  # Start with 10 second intervals
        max_interval = 60   # Cap at 1 minute intervals
        
        print(f"  • Polling with {timeout_minutes} minute timeout")
        
        try:
            while True:
                elapsed = time.time() - start_time
                
                if elapsed > timeout_seconds:
                    print(f"  ❌ Timeout after {timeout_minutes} minutes")
                    return None
                
                # Check operation status
                loop = asyncio.get_running_loop()
                operation = await loop.run_in_executor(
                    None,
                    lambda: self.client.get_operation(
                        request={"name": operation_future.operation.name}
                    )
                )
                
                if operation.done:
                    print(f"  ✅ Operation completed after {elapsed:.1f} seconds")
                    
                    if operation.error:
                        print(f"  ❌ Operation failed: {operation.error}")
                        return None
                    
                    # Get the actual result from GCS
                    return await self._retrieve_batch_result(operation_future._gcs_output_uri)
                
                # Still processing
                print(f"  ⏳ Still processing... ({elapsed:.0f}s elapsed)")
                
                # Wait with exponential backoff
                await asyncio.sleep(poll_interval)
                poll_interval = min(poll_interval * 1.2, max_interval)
            
        except Exception as e:
            print(f"  ❌ Error polling operation: {e}")
            return None
    
    async def _retrieve_batch_result(self, gcs_output_uri: str) -> Optional[Dict[str, Any]]:
        """Retrieve and parse batch processing results from GCS"""
        try:
            print(f"  • Retrieving results from: {gcs_output_uri}")
            
            # Parse GCS URI to get bucket and prefix
            if not gcs_output_uri.startswith("gs://"):
                print(f"  ❌ Invalid GCS URI: {gcs_output_uri}")
                return None
            
            uri_parts = gcs_output_uri[5:].split("/", 1)  # Remove "gs://" and split
            bucket_name = uri_parts[0]
            prefix = uri_parts[1] if len(uri_parts) > 1 else ""
            
            # List output files
            bucket = self.storage_client.bucket(bucket_name)
            
            loop = asyncio.get_running_loop()
            blobs = await loop.run_in_executor(
                None,
                lambda: list(bucket.list_blobs(prefix=prefix))
            )
            
            # Find JSON result files
            json_blobs = [blob for blob in blobs if blob.name.endswith('.json')]
            
            if not json_blobs:
                print(f"  ❌ No JSON result files found")
                return None
            
            print(f"  • Found {len(json_blobs)} result files")
            
            # Download and parse the first JSON result
            result_blob = json_blobs[0]
            print(f"  • Downloading: {result_blob.name}")
            
            content = await loop.run_in_executor(
                None,
                lambda: result_blob.download_as_bytes()
            )
            
            result_data = json.loads(content.decode('utf-8'))
            
            print(f"  ✅ Retrieved batch result")
            return result_data
            
        except Exception as e:
            print(f"  ❌ Failed to retrieve batch result: {e}")
            return None
    
    async def _cleanup_gcs_file(self, gcs_uri: str):
        """Clean up temporary GCS file"""
        try:
            if not gcs_uri.startswith("gs://"):
                return
            
            uri_parts = gcs_uri[5:].split("/", 1)
            bucket_name = uri_parts[0]
            blob_name = uri_parts[1] if len(uri_parts) > 1 else ""
            
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, blob.delete)
            
            print(f"  ✅ Cleaned up: {gcs_uri}")
            
        except Exception as e:
            print(f"  ⚠️ Cleanup warning: {e}")
            # Non-critical error, don't fail the operation
    
    def _convert_to_standard_format(self, batch_result: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
        """
        Convert batch processing result to standard Form Parser format
        
        Args:
            batch_result: Raw batch processing result from GCS
            file_path: Original file path for metadata
            
        Returns:
            Standardized result matching Form Parser output
        """
        try:
            # Extract document from batch result
            # Batch results have different structure than sync results
            document_data = batch_result
            
            # If this is a batch response, extract the document
            if "responses" in batch_result and batch_result["responses"]:
                document_data = batch_result["responses"][0]
            
            if "document" in document_data:
                document_data = document_data["document"]
            
            # Create standardized result structure
            result = {
                "success": True,
                "text": document_data.get("text", ""),
                "form_fields": self._extract_form_fields_from_batch(document_data),
                "tables": self._extract_tables_from_batch(document_data),
                "entities": self._extract_entities_from_batch(document_data),
                "checkboxes": self._extract_checkboxes_from_batch(document_data),
                "pages": len(document_data.get("pages", [])),
                "confidence": self._calculate_confidence_from_batch(document_data),
                "metadata": {
                    "processor": "form_parser_batch",
                    "file": file_path.name,
                    "pages_count": len(document_data.get("pages", [])),
                    "extraction_time": datetime.now().isoformat(),
                    "processing_mode": "batch"
                }
            }
            
            return result
            
        except Exception as e:
            print(f"  ❌ Error converting batch result: {e}")
            return {
                "success": False,
                "error": f"Failed to convert batch result: {str(e)}"
            }
    
    def _extract_form_fields_from_batch(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract form fields from batch result"""
        form_fields = {}
        
        try:
            pages = document_data.get("pages", [])
            for page in pages:
                for field in page.get("formFields", []):
                    # Extract field name and value
                    field_name = self._extract_text_from_layout(field.get("fieldName"), document_data)
                    field_value = self._extract_text_from_layout(field.get("fieldValue"), document_data)
                    
                    if field_name:
                        field_name = field_name.strip().replace(":", "").replace("\n", " ")
                        field_value = field_value.strip() if field_value else ""
                        
                        form_fields[field_name] = {
                            "value": field_value,
                            "confidence": field.get("fieldName", {}).get("confidence", 0.0)
                        }
        except Exception as e:
            print(f"  ⚠️ Error extracting form fields: {e}")
        
        return form_fields
    
    def _extract_tables_from_batch(self, document_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract tables from batch result"""
        tables = []
        
        try:
            pages = document_data.get("pages", [])
            for page_num, page in enumerate(pages):
                for table_num, table in enumerate(page.get("tables", [])):
                    table_data = {
                        "page": page_num + 1,
                        "table_index": table_num,
                        "headers": [],
                        "rows": []
                    }
                    
                    # Extract header rows
                    for header_row in table.get("headerRows", []):
                        header_cells = []
                        for cell in header_row.get("cells", []):
                            cell_text = self._extract_text_from_layout(cell.get("layout"), document_data)
                            header_cells.append(cell_text.strip() if cell_text else "")
                        table_data["headers"].append(header_cells)
                    
                    # Extract body rows
                    for row in table.get("bodyRows", []):
                        row_cells = []
                        for cell in row.get("cells", []):
                            cell_text = self._extract_text_from_layout(cell.get("layout"), document_data)
                            row_cells.append(cell_text.strip() if cell_text else "")
                        table_data["rows"].append(row_cells)
                    
                    tables.append(table_data)
        except Exception as e:
            print(f"  ⚠️ Error extracting tables: {e}")
        
        return tables
    
    def _extract_entities_from_batch(self, document_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract entities from batch result"""
        entities = []
        
        try:
            for entity in document_data.get("entities", []):
                entity_data = {
                    "type": entity.get("type", ""),
                    "text": entity.get("mentionText", ""),
                    "confidence": entity.get("confidence", 0.0)
                }
                
                # Add page reference if available
                if entity.get("pageAnchor", {}).get("pageRefs"):
                    entity_data["pages"] = [
                        ref.get("page", 0) + 1 
                        for ref in entity["pageAnchor"]["pageRefs"]
                    ]
                
                entities.append(entity_data)
        except Exception as e:
            print(f"  ⚠️ Error extracting entities: {e}")
        
        return entities
    
    def _extract_checkboxes_from_batch(self, document_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract checkboxes from batch result"""
        checkboxes = []
        
        try:
            pages = document_data.get("pages", [])
            for page_num, page in enumerate(pages):
                for field in page.get("formFields", []):
                    # Check if this is a checkbox field
                    if field.get("valueType") and "checkbox" in field.get("valueType", "").lower():
                        field_name = self._extract_text_from_layout(field.get("fieldName"), document_data)
                        field_value = self._extract_text_from_layout(field.get("fieldValue"), document_data)
                        
                        checkbox_data = {
                            "page": page_num + 1,
                            "label": field_name.strip() if field_name else "",
                            "checked": field_value.lower() in ["true", "yes", "checked", "x"] if field_value else False,
                            "confidence": field.get("fieldValue", {}).get("confidence", 0.0)
                        }
                        
                        checkboxes.append(checkbox_data)
        except Exception as e:
            print(f"  ⚠️ Error extracting checkboxes: {e}")
        
        return checkboxes
    
    def _extract_text_from_layout(self, layout: Dict[str, Any], document_data: Dict[str, Any]) -> str:
        """Extract text from layout element in batch result"""
        if not layout or not layout.get("textAnchor"):
            return ""
        
        try:
            text_segments = []
            document_text = document_data.get("text", "")
            
            for segment in layout["textAnchor"].get("textSegments", []):
                start = segment.get("startIndex", 0)
                end = segment.get("endIndex", len(document_text))
                text_segments.append(document_text[start:end])
            
            return "".join(text_segments)
        except Exception:
            return ""
    
    def _calculate_confidence_from_batch(self, document_data: Dict[str, Any]) -> float:
        """Calculate overall confidence from batch result"""
        confidences = []
        
        try:
            # Collect confidence scores from form fields
            pages = document_data.get("pages", [])
            for page in pages:
                for field in page.get("formFields", []):
                    if field.get("fieldName", {}).get("confidence"):
                        confidences.append(field["fieldName"]["confidence"])
                    if field.get("fieldValue", {}).get("confidence"):
                        confidences.append(field["fieldValue"]["confidence"])
            
            # Collect confidence scores from entities
            for entity in document_data.get("entities", []):
                if entity.get("confidence"):
                    confidences.append(entity["confidence"])
            
            # Calculate average
            if confidences:
                return sum(confidences) / len(confidences)
            else:
                return 0.85  # Default confidence for batch processing
        except Exception:
            return 0.85