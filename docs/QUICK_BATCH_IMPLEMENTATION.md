# 🚀 Quick Batch Processing Implementation

## 5-Minute Setup Guide

This is a condensed implementation guide for adding Document AI batch processing to any existing document processing pipeline.

## 1. Add Dependencies

**requirements.txt**
```txt
google-cloud-storage==2.10.0
```

## 2. Environment Configuration

**.env**
```bash
# Existing Document AI config
GOOGLE_CLOUD_PROJECT=your-project-id
DOCAI_FORM_PARSER_ID=your-processor-id

# NEW: Batch processing config
DOCAI_BATCH_ENABLED=true
DOCAI_BATCH_THRESHOLD_MB=2.0
DOCAI_BATCH_TIMEOUT_MINUTES=10
```

## 3. Copy Core Files

Copy these 3 files from this repository:

1. **`src/extraction_methods/docai_batch_processor.py`** (629 lines)
   - Complete batch processing implementation
   - GCS workflow with auto-cleanup
   - LRO polling with exponential backoff

2. **Batch config additions to your `docai_config.py`**:
   ```python
   # Add this to your existing docai_config.py
   BATCH_CONFIG = {
       "enabled": os.getenv("DOCAI_BATCH_ENABLED", "true").lower() == "true",
       "threshold_mb": float(os.getenv("DOCAI_BATCH_THRESHOLD_MB", "2.0")),
       "timeout_minutes": int(os.getenv("DOCAI_BATCH_TIMEOUT_MINUTES", "10")),
       "temp_bucket_suffix": "docai-batch-temp",
       "cleanup_hours": 24
   }
   
   def is_batch_processor_configured() -> bool:
       if not is_form_parser_configured():
           return False
       try:
           import google.cloud.storage
           return BATCH_CONFIG["enabled"]
       except ImportError:
           return False
   ```

3. **`test_batch_processing.py`** (optional)
   - Test script to validate implementation

## 4. Integrate with Your Extractor

**Add to your main document extractor class:**

```python
class YourDocumentExtractor:
    def __init__(self):
        # Your existing initialization
        self.form_parser = FormParserExtractor()
        
        # NEW: Add batch processor
        self.batch_processor = None
        if is_batch_processor_configured():
            from .docai_batch_processor import BatchDocumentProcessor
            self.batch_processor = BatchDocumentProcessor()
    
    async def process_document(self, file_path):
        file_size_mb = Path(file_path).stat().st_size / (1024 * 1024)
        
        # NEW: Route large files to batch processing
        if file_size_mb >= 2.0 and self.batch_processor:
            print(f"🔄 Large file ({file_size_mb:.1f}MB) - using batch processing")
            result = await self.batch_processor.process_large_document(file_path)
            
            if result.get("success"):
                return result
            else:
                print(f"⚠️ Batch failed: {result.get('error')} - falling back to sync")
        
        # Existing sync processing
        if file_size_mb <= 1.5:  # Form Parser sync limit
            return await self.form_parser.extract(file_path)
        else:
            # Fall back to your existing Claude Vision or other method
            return await self.your_fallback_method(file_path)
```

## 5. GCS Permissions (Production)

**Grant Document AI service account GCS permissions:**

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe PROJECT_ID --format="value(projectNumber)")

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@document-ai.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"
```

## 6. Test Implementation

```bash
# Install dependency
pip install google-cloud-storage

# Test with your large documents
python3 test_batch_processing.py
```

## Expected Results

- **Small files (<2MB)**: Continue using sync Form Parser (3-5 seconds)
- **Large files (≥2MB)**: Use batch processing (2-10 minutes)
- **Quality**: Same extraction quality as sync Form Parser
- **Cost**: Same $30/1000 pages pricing
- **Fallback**: Graceful fallback to your existing Claude Vision method

## Key Benefits

✅ **Handles up to 200 pages** (vs 15-page sync limit)  
✅ **Same quality and cost** as sync Form Parser  
✅ **Automatic routing** based on file size  
✅ **Zero impact** on existing small document processing  
✅ **Graceful fallbacks** if batch processing fails  

## Troubleshooting

**Common Issue**: GCS Permission Error
```
Error: 403 The caller does not have permission storage.objects.get
```
**Solution**: Configure Document AI service account permissions (step 5 above)

**Disable if Needed**:
```bash
DOCAI_BATCH_ENABLED=false
```

This routes all documents back to your original workflow.

---

**Implementation Time**: ~30 minutes  
**Testing Time**: ~15 minutes  
**Production Setup**: ~15 minutes (GCS permissions)