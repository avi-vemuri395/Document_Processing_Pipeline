# DocAI Test Suite

This folder contains tests specifically for Google Document AI extraction capabilities.

## Test Files

### 1. `test_docai_only_extraction.py`
- Tests DocAI extraction without Claude Vision fallback
- Processes 6 small PDFs (< 1.5MB each)
- Saves individual results and combined data
- Best for testing pure DocAI capabilities

### 2. `test_comprehensive_docai_extraction.py`
- Comprehensive test with verbose output
- Processes 6 diverse PDF types
- Saves incremental merges after each document
- Shows detailed extraction metrics
- May timeout for large documents

### 3. `test_fast_docai_fix.py`
- Quick test with 2 PDFs and 1 Excel file (in parent directory)
- Tests DocAI structure processing
- Verifies metadata preservation

## Running Tests

### Individual Tests
```bash
# Quick test (1 minute)
python3 test_fast_docai_fix.py

# DocAI-only test (2 minutes)
python3 tests/docai/test_docai_only_extraction.py

# Comprehensive test (5+ minutes)
python3 tests/docai/test_comprehensive_docai_extraction.py
```

### Run All Tests
```bash
# Run complete test suite with timeouts
./tests/docai/run_docai_tests.sh
```

## Output Structure

Tests save results to `outputs/test_results/docai_tests/`:

```
docai_tests/
├── {test_id}/
│   ├── incremental_merges/     # Document-by-document results
│   │   ├── merge_01_*.json
│   │   ├── merge_02_*.json
│   │   └── ...
│   ├── master_data_final.json  # Final merged data
│   ├── test_summary.json       # Test statistics
│   └── analysis_report.md      # Human-readable report
└── *.log                        # Test execution logs
```

## Key Findings

### DocAI Limitations
- **15-page limit** for non-allowlisted projects
- **File size indicator**: Files > 1.5MB likely exceed page limit
- **Best performance**: Structured forms and financial documents

### Success Rates
- Small PDFs (< 1.5MB): ~90% success
- Large PDFs (> 1.5MB): Falls back to Claude Vision
- Form extraction confidence: 75-85%

### Optimal Document Types for DocAI
1. Personal Financial Statements
2. Tax Returns (if under 15 pages)
3. Organization Charts
4. Management Bios
5. Simple forms and structured documents

## Cost Comparison

| Method | Cost | Speed | Accuracy |
|--------|------|-------|----------|
| DocAI Form Parser | $30/1000 pages | 5-10s/doc | 75-85% confidence |
| Claude Vision | ~$0.01-0.02/doc | 30-60s/doc | 85-97% accuracy |
| Hybrid Excel | $0 | <1s/doc | 100% numeric accuracy |

## Recommendations

1. **Use DocAI for**: Structured forms under 15 pages
2. **Use Claude Vision for**: Complex or large documents
3. **Use Hybrid Excel for**: Spreadsheet data extraction
4. **Implement page counting**: Pre-check PDFs before routing to DocAI
5. **Consider PDF splitting**: For documents over 15 pages