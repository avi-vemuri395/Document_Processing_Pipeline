1. Intent Classification

  Classification: RESEARCH / NEW FEATURE

  This is a request to plan and document Phase 3 implementation, which involves new features (table extraction,
  third bank template, financial statement parsing, Excel/CSV export) as outlined in the roadmap.

  ---
  2. RESEARCH / NEW FEATURE Path

  Requirements

  Based on the Phase 3 roadmap (Week 3):
  1. Table Extraction Engine - Extract structured data from tables (debt schedules, asset/liability statements)
  2. Financial Statement Parser - Parse balance sheets, income statements, cash flow statements
  3. Third Bank Template - Add support for a third partner bank
  4. Export Functionality - Export to Excel/CSV formats

  Plan

  Phase 3 Architecture

  Week 3: Table Extraction & Third Bank Support
  ├── Days 1-2: Table Extraction Engine
  │   ├── Multiple extraction strategies (PDFPlumber, Camelot, OCR)
  │   ├── Header recognition & cell merging
  │   └── Multi-page table continuation
  ├── Day 3: Financial Statement Parser
  │   ├── Balance sheet parser
  │   ├── Income statement parser
  │   └── Debt schedule parser
  ├── Day 4: Third Bank Template
  │   └── Wells Fargo or Chase (TBD)
  └── Day 5: Export Functionality
      ├── Excel exporter with formatting
      └── CSV exporter for data integration

  Technical Components

  1. Table Extractor (src/template_extraction/extractors/table.py)
  - Strategy pattern with multiple backends
  - Confidence-based selection
  - Row/column header detection
  - Total validation

  2. Financial Parsers (src/template_extraction/parsers/)
  - Specialized parsers for each statement type
  - Business logic validation
  - Cross-footing checks

  3. Export System (src/template_extraction/exporters/)
  - Excel with formatting/formulas
  - CSV for data pipelines
  - JSON for API integration

  Options

  Option 1: Full Implementation (5 days)
  - Complete all Phase 3 features
  - Pros: Comprehensive, follows roadmap exactly
  - Cons: Large scope, potential for bugs

  Option 2: Core Features First (3 days)
  - Table extraction + Excel export only
  - Pros: Faster delivery, simpler
  - Cons: Incomplete Phase 3

  Option 3: Incremental Rollout (5 days)
  - Day 1-2: Basic table extraction
  - Day 3: Third bank template
  - Day 4-5: Export + refinements
  - Pros: Early validation, easier debugging
  - Cons: Less comprehensive parsers

  Recommendation

  Choose Option 3: Incremental Rollout

  Rationale:
  - Delivers value quickly with basic table extraction
  - Third bank validates multi-bank architecture
  - Export functionality enables immediate business use
  - Can add sophisticated parsers in Phase 4 if needed

  ---
  3. Implementation Plan

  Day 1-2: Table Extraction

  # src/template_extraction/extractors/table.py
  class TableExtractor(BaseExtractor):
      def __init__(self):
          self.strategies = [
              PDFPlumberStrategy(),  # Best for digital PDFs
              CamelotStrategy(),     # Complex tables
              OCRTableStrategy()     # Scanned documents
          ]

  Day 3: Third Bank Template

  - Analyze Wells Fargo or Chase PDF structure
  - Create templates/form_specs/wells_fargo_v1.json
  - Test with existing extractors

  Day 4-5: Export Functionality

  # src/template_extraction/exporters/excel_exporter.py
  class ExcelExporter:
      def export(self, extraction_results, template="default"):
          # Create formatted Excel with:
          # - Summary sheet
          # - Detail sheets per document
          # - Formulas for totals

  ---
  4. Phase 3 README Documentation

  # Phase 3: Table Extraction & Export Implementation

  ## Overview
  Phase 3 adds table extraction capabilities, a third bank template, and export functionality to enable production
  use of extracted data.

  ## Goals
  - Extract structured data from financial tables
  - Support 3+ partner banks
  - Export to Excel/CSV for business workflows
  - Maintain <2 second processing time

  ## Implementation Schedule

  ### Days 1-2: Table Extraction Engine
  - [ ] Create `src/template_extraction/extractors/table.py`
  - [ ] Implement PDFPlumber strategy for digital PDFs
  - [ ] Add Camelot strategy for complex tables
  - [ ] Create table field type in models
  - [ ] Update orchestrator to include TableExtractor
  - [ ] Test with debt schedule tables

  ### Day 3: Third Bank Template
  - [ ] Analyze Wells Fargo/Chase PDF structure
  - [ ] Create template specification (30+ fields)
  - [ ] Test extraction with all extractors
  - [ ] Validate multi-bank support

  ### Day 4: Excel Export
  - [ ] Create `src/template_extraction/exporters/excel_exporter.py`
  - [ ] Implement formatted Excel output
  - [ ] Add summary and detail sheets
  - [ ] Include formulas and totals

  ### Day 5: CSV Export & Testing
  - [ ] Create `src/template_extraction/exporters/csv_exporter.py`
  - [ ] Add batch export capabilities
  - [ ] Performance testing with 100+ documents
  - [ ] Documentation updates

  ## Success Metrics
  - Table extraction accuracy > 85%
  - Support for 5+ table formats
  - 3 banks fully supported
  - Export to Excel/CSV working
  - Processing time < 2 seconds

  ## Testing Strategy
  1. Unit tests for each extractor strategy
  2. Integration tests for table extraction
  3. End-to-end tests with real bank documents
  4. Performance benchmarks

  ## Dependencies
  ```bash
  pip install camelot-py[cv]  # For table extraction
  pip install openpyxl        # For Excel export
  pip install xlsxwriter      # Alternative Excel library

  File Structure

  src/template_extraction/
  ├── extractors/
  │   └── table.py           # NEW: Table extraction
  ├── parsers/               # NEW: Financial parsers
  │   ├── __init__.py
  │   ├── balance_sheet.py
  │   └── debt_schedule.py
  ├── exporters/             # NEW: Export functionality
  │   ├── __init__.py
  │   ├── excel_exporter.py
  │   └── csv_exporter.py
  templates/form_specs/
  └── wells_fargo_v1.json   # NEW: Third bank template

  Key Risks & Mitigations

  - Table complexity: Use multiple strategies with fallback
  - Performance impact: Cache extracted tables
  - Export formatting: Use templates for consistent output

  Next Steps After Phase 3

  - Phase 4: LLM enhancement for ambiguous fields
  - Phase 5: Production optimization
  - Phase 6: All 9-15 forms supported

  ---

  ## 5. Next Steps Checklist

  1. **Create Phase 3 branch**
     ```bash
     git checkout -b phase-3-table-extraction

  2. Install dependencies
  pip install camelot-py[cv] openpyxl xlsxwriter
  3. Start with table extractor
    - Create src/template_extraction/extractors/table.py
    - Implement PDFPlumber strategy first
    - Test with sample debt schedule
  4. Document progress
    - Update PHASE_3_SUMMARY.md daily
    - Track metrics in test results
  5. Validate with stakeholders
    - Demo table extraction early
    - Get feedback on Excel format
    - Confirm third bank choice