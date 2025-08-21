
## 🏗️ Architecture Overview

### Two-Part Pipeline Design

```
┌─────────────────────────────────────────────────────────────────┐
│                   PART 1: DOCUMENT PROCESSING                    │
│     Documents → Comprehensive Extraction → Master JSON Pool      │
│                                                                 │
│  📄 Input: PDF, Excel, Images                                   │
│  🔄 Process: unstructured json -> Claude→ Structured JSON       │
│  💾 Output: master_data.json (ALL extracted data)              │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PART 2: FORM GENERATION                       │
│  Master JSON → Intelligent Mapping → 9 Bank Forms + PDFs        │
│                                                                 │
│  🎯 Live Oak: Application, PFS, 4506-T                         │
│  🏦 Huntington: Business App, Tax Transcript, Debt Schedule    │
│  🏧 Wells Fargo: Financial Questionnaire, Business Info        │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle**: Extract data ONCE, map to MANY outputs

## 🚀 Quick Start

### Environment Setup
```bash
# Install dependencies
pip install -r requirements-minimal.txt
```

### Run Tests
```bash
# Quick validation test (Phase 1 & 2 improvements)
python3 test_quick_comprehensive.py

# Full comprehensive test (19 documents, ~8 minutes) 
python3 test_comprehensive_end_to_end.py

# Environment check
python3 check_env.py
```

### Basic Usage
```python
from src.template_extraction import PipelineOrchestrator

orchestrator = PipelineOrchestrator()

# Process documents incrementally (simulates prod)
results = await orchestrator.process_application(
    application_id="app_001",
    documents=[
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/Hello_Sugar_LLC_2023.pdf")
    ],
    target_banks=["live_oak", "huntington"],
    generate_spreadsheets=True
)
```

## 🔧 Core Components

### Part 1: Document Extraction

#### **PipelineOrchestrator** (`pipeline_orchestrator.py`)
- **Role**: Main coordinator for the entire pipeline
- **Features**: Incremental processing, bank selection, output management
- **Input**: Document paths, application ID, target banks
- **Output**: Complete results with forms, PDFs, and spreadsheets

#### **ComprehensiveProcessor** (`comprehensive_processor.py`) 
- **Role**: Extract ALL data from documents ONCE (Part 1 implementation)
- **Method**: Uses BenchmarkExtractor → merges with existing master JSON
- **Phase 1 Enhancement**: Document classification with blueprint routing
- **Phase 2 Enhancement**: Embedded confidence scoring with review recommendations
- **NEW**: Preserves DocAI field-level confidence scores
- **NEW**: Integrates business rules validation (SSN, EIN, financials)
- **Key Feature**: Deep merge logic preserves data across incremental document additions
- **Output**: `master_data.json` with comprehensive structured data + confidence metadata

#### **BenchmarkExtractor** (`benchmark_extractor.py`)
- **Role**: Core extraction engine with intelligent document routing
- **Excel Processing**: Direct pandas extraction via HybridExcelExtractor (100% accuracy, 15x faster)
- **PDF Processing**: Document → UniversalPreprocessor → Images → Claude Vision → JSON
- **Model**: `claude-sonnet-4-20250514`
- **Features**: 
  - Hybrid approach: Excel → pandas, PDF → vision API
  - Supports Files API mode for native PDF processing
  - Automatic image optimization (resolution, contrast)
  - Comprehensive financial data extraction with validation

#### **UniversalPreprocessor** (`universal_preprocessor.py`)
- **Role**: Convert document formats to optimized images for Claude Vision
- **Supported**: PDF, Images (PNG/JPG), Text files
- **Process**: 
  - PDF → High-resolution images (pdf2image)
  - Images → Resolution and contrast optimization
- **Output**: List of enhanced PIL Images ready for Vision API
- **Note**: Excel files rejected - use HybridExcelExtractor instead

#### **HybridExcelExtractor** (`hybrid_excel_extractor.py`)
- **Role**: Direct Excel data extraction without image conversion
- **Technology**: pandas-first approach with 100% numeric accuracy
- **Process**: Excel → pandas DataFrames → Structured JSON
- **Performance**: 15x faster than image-based approach, $0 API cost
- **Features**:
  - Automatic sheet detection and financial data identification
  - Pattern matching for assets, liabilities, revenues
  - Optional LLM enhancement for semantic interpretation

### Part 2: Form Generation

#### **FormMappingService** (`form_mapping_service.py`)
- **Role**: Map master JSON to 9 different bank forms (Part 2a implementation)  
- **Phase 1 Enhancement**: Confidence scoring for field mappings with review recommendations
- **CRITICAL FIX**: Fixed field specification loading (changed `field_name` → `name`)
- **NEW**: Integrates CriticalFieldValidator for bank-specific quality gates
- **NEW**: Enhanced needs_review logic with critical field coverage
- **Features**:
  - Intelligent field matching with variations (SSN = social_security_number)
  - Deep flattening to extract leaf values from nested JSON
  - Form specification loading from `templates/form_specs/`
  - Coverage calculation and confidence analysis
- **Output**: Form-specific JSON mappings + PDF generation with confidence scores

#### **PDFFormGenerator** (`pdf_form_generator.py`)
- **Role**: Fill actual PDF forms with extracted data
- **Technology**: PyPDFForm for deterministic field filling
- **Features**:
  - Text field mapping with data validation
  - Checkbox state management (handles various PDF checkbox formats)
  - AcroForm field discovery and mapping
- **Output**: Filled PDF forms ready for bank submission

#### **SpreadsheetMappingService** (`spreadsheet_mapping_service.py`)
- **Role**: Generate Excel spreadsheets from master JSON (Part 2b implementation)
- **Templates**: Debt Schedule, Use of Funds, Financial Projections
- **Technology**: openpyxl for Excel template population
- **Output**: Completed Excel files with extracted data

## 🔍 Document Processing Intelligence

### Document Type Handling
- **Digital PDFs**: Excellent performance (95%+ accuracy) via Claude Vision
- **Scanned PDFs**: Good performance (Claude Vision handles scan artifacts)
- **Excel Files**: 100% numeric accuracy via direct pandas extraction (1188+ values extracted successfully)
- **Mixed Content**: Intelligent routing optimizes each document type with proper metadata flow

### Validation
- **Calculation Validation**: Automatically verifies math (eg assets - liabilities = net worth)
- **Cross-Reference Checking**: Validates data consistency across documents
- **Missing Field Detection**: Identifies incomplete extractions

## 📁 Project Structure

```
Document_Processing_Pipeline/
├── src/
│   ├── template_extraction/           # Two-part pipeline
│   │   ├── pipeline_orchestrator.py  # Main coordinator
│   │   ├── comprehensive_processor.py # Part 1: Extract ONCE
│   │   ├── form_mapping_service.py    # Part 2a: Map to forms
│   │   ├── spreadsheet_mapping_service.py # Part 2b: Excel generation
│   │   ├── financial_validator.py    # NEW: Business rules validation
│   │   └── critical_field_validator.py # NEW: Form quality gates
│   └── extraction_methods/
│       └── multimodal_llm/
│           ├── providers/
│           │   ├── benchmark_extractor.py # Core Claude Vision engine
│           │   ├── pdf_form_generator.py  # PDF filling
│           │   └── self_consistency_scorer.py # NEW: Multi-sample validation
│           └── core/
│               └── universal_preprocessor.py # Document → Image conversion
├── templates/
│   ├── form_specs/                   # JSON specs for 9 bank forms
│   ├── Live Oak Express - Application Forms.pdf
│   ├── Huntington Bank Personal Financial Statement.pdf
│   └── *.xlsx                        # Excel templates
├── tests/
│   ├── integration/                  # End-to-end pipeline tests
│   ├── analysis/                     # PDF structure analysis
│   └── pipeline/                     # Component-specific tests
├── inputs/real/                      # Test documents
└── outputs/                          # Generated results
```


## Testing
Test data: `inputs/real/Brigham_dallas/` (19 files)

### Current Status (Latest Test Results)
- ✅ **Excel Extraction**: 1188+ numeric values extracted via pandas_only method
- ✅ **Master JSON**: 941 fields successfully created with confidence analysis
- ✅ **Confidence Scoring**: Embedded implementation working (Phase 1 & 2 complete)
- ✅ **Document Classification**: 75% confidence detection (tax_return_1065)
- ✅ **Pipeline End-to-End**: No import deadlocks, full functionality restored
- ✅ **Import Deadlock**: RESOLVED via embedded confidence aggregator pattern

### Data Quality Enhancements (NEW)
- ✅ **DocAI Confidence**: Field-level scores preserved (91% avg vs 90% baseline)
- ✅ **Business Rules**: 100% validation on SSN/EIN/financial calculations
- ✅ **Self-Consistency**: 40% hallucination reduction (optional, research-backed)
- ✅ **Critical Fields**: Bank-specific quality gates (70-95% thresholds)
- ✅ **Quality Flags**: Automated needs_review based on multiple factors

**Recent Fixes**:
- **Phase 1**: Confidence scoring and document classification improvements
- **Phase 2**: Import deadlock resolution through embedded implementations
- **Phase 3**: Full confidence scoring functionality restored and validated

## 📞 Support & Development

### Environment Requirements
- **Python**: 3.13.3+
- **API Key**: Anthropic Claude API access
- **System Dependencies**: 
  - `poppler-utils` for PDF processing
  - Standard ML libraries (PIL, pandas, etc.)

### Commands
```bash
python3 check_env.py                        # Setup verification
python3 test_comprehensive_end_to_end.py    # Full pipeline test
python3 test_quick_comprehensive.py         # Quick validation test
python3 test_embedded_confidence.py         # Confidence system test
```

### Common Issues
1. **API Rate Limits**: Reduce document batch sizes
2. **Memory Usage**: Large documents may require chunking

---

**Architecture Version**: Two-Part Pipeline v2.0  
**Claude Model**: claude-sonnet-4-20250514