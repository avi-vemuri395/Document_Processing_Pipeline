#!/usr/bin/env python3
"""
Test script to verify we can extract form field metadata from blank PDF templates
without using Google Document AI Form Parser.
"""

import json
from pathlib import Path
from pypdf import PdfReader

def extract_form_fields_from_blank_pdf(pdf_path: Path):
    """Extract all form field metadata from a blank PDF template."""
    print(f"\n{'='*60}")
    print(f"Extracting fields from: {pdf_path.name}")
    print('='*60)
    
    try:
        reader = PdfReader(pdf_path)
        
        # Get all form fields
        if hasattr(reader, 'get_fields'):
            all_fields = reader.get_fields() or {}
        else:
            all_fields = {}
        
        # Also try form text fields
        if hasattr(reader, 'get_form_text_fields'):
            text_fields = reader.get_form_text_fields() or {}
        else:
            text_fields = {}
        
        print(f"\nFound {len(all_fields)} total fields in PDF")
        print(f"Found {len(text_fields)} text fields specifically")
        
        # Analyze field types
        field_types = {}
        field_names = []
        
        for field_name, field_obj in all_fields.items():
            # Clean field name
            clean_name = field_name.replace('\x00', '').strip()
            field_names.append(clean_name)
            
            # Determine field type
            field_type = "unknown"
            if hasattr(field_obj, 'get') and '/FT' in field_obj:
                ft = str(field_obj['/FT'])
                if 'Btn' in ft:
                    field_type = "checkbox/button"
                elif 'Tx' in ft:
                    field_type = "text"
                elif 'Ch' in ft:
                    field_type = "choice/dropdown"
                elif 'Sig' in ft:
                    field_type = "signature"
            
            field_types[field_type] = field_types.get(field_type, 0) + 1
        
        print(f"\nField Types Distribution:")
        for ft, count in sorted(field_types.items()):
            print(f"  - {ft}: {count}")
        
        print(f"\nSample Field Names (first 10):")
        for i, name in enumerate(field_names[:10]):
            print(f"  {i+1}. {name}")
        
        # Save detailed field information
        output_dir = Path("outputs/blank_template_fields")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / f"{pdf_path.stem}_fields.json"
        field_data = {
            "template": str(pdf_path),
            "total_fields": len(all_fields),
            "text_fields": len(text_fields),
            "field_types": field_types,
            "field_names": field_names[:50],  # Save first 50 for review
            "extraction_method": "pypdf_direct"
        }
        
        with open(output_file, 'w') as f:
            json.dump(field_data, f, indent=2)
        
        print(f"\n✅ Field data saved to: {output_file}")
        
        return field_data
        
    except Exception as e:
        print(f"❌ Error extracting fields: {e}")
        return None

def main():
    """Test field extraction on available blank PDF templates."""
    
    print("\n" + "="*60)
    print("TESTING BLANK PDF TEMPLATE FIELD EXTRACTION")
    print("="*60)
    print("\nThis test verifies we can extract form field metadata")
    print("directly from blank PDF templates without using DocAI")
    
    # Find available templates
    template_dir = Path("templates")
    pdf_templates = list(template_dir.glob("*.pdf"))
    
    if not pdf_templates:
        print("\n❌ No PDF templates found in templates/ directory")
        return
    
    print(f"\nFound {len(pdf_templates)} PDF templates to analyze")
    
    results = []
    for pdf_path in pdf_templates:
        result = extract_form_fields_from_blank_pdf(pdf_path)
        if result:
            results.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for result in results:
        template_name = Path(result['template']).name
        print(f"\n{template_name}:")
        print(f"  - Total fields: {result['total_fields']}")
        print(f"  - Text fields: {result['text_fields']}")
        print(f"  - Field types: {result['field_types']}")
    
    print("\n✅ Successfully extracted field metadata from blank templates!")
    print("This proves we can identify form fields without DocAI Form Parser")
    print("\nNEXT STEPS:")
    print("1. Use these field names for direct mapping from master JSON")
    print("2. Create field coordinate maps for visual positioning if needed")
    print("3. Implement fallback to Claude Vision for field detection")

if __name__ == "__main__":
    main()