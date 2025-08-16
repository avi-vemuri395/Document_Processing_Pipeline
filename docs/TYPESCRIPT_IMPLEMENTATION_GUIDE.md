# TypeScript Implementation Guide

## Repository Navigation & Feature Mapping

This guide maps the document processing pipeline's features to their implementation files, helping developers quickly locate and understand functionality without extensive code examples.

---

## Project Structure Overview

```
Document_Processing_Pipeline/
├── src/
│   ├── template_extraction/        # NEW: Two-part pipeline (Extract ONCE → Map to MANY)
│   └── extraction_methods/         # LEGACY: Original extraction components
├── templates/                      # Form specifications and PDF templates
├── tests/                          # Comprehensive test suites
├── outputs/                        # Generated outputs (git-ignored)
└── inputs/                         # Test documents
```

---

## Core Architecture Components

### Part 1: Document Processing (Extract ONCE)

#### `src/template_extraction/comprehensive_processor.py`
**Purpose:** Orchestrates extraction from all document types into master JSON

**Key Features:**
- Document type detection and routing
- Excel-specific handling via HybridExcelExtractor
- PDF/image processing via BenchmarkExtractor
- Master JSON creation and management
- Incremental document processing with merging
- Extraction metadata tracking

**Key Methods:**
- `process_documents()` - Main entry point for batch processing
- `_process_single_document()` - Routes based on file type
- `_merge_into_master()` - Implements deep merge with conflict resolution
- `_save_master_data()` - Persists to JSON with metadata

**Integration Points:**
- Uses `HybridExcelExtractor` for `.xlsx` files
- Falls back to `BenchmarkExtractor` for PDFs/images
- Creates `master_data.json` in Part 1 output directory

---

### Part 2a: Form Mapping (Map to MANY)

#### `src/template_extraction/form_mapping_service.py`
**Purpose:** Maps master JSON to 9 different bank forms

**Key Features:**
- Dynamic form specification loading
- Intelligent field mapping with confidence scoring
- PDF generation for banks with templates
- Coverage analysis and reporting
- Field name variation handling

**Key Methods:**
- `map_all_forms()` - Processes all 9 bank forms
- `_intelligent_field_mapping_with_confidence()` - Maps with scoring
- `_find_field_match()` - Handles field name variations
- `_generate_pdf()` - Creates filled PDFs

**Configuration:**
- `BANK_FORMS` dict - Defines which forms each bank needs
- `PDF_TEMPLATES` dict - Maps banks to PDF template files
- Form specs in `templates/form_specs/*.json`

**Bug Fix Applied:**
- Lines 335, 397: Handles both `name` and `field_name` properties

---

### Part 2b: Spreadsheet Generation

#### `src/template_extraction/spreadsheet_mapping_service.py`
**Purpose:** Generates Excel spreadsheets from master data

**Key Features:**
- Debt schedule generation
- Use of funds spreadsheet
- Financial summary tables
- Auto-formatting and formulas

**Key Methods:**
- `populate_all_spreadsheets()` - Generates all spreadsheet types
- `_create_debt_schedule()` - Formats liability data
- `_create_use_of_funds()` - Structures financial allocations

---

### Pipeline Orchestration

#### `src/template_extraction/pipeline_orchestrator.py`
**Purpose:** Coordinates the entire two-part pipeline

**Key Features:**
- Application-level processing
- Incremental document handling
- Bank-specific form generation
- Optional spreadsheet creation

**Key Methods:**
- `process_application()` - Main entry point
- `process_incremental()` - Add documents to existing application
- `_ensure_master_exists()` - Manages master JSON lifecycle

**Usage Pattern:**
```python
# Process initial documents
orchestrator.process_application(
    application_id="app_001",
    documents=[doc1, doc2],
    target_banks=["live_oak", "huntington"]
)

# Add more documents later
orchestrator.process_incremental(
    application_id="app_001", 
    new_document=doc3
)
```

---

## Legacy Extraction Components

### Document Extraction

#### `src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py`
**Purpose:** Core extraction engine using Claude Vision API

**Key Features:**
- Hybrid routing (Excel → pandas, Others → Vision API)
- Single API call for entire document
- Support for Files API and standard API
- Structured prompt for loan data extraction

**Configuration:**
- `USE_FILES_API` environment variable
- Model: `claude-3-5-sonnet-20241022`
- Focus: SSN, business info, ownership, financials

---

### Excel Processing

#### `src/extraction_methods/multimodal_llm/extractors/hybrid_excel_extractor.py`
**Purpose:** Direct Excel extraction without OCR

**Key Features:**
- Pandas-first extraction (100% accuracy on numbers)
- Multi-sheet processing
- Table structure detection
- Optional LLM enhancement
- 15x faster than image conversion

**Extraction Modes:**
- `pandas_only` - Pure deterministic extraction
- `llm_enhanced` - Adds semantic understanding
- `hybrid` - Combines both approaches

---

### Form Processing

#### `src/extraction_methods/multimodal_llm/providers/form_filler.py`
**Purpose:** Dynamic form field mapping using LLM

**Key Features:**
- Loads form fields from templates
- Intelligent field matching
- Handles name variations
- Complete workflow automation

**Supported Forms:**
- Live Oak: 203 fields
- Huntington: 461 fields

---

### PDF Generation

#### `src/extraction_methods/multimodal_llm/providers/pdf_form_generator.py`
**Purpose:** Fills PDF forms with extracted data

**Key Features:**
- Deterministic PDF filling via pypdf
- Checkbox state management
- Field discovery from PDF structure
- ~700KB output files

**Key Methods:**
- `generate_filled_pdf()` - Main entry point
- `_update_checkboxes()` - Handles checkbox complexity
- `_fill_form_fields()` - Text field population

---

### Dynamic Form Discovery

#### `src/extraction_methods/multimodal_llm/providers/dynamic_form_mapper.py`
**Purpose:** Extracts fields from any PDF without pre-configuration

**Key Features:**
- Automatic field detection
- Caching for performance
- Fallback strategies
- Universal form support

**Cache Location:** `outputs/form_mappings/*_dynamic.json`

---

## Form Specifications

### Location: `templates/form_specs/`

**File Naming Convention:** `{bank}_{form_type}_v1.json`

**Structure:**
```json
{
  "form_id": "unique_identifier",
  "version": "2025.01",
  "fields": [
    {
      "id": "field_identifier",
      "field_name": "Display Name",  // Note: Some use "name" instead
      "type": "text|money|date|checkbox",
      "required": true/false
    }
  ]
}
```

**Available Specifications:**
- `live_oak_application_v1.json` - Main application
- `live_oak_pfs_v1.json` - Personal financial statement
- `huntington_business_app_v1.json` - Business application
- `huntington_pfs_v1.json` - Personal financial statement
- `wells_fargo_loan_app_v1.json` - Loan application
- (9 total across 3 banks)

---

## Test Infrastructure

### Comprehensive Testing

#### `tests/integration/test_comprehensive_end_to_end.py`
**Purpose:** Full pipeline validation with all features

**Test Phases:**
1. Initial document processing
2. Incremental document addition
3. Conflict resolution testing
4. Complete application processing

**Validation Points:**
- Master JSON creation
- Field extraction counts
- Form mapping coverage
- PDF generation
- Spreadsheet creation
- Phase 1 & 2 improvements

---

## Output Structure

```
outputs/applications/{application_id}/
├── part1_document_processing/
│   ├── master_data.json           # Combined extraction
│   ├── extractions/               # Individual document results
│   └── logs/                      # Processing logs
│
├── part2_form_mapping/
│   ├── banks/
│   │   ├── live_oak/             # Bank-specific outputs
│   │   ├── huntington/
│   │   └── wells_fargo/
│   └── mapping_summary.json      # Overall statistics
│
└── part2_spreadsheets/
    ├── debt_schedule.xlsx
    └── use_of_funds.xlsx
```

---

## Configuration Files

### Environment Variables (`.env`)
```
ANTHROPIC_API_KEY=sk-ant-api03-xxx
USE_FILES_API=false
TORCH_DEVICE=cpu
RECOGNITION_BATCH_SIZE=4
```

### Project Documentation
- `CLAUDE.md` - AI assistant instructions
- `README.md` - Project overview
- `docs/architecture/` - Technical documentation

---

## Feature Location Quick Reference

| Feature | Primary File | Supporting Files |
|---------|-------------|------------------|
| Master JSON Creation | `comprehensive_processor.py` | `benchmark_extractor.py` |
| Excel Extraction | `hybrid_excel_extractor.py` | `comprehensive_processor.py` |
| PDF Text Extraction | `benchmark_extractor.py` | `universal_preprocessor.py` |
| Form Field Mapping | `form_mapping_service.py` | Form specs in `templates/` |
| PDF Generation | `pdf_form_generator.py` | `form_mapping_service.py` |
| Confidence Scoring | `form_mapping_service.py` | Embedded in service |
| Document Classification | `comprehensive_processor.py` | Via file extension |
| Incremental Processing | `pipeline_orchestrator.py` | `comprehensive_processor.py` |
| Spreadsheet Generation | `spreadsheet_mapping_service.py` | Master data dependency |
| Testing | `test_comprehensive_end_to_end.py` | Multiple test files |

---

## Common Development Tasks

### Adding a New Bank Form
1. Create form spec in `templates/form_specs/{bank}_{type}_v1.json`
2. Add to `BANK_FORMS` dict in `form_mapping_service.py`
3. Optionally add PDF template to `templates/`
4. Update `PDF_TEMPLATES` dict if PDF exists

### Adding a New Document Type
1. Update classification in `comprehensive_processor.py`
2. Add extraction logic in `_process_single_document()`
3. Create specific extractor if needed
4. Update routing logic

### Improving Field Mapping
1. Edit `_find_field_match()` in `form_mapping_service.py`
2. Add field variations to the `variations` dict
3. Test with comprehensive test suite

### Adding a New Spreadsheet Type
1. Create method in `spreadsheet_mapping_service.py`
2. Add to `populate_all_spreadsheets()`
3. Define output path structure
4. Implement formatting logic

---

## Debugging Entry Points

### Check Extraction Quality
- Start: `comprehensive_processor.py::_process_single_document()`
- Follow: Document type routing
- End: Individual extractor (Excel or Vision)

### Trace Form Mapping Issues
- Start: `form_mapping_service.py::_intelligent_field_mapping_with_confidence()`
- Check: Form spec loading in `_load_all_form_specifications()`
- Debug: Field matching in `_find_field_with_confidence()`

### Investigate PDF Generation
- Start: `pdf_form_generator.py::generate_filled_pdf()`
- Check: Template path and field discovery
- Debug: Checkbox states in `_update_checkboxes()`

---

## Performance Optimization Points

1. **Excel Processing**: Already optimized with pandas (15x faster)
2. **Vision API Calls**: Batch pages when possible
3. **Form Mapping**: Uses lazy loading for components
4. **PDF Generation**: Cached form field discovery
5. **Master JSON**: Incremental updates, not full rewrites

---

## Known Issues & Solutions

### Issue: Form mapping shows 0% coverage
**Solution:** Fixed in form_mapping_service.py lines 335, 397
- Handles both `name` and `field_name` properties

### Issue: Excel extraction fails
**Solution:** Routes to HybridExcelExtractor automatically
- Bypasses image conversion for 100% accuracy

### Issue: Import deadlocks
**Solution:** Lazy loading pattern implemented
- Components loaded on-demand

---

## Next Steps for Improvement

1. **Add OCR fallback** for scanned PDFs (Marker+Surya)
2. **Implement content-hash deduplication** 
3. **Add provenance tracking** at field level
4. **Create API routing layer** for paid services
5. **Build budget tracking system** for API costs

This guide provides a roadmap through the codebase without extensive code snippets, focusing on where features live and how components interact.