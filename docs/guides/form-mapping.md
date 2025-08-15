# Form Field Mapping Guide

## Overview

The system supports three methods for extracting form fields from PDF forms, ensuring it works with ANY PDF form without requiring pre-configuration.

## Field Extraction Methods

### 1. Static Mapping (Fastest)
Pre-generated JSON files in `outputs/form_mappings/` containing all field names and metadata.

**When to use**: When you have commonly used forms that don't change.

**How it was created**:
```bash
python3 analyze_pdf_fields.py
```

This script uses `pdfplumber` to extract field metadata directly from the PDF's internal structure.

### 2. Dynamic Extraction (Automatic)
The `DynamicFormMapper` class extracts fields on-the-fly from any PDF.

**When to use**: For new forms or when static mapping doesn't exist.

**How it works**:
```python
from src.extraction_methods.multimodal_llm.providers import DynamicFormMapper

mapper = DynamicFormMapper()
form_structure = mapper.get_form_fields("path/to/any/form.pdf")
# Returns dict with all field names, types, and sections
```

### 3. Fallback Common Fields
If both methods fail, the system uses a set of common loan application fields.

**When used**: PDF has no extractable fields or pdfplumber isn't available.

## Hierarchy of Field Discovery

```
1. Check for static mapping JSON
   ↓ (if not found)
2. Try dynamic extraction with pdfplumber
   ↓ (if fails)
3. Use common fields fallback
```

## Adding Support for New Forms

### Option 1: Generate Static Mapping (Recommended for frequently used forms)

```python
# Run the analyzer to create a mapping
python3 analyze_pdf_fields.py

# Or programmatically:
from analyze_pdf_fields import analyze_pdf_form_fields, create_field_mapping_template

analysis = analyze_pdf_form_fields("path/to/new/form.pdf")
mapping = create_field_mapping_template(analysis)

# Save to outputs/form_mappings/
```

### Option 2: Use Dynamic Extraction (No setup needed)

The system automatically extracts fields when processing a new form:

```python
from src.extraction_methods.multimodal_llm.providers import LLMFormFiller

filler = LLMFormFiller()
# Automatically uses DynamicFormMapper if no static mapping exists
form_structure = await filler._read_form_template("path/to/new/form.pdf")
```

## Field Types Supported

- **Text Fields** (`/'Tx`): Regular text input
- **Checkboxes** (`/'Btn`): Yes/No, True/False
- **Dropdowns** (`/'Ch`): Selection from options
- **Signatures** (`/'Sig`): Signature fields
- **Dates**: Text fields with "date" in the name

## Performance Comparison

| Method | Speed | Fields Found | Setup Required |
|--------|-------|--------------|----------------|
| Static Mapping | < 0.1s | All (203+) | Yes (one-time) |
| Dynamic Extraction | ~1s | All (203+) | No |
| Fallback | < 0.01s | ~25 common | No |

## Caching

Dynamic extraction results are cached in two ways:
1. **Memory cache**: For the current session
2. **File cache**: In `outputs/form_mappings/*_dynamic.json`

Cache invalidates when the PDF file changes (based on modification time and size).

## Example: Complete Workflow

```python
import asyncio
from pathlib import Path
from src.extraction_methods.multimodal_llm.providers import (
    LLMFormFiller,
    PDFFormGenerator
)

async def process_any_form(documents_folder, pdf_form_path):
    """Works with ANY PDF form - no setup needed."""
    
    # 1. Extract data from documents
    filler = LLMFormFiller()
    extracted_data = await filler.extractor.extract_all(documents_folder)
    
    # 2. Get form fields (static, dynamic, or fallback)
    form_structure = await filler._read_form_template(pdf_form_path)
    print(f"Found {len(form_structure['fields'])} fields")
    
    # 3. Map data to fields using LLM
    filled_form = await filler._fill_form_with_llm(form_structure, extracted_data)
    
    # 4. Generate filled PDF
    generator = PDFFormGenerator()
    pdf_path = generator.generate_filled_pdf(
        "output_name",
        filled_form['filled_fields'],
        "outputs/filled_pdfs"
    )
    
    return pdf_path

# Run it
asyncio.run(process_any_form(
    "inputs/real/Brigham_dallas",
    "templates/Any_New_Form.pdf"
))
```

## Troubleshooting

### "No fields found in PDF"
- The PDF might not be a fillable form (just a static PDF)
- Try opening in Adobe Acrobat to verify it has fillable fields

### "pdfplumber not available"
- Install with: `pip install pdfplumber`
- System will fall back to common fields if not available

### "Field names don't match data"
- The LLM handles intelligent mapping between extracted data and form fields
- Check the confidence scores in the output JSON

## Dependencies

- **Required**: `anthropic` (for LLM extraction and mapping)
- **Recommended**: `pdfplumber` (for dynamic field extraction)
- **For PDF filling**: `pypdf` or `PyPDFForm`

## Key Benefits

1. **Universal Compatibility**: Works with ANY PDF form
2. **No Manual Setup**: Dynamic extraction requires no configuration
3. **Intelligent Mapping**: LLM maps data to fields regardless of naming differences
4. **Performance**: Caching ensures fast repeated processing
5. **Graceful Degradation**: Multiple fallback options ensure it always works