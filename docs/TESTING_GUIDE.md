# Testing Guide - Document Processing Pipeline

## Overview

This guide documents all available tests, their purposes, and when to use each one. The testing infrastructure follows a 3-tier strategy for different use cases.

---

## Test Categories

### 🚀 Quick Tests (<30 seconds)

#### **test_multi_document_subset.py** ✨ NEW
- **Purpose**: Balanced subset testing with diverse document types
- **Documents**: 2 PDFs + 2 Excel files
- **Runtime**: ~25 seconds
- **Output**: `outputs/test_tracking/{timestamp}/multi_document_subset/`
- **Use When**: Development iterations, pre-commit checks
```bash
python3 test_multi_document_subset.py
```

#### **test_fast_docai_fix.py**
- **Purpose**: Quick DocAI validation
- **Documents**: 2 PDFs + 1 Excel (small files)
- **Runtime**: ~15 seconds
- **Output**: `outputs/test_results/{test_id}/`
- **Use When**: Testing DocAI functionality
```bash
python3 test_fast_docai_fix.py
```

#### **test_fusion_validation.py**
- **Purpose**: Validate fusion components
- **Documents**: None (uses mock data)
- **Runtime**: <5 seconds
- **Output**: Console only
- **Use When**: Testing fusion system
```bash
python3 test_fusion_validation.py
```

#### **tests/feature/schema_driven/test_schema_comparison.py**
- **Purpose**: Compare schema-driven vs string-matching approaches
- **Documents**: Uses existing master data from comprehensive test
- **Runtime**: ~20 seconds
- **Output**: Detailed comparison report with ROI analysis
- **Use When**: Validating schema-driven improvements
- **Key Metrics**: Field coverage improvement, semantic accuracy, cost analysis
- **NEW Features Tested**: 
  - DocAI confidence preservation
  - Business rules validation
  - Critical field coverage
```bash
python3 tests/feature/schema_driven/test_schema_comparison.py
```

---

### 🔄 Integration Tests (1-2 minutes)

#### **test_fusion_real_documents.py**
- **Purpose**: Test multimodal fusion with real documents
- **Documents**: 1 PDF (first available)
- **Runtime**: ~45 seconds
- **Output**: In-memory (no file output)
- **Use When**: Validating fusion improvements
```bash
ENABLE_FUSION=true python3 test_fusion_real_documents.py
```

#### **tests/pipeline/test_two_part_pipeline.py**
- **Purpose**: Validate two-part architecture
- **Documents**: 2 PDFs from Brigham_dallas
- **Runtime**: ~60 seconds
- **Output**: `outputs/applications/{app_id}/`
- **Use When**: Testing pipeline architecture
```bash
python3 tests/pipeline/test_two_part_pipeline.py
```

---

### 📊 Comprehensive Tests (5+ minutes)

#### **tests/integration/test_comprehensive_end_to_end.py**
- **Purpose**: Full pipeline validation with all components
- **Documents**: All 19 files from Brigham_dallas
- **Runtime**: 5-10 minutes
- **Output**: `outputs/applications/{app_id}/`
- **Use When**: CI/CD, major changes, release validation
- **NEW Validations**:
  - DocAI field-level confidence preservation
  - Business rules validation (SSN, EIN, financial calculations)
  - Critical field coverage per bank form
  - Enhanced confidence aggregation
  - Self-consistency scoring (when enabled)
```bash
PYTHONPATH=. python3 tests/integration/test_comprehensive_end_to_end.py
```

---

## Data Quality Features (NEW)

### Validation Components Testing

#### **Business Rules Validation**
- Automatically integrated in `ComprehensiveProcessor`
- Zero additional API cost
- Tests SSN/EIN formats, financial calculations
- Run any extraction test to validate

#### **DocAI Confidence Preservation**
- Automatically captures field-level confidence from Document AI
- No configuration needed
- Validated in `test_comprehensive_end_to_end.py`
- Check extraction JSON for confidence scores

#### **Self-Consistency Scoring** (Optional)
- Enable with environment variable:
```bash
ENABLE_SELF_CONSISTENCY=true python3 test_comprehensive_end_to_end.py
```
- Runs 3 samples at temperature 0.7
- 40% hallucination reduction (research-backed)

#### **Critical Field Validation**
- Integrated in `FormMappingService`
- Bank-specific thresholds (70-95%)
- Check form JSON output for quality gates

---

## Output Locations

### Standard Output Structure
```
outputs/
├── test_tracking/              # NEW: Standardized test results
│   └── {timestamp}/
│       └── {test_name}/
│           ├── metrics.json    # Performance metrics
│           ├── summary.txt     # Human-readable summary
│           ├── extracted_data/ # Document extractions
│           └── master_data.json # Combined data
├── applications/               # Full pipeline outputs
│   └── {app_id}/
│       ├── part1_document_processing/
│       │   ├── master_data.json
│       │   └── extractions/
│       └── part2_form_mapping/
│           └── banks/
├── test_results/              # Legacy test outputs
└── form_mappings/             # Cached form field mappings
```

---

## Document Types Tested

### Available Test Data
- **PDFs (63 total)**:
  - Tax Returns: 2022-2024 (3 files, 5-8MB each)
  - Personal Financial Statements (1 file, 0.5MB)
  - Business Documents (multiple)
  - Organization Charts
  - Bank Forms

- **Excel Files (10 total)**:
  - Financial Statements (P&L, Balance Sheet)
  - Aging Reports (AR/AP)
  - ~10-30KB each

### Document Coverage by Test

| Test | PDFs | Excel | Tax Returns | PFS | Financial Statements |
|------|------|-------|-------------|-----|---------------------|
| multi_document_subset | 2 | 2 | ✅ | ✅ | ✅ |
| fast_docai_fix | 2 | 1 | ❌ | ✅ | ✅ |
| comprehensive_end_to_end | 15+ | 4 | ✅ | ✅ | ✅ |

---

## Test Comparison

### Comparing Test Runs

The new `TestResultManager` enables comparison between test runs:

```bash
# Run test and note output directory
python3 test_multi_document_subset.py
# Output: outputs/test_tracking/20250120_123456/multi_document_subset/

# Run again after changes
python3 test_multi_document_subset.py
# Output: outputs/test_tracking/20250120_134512/multi_document_subset/

# Compare results
python3 test_multi_document_subset.py compare \
  outputs/test_tracking/20250120_123456/multi_document_subset \
  outputs/test_tracking/20250120_134512/multi_document_subset
```

### Metrics Tracked

Each test run captures:
- **Document metrics**: Processing time, field count, extraction method
- **Performance metrics**: Total time, average fields/doc
- **Fusion metrics**: Quality scores, strategy used
- **Error tracking**: Failed documents and reasons

---

## Configuration

### Enabling Features

```bash
# Enable fusion
export ENABLE_FUSION=true
export FUSION_MODE=adaptive

# Enable DocAI diagnostics
export DOCAI_ENABLE_DIAGNOSTICS=true

# Set processing limits
export MAX_PAGES_PER_DOCUMENT=15
```

### API Requirements

Tests that use APIs:
- **DocAI Tests**: Require Google Cloud credentials
- **Vision Tests**: Require Anthropic API key
- **Fusion Tests**: May use both APIs

---

## Test Selection Guide

### When to Use Each Test

**During Development:**
```bash
# Quick validation after code changes
python3 test_multi_document_subset.py

# Test specific component
python3 test_fusion_validation.py
```

**Before Committing:**
```bash
# Run subset test for good coverage
python3 test_multi_document_subset.py

# If working on fusion
ENABLE_FUSION=true python3 test_fusion_real_documents.py
```

**CI/CD Pipeline:**
```bash
# Full validation
PYTHONPATH=. python3 tests/integration/test_comprehensive_end_to_end.py
```

**Debugging Issues:**
```bash
# Test with specific documents
python3 test_fast_docai_fix.py

# Compare before/after
python3 test_multi_document_subset.py compare {dir1} {dir2}
```

---

## Performance Benchmarks

### Expected Runtimes

| Test | Target | Typical | Max Acceptable |
|------|--------|---------|----------------|
| multi_document_subset | <30s | 25s | 45s |
| fast_docai_fix | <20s | 15s | 30s |
| fusion_validation | <5s | 2s | 10s |
| comprehensive_end_to_end | <10min | 7min | 15min |

### Field Extraction Targets

| Document Type | Min Fields | Target | With Fusion |
|--------------|------------|--------|-------------|
| Tax Return | 100 | 150 | 200+ |
| PFS | 200 | 300 | 400+ |
| Excel P&L | 50 | 70 | 80+ |
| Excel Balance Sheet | 30 | 40 | 50+ |

---

## Troubleshooting

### Common Issues

**Test Fails to Find Documents:**
- Ensure `inputs/real/Brigham_dallas/` directory exists
- Check file permissions

**DocAI Failures:**
- Verify Google Cloud credentials
- Check 15-page limit for PDFs
- Ensure processor ID is valid

**Fusion Not Activating:**
- Set `ENABLE_FUSION=true`
- Check fusion components imported successfully
- Verify both DocAI and Vision are available

**Slow Performance:**
- Reduce document count for quick tests
- Use `test_multi_document_subset.py` instead of comprehensive
- Check API rate limits

---

## Adding New Tests

### Creating a Test

1. **Choose appropriate category** (quick/integration/comprehensive)
2. **Use TestResultManager** for output tracking
3. **Follow naming convention**: `test_{purpose}_{scope}.py`
4. **Document in this guide**

### Example Test Structure

```python
from pathlib import Path
from test_multi_document_subset import TestResultManager

async def test_new_feature():
    # Initialize result manager
    result_manager = TestResultManager("new_feature_test")
    
    # Select documents
    test_docs = [
        Path("inputs/real/..."),
        # ...
    ]
    
    # Process documents
    for doc in test_docs:
        result = await process(doc)
        result_manager.log_document_processing(doc, result, time)
    
    # Save results
    output_dir = result_manager.save_results(all_results)
    print(f"Results saved to: {output_dir}")
```

---

## Best Practices

1. **Start with quick tests** during development
2. **Use subset test** before committing
3. **Run comprehensive test** before releases
4. **Track metrics** to identify regressions
5. **Compare runs** after major changes
6. **Document new tests** in this guide

---

## Summary

The testing infrastructure provides comprehensive coverage with appropriate tests for different scenarios:

- **Development**: Use `test_multi_document_subset.py` (25s, good coverage)
- **Pre-commit**: Run subset + component tests (<1 min total)
- **CI/CD**: Use comprehensive test (full validation)
- **Debugging**: Use specific component tests

All tests now support standardized output tracking and comparison capabilities through the `TestResultManager` class.