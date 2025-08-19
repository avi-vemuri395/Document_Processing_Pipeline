# Google Document AI Setup Guide for Financial Documents

## Overview
This guide helps you set up Google Document AI for optimal processing of loan applications, tax returns, and financial statements in our pipeline.

## Prerequisites

1. **Google Cloud Account** with billing enabled (~$0.03 per page)
2. **Google Cloud Project** created and configured
3. **Document AI API** enabled in your project
4. **Optional**: Request imageless mode allowlist for 30-page processing

## Recommended Processor Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create Form Parser (Primary - Recommended)

**Best for**: Loan applications, tax forms, financial statements

1. Go to [Google Cloud Console](https://console.cloud.google.com/ai/document-ai)
2. Select your project
3. Click "Create Processor"
4. Choose **"Form Parser"** (under Document Understanding)
5. Select location (US or EU)
6. Name your processor (e.g., "Financial-Forms-Parser")
7. Copy the Processor ID (16-character hex string)

### 3. Create General Processor (Fallback - Optional)

**Best for**: Complex layouts, handwritten documents, unstructured content

1. Follow same steps as above
2. Choose **"General Processor"** (under Document OCR)
3. Name your processor (e.g., "General-Document-Processor")
4. Copy the Processor ID

### 4. Configure Environment

Add to your `.env` file:

```bash
# Google Cloud Document AI Configuration
GOOGLE_CLOUD_PROJECT=your-project-id           # From Google Cloud Console
GOOGLE_CLOUD_LOCATION=us                       # or 'eu' based on processor location

# Processor IDs (Form Parser is primary, General is fallback)
DOCAI_FORM_PARSER_ID=your-form-parser-id       # Primary: $30/1000 pages, excellent for forms
DOCAI_GENERAL_PROCESSOR_ID=your-general-id     # Fallback: $1.50/1000 pages, good for complex docs

# Processing Configuration
DOCAI_USE_IMAGELESS_MODE=true                  # Enable for 30-page processing (requires allowlist)
DOCAI_TIMEOUT=120                              # Processing timeout in seconds
DOCAI_MAX_RETRIES=3                           # Retry attempts for transient errors
```

### 5. Request Imageless Mode (Optional but Recommended)

To process documents with 16-30 pages:

1. **Contact Google Cloud Support** or your account team
2. **Request**: Add your project to the "imageless mode allowlist" for Document AI
3. **Specify**: Form Parser processor ID and project ID
4. **Timeline**: Usually approved within 1-2 business days

**Benefits of Imageless Mode:**
- Process up to 30 pages (vs 15 pages standard)
- Faster processing (no image rendering)
- Lower resource usage
- Better handling of large tax returns and complex applications

### 6. Authentication Setup

Choose one method based on your environment:

#### Option A: Application Default Credentials (Development)

```bash
gcloud auth application-default login
```

#### Option B: Service Account (Production)

```bash
# Create service account
gcloud iam service-accounts create docai-processor \
    --display-name="Document AI Processor"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:docai-processor@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/documentai.apiUser"

# Download key
gcloud iam service-accounts keys create \
    ./credentials/docai-service-account.json \
    --iam-account=docai-processor@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Add to .env
GOOGLE_APPLICATION_CREDENTIALS=./credentials/docai-service-account.json
```

## Document Type Optimization Guide

### Financial Documents (Form Parser Recommended)

#### **Excellent Performance** ✅
| Document Type | Pages | Accuracy | Processing Time | Cost/Doc |
|---------------|-------|----------|-----------------|----------|
| **Loan Applications** | 1-15 | 90-95% | 3-8 seconds | $0.45-2.25 |
| **Tax Forms (1040, 1065)** | 2-30 | 85-95% | 5-15 seconds | $0.90-4.50 |
| **Personal Financial Statements** | 1-5 | 95-98% | 2-5 seconds | $0.15-0.75 |
| **Bank Statements** | 1-10 | 85-90% | 3-10 seconds | $0.45-1.50 |
| **W-2/1099 Forms** | 1-2 | 95-99% | 2-3 seconds | $0.15-0.30 |

#### **Good Performance** ⚠️
| Document Type | Pages | Accuracy | Processing Time | Cost/Doc |
|---------------|-------|----------|-----------------|----------|
| **Complex Tax Returns** | 15-30* | 80-90% | 10-20 seconds | $2.25-4.50 |
| **Multi-page Statements** | 10-25* | 75-85% | 8-18 seconds | $1.50-3.75 |
| **Mixed Content Forms** | 5-15 | 70-85% | 5-12 seconds | $0.75-2.25 |

*Requires imageless mode allowlist

#### **Fallback to General Processor** 🔄
- **Handwritten applications**: Better OCR for handwriting
- **Complex layouts**: Advanced layout analysis
- **Non-standard forms**: Custom document structures
- **Damaged/poor quality**: Better noise handling

### Supported File Formats

```python
# Recommended formats (best to worst)
OPTIMAL_FORMATS = [
    ".pdf",     # Best - native text + structure preservation
    ".tiff",    # Excellent - high resolution scanned documents  
    ".png",     # Good - clean scanned forms
    ".jpg",     # Fair - photos of documents (avoid if possible)
]

# File size recommendations
MAX_FILE_SIZE = 40MB        # Hard limit
OPTIMAL_SIZE = "<10MB"      # Best performance
RESOLUTION = "300+ DPI"     # For scanned documents
```

### Processing Strategy by Document Type

```python
# Our implementation automatically routes documents:

FORM_PARSER_PRIORITY = [
    "loan_applications",     # SBA, commercial, personal loans
    "tax_forms",            # 1040, 1065, 1120S, W-2, 1099
    "financial_statements", # PFS, balance sheets, P&L
    "bank_statements",      # Account statements, credit reports
    "structured_forms"      # Applications, surveys, intake forms
]

GENERAL_PROCESSOR_PRIORITY = [
    "handwritten_docs",     # Signatures, handwritten applications
    "complex_layouts",      # Multi-column, irregular formats
    "mixed_content",        # Text + images + tables
    "poor_quality",         # Faded, skewed, damaged documents
    "large_documents"       # >15 pages (if no imageless allowlist)
]

CLAUDE_VISION_FALLBACK = [
    "very_large_docs",      # >30 pages
    "unsupported_formats",  # Non-standard layouts
    "processing_failures",  # When DocAI fails
    "special_cases"         # Charts, diagrams, creative layouts
]
```

## Verification

### 1. Verify Setup

```bash
python scripts/verify_docai_setup.py
```

Expected output:
```
✅ Configuration loaded successfully
✅ Google Cloud libraries imported successfully  
✅ Authentication successful
✅ ALL CHECKS PASSED - Ready to use Document AI!
```

### 2. Test Processing

```bash
python test_general_processor.py
```

## Usage

### With BenchmarkExtractor (Automatic)

The Document AI integration is automatic when configured:

```python
from src.extraction_methods.multimodal_llm.providers import BenchmarkExtractor

# DocAI will be used automatically if configured
extractor = BenchmarkExtractor()
result = await extractor.extract_all("document.pdf")

# Check metadata to see what was used
print(result['_metadata']['extraction_methods'])
# Output: {'docai': 'general_processor (1 files)', ...}
```

### Direct Usage

```python
from src.extraction_methods.docai_general_processor import GeneralProcessorExtractor

processor = GeneralProcessorExtractor()
result = await processor.extract(Path("document.pdf"))

if result.get("success"):
    print(f"Text: {result['text'][:100]}...")
    print(f"Entities: {len(result['entities'])}")
    print(f"Tables: {len(result['tables'])}")
```

## Processing Flow

```
Document Input
    ↓
Excel File? → Yes → Pandas Extraction (FREE)
    ↓ No
DocAI Configured? → Yes → General Processor ($1.50/1000 pages)
    ↓ No or Failed           ↓ Success
Claude Vision ($3/1000) ← ← ← ↓
    ↓                         ↓
Extracted JSON ← ← ← ← ← ← ← ←
```

## Cost Comparison

| Method | Cost per 1000 pages | Speed | Accuracy |
|--------|---------------------|-------|----------|
| Pandas (Excel) | $0 | Instant | 100% |
| DocAI General | $1.50 | 2-5 sec | 85-90% |
| Claude Vision | $3.00 | 5-10 sec | 90-95% |

## Troubleshooting

### "Permission denied" error
- Check service account roles
- Verify processor ID is correct
- Ensure Document AI API is enabled

### "Processor not found"
- Verify processor ID matches exactly
- Check region/location settings
- Ensure processor is deployed

### "Authentication failed"
- Run `gcloud auth application-default login`
- Check GOOGLE_APPLICATION_CREDENTIALS path
- Verify service account key exists

## Support

For issues, check:
- [Document AI Documentation](https://cloud.google.com/document-ai/docs)
- [Python Client Library](https://cloud.google.com/python/docs/reference/documentai/latest)
- Project logs in Google Cloud Console