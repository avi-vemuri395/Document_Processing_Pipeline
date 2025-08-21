# Test Structure Documentation

## Overview
All tests are organized in the `tests/` directory following pytest best practices. Previously, 26 test files were scattered in the root directory. They have now been properly organized into categorical subdirectories.

## Directory Structure

```
tests/
├── unit/                       # Fast, isolated tests (~5 seconds)
│   ├── test_simple_config.py
│   └── test_openai_availability.py
│
├── integration/                # Tests with external services (1-2 minutes)
│   ├── test_comprehensive_end_to_end.py  # PRIMARY: Full pipeline
│   ├── test_batch_processing.py
│   ├── test_multi_document_subset.py
│   └── (7 other integration tests)
│
├── smoke/                      # Quick validation tests (~15 seconds)
│   └── test_fast_docai_fix.py  # PRIMARY: All features quick test
│
├── feature/                    # Feature-specific tests
│   ├── dynamic_extraction/     # Dynamic form extraction (3 files)
│   │   ├── test_dynamic_migration_phase2.py
│   │   ├── test_pdf_generation_validation.py
│   │   └── test_huntington_complexity.py
│   │
│   ├── schema_driven/          # Schema-driven mapping (4 files)
│   │   ├── test_schema_driven_integration.py
│   │   ├── test_schema_driven_validation.py
│   │   ├── test_schema_driven_quick.py
│   │   └── test_schema_comparison.py    # Compare approaches & ROI
│   │
│   └── fusion/                 # Multimodal fusion (3 files)
│       ├── test_fusion_real_documents.py
│       ├── test_fusion_validation.py
│       └── test_fusion_components.py
│
├── performance/                # Performance and quality tests
│   ├── test_processor_investigation.py
│   └── test_general_processor_quality.py
│
├── pipeline/                   # Pipeline component tests
│   ├── test_two_part_pipeline.py
│   ├── test_incremental_processing.py
│   └── test_spreadsheet_population.py
│
├── docai/                      # DocAI specific tests
│   ├── test_comprehensive_docai_extraction.py
│   └── test_docai_only_extraction.py
│
├── analysis/                   # Analysis utilities
│   └── test_pdf_technical_structure.py
│
├── scripts/                    # Test runners
│   ├── run_comprehensive_test.py  # Runs full test suite
│   ├── run_fast_test.py           # Quick validation
│   └── run_chunking_tests.py
│
├── tools/                      # Debug and analysis tools
│   ├── check_env.py            # Environment validation
│   ├── diagnose_docai.py       # DocAI diagnostics
│   ├── analyze_actual_costs.py # API cost analysis
│   ├── analyze_api_costs.py
│   ├── analyze_excel_files.py
│   ├── analyze_repeated_extractions.py
│   └── debug_extraction_analysis.py
│
├── utils/                      # Test utilities
│   └── test_result_manager.py
│
├── fixtures/                   # Test fixtures
├── conftest.py                # Pytest configuration
└── __init__.py
```

## Primary Test Files

### 1. Quick Validation (15 seconds)
**File**: `tests/smoke/test_fast_docai_fix.py`
- Tests all major features quickly
- Part 1: Document extraction with DocAI
- Part 2: Schema-driven form mapping  
- Part 3: Dynamic form extraction
- **Run**: `python3 tests/smoke/test_fast_docai_fix.py`

### 2. Full Pipeline Test (8 minutes)
**File**: `tests/integration/test_comprehensive_end_to_end.py`
- Complete pipeline validation
- Phase 0: DocAI validation
- Phase 1-4: Incremental processing
- Phase 5: Dynamic form extraction
- **Run**: `python3 tests/scripts/run_comprehensive_test.py`

## Running Tests

### By Category
```bash
# Unit tests (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Feature tests
pytest tests/feature/

# Specific feature
pytest tests/feature/schema_driven/
pytest tests/feature/fusion/
pytest tests/feature/dynamic_extraction/

# Smoke tests
pytest tests/smoke/

# Performance tests
pytest tests/performance/
```

### By Speed
```bash
# Fast tests only
pytest -m "not slow"

# All tests
pytest
```

### Using Test Runners
```bash
# Quick validation
python3 tests/scripts/run_fast_test.py

# Full comprehensive test
python3 tests/scripts/run_comprehensive_test.py
```

### Using Tools
```bash
# Check environment
python3 tests/tools/check_env.py

# Diagnose DocAI issues
python3 tests/tools/diagnose_docai.py

# Analyze API costs
python3 tests/tools/analyze_api_costs.py
```

## Test Markers

Tests are marked with pytest markers for easy filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.smoke` - Quick smoke tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.feature` - Feature tests
- `@pytest.mark.docai` - Requires DocAI
- `@pytest.mark.fusion` - Fusion tests
- `@pytest.mark.schema` - Schema-driven tests
- `@pytest.mark.dynamic` - Dynamic extraction tests
- `@pytest.mark.slow` - Tests taking >30 seconds

## Configuration

### pytest.ini
Located at project root, configures:
- Test discovery patterns
- Test paths
- Python path
- Markers
- Output options

### Environment Variables
Key variables for testing:
- `USE_DYNAMIC_FORM_EXTRACTION=true` - Enable dynamic extraction
- `DYNAMIC_FORMS_ENABLED_FOR=live_oak,huntington,wells_fargo`
- `ENABLE_SCHEMA_DRIVEN=true` - Enable schema mapping
- `ENABLE_FUSION=true` - Enable multimodal fusion

## Migration from Root Directory

Previously scattered test files have been organized:
- **26 files moved** from root to appropriate subdirectories
- **0 test files remain in root** - Clean project structure
- **37 total test files** now properly organized
- All imports and paths updated for compatibility

## Best Practices

1. **Add new tests** to appropriate category directory
2. **Use markers** to categorize tests
3. **Keep unit tests fast** (<5 seconds each)
4. **Document test purpose** in docstrings
5. **Use fixtures** from conftest.py
6. **Run smoke tests** before commits
7. **Run full suite** before merges