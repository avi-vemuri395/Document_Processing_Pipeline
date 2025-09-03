#!/usr/bin/env python3
"""
Test the Direct PDF Field Mapper - Alternative to DocAI Form Parser
This demonstrates mapping master JSON data to PDF fields without using DocAI.
"""

import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.template_extraction.direct_pdf_field_mapper import DirectPDFFieldMapper
from src.extraction_methods.multimodal_llm.providers.pdf_form_generator import PDFFormGenerator

def test_direct_mapping():
    """Test direct PDF field extraction and mapping."""
    
    print("\n" + "="*60)
    print("TESTING DIRECT PDF FIELD MAPPING (DocAI Alternative)")
    print("="*60)
    
    # Initialize mapper
    mapper = DirectPDFFieldMapper()
    
    # 1. Test with Live Oak template
    template_path = Path("templates/Live Oak Express - Application Forms.pdf")
    if not template_path.exists():
        print(f"❌ Template not found: {template_path}")
        return
    
    print(f"\n1. Extracting fields from: {template_path.name}")
    print("-"*60)
    
    # Extract PDF fields
    pdf_fields = mapper.extract_pdf_fields(template_path)
    print(f"✓ Extracted {len(pdf_fields)} fields from PDF template")
    
    # Show sample fields
    print("\nSample PDF fields extracted:")
    for i, (field_name, field_info) in enumerate(list(pdf_fields.items())[:5]):
        print(f"  {i+1}. {field_name} ({field_info['type']})")
        if field_info.get('standard_field'):
            print(f"      → maps to: {field_info['standard_field']}")
    
    # 2. Load master JSON data
    master_json_path = Path("outputs/applications/fast_docai_fix_test_20250825_211920/part1_document_processing/master_data.json")
    
    if master_json_path.exists():
        print(f"\n2. Loading master data from recent test run")
        print("-"*60)
        
        with open(master_json_path, 'r') as f:
            master_data = json.load(f)
        
        print(f"✓ Loaded master data with {len(master_data)} top-level sections")
        
        # Show what data we have
        for section, content in master_data.items():
            if isinstance(content, dict):
                field_count = sum(1 for v in content.values() if v)
                print(f"  - {section}: {field_count} fields")
        
        # 3. Map data to PDF fields
        print(f"\n3. Mapping master data to PDF fields")
        print("-"*60)
        
        mapped_data = mapper.map_data_to_pdf_fields(master_data, pdf_fields)
        
        print(f"\n✓ Mapped {len(mapped_data)} fields out of {len(pdf_fields)} PDF fields")
        print(f"  Coverage: {len(mapped_data)/len(pdf_fields)*100:.1f}%")
        
        # Show sample mappings
        print("\nSample successful mappings:")
        for i, (field, value) in enumerate(list(mapped_data.items())[:10]):
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            print(f"  {field}: {value}")
        
        # 4. Save mapped data
        output_dir = Path("outputs/direct_mapping_test")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "live_oak_mapped.json"
        with open(output_file, 'w') as f:
            json.dump({
                "pdf_template": str(template_path),
                "fields_extracted": len(pdf_fields),
                "fields_mapped": len(mapped_data),
                "coverage_percentage": round(len(mapped_data)/len(pdf_fields)*100, 1),
                "mapped_data": mapped_data
            }, f, indent=2)
        
        print(f"\n✓ Saved mapping results to: {output_file}")
        
        # 5. Try to fill the PDF (if we have PDFFormGenerator)
        try:
            pdf_generator = PDFFormGenerator()
            output_pdf = output_dir / "live_oak_filled_direct.pdf"
            
            print(f"\n4. Attempting to fill PDF with mapped data")
            print("-"*60)
            
            success = pdf_generator.fill_pdf(
                template_path=template_path,
                field_data=mapped_data,
                output_path=output_pdf
            )
            
            if success:
                print(f"✓ Successfully generated filled PDF: {output_pdf}")
                print(f"  File size: {output_pdf.stat().st_size / 1024:.1f} KB")
            else:
                print("⚠️ PDF generation completed with warnings")
                
        except Exception as e:
            print(f"⚠️ Could not fill PDF: {e}")
    
    else:
        # Create sample data for demonstration
        print("\n2. Using sample data (no master JSON found)")
        print("-"*60)
        
        sample_data = {
            "personal_info": {
                "Name": "John Doe",
                "Social Security Number": "123-45-6789",
                "Email address": "john.doe@example.com",
                "Mobile Telephone Number": "555-123-4567"
            },
            "business_info": {
                "Business Applicant Name": "Doe Enterprises LLC",
                "ownership": "100%"
            },
            "financial_info": {
                "Total": "4,397,552",
                "Total Liabilities .": "2,044,663"
            }
        }
        
        mapped_data = mapper.map_data_to_pdf_fields(sample_data, pdf_fields)
        print(f"✓ Mapped {len(mapped_data)} fields from sample data")
    
    # Summary
    print("\n" + "="*60)
    print("SOLUTION SUMMARY")
    print("="*60)
    print("\n✅ Successfully demonstrated direct PDF field extraction!")
    print("\nThis approach bypasses DocAI Form Parser limitations by:")
    print("1. Extracting field metadata directly from blank PDFs using pypdf")
    print("2. Using intelligent fuzzy matching to map data fields") 
    print("3. Supporting all field types (text, checkbox, dropdown)")
    print("4. No external API calls or costs")
    print("\nAdvantages over DocAI Form Parser:")
    print("• Works with blank templates (DocAI fails on unfilled forms)")
    print("• Zero cost (no API charges)")
    print("• Instant processing (no network latency)")
    print("• Full control over matching logic")

def main():
    try:
        test_direct_mapping()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()