# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Document processing pipeline for loan applications that automates extraction from financial documents and fills standardized bank forms. Achieves **85-97% accuracy** using Claude 3.5 Sonnet's vision capabilities, reducing processing time from 3-5 days to 2-4 hours.

## Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   PART 1: DOCUMENT PROCESSING                    │
│     Documents → Comprehensive Extraction → Master JSON Pool      │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PART 2: FORM GENERATION                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Part 2a: Bank Forms (9 forms across 3 banks)           │    │
│  │  • Live Oak: Application, PFS, 4506-T                   │    │
│  │  • Huntington: Business App, Tax Transcript,            │    │
│  │    Debt Schedule, Financial Statement                   │    │
│  │  • Wells Fargo: Financial Questionnaire, Business Info  │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Part 2b: Spreadsheets (Optional)                       │    │
│  │  • Debt Schedule Excel                                  │    │
│  │  • Use of Funds Excel                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

The system follows a **two-part architecture** that extracts data ONCE and maps to MANY:
1. **Part 1**: Extract ALL data from documents ONCE into a master JSON pool
2. **Part 2a**: Map the master JSON to 9 different bank forms
3. **Part 2b**: Optional - Populate Excel spreadsheets from master JSON

### NEW Pipeline Components

Located in `src/template_extraction/`:

1. **ComprehensiveProcessor** (`comprehensive_processor.py`)
   - Implements Part 1: Extract data ONCE from all documents
   - Creates and maintains master_data.json
   - Supports incremental document processing
   - Merges new data with existing master (last wins strategy)

2. **FormMappingService** (`form_mapping_service.py`)
   - Implements Part 2a: Maps master JSON to 9 bank forms
   - Handles form template discovery
   - Generates filled PDFs where templates exist
   - Creates JSON mappings for all forms

3. **SpreadsheetMappingService** (`spreadsheet_mapping_service.py`)
   - Implements Part 2b: Populates Excel templates
   - Debt Schedule: Maps liabilities to structured Excel
   - Use of Funds: Maps financial data to Excel template

4. **PipelineOrchestrator** (`pipeline_orchestrator.py`)
   - Coordinates the entire two-part pipeline
   - Manages incremental document processing
   - Handles bank-specific form generation
   - Optional spreadsheet generation

### Legacy Components (Still Used)

Located in `src/extraction_methods/multimodal_llm/providers/`:

1. **BenchmarkExtractor** (`benchmark_extractor.py`, 203 lines)
   - Converts documents to images via UniversalPreprocessor
   - Single Claude API call extracts ALL data as unstructured JSON
   - Focus on loan application data: SSN, business info, ownership percentages
   - Model: `claude-sonnet-4-20250514`
   - Supports Files API via `use_files_api` flag or `USE_FILES_API` env var

2. **LLMFormFiller** (`form_filler.py`, 360 lines)
   - Dynamically loads form fields (203 for Live Oak, 461 for Huntington)
   - Uses Claude to intelligently map extracted data to form fields
   - Handles field name mismatches automatically
   - Complete workflow: Extract → Read form → Fill with LLM

3. **PDFFormGenerator** (`pdf_form_generator.py`, ~550 lines)
   - Deterministic PDF filling using pypdf
   - **NEW**: Dedicated checkbox handler for proper state management
   - Maps data to actual PDF form fields (text and checkbox)
   - Generates filled PDFs (~700KB each)
   - Also includes `AcroFormFiller` for alternative filling approach

4. **DynamicFormMapper** (`dynamic_form_mapper.py`, 440 lines)
   - Extracts fields from ANY PDF form without pre-configuration
   - Caches results for performance in `outputs/form_mappings/`
   - Falls back to common fields if extraction fails

5. **UniversalPreprocessor** (`src/extraction_methods/multimodal_llm/core/universal_preprocessor.py`)
   - Converts all document types to images for vision processing
   - Handles PDF, images, Excel, and text documents
   - Excel files: pandas → HTML → image conversion

## Primary Commands

```bash
# Environment setup and verification
python3 check_env.py                         # Verify API keys and dependencies

# NEW Two-Part Pipeline Tests
python3 test_two_part_pipeline.py           # Test the correct two-part architecture
python3 test_comprehensive_end_to_end.py    # Full 4-phase incremental test
python3 test_incremental_processing.py      # Test document merging logic
python3 test_spreadsheet_population.py      # Test Excel generation
python3 run_comprehensive_test.py           # Run all pipeline tests

# Legacy tests (still useful for components)
python3 test_focused_end_to_end.py          # 2 docs, reliable, ~$0.01 API cost
python3 test_optimized_end_to_end.py        # 5 docs, max coverage, may hit rate limits
python3 test_dynamic_mapping.py             # Test form field extraction
```

## Development Workflow

### NEW: Processing with Two-Part Pipeline

```python
from src.template_extraction import PipelineOrchestrator
from pathlib import Path

# Initialize the orchestrator
orchestrator = PipelineOrchestrator()

# Process application with incremental documents
documents = [
    Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
    Path("inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf")
]

# Generate forms for specific banks
results = await orchestrator.process_application(
    application_id="brigham_001",
    documents=documents,
    target_banks=["live_oak", "huntington"],  # Only these banks
    generate_spreadsheets=True  # Also create Excel files
)

# Results include:
# - Master JSON: outputs/master_data/brigham_001_master.json
# - Bank PDFs: outputs/filled_pdfs/brigham_001_live_oak_application.pdf
# - Spreadsheets: outputs/spreadsheets/brigham_001_debt_schedule.xlsx
```

### Adding Documents Incrementally

```python
# Day 1: Initial documents
await orchestrator.process_application("app_001", [doc1, doc2])

# Day 3: Add more documents (automatically merges)
await orchestrator.process_application("app_001", [doc3, doc4])

# Day 7: Final documents and generate forms
results = await orchestrator.process_application(
    "app_001", [doc5], 
    target_banks=["live_oak", "huntington", "wells_fargo"]
)
```

### Legacy: Direct Form Filling (Still Works)

```python
from src.extraction_methods.multimodal_llm.providers import LLMFormFiller

filler = LLMFormFiller()  # Uses ANTHROPIC_API_KEY from .env
filled_form = await filler.fill_forms_from_documents(
    "inputs/real/Brigham_dallas",  # Document folder
    "templates/Live Oak Express - Application Forms.pdf"  # Form template
)
```


## Critical Implementation Details

### API Rate Limits
- **Reliable**: 2-3 documents (~13 images)
- **Maximum**: 5 documents (~29 images, may hit 413 errors)
- **Token limit**: 30,000 tokens/minute
- Each page becomes 1-2 images after preprocessing

### Form Field Mapping

The system intelligently handles three mapping scenarios:
1. **Explicit mapping** (`_mapping.json`): Direct field mappings
2. **Dynamic discovery** (`_dynamic.json`): Auto-generated from PDF
3. **No mapping**: Direct field name matching

Checkbox fields require special handling:
- States vary by field: `/Yes`, `/On`, `/Yes_4`, `/No_4`
- System discovers valid states from PDF appearance dictionary
- Implemented in `PDFFormGenerator._update_checkboxes()`

### Extraction Focus Areas

The extraction prompt (benchmark_extractor.py:107-147) targets:
- SSN, business info, ownership percentages
- Assets, liabilities, net worth
- Business structure (LLC, C-Corp, etc.)
- Tax returns and financial statements

## Test Documents

`inputs/real/Brigham_dallas/`:
- 19 files total (PFS, tax returns 2021-2024, business docs)
- Expected values:
  - Total Assets: $4,397,552
  - Total Liabilities: $2,044,663
  - Net Worth: $2,352,889
  - SSN: XXX-XX-3074 (redacted)

## Output Structure

```
outputs/
├── master_data/                  # NEW: Master JSON pools
│   └── {application_id}_master.json
├── filled_pdfs/                  # Generated PDFs
│   ├── {app_id}_live_oak_application.pdf
│   ├── {app_id}_huntington_business_app.pdf
│   └── ...
├── filled_forms/                 # JSON mappings for all forms
│   ├── {app_id}_live_oak_application.json
│   ├── {app_id}_wells_fargo_financial.json
│   └── ...
├── spreadsheets/                 # NEW: Excel outputs
│   ├── {app_id}_debt_schedule.xlsx
│   └── {app_id}_use_of_funds.xlsx
├── extraction_logs/              # NEW: Processing history
│   └── {app_id}_extraction_log.json
└── form_mappings/                # Cached form field mappings
    └── Live Oak Express - Application Forms_dynamic.json
```

## Performance Metrics

- **Accuracy**: 85-97% (vs 71% with regex)
- **Fields filled**: 22/203 (17 text + 5 checkbox)
- **Processing time**: ~30 seconds per document set
- **API cost**: ~$0.01-0.02 per document set

## Recent Improvements (August 2025)

- ✅ **Two-Part Pipeline Architecture**: Extract ONCE, map to MANY forms
- ✅ **Incremental Processing**: Documents added over time with smart merging
- ✅ **Master JSON Pool**: Central data store for all extracted information
- ✅ **Spreadsheet Generation**: Excel template population from master JSON
- ✅ **Multi-Bank Support**: 9 forms across 3 banks from single extraction
- ✅ Checkbox field support with proper state management
- ✅ Dynamic form field discovery without configuration
- ✅ Files API integration for improved performance

## Environment Requirements

```bash
# Required API key in .env file
ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE

# System dependency for PDF→image conversion
brew install poppler  # macOS
sudo apt-get install poppler-utils  # Ubuntu

# Python dependencies (Python 3.13.3)
pip install -r requirements-minimal.txt
```

## Production Workflow Context

The production system implements the two-part architecture:

### Part 1: Document Ingestion (Continuous)
1. Files uploaded incrementally over days/weeks
2. Each document processed ONCE via ComprehensiveProcessor
3. Extracted data merged into master JSON pool
4. Master JSON saved to S3 with version history
5. Extraction logs maintained for audit trail

### Part 2: Form Generation (On-Demand)
When user selects target banks:
1. FormMappingService reads master JSON
2. Maps data to 9 bank-specific forms:
   - **Live Oak**: Application, PFS, 4506-T (PDFs + JSON)
   - **Huntington**: Business App, Tax Transcript, Debt Schedule, Financial Statement (PDFs + JSON)
   - **Wells Fargo**: Financial Questionnaire, Business Info (JSON only - no PDF templates)
3. Optional: SpreadsheetMappingService generates Excel files
4. All outputs uploaded to S3 for delivery

### Key Architecture Benefits
- **Extract Once**: Documents processed only once, not 9 times
- **Incremental**: New documents seamlessly merge with existing data
- **Flexible**: Add new banks/forms without re-extracting documents
- **Efficient**: ~90% reduction in API calls vs template-per-form approach