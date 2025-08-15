# Document Processing Pipeline

Automated loan document extraction system that processes financial documents and fills bank forms using Claude 3.5 Vision API. Reduces processing time from 3-5 days to **2-4 hours** with **85-97% accuracy**.

## Two-Part Architecture

```
PART 1: Extract ONCE → Master JSON Pool
PART 2: Map to MANY → 9 Bank Forms + PDFs
```

## Key Files & Flow

### 1. Entry Point
**`pipeline_orchestrator.py`** - Coordinates the entire two-part pipeline
```python
# Usage
results = await orchestrator.process_application(
    application_id="app_001",
    documents=["pfs.pdf", "tax_return.pdf"],
    target_banks=["live_oak", "huntington"]
)
```

### 2. Part 1: Document Extraction
**`comprehensive_processor.py`** - Extracts ALL data from documents ONCE
- Calls Claude API with vision to extract structured data
- Merges new documents with existing master JSON (incremental processing)
- Output: `master_data.json` with all extracted information

**`benchmark_extractor.py`** - Core extraction engine
- Converts documents to images for Claude Vision
- Single API call extracts all financial data
- Returns structured JSON with SSN, assets, liabilities, business info

### 3. Part 2: Form Mapping
**`form_mapping_service.py`** - Maps master JSON to 9 different bank forms
- Intelligent field matching (handles name variations)
- Deep flattening to extract leaf values from nested data
- Generates both JSON mappings and filled PDFs

**`pdf_form_generator.py`** - Fills actual PDF forms
- Maps extracted data to PDF form fields
- Handles text fields and checkboxes
- Outputs filled PDFs ready for submission

## Supported Forms (9 Total)

- **Live Oak**: Application, PFS, 4506-T
- **Huntington**: Business App, PFS, Tax Transcript, Debt Schedule  
- **Wells Fargo**: Loan App, Financial Questionnaire

## Quick Test

```bash
# Test complete pipeline
python test_two_part_pipeline.py

# Environment setup
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE
```

## Performance Metrics

- **Speed**: 30-60 seconds per document set
- **Accuracy**: 85-97% field extraction
- **Cost**: ~$0.01-0.05 per document
- **Coverage**: Fills 100-150+ fields per application