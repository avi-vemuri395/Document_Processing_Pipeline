#!/usr/bin/env python3
"""
Test script to trace PDF generation flow step-by-step.
This demonstrates the complete data flow from master JSON to filled PDF.
"""

import json
from pathlib import Path
from datetime import datetime

# Import PDF generation components
from src.extraction_methods.multimodal_llm.providers.pdf_form_generator import PDFFormGenerator, AcroFormFiller


def trace_pdf_generation():
    """Trace the PDF generation flow with sample data."""
    
    print("\n" + "="*80)
    print("  PDF GENERATION FLOW TRACE")
    print("  Tracking data flow from master JSON to filled PDF")
    print("="*80)
    
    # Step 1: Sample master data (simulating what comes from Part 1)
    sample_master_data = {
        "Name": "John Doe",
        "Social Security Number": "123-45-6789",
        "Mobile Telephone Number": "(555) 123-4567",
        "Email address": "john.doe@example.com",
        "Business Applicant Name": "Doe Enterprises LLC",
        "EIN": "12-3456789",
        "Total Assets": "4397552",
        "Total Liabilities": "2044663",
        "Net Worth (Total Assets minus Total Liabilities)": "2352889",
        "Married": True,
        "Unmarried": False,
        "US Citizen": True,
        "What percentage of the applicant business dowill you own": "100"
    }
    
    print("\n📊 STEP 1: Master Data (from Part 1)")
    print(f"  Fields: {len(sample_master_data)}")
    for key, value in list(sample_master_data.items())[:5]:
        print(f"    • {key}: {value}")
    print(f"    ... and {len(sample_master_data) - 5} more fields")
    
    # Step 2: Initialize PDF Generator
    print("\n🔧 STEP 2: Initialize PDF Generator")
    generator = PDFFormGenerator()
    print(f"  PDF Library: {generator.filler.pdf_library}")
    print(f"  Mappings Directory: {generator.mappings_dir}")
    
    # Step 3: Demonstrate mapping loading
    print("\n📋 STEP 3: Load Field Mappings")
    template_name = "Live Oak Express - Application Forms"
    template_path = Path("templates/Live Oak Express - Application Forms.pdf")
    mapping_base = generator.mappings_dir / template_name
    
    print(f"  Template: {template_path.name}")
    print(f"  Looking for mappings at: {mapping_base}")
    
    # Check what mapping files exist
    mapping_files = [
        Path(str(mapping_base) + "_mapping.json"),
        Path(str(mapping_base) + "_dynamic.json"),
        mapping_base.parent / f"{mapping_base.name}_mapping.json",
        mapping_base.parent / f"{mapping_base.name}_dynamic.json"
    ]
    
    for mapping_file in mapping_files:
        if mapping_file.exists():
            print(f"    ✅ Found: {mapping_file.name}")
            # Load and show sample mappings
            with open(mapping_file, 'r') as f:
                mapping_data = json.load(f)
                if 'mappings' in mapping_data:
                    sample_mappings = list(mapping_data['mappings'].items())[:3]
                    print(f"      Sample mappings:")
                    for pdf_field, info in sample_mappings:
                        print(f"        {pdf_field} → {info.get('source_field', 'N/A')}")
                elif 'fields' in mapping_data:
                    print(f"      Dynamic fields: {len(mapping_data['fields'])}")
        else:
            print(f"    ❌ Not found: {mapping_file.name}")
    
    # Step 4: Demonstrate field mapping transformation
    print("\n🔄 STEP 4: Field Mapping Transformation")
    filler = AcroFormFiller()
    filler.load_mapping(mapping_base)
    
    if filler.mapping is None:
        print("  Mode: Direct pass-through (no mapping file)")
        print("  Field names will be used as-is")
    elif filler.mapping:
        print(f"  Mode: Explicit mapping ({len(filler.mapping)} mappings)")
        print("  Sample transformations:")
        for pdf_field, mapping_info in list(filler.mapping.items())[:3]:
            source = mapping_info.get('source_field', 'N/A')
            field_type = mapping_info.get('type', 'text')
            print(f"    • {source} → {pdf_field} (type: {field_type})")
    else:
        print("  Mode: Pattern matching fallback")
    
    # Step 5: Show data transformation
    print("\n📝 STEP 5: Data Transformation for PDF")
    mapped_data = filler._map_data_to_fields(sample_master_data)
    print(f"  Input fields: {len(sample_master_data)}")
    print(f"  Output fields: {len(mapped_data)}")
    
    # Show checkbox handling
    checkbox_fields = {k: v for k, v in mapped_data.items() 
                      if isinstance(v, bool) or v in ['Yes', 'No', 'Off', 'On', True, False]}
    if checkbox_fields:
        print(f"  Checkbox fields ({len(checkbox_fields)}):")
        for field, value in checkbox_fields.items():
            print(f"    • {field}: {value}")
    
    # Step 6: Library-specific handling
    print("\n📚 STEP 6: Library-Specific Handling")
    print(f"  Using: {filler.pdf_library}")
    
    if filler.pdf_library == "PyPDFForm":
        print("  PyPDFForm specifics:")
        print("    • Filters out False checkbox values")
        print("    • Converts string booleans to actual booleans")
        filtered_count = len([k for k, v in sample_master_data.items() 
                             if isinstance(v, bool) and not v])
        print(f"    • Would remove {filtered_count} false checkboxes")
    elif filler.pdf_library in ["pypdf", "PyPDF2"]:
        print("  pypdf/PyPDF2 specifics:")
        print("    • Uses _update_checkboxes() for checkbox states")
        print("    • Discovers valid states from PDF appearance dictionary")
        print("    • Common states: /Yes, /No, /Off, /On")
    
    # Step 7: Output generation
    print("\n💾 STEP 7: Output Generation")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("outputs/filled_pdfs")
    output_file = output_dir / f"{template_path.stem}_filled_{timestamp}.pdf"
    print(f"  Output path: {output_file}")
    print(f"  Flatten: False (keeps form editable)")
    
    print("\n" + "="*80)
    print("  FLOW SUMMARY")
    print("="*80)
    print("""
  1. Master JSON (Part 1) → FormMappingService
  2. FormMappingService → PDFFormGenerator.generate_filled_pdf()
  3. PDFFormGenerator → AcroFormFiller.load_mapping()
  4. AcroFormFiller._map_data_to_fields() → Transform data
  5. AcroFormFiller.fill_pdf() → Choose library
  6. Library-specific filling (PyPDFForm/pypdf/fillpdf)
  7. Save filled PDF to outputs/filled_pdfs/
  
  Key Features:
  • 3 mapping strategies: explicit, direct, pattern-matching
  • Special checkbox handling with state discovery
  • Multi-library support with graceful fallback
  • Preserves form editability by default
  """)


if __name__ == "__main__":
    trace_pdf_generation()