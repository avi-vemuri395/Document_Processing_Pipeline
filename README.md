
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
# Fast test (2 PDFs + 2 Excel, ~2 minutes)
python3 run_fast_test.py

# Comprehensive test (19 documents, ~8 minutes)
python3 run_comprehensive_test.py

# Analyze PDF structure (no API calls)
python3 tests/analysis/test_pdf_technical_structure.py
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
- **Key Feature**: Deep merge logic preserves data across incremental document additions
- **Output**: `master_data.json` with comprehensive structured data

#### **BenchmarkExtractor** (`benchmark_extractor.py`)
- **Role**: Core extraction engine using Claude 4 Sonnet Vision API
- **Process**: Document → UniversalPreprocessor → Images → Claude Vision → JSON
- **Model**: `claude-sonnet-4-20250514`
- **Features**: 
  - Supports Files API mode for native PDF processing (rate limit issues)
  - Automatic image optimization (resolution, contrast)
  - Comprehensive financial data extraction with validation

#### **UniversalPreprocessor** (`universal_preprocessor.py`)
- **Role**: Convert ANY document format to optimized images for Claude Vision
- **Supported**: PDF, Excel (.xlsx/.xls), Images (PNG/JPG), Text files
- **Process**: 
  - PDF → High-resolution images (pdf2image)
  - Excel → HTML tables → Screenshot images (pandas + matplotlib)
  - Images → Resolution and contrast optimization
- **Output**: List of enhanced PIL Images ready for Vision API

### Part 2: Form Generation

#### **FormMappingService** (`form_mapping_service.py`)
- **Role**: Map master JSON to 9 different bank forms (Part 2a implementation)
- **Features**:
  - Intelligent field matching with variations (SSN = social_security_number)
  - Deep flattening to extract leaf values from nested JSON
  - Form specification loading from `templates/form_specs/`
  - Coverage calculation and validation
- **Output**: Form-specific JSON mappings + PDF generation

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
- **Digital PDFs**: Excellent performance (95%+ accuracy)
- **Scanned PDFs**: Good performance (Claude Vision sort of handles scan artifacts)
- **Excel Files**: Need multi page
- **Mixed Content**: Handles varying quality and formats

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
│   │   └── spreadsheet_mapping_service.py # Part 2b: Excel generation
│   └── extraction_methods/
│       └── multimodal_llm/
│           ├── providers/
│           │   ├── benchmark_extractor.py # Core Claude Vision engine
│           │   └── pdf_form_generator.py  # PDF filling
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

## 🔮 Future Enhancements

### Priority 2: Document Intelligence Router
**Goal**: Optimize processing based on document characteristics
**Implementation**:
```python
class DocumentRouter:
    def classify_document(self, path) -> DocumentType:
        # Digital PDF → Direct Vision API
        # Scanned PDF → Enhanced preprocessing  
        # Excel → Direct parsing or improved imaging
        # Complex tables → Specialized extraction
```

### Priority 3: Advanced Extraction Features
- **Multi-page table recognition**: Handle tables spanning multiple pages
- **Confidence scoring per field**: Quality metrics for each extracted value

### Priority 4: Production Optimizations
- **Batch processing**: Process multiple documents in parallel
- **Caching layer**: Cache extraction results for duplicate documents
- **Incremental updates**: Smart re-processing when documents change
- **API rate limiting**: Intelligent chunking

## 🧪 Testing & Validation

### Test packets ###
- **Brigham Dallas Package**: 19 files (PFS, tax returns 2021-2024, business docs)
- **Dave Burlington Package**: Complete loan application with projections

## 📞 Support & Development

### Environment Requirements
- **Python**: 3.13.3+
- **API Key**: Anthropic Claude API access
- **System Dependencies**: 
  - `poppler-utils` for PDF processing
  - Standard ML libraries (PIL, pandas, etc.)

### Key Commands
```bash
# Setup
python3 check_env.py

# Quick validation  
python3 run_fast_test.py

# Full system test
python3 run_comprehensive_test.py

# Analyze document types
python3 tests/analysis/test_pdf_technical_structure.py
```

### Common Issues
1. **API Rate Limits**: Reduce document batch sizes
2. **Memory Usage**: Large documents may require chunking

---

**Architecture Version**: Two-Part Pipeline v2.0  
**Claude Model**: claude-sonnet-4-20250514