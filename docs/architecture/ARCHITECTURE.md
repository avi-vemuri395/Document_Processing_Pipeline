# System Architecture

## Overview

The Document Processing Pipeline implements a **two-part architecture** that separates data extraction from form generation, enabling efficient processing of loan application documents for multiple banks.

## Core Design Principles

1. **Extract Once, Map Many**: Documents are processed once to create a master data pool, then mapped to multiple output formats
2. **Incremental Processing**: Support for documents arriving over time with intelligent merging
3. **Bank Agnostic Extraction**: Core extraction doesn't know about specific bank requirements
4. **Flexible Output Generation**: Easy to add new banks, forms, or output formats

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         DOCUMENT PROCESSING PIPELINE                       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                     PART 1: DATA EXTRACTION                        │  │
│  │                                                                     │  │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐    │  │
│  │  │   Documents  │───▶│  Universal   │───▶│   Claude 3.5     │    │  │
│  │  │  (PDF, IMG,  │    │ Preprocessor │    │  Sonnet Vision   │    │  │
│  │  │   txt,Excel) │    │              │    │   Extraction     │    │  │
│  │  └──────────────┘    └──────────────┘    └─────────┬────────┘    │  │
│  │                                                      │             │  │
│  │                    ┌──────────────────────────┐     │             │  │
│  │                    │   Comprehensive         │◀────┘             │  │
│  │                    │     Processor           │                    │  │
│  │                    │  • Structure data       │                    │  │
│  │                    │  • Merge incremental    │                    │  │
│  │                    │  • Maintain master JSON │                    │  │
│  │                    └───────────┬──────────────┘                   │  │
│  │                                │                                  │  │
│  │                    ┌───────────▼──────────────┐                   │  │
│  │                    │    MASTER JSON POOL      │                   │  │
│  │                    │  • All extracted data    │                   │  │
│  │                    │  • Version history       │                   │  │
│  │                    │  • Audit trail           │                   │  │
│  │                    └───────────┬──────────────┘                   │  │
│  └────────────────────────────────┼────────────────────────────────┘  │
│                                   │                                    │
│  ┌────────────────────────────────┼────────────────────────────────┐  │
│  │                     PART 2: OUTPUT GENERATION                    │  │
│  │                                │                                 │  │
│  │         ┌──────────────────────┼──────────────────────┐         │  │
│  │         │                      │                       │         │  │
│  │  ┌──────▼───────┐    ┌────────▼────────┐    ┌────────▼──────┐  │  │
│  │  │    Form      │    │   Spreadsheet   │    │    Future     │  │  │
│  │  │   Mapping    │    │    Mapping      │    │   Outputs     │  │  │
│  │  │   Service    │    │    Service      │    │   (APIs,      │  │  │
│  │  │              │    │                 │    │   Reports)    │  │  │
│  │  └──────┬───────┘    └────────┬────────┘    └───────────────┘  │  │
│  │         │                      │                                 │  │
│  │  ┌──────▼───────────────────────▼────────────────────────────┐  │  │
│  │  │                    OUTPUT ARTIFACTS                       │  │  │
│  │  │                                                           │  │  │
│  │  │  • Live Oak: Application.pdf, PFS.pdf, 4506-T.pdf       │  │  │
│  │  │  • Huntington: Business.pdf, Tax.pdf, Debt.pdf,         │  │  │
│  │  │               Financial.pdf                              │  │  │
│  │  │  • Wells Fargo: Financial.json, Business.json           │  │  │
│  │  │  • Spreadsheets: Debt_Schedule.xlsx, Use_of_Funds.xlsx  │  │  │
│  │  └───────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Part 1: Data Extraction

#### ComprehensiveProcessor (`src/template_extraction/comprehensive_processor.py`)

**Purpose**: Extract data once from all documents and maintain master JSON pool

**Key Methods**:
- `process_document()`: Extract data from single document
- `process_documents()`: Batch process multiple documents
- `_merge_with_master()`: Intelligent merging with conflict resolution
- `_structure_extracted_data()`: Convert raw extraction to structured format

**Data Flow**:
1. Receives document paths
2. Converts to images via UniversalPreprocessor
3. Sends to Claude 3.5 Sonnet for extraction
4. Structures extracted data
5. Merges with existing master JSON
6. Saves updated master to disk

**Merge Strategy**:
- Last document wins for conflicts
- Arrays are appended (e.g., multiple debts)
- Nested objects are deep merged
- Maintains extraction history

#### BenchmarkExtractor (`src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py`)

**Purpose**: Core LLM extraction using vision capabilities

**Features**:
- Single API call for all data extraction
- Vision-based processing (no OCR needed)
- Handles multi-page documents
- Supports Files API for large documents

### Part 2: Output Generation

#### FormMappingService (`src/template_extraction/form_mapping_service.py`)

**Purpose**: Map master JSON to bank-specific forms

**Bank Forms**:
```python
BANK_FORMS = {
    'live_oak': [
        'application',  # Live Oak Express Application
        'pfs',         # Personal Financial Statement
        '4506t'        # Tax Form 4506-T
    ],
    'huntington': [
        'business_app',      # Business Application
        'tax_transcript',    # Tax Transcript
        'debt_schedule',     # Debt Schedule
        'financial_statement' # Financial Statement
    ],
    'wells_fargo': [
        'financial_questionnaire',  # Financial Questionnaire
        'business_info'             # Business Information
    ]
}
```

**Mapping Process**:
1. Load master JSON for application
2. Apply bank-specific mapping rules
3. Generate PDF if template exists
4. Always create JSON mapping
5. Return paths to generated artifacts

#### SpreadsheetMappingService (`src/template_extraction/spreadsheet_mapping_service.py`)

**Purpose**: Populate Excel templates from master JSON

**Supported Spreadsheets**:
- **Debt Schedule**: Maps liabilities to structured rows
- **Use of Funds**: Maps financial data to categories

**Features**:
- Preserves Excel formatting
- Handles formulas and calculations
- Supports multiple worksheets
- Maintains data validation rules

#### PipelineOrchestrator (`src/template_extraction/pipeline_orchestrator.py`)

**Purpose**: Coordinate the entire two-part pipeline

**Key Methods**:
```python
async def process_application(
    self,
    application_id: str,
    documents: List[Path],
    target_banks: Optional[List[str]] = None,
    generate_spreadsheets: bool = False
) -> ProcessingResult
```

**Orchestration Flow**:
1. Part 1: Process documents → Update master JSON
2. Part 2a: Generate bank forms if target_banks specified
3. Part 2b: Generate spreadsheets if requested
4. Return all generated artifacts

## Data Structures

### Master JSON Schema

```json
{
  "application_id": "string",
  "last_updated": "ISO 8601 timestamp",
  "extraction_version": "string",
  "applicant_info": {
    "name": "string",
    "ssn": "string",
    "address": "object",
    "phone": "string",
    "email": "string"
  },
  "business_info": {
    "name": "string",
    "type": "LLC|C-Corp|S-Corp|Partnership|Sole Prop",
    "ein": "string",
    "formation_date": "string",
    "ownership_percentage": "number"
  },
  "financial_info": {
    "assets": {
      "cash": "number",
      "investments": "number",
      "real_estate": "number",
      "total": "number"
    },
    "liabilities": {
      "mortgages": "array",
      "loans": "array",
      "credit_cards": "array",
      "total": "number"
    },
    "net_worth": "number",
    "annual_income": "number"
  },
  "tax_returns": {
    "2021": "object",
    "2022": "object",
    "2023": "object",
    "2024": "object"
  },
  "extraction_history": [
    {
      "timestamp": "ISO 8601",
      "document": "string",
      "fields_extracted": "number"
    }
  ]
}
```

### Processing Result Schema

```json
{
  "application_id": "string",
  "status": "success|partial|failed",
  "master_json_path": "string",
  "generated_forms": {
    "live_oak": {
      "application": {
        "pdf": "path/to/pdf",
        "json": "path/to/json"
      }
    }
  },
  "spreadsheets": {
    "debt_schedule": "path/to/xlsx",
    "use_of_funds": "path/to/xlsx"
  },
  "errors": [],
  "warnings": []
}
```

## Error Handling

### Extraction Errors
- Document conversion failures → Log and skip document
- API rate limits → Exponential backoff with retry
- Invalid document format → Return error in result

### Mapping Errors
- Missing required fields → Use defaults or skip field
- Invalid data types → Attempt conversion or log warning
- Template not found → Generate JSON-only output

### Recovery Strategies
- Partial processing: Continue with available data
- Incremental saves: Persist progress after each document
- Audit logging: Track all operations for debugging

## Performance Considerations

### Optimization Strategies

1. **Batch Processing**: Group documents for efficient API usage
2. **Caching**: Cache form field mappings and templates
3. **Parallel Processing**: Process independent banks concurrently
4. **Lazy Loading**: Only load master JSON when needed
5. **Incremental Updates**: Only process new documents

### Benchmarks

| Operation | Time | API Cost |
|-----------|------|----------|
| Extract 5 documents | ~30s | $0.05 |
| Map to 9 forms | ~10s | $0.02 |
| Generate 2 spreadsheets | ~2s | $0.00 |
| Total pipeline | ~45s | $0.07 |

## Scalability

### Horizontal Scaling
- Stateless processors allow multiple workers
- S3 backend for shared state
- Queue-based document processing
- Load balancing across API keys

### Vertical Scaling
- Increase document batch size
- Process multiple applications in parallel
- Use Files API for large documents
- Optimize prompt engineering

## Security Considerations

1. **Data Privacy**: 
   - PII redaction in logs
   - Encrypted storage for master JSON
   - Secure API key management

2. **Access Control**:
   - Application-specific data isolation
   - Role-based access to outputs
   - Audit trail for all operations

3. **Compliance**:
   - GDPR data retention policies
   - SOC2 audit logging
   - PCI DSS for financial data

## Future Enhancements

### Planned Features
1. **Real-time Processing**: WebSocket updates for progress
2. **ML Confidence Scores**: Track extraction confidence
3. **Smart Field Validation**: Business logic validation
4. **Template Learning**: Learn from corrections
5. **Multi-language Support**: Process non-English documents

### Integration Points
- **CRM Systems**: Salesforce, HubSpot integration
- **Document Management**: SharePoint, Google Drive
- **Banking APIs**: Direct submission to banks
- **Analytics**: Business intelligence dashboards

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies
- Validate data transformations

### Integration Tests
- Test component interactions
- Validate end-to-end flow
- Check error propagation

### System Tests
- `test_two_part_pipeline.py`: Core architecture validation
- `test_comprehensive_end_to_end.py`: Full pipeline with phases
- `test_incremental_processing.py`: Document merging logic
- `test_spreadsheet_population.py`: Excel generation

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Production Environment                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │   API        │      │   Worker     │                │
│  │   Gateway    │─────▶│   Cluster    │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                        │
│  ┌──────────────────────────────┼──────────────────┐   │
│  │            │                 │                   │   │
│  │  ┌─────────▼──────┐  ┌──────▼──────┐  ┌────────▼─┐ │
│  │  │   Document     │  │   Master    │  │  Output  │ │
│  │  │   Storage      │  │   JSON DB   │  │  Storage │ │
│  │  │   (S3)         │  │  (DynamoDB) │  │   (S3)   │ │
│  │  └────────────────┘  └─────────────┘  └──────────┘ │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

### Metrics
- Documents processed per hour
- API costs per application
- Error rates by component
- Form generation success rate

### Logging
- Structured JSON logging
- Correlation IDs for tracing
- Error aggregation
- Performance profiling

### Alerts
- API rate limit warnings
- Extraction failure thresholds
- Processing time anomalies
- Cost budget alerts