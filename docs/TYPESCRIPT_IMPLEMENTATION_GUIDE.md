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

## SECTION 1: Google Document AI Implementation Details

### Overview
The current implementation uses Google Document AI as the primary extraction engine, with Claude Vision as an intelligent fallback. This hybrid approach achieves 85-97% accuracy while optimizing costs.

### Document AI Architecture

#### Processing Flow
1. **Document Classification** → Pre-classified by UI (LoanApplicationItemType enum)
2. **Processor Selection** → Form Parser for structured, Claude for narrative
3. **Extraction** → DocAI extracts entities, tables, key-values, checkboxes
4. **Fallback** → Claude Vision for failed/large documents
5. **Result Merging** → Unified JSON output

#### Key Processors Used

##### Form Parser Processor
- **Purpose:** Extract structured data from forms and documents
- **Capabilities:** Key-value pairs, tables, entities, checkboxes, layout analysis
- **Limits:** 15 pages synchronous, 30 pages with imageless mode (requires allowlist)
- **Cost:** $30 per 1000 pages
- **Confidence:** 78-85% typical
- **Best For:** Tax returns, financial statements, application forms

##### General Processor (Fallback)
- **Purpose:** Universal document processing
- **Capabilities:** Text, entities, tables, basic structure
- **Limits:** 30 pages
- **Cost:** $1.50 per 1000 pages
- **Confidence:** 70-75% typical
- **When Used:** Form Parser unavailable or as cost-saving measure

#### Configuration Requirements

##### Environment Variables
```bash
# Required for DocAI
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us"  # or "eu"
DOCAI_FORM_PARSER_ID="16-char-hex-id"
DOCAI_GENERAL_PROCESSOR_ID="16-char-hex-id"  # Optional fallback

# Processing options
DOCAI_TIMEOUT="120"  # seconds
DOCAI_MAX_RETRIES="3"
DOCAI_MAX_PAGES_PER_REQUEST="15"
DOCAI_USE_IMAGELESS_MODE="false"  # Requires Google allowlist
```

##### Authentication
- **Service Account:** JSON key file with Document AI API permissions
- **Required Roles:** 
  - `documentai.processor.process` 
  - `documentai.processor.get`
- **Setup:** Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

#### API Response Structure

##### Form Parser Response
```typescript
interface FormParserResponse {
  text: string;                    // Full extracted text
  confidence: number;               // Overall confidence (0-1)
  pages: Array<{
    pageNumber: number;
    dimension: { width: number; height: number; unit: string };
    layout: Layout;
    blocks: Block[];
    paragraphs: Paragraph[];
    lines: Line[];
    tokens: Token[];
  }>;
  entities: Array<{
    type: string;                 // e.g., "person", "organization", "date"
    mentionText: string;
    confidence: number;
    pageAnchor: PageAnchor;
  }>;
  tables: Array<{
    layout: Layout;
    headerRows: Row[];
    bodyRows: Row[];
  }>;
  formFields: Array<{
    fieldName: { text: string; confidence: number };
    fieldValue: { text: string; confidence: number };
    pageAnchor: PageAnchor;
  }>;
  checkboxes: Array<{
    name: string;
    value: "checked" | "unchecked";
    confidence: number;
  }>;
}
```

#### Processing Strategies

##### Document Type Routing
```
Structured Documents → Form Parser
├── Tax Returns (1040, 1065, 1120S)
├── Financial Statements (PFS, Balance Sheet, P&L)
├── Bank Statements
├── Debt Schedules
└── Application Forms

Narrative Documents → Claude Vision
├── Business Plans
├── Management Bios
├── Letters of Intent
├── Legal Documents
└── Executive Summaries

Tabular Documents → Hybrid Approach
├── Excel → Pandas (100% accuracy, no API)
├── PDF Tables → Form Parser
└── Complex Tables → Claude Vision
```

##### Error Handling & Fallbacks
1. **Rate Limiting:** 429 errors → Exponential backoff with jitter
2. **Page Limit Exceeded:** Split document into chunks
3. **Low Confidence:** Re-process with Claude Vision
4. **Timeout:** Retry with increased timeout
5. **Authentication Failed:** Check service account permissions

---

## SECTION 2: TypeScript Migration Guide

### Overview
This section provides a detailed guide for migrating the Python document processing pipeline to TypeScript, broken into logical PRs for incremental deployment.

### Required Libraries & Dependencies

#### Core Processing Libraries
```json
{
  "@google-cloud/documentai": "^8.0.0",     // Google Document AI client
  "@anthropic-ai/sdk": "^0.20.0",           // Claude API client
  "pdf-lib": "^1.17.1",                     // PDF manipulation
  "pdfjs-dist": "^3.11.0",                  // PDF parsing
  "xlsx": "^0.18.5",                        // Excel processing
  "sharp": "^0.33.0",                       // Image processing
  "tesseract.js": "^5.0.0"                  // OCR fallback (optional)
}
```

#### Utility Libraries
```json
{
  "lodash": "^4.17.21",                     // Data manipulation
  "joi": "^17.11.0",                        // Schema validation
  "winston": "^3.11.0",                     // Logging
  "bull": "^4.11.0",                        // Job queue for async processing
  "redis": "^4.6.0",                        // Caching layer
  "dotenv": "^16.3.0"                       // Environment configuration
}
```

### PR Breakdown for Migration

#### PR 1: Core Infrastructure Setup
**Scope:** Foundation and configuration
- Set up TypeScript project structure
- Configure Google Cloud SDK authentication
- Implement configuration management system
- Add environment variable validation
- Create base error handling classes
- Set up logging infrastructure

**Key Files to Create:**
- `src/config/docai.config.ts` - DocAI configuration
- `src/config/app.config.ts` - Application settings
- `src/utils/logger.ts` - Winston logger setup
- `src/errors/index.ts` - Custom error classes
- `src/types/document.types.ts` - Core type definitions

**Testing:** Configuration validation, logger output

---

#### PR 2: Document Classification System
**Scope:** Document type detection and routing
- Port `EnhancedDocumentClassifier` logic
- Implement LoanApplicationItemType enum
- Create document routing logic
- Add filename-based classification
- Implement content-based classification fallback

**Key Files to Create:**
- `src/classifiers/DocumentClassifier.ts`
- `src/types/LoanApplicationItemType.ts`
- `src/routers/DocumentRouter.ts`
- `src/utils/patterns.ts` - Regex patterns for classification

**Testing:** Classification accuracy for all document types

---

#### PR 3: Google Document AI Integration
**Scope:** Form Parser and General Processor clients
- Implement DocAI client wrapper
- Add Form Parser processor
- Add General Processor fallback
- Implement retry logic with exponential backoff
- Add response parsing and normalization

**Key Files to Create:**
- `src/processors/DocAIClient.ts` - Base client
- `src/processors/FormParserProcessor.ts`
- `src/processors/GeneralProcessor.ts`
- `src/utils/retry.ts` - Retry mechanisms
- `src/parsers/DocAIResponseParser.ts`

**Testing:** Process sample documents, verify extraction

---

#### PR 4: Claude Vision Integration
**Scope:** Anthropic API integration for narrative documents
- Implement Claude client wrapper
- Add image preprocessing logic
- Create prompt templates
- Implement response parsing
- Add rate limiting

**Key Files to Create:**
- `src/processors/ClaudeProcessor.ts`
- `src/preprocessors/ImagePreprocessor.ts`
- `src/templates/prompts.ts`
- `src/utils/rateLimiter.ts`

**Testing:** Process narrative documents, verify extraction

---

#### PR 5: Excel Processing Module
**Scope:** Direct Excel extraction without OCR
- Implement XLSX parser
- Add sheet detection logic
- Create table extraction
- Add financial data detection
- Implement pure TypeScript extraction (no API calls)

**Key Files to Create:**
- `src/processors/ExcelProcessor.ts`
- `src/extractors/TableExtractor.ts`
- `src/utils/financial.ts` - Financial data patterns

**Testing:** Process Excel files, verify 100% numeric accuracy

---

#### PR 6: Enhanced Document Router
**Scope:** Intelligent routing based on document type
- Implement document type to processor mapping
- Add narrative vs structured classification
- Create cost optimization logic
- Add processor selection algorithm
- Implement fallback chains

**Key Files to Create:**
- `src/routers/EnhancedDocumentRouter.ts`
- `src/strategies/ProcessingStrategy.ts`
- `src/optimizers/CostOptimizer.ts`

**Testing:** Verify correct processor selection for each type

---

#### PR 7: Rate Limiting & Error Handling
**Scope:** Robust error handling and rate limiting
- Implement rate limiter for all APIs
- Add exponential backoff with jitter
- Create error recovery strategies
- Add circuit breaker pattern
- Implement dead letter queue

**Key Files to Create:**
- `src/middleware/RateLimiter.ts`
- `src/utils/backoff.ts`
- `src/patterns/CircuitBreaker.ts`
- `src/queues/DeadLetterQueue.ts`

**Testing:** Simulate rate limit scenarios, verify recovery

---

#### PR 8: Result Merging & Normalization
**Scope:** Combine results from multiple processors
- Implement result merger
- Add confidence aggregation
- Create field deduplication
- Add provenance tracking
- Implement master JSON structure

**Key Files to Create:**
- `src/mergers/ResultMerger.ts`
- `src/aggregators/ConfidenceAggregator.ts`
- `src/utils/deduplication.ts`
- `src/models/MasterDocument.ts`

**Testing:** Merge multiple extraction results

---

#### PR 9: Preprocessing Layer
**Scope:** Extract data without API calls
- Port DocumentPreprocessor logic
- Implement table detection
- Add key-value extraction
- Create pattern matching
- Add preprocessing decision logic

**Key Files to Create:**
- `src/preprocessors/DocumentPreprocessor.ts`
- `src/extractors/KeyValueExtractor.ts`
- `src/detectors/TableDetector.ts`
- `src/matchers/PatternMatcher.ts`

**Testing:** Extract fields without API calls

---

#### PR 10: Form Mapping Service
**Scope:** Map extracted data to bank forms
- Implement form specification loader
- Create intelligent field mapping
- Add confidence scoring
- Implement coverage analysis
- Add field variation handling

**Key Files to Create:**
- `src/services/FormMappingService.ts`
- `src/mappers/FieldMapper.ts`
- `src/analyzers/CoverageAnalyzer.ts`
- `src/specs/FormSpecificationLoader.ts`

**Testing:** Map to all 9 bank forms

---

#### PR 11: PDF Generation
**Scope:** Generate filled PDF forms
- Implement PDF form filler
- Add checkbox handling
- Create field discovery
- Add template management
- Implement batch PDF generation

**Key Files to Create:**
- `src/generators/PDFGenerator.ts`
- `src/fillers/FormFiller.ts`
- `src/handlers/CheckboxHandler.ts`
- `src/managers/TemplateManager.ts`

**Testing:** Generate PDFs for all banks

---

#### PR 12: Pipeline Orchestration
**Scope:** Coordinate entire processing pipeline
- Implement main orchestrator
- Add job queue management
- Create progress tracking
- Add incremental processing
- Implement application-level logic

**Key Files to Create:**
- `src/orchestrators/PipelineOrchestrator.ts`
- `src/queues/JobQueue.ts`
- `src/trackers/ProgressTracker.ts`
- `src/services/ApplicationService.ts`

**Testing:** End-to-end pipeline test

---

#### PR 13: Caching & Performance
**Scope:** Optimize performance with caching
- Implement Redis caching layer
- Add document fingerprinting
- Create cache invalidation logic
- Add result caching
- Implement preprocessing cache

**Key Files to Create:**
- `src/cache/CacheManager.ts`
- `src/utils/fingerprint.ts`
- `src/strategies/CacheStrategy.ts`

**Testing:** Verify cache hits, measure performance

---

#### PR 14: Monitoring & Observability
**Scope:** Add comprehensive monitoring
- Implement metrics collection
- Add API cost tracking
- Create performance monitoring
- Add error tracking
- Implement alerting

**Key Files to Create:**
- `src/monitoring/MetricsCollector.ts`
- `src/trackers/CostTracker.ts`
- `src/monitors/PerformanceMonitor.ts`
- `src/alerts/AlertManager.ts`

**Testing:** Verify metrics collection

---

#### PR 15: Testing Infrastructure
**Scope:** Comprehensive test suite
- Add unit tests for all modules
- Create integration tests
- Add E2E test scenarios
- Implement test fixtures
- Add performance benchmarks

**Key Files to Create:**
- `tests/unit/**/*.test.ts`
- `tests/integration/**/*.test.ts`
- `tests/e2e/**/*.test.ts`
- `tests/fixtures/**/*`
- `tests/benchmarks/**/*.bench.ts`

**Testing:** All tests pass with >80% coverage

---

### Key Implementation Considerations

#### Authentication & Security
1. **Service Account Management:** Store credentials securely, rotate regularly
2. **API Key Security:** Use environment variables, never commit keys
3. **Data Encryption:** Encrypt sensitive data at rest and in transit
4. **Access Control:** Implement role-based access for different operations
5. **Audit Logging:** Track all document processing activities

#### Performance Optimization
1. **Batch Processing:** Group documents for efficient API usage
2. **Parallel Processing:** Use worker threads for CPU-intensive tasks
3. **Lazy Loading:** Load processors only when needed
4. **Connection Pooling:** Reuse API connections
5. **Memory Management:** Stream large files, avoid loading into memory

#### Error Recovery Strategies
1. **Retry Logic:** Exponential backoff for transient failures
2. **Circuit Breaker:** Prevent cascading failures
3. **Fallback Chain:** DocAI → Claude → Manual review
4. **Partial Success:** Save successful extractions even if some fail
5. **Dead Letter Queue:** Handle permanently failed documents

#### Cost Optimization
1. **Processor Selection:** Use cheapest processor that meets accuracy needs
2. **Preprocessing:** Extract obvious fields without API calls
3. **Caching:** Cache extraction results by document hash
4. **Batch API:** Use batch endpoints when available
5. **Budget Limits:** Implement daily/monthly spending caps

---

## SECTION 3: Core Workflows

### Document Processing Workflow

#### Step 1: Document Receipt
- File uploaded to S3/storage
- Metadata recorded (type, size, upload time)
- Document queued for processing

#### Step 2: Classification
- Filename analysis (75% confidence)
- Content sampling if needed
- Route to appropriate processor

#### Step 3: Preprocessing (Optional)
- Extract tables without OCR
- Find key-value pairs via patterns
- Determine if API needed

#### Step 4: Primary Processing
- **Structured:** DocAI Form Parser
- **Narrative:** Claude Vision
- **Excel:** Pandas extraction

#### Step 5: Fallback Processing
- If primary fails → try secondary
- If confidence low → reprocess
- If page limit exceeded → chunk

#### Step 6: Result Merging
- Combine multiple extractions
- Deduplicate fields
- Calculate confidence scores

#### Step 7: Validation
- Schema validation
- Business rule checks
- Confidence thresholds

#### Step 8: Storage
- Save to master JSON
- Update extraction logs
- Cache results

### Form Mapping Workflow

#### Step 1: Load Master Data
- Read extracted JSON
- Validate completeness
- Check data quality

#### Step 2: Load Form Specifications
- Read bank form templates
- Parse field requirements
- Load validation rules

#### Step 3: Field Mapping
- Match extracted to required fields
- Handle name variations
- Calculate confidence scores

#### Step 4: PDF Generation
- Load PDF template
- Fill form fields
- Update checkboxes
- Save filled PDF

#### Step 5: Coverage Analysis
- Calculate field coverage
- Identify missing data
- Generate reports

### Incremental Processing Workflow

#### Step 1: Check Existing Data
- Load existing master JSON
- Identify processed documents
- Determine merge strategy

#### Step 2: Process New Documents
- Extract from new files only
- Maintain processing history
- Track document versions

#### Step 3: Merge Results
- Deep merge with conflict resolution
- Last-write-wins for conflicts
- Preserve metadata

#### Step 4: Update Master
- Save merged data
- Update timestamps
- Log changes

---

## SECTION 4: Migration Checklist

### Pre-Migration
- [ ] Audit current Python implementation
- [ ] Document all business rules
- [ ] Create test document set
- [ ] Set up TypeScript project
- [ ] Configure CI/CD pipeline

### Infrastructure
- [ ] Set up Google Cloud project
- [ ] Configure service accounts
- [ ] Set up Redis cache
- [ ] Configure job queue
- [ ] Set up monitoring

### Core Implementation
- [ ] Port document classifiers
- [ ] Implement DocAI integration
- [ ] Add Claude integration
- [ ] Create Excel processor
- [ ] Build result merger

### Testing
- [ ] Unit tests (>80% coverage)
- [ ] Integration tests
- [ ] E2E scenarios
- [ ] Performance benchmarks
- [ ] Load testing

### Deployment
- [ ] Staging deployment
- [ ] A/B testing setup
- [ ] Production deployment
- [ ] Monitoring verification
- [ ] Rollback plan ready

### Post-Migration
- [ ] Performance comparison
- [ ] Cost analysis
- [ ] User training
- [ ] Documentation update
- [ ] Deprecate Python version

---

## SECTION 5: Key Differences from Python Implementation

### Type Safety
- **Python:** Runtime type checking, optional type hints
- **TypeScript:** Compile-time type checking, enforced types
- **Migration:** Define interfaces for all data structures

### Async Handling
- **Python:** `async/await` with asyncio
- **TypeScript:** Native `Promise` and `async/await`
- **Migration:** Convert asyncio patterns to Promise patterns

### Package Management
- **Python:** pip/poetry with requirements.txt
- **TypeScript:** npm/yarn with package.json
- **Migration:** Map Python packages to Node equivalents

### File System
- **Python:** `pathlib.Path`
- **TypeScript:** Node.js `fs` and `path` modules
- **Migration:** Use `fs.promises` for async file operations

### HTTP Clients
- **Python:** `aiohttp`, `requests`
- **TypeScript:** `axios`, `fetch`, native `https`
- **Migration:** Standardize on axios for consistency

### Data Processing
- **Python:** pandas, numpy
- **TypeScript:** Native arrays, lodash, or DataFrame libraries
- **Migration:** Consider `danfojs` for pandas-like operations

---

## Appendix: Quick Reference

### Environment Variables
```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=
GOOGLE_APPLICATION_CREDENTIALS=
DOCAI_FORM_PARSER_ID=
DOCAI_GENERAL_PROCESSOR_ID=

# Anthropic
ANTHROPIC_API_KEY=

# Application
NODE_ENV=production
LOG_LEVEL=info
CACHE_TTL=3600
MAX_RETRIES=3
```

### Common Commands
```bash
# Development
npm run dev              # Start development server
npm run build           # Build TypeScript
npm run test            # Run tests
npm run lint            # Lint code

# Processing
npm run process -- --file document.pdf --type TAX_RETURN
npm run batch -- --dir ./documents --output ./results
npm run validate -- --master ./master.json

# Deployment
npm run deploy:staging
npm run deploy:production
npm run rollback
```

This guide provides a roadmap through the codebase without extensive code snippets, focusing on where features live and how components interact.