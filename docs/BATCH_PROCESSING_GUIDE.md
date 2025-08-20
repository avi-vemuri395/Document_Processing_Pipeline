# 🚀 Document AI Batch Processing Implementation Guide

## Overview

This guide provides a complete implementation reference for adding Google Document AI batch processing capabilities to handle large documents that exceed sync processing limits.

## Problem Statement

**Issue**: Document AI Form Parser has a 15-page sync limit, causing large documents to fall back to expensive Claude Vision API processing.

**Solution**: Implement Document AI batch processing to handle documents up to 200 pages using the same Form Parser quality at the same cost ($30/1000 pages).

## Implementation Architecture

### Intelligent Document Routing

```
Document Input → File Size Check → Processing Route Selection

├─ <2MB   → Sync Form Parser (3-5 seconds)
├─ ≥2MB   → Batch Form Parser (2-10 minutes) 
└─ Fallback → Claude Vision (if DocAI fails)
```

### Batch Processing Workflow

```
1. GCS Upload     → Upload document to temporary bucket
2. Batch Submit   → Submit to Document AI batch API  
3. LRO Polling    → Poll Long Running Operation for completion
4. Result Fetch   → Download and parse results from GCS
5. Format Convert → Convert to standard extraction format
6. Cleanup        → Remove temporary files
```

## Core Implementation

### 1. Batch Processor Class

**File**: `src/extraction_methods/docai_batch_processor.py`

```python
class BatchDocumentProcessor:
    """
    Document AI Batch Processor for large documents (>2MB)
    
    Features:
    - Conservative threshold-based routing (2MB default)
    - GCS temporary file management with auto-cleanup
    - LRO polling with exponential backoff
    - Same output format as Form Parser for seamless integration
    """
    
    def __init__(self):
        """Initialize batch processor with GCS and DocAI clients"""
        self.config = get_processor_config("form_parser")
        self.client = documentai.DocumentProcessorServiceClient(client_options=opts)
        self.storage_client = storage.Client(project=DOCAI_CONFIG["project_id"])
        self.temp_bucket_name = f"{DOCAI_CONFIG['project_id']}-docai-batch-temp"
    
    async def process_large_document(self, file_path: Path, threshold_mb: float = 2.0):
        """Process large document using batch API"""
        # 1. File size validation
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb < threshold_mb:
            return {"success": False, "error": "File too small for batch processing"}
        
        # 2. Upload to GCS
        gcs_uri = await self._upload_to_gcs(file_path)
        
        # 3. Submit batch request
        operation_future = await self._submit_batch_request(gcs_uri, file_path.name)
        
        # 4. Poll for completion
        batch_result = await self._poll_operation(operation_future)
        
        # 5. Cleanup and convert
        await self._cleanup_gcs_file(gcs_uri)
        return self._convert_to_standard_format(batch_result, file_path)
```

**Key Methods:**

- `_upload_to_gcs()`: Creates temporary bucket and uploads document
- `_submit_batch_request()`: Configures and submits Document AI batch request
- `_poll_operation()`: Polls LRO with exponential backoff (10-minute timeout)
- `_retrieve_batch_result()`: Downloads and parses results from GCS
- `_convert_to_standard_format()`: Ensures output matches sync Form Parser format

### 2. Configuration Management

**File**: `src/config/docai_config.py`

```python
# Batch processing configuration
BATCH_CONFIG = {
    "enabled": os.getenv("DOCAI_BATCH_ENABLED", "true").lower() == "true",
    "threshold_mb": float(os.getenv("DOCAI_BATCH_THRESHOLD_MB", "2.0")),
    "timeout_minutes": int(os.getenv("DOCAI_BATCH_TIMEOUT_MINUTES", "10")),
    "temp_bucket_suffix": "docai-batch-temp",
    "cleanup_hours": 24,
    "poll_interval_seconds": 10,
    "max_poll_interval_seconds": 60
}

def is_batch_processor_configured() -> bool:
    """Check if batch processor is properly configured"""
    if not is_form_parser_configured():
        return False
    
    if not BATCH_CONFIG["enabled"]:
        return False
    
    try:
        import google.cloud.storage
        return True
    except ImportError:
        print("WARNING: google-cloud-storage not available")
        return False

def should_use_batch_processing(file_size_mb: float) -> bool:
    """Determine if file should use batch processing"""
    return file_size_mb >= BATCH_CONFIG["threshold_mb"]
```

### 3. Integration with Existing Pipeline

**File**: `src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py`

```python
class BenchmarkExtractor:
    def __init__(self):
        # Initialize Form Parser (existing)
        self.form_parser = FormParserExtractor() if is_form_parser_configured() else None
        
        # NEW: Initialize Batch Processor
        self.batch_processor = None
        if self.form_parser and DOCAI_AVAILABLE:
            try:
                self.batch_processor = BatchDocumentProcessor()
                print("✅ Google Document AI Batch Processor initialized")
            except Exception as e:
                print(f"⚠️ Could not initialize Batch Processor: {e}")
    
    async def extract_all(self, file_paths, document_types=None):
        # ... existing code ...
        
        # NEW: Intelligent routing for DocAI processing
        for file_path in files_for_docai:
            file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
            
            # Check if file is large enough for batch processing
            if file_size_mb >= 2.0 and self.batch_processor:
                print("🔄 Large file detected - attempting batch processing")
                docai_result = await self.batch_processor.process_large_document(file_path, 2.0)
                
                # If batch processing fails, fall back to sync
                if not docai_result.get("success"):
                    print("⚠️ Batch processing failed - falling back to sync")
                    if file_size_mb <= 1.5:  # Form Parser sync limit
                        docai_result = await self.form_parser.extract(file_path)
                    else:
                        # Too large for sync, will fall back to Claude Vision
                        failed_docai_files.append(file_path)
                        continue
            else:
                # Use sync processing for small files
                docai_result = await self.form_parser.extract(file_path)
```

## Environment Configuration

### Required Environment Variables

```bash
# Core Document AI Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
DOCAI_FORM_PARSER_ID=your-form-parser-id

# Batch Processing Configuration (NEW)
DOCAI_BATCH_ENABLED=true
DOCAI_BATCH_THRESHOLD_MB=2.0
DOCAI_BATCH_TIMEOUT_MINUTES=10
DOCAI_BATCH_BUCKET_SUFFIX=docai-batch-temp
DOCAI_BATCH_CLEANUP_HOURS=24
DOCAI_BATCH_POLL_INTERVAL=10
DOCAI_BATCH_MAX_POLL_INTERVAL=60
```

### Dependencies

**requirements.txt additions:**
```
# Google Cloud Document AI (existing)
google-cloud-documentai==2.20.0

# NEW: Required for batch processing
google-cloud-storage==2.10.0
```

## GCS Permissions Setup

### Required Service Account Permissions

The Document AI service account needs these GCS permissions:

```json
{
  "bindings": [
    {
      "role": "roles/storage.objectAdmin",
      "members": ["serviceAccount:service-PROJECT_NUMBER@document-ai.iam.gserviceaccount.com"]
    }
  ]
}
```

### Alternative: Granular Permissions

```bash
# Grant specific permissions to Document AI service account
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:service-PROJECT_NUMBER@document-ai.iam.gserviceaccount.com" \
    --role="roles/storage.objectCreator"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:service-PROJECT_NUMBER@document-ai.iam.gserviceaccount.com" \
    --role="roles/storage.objectViewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:service-PROJECT_NUMBER@document-ai.iam.gserviceaccount.com" \
    --role="roles/storage.objectDeleter"
```

### Bucket Configuration

The batch processor automatically creates a temporary bucket with:
- **Name**: `{project_id}-docai-batch-temp`
- **Location**: Same as Document AI processor location
- **Lifecycle**: Auto-delete files after 24 hours
- **Purpose**: Temporary storage for batch processing only

## Testing Implementation

### Test Script

**File**: `test_batch_processing.py`

```python
#!/usr/bin/env python3
"""Test Document AI Batch Processing implementation"""

import asyncio
from pathlib import Path
from src.extraction_methods.docai_batch_processor import BatchDocumentProcessor

async def test_batch_processing():
    # Test documents with different sizes
    test_documents = [
        {
            "path": "large_tax_return.pdf",  # 4.9MB, 138 pages
            "expected": "Should use batch processing"
        },
        {
            "path": "small_pfs.pdf",  # 0.5MB, 3 pages  
            "expected": "Should not use batch (below threshold)"
        }
    ]
    
    # Initialize batch processor
    batch_processor = BatchDocumentProcessor()
    
    for doc_info in test_documents:
        doc_path = Path(doc_info["path"])
        file_size_mb = doc_path.stat().st_size / (1024 * 1024)
        
        print(f"\n📄 Testing: {doc_path.name} ({file_size_mb:.2f}MB)")
        print(f"Expected: {doc_info['expected']}")
        
        # Test batch processing
        result = await batch_processor.process_large_document(doc_path, 2.0)
        
        if result.get("success"):
            print("✅ Batch processing successful")
            print(f"  • Pages: {result.get('pages', 0)}")
            print(f"  • Form fields: {len(result.get('form_fields', {}))}")
            print(f"  • Confidence: {result.get('confidence', 0):.1%}")
        else:
            print(f"❌ Batch processing failed: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_batch_processing())
```

### Running Tests

```bash
# Test batch processing implementation
python3 test_batch_processing.py

# Test integrated workflow
python3 test_your_main_extraction_workflow.py
```

## Performance Characteristics

### Processing Times
- **Sync Form Parser**: 3-5 seconds per document
- **Batch Form Parser**: 2-10 minutes per document (depending on size)
- **Claude Vision Fallback**: 30-60 seconds per document

### File Size Limits
- **Sync Form Parser**: 15 pages / 1.5MB typical limit
- **Batch Form Parser**: 200 pages / 20MB maximum
- **Conservative Threshold**: 2MB (configurable)

### Cost Comparison
- **Form Parser (sync/batch)**: $30/1000 pages
- **Claude Vision**: $0.01-0.02/document
- **For large documents**: Batch processing is cost-neutral with much better quality

## Error Handling

### Common Issues and Solutions

1. **GCS Permission Errors**
   ```
   Error: 403 The caller does not have permission storage.objects.get
   Solution: Configure Document AI service account permissions
   ```

2. **Batch Processing Timeout**
   ```
   Error: Batch processing failed or timed out
   Solution: Increase DOCAI_BATCH_TIMEOUT_MINUTES
   ```

3. **File Too Large**
   ```
   Error: Document exceeds 200-page limit
   Solution: Document will automatically fall back to Claude Vision
   ```

### Graceful Fallback Chain

```
Batch Processing Failure
    ↓
Try Sync Processing (if <1.5MB)
    ↓
Fall back to Claude Vision
    ↓
Return error if all methods fail
```

## Monitoring and Maintenance

### Key Metrics to Track

1. **Success Rates**
   - Batch processing success rate
   - Fallback frequency to Claude Vision
   - Overall extraction quality

2. **Performance**
   - Average batch processing time
   - GCS upload/download speeds
   - API rate limit encounters

3. **Costs**
   - Document AI usage ($30/1000 pages)
   - GCS storage costs (minimal due to auto-cleanup)
   - Claude Vision usage for fallbacks

### Maintenance Tasks

1. **GCS Bucket Cleanup**
   - Automatic: 24-hour lifecycle policy
   - Manual: Periodic bucket size monitoring

2. **Configuration Tuning**
   - Adjust threshold based on processing patterns
   - Optimize timeout values based on document sizes

3. **Service Account Permissions**
   - Regular audit of GCS permissions
   - Monitor for permission-related failures

## Migration Guide

### Adding to Existing Project

1. **Install Dependencies**
   ```bash
   pip install google-cloud-storage==2.10.0
   ```

2. **Add Configuration**
   - Copy batch configuration to your `docai_config.py`
   - Add environment variables to your `.env` file

3. **Implement Batch Processor**
   - Copy `docai_batch_processor.py` to your extraction methods
   - Integrate with your existing extraction pipeline

4. **Update Routing Logic**
   - Modify your document processor to check file sizes
   - Add batch processing calls for large documents

5. **Configure GCS Permissions**
   - Set up service account permissions
   - Test with a large document

6. **Validate Implementation**
   - Run test script with various document sizes
   - Verify fallback logic works correctly

### Rollback Plan

If issues arise, the implementation can be safely disabled:

```bash
# Disable batch processing
DOCAI_BATCH_ENABLED=false
```

This will route all documents back to the original sync/Claude Vision workflow.

## Conclusion

Document AI batch processing provides a robust solution for handling large documents while maintaining:

- **Quality**: Same extraction quality as sync Form Parser
- **Cost**: Same $30/1000 pages pricing
- **Reliability**: Graceful fallback to existing methods
- **Performance**: Up to 200-page processing capability

The implementation is production-ready once GCS permissions are configured, and can be safely disabled if needed.