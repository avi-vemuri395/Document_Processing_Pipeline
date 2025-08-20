# Document Processing Pipeline - Architecture Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture Principles](#core-architecture-principles) 
3. [Document Processing Flow](#document-processing-flow)
4. [Component Architecture](#component-architecture)
   - [Part 1: Data Extraction](#part-1-data-extraction)
   - [Part 2: Output Generation](#part-2-output-generation)
5. [Document Classification Logic](#document-classification-logic)
6. [Intelligent Routing System](#intelligent-routing-system)
7. [Incremental Processing & Merging](#incremental-processing--merging)
8. [JSON Persistence Strategy](#json-persistence-strategy)
9. [Testing Architecture](#testing-architecture)
10. [Performance Characteristics](#performance-characteristics)
11. [Cost Optimization Strategy](#cost-optimization-strategy)

## System Overview

The Document Processing Pipeline implements a **hybrid extraction architecture** using Google Document AI as the primary processor with Claude Vision as an intelligent fallback. The system processes loan application documents through a two-part pipeline that extracts data once and maps it to multiple bank-specific output formats.

**Key Achievement**: 85-97% accuracy while reducing processing time from 3-5 days to 2-4 hours.

## Core Architecture Principles

1. **Extract Once, Map Many**: Documents are processed once to create a master data pool, then mapped to multiple output formats
2. **Intelligent Document Routing**: Documents are classified and routed to the optimal processor based on type, size, and structure
3. **Cost-Optimized Processing**: DocAI for structured forms ($0.03/doc), Claude Vision for narrative text ($0.01-0.02/doc), Direct pandas for Excel ($0)
4. **Incremental Processing**: Supports documents arriving over time with intelligent merging and version history
5. **High Accuracy Extraction**: 85-97% accuracy with specialized processors for different document types
6. **Comprehensive JSON Persistence**: Every extraction, mapping, and orchestration result saved as structured JSON

## Document Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DOCUMENT PROCESSING PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                    PART 1: EXTRACT ONCE                                │ │
│ │                                                                         │ │
│ │ Documents → Classification → Routing → Processing → Master JSON        │ │
│ │                                                                         │ │
│ │ ┌───────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────────┐  │ │
│ │ │Documents  │→ │DocumentClass │→ │Intelligent  │→ │BenchmarkExtract│  │ │
│ │ │(PDF,Excel,│  │ifier         │  │Routing      │  │• DocAI         │  │ │
│ │ │ IMG, txt) │  │• Heuristics  │  │• DocAI ≤15p │  │• Claude Vision │  │ │
│ │ │           │  │• File Size   │  │• Claude >15p│  │• Excel Direct  │  │ │
│ │ │           │  │• Type Map    │  │• Excel→Pand │  │• Unified JSON  │  │ │
│ │ └───────────┘  └──────────────┘  └─────────────┘  └────────┬───────┘  │ │
│ │                                                           │           │ │
│ │                    ┌─────────────────────────────────────┐│           │ │
│ │                    │        MASTER JSON POOL             ││           │ │
│ │                    │ • All extracted fields              ││           │ │
│ │                    │ • Version history                   ││           │ │
│ │                    │ • Processing metadata               ││           │ │
│ │                    │ • Confidence scores                 ││           │ │
│ │                    │ • Document classification           ││           │ │
│ │                    └─────────────────┬───────────────────┘│           │ │
│ └─────────────────────────────────────┼────────────────────────────────┘ │
│                                       │                                  │
│ ┌─────────────────────────────────────┼────────────────────────────────┐ │
│ │                    PART 2: MAP TO MANY                               │ │
│ │                                     │                                 │ │
│ │        ┌────────────────────────────┼─────────────────────────┐      │ │
│ │        │                            │                         │      │ │
│ │  ┌─────▼──────┐              ┌─────▼─────────┐     ┌────────▼────┐  │ │
│ │  │Form Mapping│              │Spreadsheet    │     │Future Outs  │  │ │
│ │  │Service     │              │Mapping Service│     │(APIs, etc.) │  │ │
│ │  │• Live Oak  │              │• Debt Schedule│     │             │  │ │
│ │  │• Huntington│              │• Use of Funds │     │             │  │ │
│ │  │• Wells Fargo│             │• Excel Templates│    │             │  │ │
│ │  └─────┬──────┘              └─────┬─────────┘     └─────────────┘  │ │
│ │        │                           │                                │ │
│ │  ┌─────▼─────────────────────────────▼──────────────────────────┐   │ │
│ │  │                    OUTPUT ARTIFACTS                          │   │ │
│ │  │                                                              │   │ │
│ │  │ • Bank PDFs: application.pdf, pfs.pdf, tax.pdf             │   │ │
│ │  │ • JSON Mappings: {bank}_{form}_mapped.json                  │   │ │
│ │  │ • Excel Files: debt_schedule.xlsx, use_of_funds.xlsx       │   │ │
│ │  │ • Orchestration: pipeline_results.json                     │   │ │
│ │  └─────────────────────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Part 1: Data Extraction

The extraction layer implements intelligent document routing with multiple processing strategies optimized for different document types.

#### PipelineOrchestrator (`src/template_extraction/pipeline_orchestrator.py`)

**Logic**: Main entry point that coordinates the two-part pipeline architecture.

**Key Methods**:
- `process_application()`: Complete pipeline execution for new applications
- `process_incremental()`: Add single documents to existing applications
- `_save_results()`: Persist orchestration metadata as JSON

**Orchestration Flow**:
1. Initialize application workspace in `outputs/applications/{id}/`
2. Execute Part 1 (extraction) via ComprehensiveProcessor
3. Execute Part 2a (form mapping) via FormMappingService  
4. Execute Part 2b (spreadsheets) via SpreadsheetMappingService
5. Save pipeline results JSON with complete metadata

#### ComprehensiveProcessor (`src/template_extraction/comprehensive_processor.py`)

**Logic**: Processes documents once and maintains master JSON pool with incremental merging. **NEW**: Includes DocAI format detection and structure processing.

**Core Processing Logic**:
1. **Document Processing Loop**: Process each document individually
2. **Classification**: Use DocumentClassifier for routing decisions
3. **Extraction**: Route to BenchmarkExtractor for unified processing
4. **Format Detection**: Automatically detect DocAI, Excel, or Claude Vision response formats
5. **Structure Processing**: Map DocAI results to pipeline categories (personal_info, business_info, financial_data)
6. **Individual Persistence**: Save each extraction as `{doc}_extraction.json`
7. **Master Merging**: Merge results into master_data.json using "last wins" strategy
8. **Metadata Tracking**: Maintain document history, timestamps, confidence scores

**NEW: DocAI Structure Processing Logic**:
```python
# _is_docai_format(): Detect DocAI response format
# _process_docai_format(): Map DocAI data to pipeline categories
# _categorize_form_fields(): Split form fields into personal vs business
# _extract_financial_from_tables(): Process tables into financial data
# _process_entities(): Structure entity data by type
```

**Result**: PDF extraction success rate improved from 0% to 66.7% (4/6 categories populated)

**Merge Strategy Implementation**:
```python
# Last document wins for scalar values
# Arrays are appended (accumulate multiple entries)
# Nested objects are deep merged recursively
# Version history preserved in metadata
```

#### BenchmarkExtractor (`src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py`)

**Logic**: Intelligent routing hub that delegates to specialized processors based on document characteristics.

**Routing Decision Tree**:
1. **Excel Files** → `HybridExcelExtractor` (pandas-direct, 100% accuracy, $0 cost)
2. **Small PDFs (≤15 pages, ≤1.5MB)** → `DocAI Form Parser` (structured extraction, $0.03/doc)
3. **Large PDFs (>15 pages, >1.5MB)** → `Claude Vision API` (fallback, $0.01-0.02/doc)
4. **Failed DocAI** → `Claude Vision API` (automatic fallback)

**Processing Logic**:
1. Categorize documents by size/type using file metadata
2. Route Excel files to direct pandas extraction
3. Route PDFs to DocAI with size limits (15 pages, timeout 60s)
4. Handle DocAI failures with Claude Vision fallback
5. Unify all results into consistent JSON structure
6. Add processing metadata (method used, timing, confidence)

#### DocumentClassifier (`src/extraction_methods/multimodal_llm/utils/document_classifier.py`)

**Logic**: Zero-cost classification using multiple strategies to optimize routing decisions.

**Classification Strategies**:
1. **Loan Type Mapping**: Direct mapping from UI-provided LoanApplicationItemType
2. **Heuristic Analysis**: Pattern matching on filename and extracted text snippets
3. **File Size Analysis**: Estimate page count from file size for routing decisions
4. **DocAI Metadata Inference**: Post-processing analysis of DocAI results

**Document Categories & Routing Logic**:
```python
STRUCTURED_FORM → DocAI (high confidence for forms, tables, structured data)
TAX_DOCUMENT → DocAI (optimized for IRS forms, schedules)
NARRATIVE_TEXT → Claude Vision (better for text-heavy, unstructured content)  
VISUAL_DIAGRAM → Claude Vision (charts, graphs, org diagrams)
```

**Confidence Scoring**: Each classification includes confidence percentage for routing thresholds.

### Part 2: Output Generation

The output layer maps the master JSON pool to various bank-specific formats without re-extracting data.

#### FormMappingService (`src/template_extraction/form_mapping_service.py`)

**Logic**: Maps master JSON fields to bank-specific form specifications using intelligent field matching.

**Core Mapping Logic**:
1. **Form Specification Loading**: Load JSON specs from `templates/form_specs/`
2. **Field Path Resolution**: Navigate nested master JSON using dot notation paths
3. **Intelligent Matching**: Handle field name variations and fuzzy matching
4. **Bank-Specific Generation**: Generate forms for Live Oak, Huntington, Wells Fargo
5. **JSON Persistence**: Save each form mapping as `{bank}_{form}_mapped.json`
6. **PDF Generation**: Generate filled PDFs where templates exist

**Bank Form Configuration**:
```python
BANK_FORMS = {
    'live_oak': ['application', 'pfs', '4506t'],
    'huntington': ['business_app', 'pfs', 'tax_transcript', 'debt_schedule'],  
    'wells_fargo': ['loan_app', 'financial']
}
```

#### SpreadsheetMappingService (`src/template_extraction/spreadsheet_mapping_service.py`)

**Logic**: Populates Excel templates with structured financial data from master JSON.

**Spreadsheet Types**:
- **Debt Schedule**: Maps liability data to structured Excel rows
- **Use of Funds**: Maps financial data to categorized Excel template

**Processing Logic**:
1. Load Excel templates with preserved formatting
2. Map master JSON data to specific cells/ranges
3. Maintain formulas and data validation
4. Save populated spreadsheets to `outputs/applications/{id}/part2_spreadsheets/`

## Document Classification Logic

### Classification Strategy Selection

The system uses multiple classification strategies in order of preference:

1. **UI Pre-classification** (Highest Priority)
   - Source: LoanApplicationItemType enum from UI
   - Reliability: 100% when available
   - Usage: Direct mapping to processing categories

2. **File Size Heuristics** (Medium Priority)  
   - Logic: `file_size_mb ≤ 1.5 ? DocAI : Claude`
   - Basis: DocAI 15-page limit (~100KB per page estimate)
   - Accuracy: ~90% for routing decisions

3. **Text Pattern Matching** (Low Priority)
   - Strategy: Keyword extraction from filename and content preview
   - Patterns: "PFS", "tax", "1040", "balance sheet", etc.
   - Usage: Fallback when other methods unavailable

### Classification Categories

```python
DocumentCategory.STRUCTURED_FORM:
    # Tax returns, financial statements, application forms
    # Route to: DocAI Form Parser
    # Confidence threshold: 70%

DocumentCategory.TAX_DOCUMENT:  
    # IRS forms, W-2s, 1099s, tax schedules
    # Route to: DocAI Form Parser
    # Confidence threshold: 80%

DocumentCategory.NARRATIVE_TEXT:
    # Business plans, management bios, letters of intent
    # Route to: Claude Vision API
    # Confidence threshold: 60%

DocumentCategory.VISUAL_DIAGRAM:
    # Organizational charts, flowcharts, diagrams
    # Route to: Claude Vision API  
    # Confidence threshold: 70%
```

## Intelligent Routing System

### Routing Decision Matrix

| Document Type | Size | Processor | Cost | Accuracy | Rationale |
|---------------|------|-----------|------|----------|-----------|
| Excel files | Any | HybridExcelExtractor | $0 | 100% | Direct pandas extraction |
| PDF ≤15 pages | ≤1.5MB | DocAI Form Parser | $0.03 | 85-97% | Structured extraction optimized |
| PDF >15 pages | >1.5MB | Claude Vision | $0.01-0.02 | 85-97% | Better for large documents |
| Failed DocAI | Any | Claude Vision | $0.01-0.02 | 85-97% | Automatic fallback |

### Routing Implementation Logic

```python
# BenchmarkExtractor.extract_all() routing logic:

1. Excel Files:
   → direct_extract_excel_files() via HybridExcelExtractor
   → 100% numeric accuracy, no API calls

2. PDF Files:
   → categorize_by_size() using file metadata
   → Small PDFs (≤1.5MB): attempt_docai_extraction()
   → Large PDFs (>1.5MB): skip DocAI, direct to Claude Vision
   → DocAI failures: automatic fallback to Claude Vision

3. Result Unification:
   → standardize_extraction_format() for consistent JSON output
   → add_processing_metadata() with method, timing, confidence
```

## Incremental Processing & Merging

### Incremental Architecture

The system supports documents arriving over time (common in loan applications) through incremental processing with intelligent merging.

#### Merge Strategy Logic

**Master JSON Structure**:
```json
{
  "personal_info": { "name": "John Doe", "ssn": "123-45-6789" },
  "financial_data": { "assets": [...], "liabilities": [...] },
  "metadata": {
    "documents_processed": ["doc1.pdf", "doc2.xlsx"],
    "processing_history": [...],
    "last_updated": "2025-01-15T10:30:00"
  }
}
```

**Merge Rules Implementation**:
1. **Scalar Values**: Last document wins (overwrites existing)
2. **Arrays**: Append new items (accumulate multiple entries)
3. **Objects**: Deep merge recursively (preserve nested structure)
4. **Metadata**: Always append to history (maintain audit trail)

#### Version History Logic

Each incremental processing maintains:
- Document processing timestamps
- Field-level change tracking  
- Processing method metadata (DocAI vs Claude vs Excel)
- Confidence scores for each extraction
- Form regeneration triggers

**Incremental Flow**:
1. Load existing master_data.json (if exists)
2. Process new document(s) individually
3. Merge results using strategy above
4. Update master_data.json atomically
5. Optionally regenerate forms with updated data

## JSON Persistence Strategy

### Comprehensive JSON Output Structure

The system saves JSON at every processing level for transparency and debugging:

```
outputs/applications/{application_id}/
├── part1_document_processing/
│   ├── extractions/
│   │   ├── {document_name}_extraction.json    # Individual extractions
│   │   └── ...
│   └── master_data.json                       # Consolidated master pool
├── part2_form_mapping/
│   └── banks/
│       ├── live_oak/
│       │   ├── application_mapped.json        # Bank-specific mappings
│       │   └── ...
│       └── ...
├── part2_spreadsheets/
│   ├── debt_schedule.xlsx                     # Excel outputs
│   ├── use_of_funds.xlsx
│   └── summary.json                           # Spreadsheet metadata
└── pipeline_results.json                      # Complete orchestration log
```

### JSON Schema Standards

**Individual Extraction JSON**:
```json
{
  "document_name": "brigham_pfs.pdf",
  "extraction_method": "docai_form_parser",
  "processing_time": 5.42,
  "confidence_score": 0.87,
  "extracted_data": { /* actual field data */ },
  "metadata": { /* processing details */ }
}
```

**Master Data JSON**:
```json
{
  "personal_info": { /* consolidated personal data */ },
  "business_info": { /* consolidated business data */ },
  "financial_data": { /* consolidated financial data */ },
  "metadata": {
    "documents_processed": [...],
    "total_fields": 941,
    "processing_history": [...],
    "confidence_analysis": { /* aggregated confidence */ }
  }
}
```

## Testing Architecture

### Comprehensive End-to-End Testing

The testing strategy validates the complete pipeline through realistic loan application scenarios.

#### Test Phase Structure

**Phase 0: DocAI Validation**
- Process 3 small documents (≤1.5MB) 
- Validate DocAI integration working
- Measure DocAI vs Claude Vision usage ratios

**Phase 1: Initial Processing**
- Process 3-4 documents to create initial master JSON
- Validate individual extractions and master creation
- Test form generation for all 3 banks

**Phase 2: Incremental Addition**  
- Add 4 more documents to existing application
- Validate incremental merging logic
- Test field count increases and data accumulation

**Phase 3: Conflict Resolution**
- Add documents with conflicting data
- Validate "last wins" merge strategy
- Test update detection and field overwrites

**Phase 4: Complete Processing**
- Process all remaining documents
- Regenerate all forms with complete data
- Validate final outputs and comprehensive coverage

#### Test Coverage Validation

**Document Type Coverage**:
- DocAI-suitable: 5 documents (PFS, tax returns, org charts)
- Claude Vision-suitable: 7 documents (large PDFs)  
- Excel files: 7 documents (balance sheets, P&L, aging reports)
- Total: 19 documents across all supported formats

**Output Validation**:
- Individual extraction JSONs for each document
- Master data JSON with 941+ extracted fields
- Form mappings for 9 bank forms across 3 banks
- PDF generation where templates exist
- Excel spreadsheet population
- Complete pipeline orchestration results

## Performance Characteristics

### Processing Speed Metrics

| Document Type | Average Processing Time | Throughput |
|---------------|------------------------|------------|
| Excel files | 0.5-2 seconds | 15x faster than OCR |
| Small PDFs (DocAI) | 5-8 seconds | ~5 docs/minute |
| Large PDFs (Claude) | 10-15 seconds | ~3 docs/minute |
| Complete application | 2-4 hours | vs 3-5 days manual |

### Accuracy Measurements

| Processor | Document Types | Accuracy Range | Confidence |
|-----------|----------------|----------------|------------|
| HybridExcelExtractor | Excel files | 100% | Numeric precision |
| DocAI Form Parser | Structured PDFs | 85-97% | High for forms/tables |
| Claude Vision API | All document types | 85-97% | Consistent across types |

### Resource Utilization

**Memory Usage**: ~50-100MB per document during processing
**Storage**: ~1-5MB JSON output per document
**Network**: Optimized API calls (single call per document)
**Concurrency**: Supports parallel document processing

## Cost Optimization Strategy

### Processing Cost Analysis

**Per-Document Costs**:
- Excel files: $0 (direct pandas extraction)
- Small PDFs: $0.03 (DocAI Form Parser)  
- Large PDFs: $0.01-0.02 (Claude Vision API)
- Average blended: ~$0.015 per document

**Cost Optimization Logic**:
1. **Route Excel directly to pandas** (bypass API calls entirely)
2. **Use DocAI for small structured documents** (higher accuracy for forms)
3. **Use Claude Vision for large/narrative documents** (better cost/performance for text)
4. **Implement intelligent fallback** (avoid double processing costs)

### ROI Calculation

**Traditional Manual Processing**:
- Time: 3-5 days per application
- Labor cost: ~$500-800 per application
- Error rate: 10-15% requiring rework

**Automated Pipeline Processing**:  
- Time: 2-4 hours per application
- API cost: ~$0.30-0.50 per application (20 documents)
- Error rate: 3-15% (varies by document quality)
- **Net savings**: 95%+ time reduction, 99%+ cost reduction

This architecture guide provides the detailed logic and implementation understanding needed to navigate and extend the Document Processing Pipeline codebase.
