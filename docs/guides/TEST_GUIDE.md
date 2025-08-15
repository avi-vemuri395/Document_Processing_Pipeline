# Testing Guide

## Overview

This guide covers the testing strategy for the Document Processing Pipeline's two-part architecture. Tests validate both the extraction phase (Part 1) and the form generation phase (Part 2).

## Quick Start

```bash
# Verify environment setup
python3 check_env.py

# Run the comprehensive test suite
python3 run_comprehensive_test.py

# Run individual test for debugging
python3 test_two_part_pipeline.py
```

## Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TEST HIERARCHY                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Comprehensive Tests (Full Pipeline)                         │
│  ├── test_comprehensive_end_to_end.py  [4 phases]            │
│  └── run_comprehensive_test.py         [Runner script]       │
│                                                               │
│  Integration Tests (Component Groups)                        │
│  ├── test_two_part_pipeline.py         [Core architecture]   │
│  ├── test_incremental_processing.py    [Document merging]    │
│  └── test_spreadsheet_population.py    [Excel generation]    │
│                                                               │
│  Component Tests (Individual Features)                       │
│  ├── test_template_extraction.py       [Extraction logic]    │
│  ├── test_dynamic_mapping.py           [Form field mapping]  │
│  └── test_form_filling_simple.py       [PDF generation]      │
│                                                               │
│  Legacy Tests (Original Implementation)                      │
│  ├── test_focused_end_to_end.py        [2 docs, reliable]    │
│  └── test_optimized_end_to_end.py      [5 docs, max coverage]│
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Core Test Files

### 1. test_comprehensive_end_to_end.py

**Purpose**: Validates the entire pipeline with incremental document processing

**Test Phases**:
```python
# Phase 1: Initial Processing (Day 1)
- Process 2 documents (PFS, Tax Return)
- Create initial master JSON
- Verify data extraction

# Phase 2: Incremental Addition (Day 3)
- Add 2 more documents
- Verify merge logic
- Check conflict resolution

# Phase 3: Final Documents (Day 5)
- Add remaining documents
- Complete master JSON
- Validate all data present

# Phase 4: Form Generation
- Generate forms for all banks
- Create spreadsheets
- Verify all outputs
```

**Expected Outputs**:
- Master JSON with all extracted data
- 7 PDFs (Live Oak: 3, Huntington: 4)
- 2 JSON files (Wells Fargo forms)
- 2 Excel spreadsheets
- Extraction logs

**Run Command**:
```bash
python3 test_comprehensive_end_to_end.py
```

### 2. test_two_part_pipeline.py

**Purpose**: Tests the core two-part architecture

**Test Coverage**:
- Document extraction (Part 1)
- Master JSON creation
- Form mapping (Part 2a)
- Multi-bank generation
- Error handling

**Key Assertions**:
```python
# Verify extraction happens once
assert extraction_count == 1

# Verify all forms generated
assert len(results['generated_forms']) == 9

# Verify master JSON structure
assert 'applicant_info' in master_data
assert 'financial_info' in master_data
```

**Run Command**:
```bash
python3 test_two_part_pipeline.py
```

### 3. test_incremental_processing.py

**Purpose**: Tests document merging and incremental updates

**Test Scenarios**:
- Add documents over multiple sessions
- Update existing fields
- Merge arrays (debts, assets)
- Conflict resolution (last wins)
- Version tracking

**Example Test Case**:
```python
async def test_merge_strategy():
    # Day 1: Initial PFS
    processor.process_document(pfs_doc, app_id)
    
    # Day 3: Updated PFS (should override)
    processor.process_document(updated_pfs, app_id)
    
    # Verify last document wins
    assert master['net_worth'] == updated_value
```

**Run Command**:
```bash
python3 test_incremental_processing.py
```

### 4. test_spreadsheet_population.py

**Purpose**: Tests Excel template population

**Test Coverage**:
- Debt Schedule generation
- Use of Funds template
- Formula preservation
- Multi-sheet handling
- Data validation

**Validation Points**:
```python
# Load generated Excel
wb = openpyxl.load_workbook(debt_schedule_path)
ws = wb.active

# Verify data populated
assert ws['D2'].value == applicant_name
assert ws['B6'].value == debt_description
assert ws['C6'].value == debt_amount

# Verify formulas intact
assert ws['C20'].value.startswith('=SUM')
```

**Run Command**:
```bash
python3 test_spreadsheet_population.py
```

## Test Data

### Primary Test Documents

Location: `inputs/real/Brigham_dallas/`

**Key Files**:
- `Brigham_Dallas_PFS.pdf` - Personal Financial Statement
- `Brigham_Dallas_2023_PTR.pdf` - 2023 Tax Return
- `Brigham_Dallas_2022_PTR.pdf` - 2022 Tax Return
- `Brigham_Business_3in1_CR.pdf` - Business Credit Report

**Expected Values**:
```python
EXPECTED_VALUES = {
    'total_assets': 4397552,
    'total_liabilities': 2044663,
    'net_worth': 2352889,
    'ssn_suffix': '3074',
    'business_type': 'LLC'
}
```

### Alternative Test Data

Location: `inputs/real/Hello_sugar/`

Used when Brigham documents unavailable:
- `hello_sugar_2022_tax_return.pdf`
- `hello_sugar_brigham_PFS.pdf`
- `hello_sugar_business_credit_report.pdf`

## Running Tests

### Full Test Suite

```bash
# Run all pipeline tests
python3 run_comprehensive_test.py

# Expected output:
# ✅ Environment check passed
# ✅ Two-part pipeline test passed
# ✅ Incremental processing test passed
# ✅ Spreadsheet population test passed
# ✅ Comprehensive end-to-end test passed
```

### Individual Tests

```bash
# Test specific component
python3 test_two_part_pipeline.py

# Test with verbose output
python3 test_comprehensive_end_to_end.py --verbose

# Test with specific documents
python3 test_incremental_processing.py --docs "PFS,2023_PTR"
```

### Debug Mode

```bash
# Enable debug logging
export DEBUG=true
python3 test_comprehensive_end_to_end.py

# Save intermediate outputs
export SAVE_INTERMEDIATE=true
python3 test_two_part_pipeline.py
```

## Test Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-xxx

# Optional
USE_FILES_API=true           # Use Files API for large documents
MAX_RETRIES=3                # API retry attempts
SAVE_INTERMEDIATE=true       # Keep intermediate files
DEBUG=true                   # Enable debug logging
```

### Test Parameters

Edit test files to adjust:
```python
# Document selection
TEST_DOCS = ['PFS', '2023_PTR']  # Subset of documents

# Bank selection  
TARGET_BANKS = ['live_oak']      # Test specific banks

# Spreadsheet generation
GENERATE_SPREADSHEETS = False    # Skip Excel generation

# API usage
USE_CACHED_EXTRACTION = True     # Use cached results
```

## Validation Strategies

### 1. Data Accuracy

```python
def validate_extraction(master_data):
    # Check required fields present
    assert master_data.get('applicant_info', {}).get('ssn')
    assert master_data.get('financial_info', {}).get('net_worth')
    
    # Validate data types
    assert isinstance(master_data['financial_info']['assets']['total'], (int, float))
    
    # Check business logic
    assets = master_data['financial_info']['assets']['total']
    liabilities = master_data['financial_info']['liabilities']['total']
    net_worth = master_data['financial_info']['net_worth']
    assert abs(net_worth - (assets - liabilities)) < 100  # Allow small rounding
```

### 2. Form Completeness

```python
def validate_form_generation(results):
    # Check all expected forms generated
    for bank in ['live_oak', 'huntington']:
        assert bank in results['generated_forms']
        
    # Verify PDF files exist and have content
    for form_path in results['generated_forms']['live_oak'].values():
        if form_path.endswith('.pdf'):
            assert Path(form_path).exists()
            assert Path(form_path).stat().st_size > 100000  # >100KB
```

### 3. Performance Metrics

```python
def validate_performance(metrics):
    # Check processing time
    assert metrics['total_time'] < 60  # Under 1 minute
    
    # Verify API usage
    assert metrics['api_calls'] < 10   # Efficient extraction
    assert metrics['api_cost'] < 0.10  # Under $0.10
    
    # Check success rate
    assert metrics['success_rate'] > 0.85  # 85%+ accuracy
```

## Common Issues & Solutions

### Issue 1: API Rate Limits

**Symptom**: `413 Request Entity Too Large` errors

**Solution**:
```python
# Reduce document batch size
TEST_DOCS = TEST_DOCS[:2]  # Process only 2 documents

# Add delays between API calls
import time
time.sleep(2)  # 2 second delay
```

### Issue 2: Missing Test Data

**Symptom**: `FileNotFoundError` for test documents

**Solution**:
```python
# Use available documents dynamically
available_docs = [f for f in TEST_DOCS if Path(f).exists()]
if not available_docs:
    available_docs = find_alternative_docs()
```

### Issue 3: Form Template Not Found

**Symptom**: `Template not found` warnings

**Solution**:
```python
# Verify templates exist
template_dir = Path("templates/forms")
assert template_dir.exists()

# Download missing templates
download_form_templates()
```

### Issue 4: Extraction Failures

**Symptom**: Empty or incomplete master JSON

**Solution**:
```python
# Enable debug mode
extractor = BenchmarkExtractor(debug=True)

# Check document quality
verify_document_quality(doc_path)

# Use fallback extraction
if not extraction_result:
    extraction_result = fallback_extraction(doc_path)
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Test Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.13'
          
      - name: Install dependencies
        run: |
          pip install -r requirements-minimal.txt
          brew install poppler
          
      - name: Run tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python3 check_env.py
          python3 run_comprehensive_test.py
```

### Local Pre-commit

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running pipeline tests..."
python3 test_two_part_pipeline.py

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
```

## Performance Benchmarks

### Expected Timings

| Test | Documents | Time | API Cost |
|------|-----------|------|----------|
| test_two_part_pipeline | 2 | ~20s | $0.02 |
| test_incremental_processing | 4 | ~35s | $0.04 |
| test_spreadsheet_population | N/A | ~5s | $0.00 |
| test_comprehensive_end_to_end | 5-6 | ~50s | $0.07 |

### Optimization Tips

1. **Cache Extractions**: Save extraction results for re-use
2. **Parallel Processing**: Process banks concurrently
3. **Batch API Calls**: Group documents for single extraction
4. **Skip Unchanged**: Don't re-process unchanged documents

## Test Coverage Report

```bash
# Generate coverage report
coverage run -m pytest tests/
coverage report

# Expected coverage
src/template_extraction/comprehensive_processor.py    95%
src/template_extraction/form_mapping_service.py       92%
src/template_extraction/spreadsheet_mapping_service.py 88%
src/template_extraction/pipeline_orchestrator.py      90%
```

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# In test
logger = logging.getLogger(__name__)
logger.debug(f"Master JSON: {json.dumps(master_data, indent=2)}")
```

### Save Intermediate Files

```python
# Save extraction results
with open('debug_extraction.json', 'w') as f:
    json.dump(extraction_result, f, indent=2)

# Save master JSON at each step
processor.save_debug_snapshot(step_name)
```

### Trace API Calls

```python
# Monkey-patch to log API calls
original_extract = extractor.extract
def logged_extract(*args, **kwargs):
    logger.info(f"API Call: {args}")
    result = original_extract(*args, **kwargs)
    logger.info(f"API Response: {len(result)} bytes")
    return result
extractor.extract = logged_extract
```

## Next Steps

After tests pass:

1. **Review Outputs**: Check generated PDFs and spreadsheets
2. **Validate Accuracy**: Compare with expected values
3. **Performance Analysis**: Review API usage and costs
4. **Deploy Changes**: Push to production after validation
5. **Monitor Production**: Track success rates and errors