#!/usr/bin/env python3
"""
Quick test to verify PDF generation works with sample data.
"""

import json
from pathlib import Path
from src.extraction_methods.multimodal_llm.providers import PDFFormGenerator

def test_pdf_generation():
    """Test PDF generation with sample filled data."""
    
    print("=" * 70)
    print("📄 PDF GENERATION TEST")
    print("=" * 70)
    
    # Sample filled data (based on what we see in extraction)
    sample_data = {
        "Name": "Brigham Dallas",
        "Social Security Number": "XXX-XX-3074",
        "Email address": "BRIGHAM@HELLOSUGAR.SALON",
        "Residence Address": "555 N College Ave #3059",
        "City State Zip": "Tempe, AZ 85281",
        "Married": True,
        "Working Capital": True,
        "US Citizen": True,
        "Total Assets": "4397552",
        "Total Liabilities": "2044663",
        "Net Worth": "2352889",
        "Business Name": "Hello Sugar Franchise LLC",
        "Primary Phone": "480-225-7076",
        "Date": "08/14/2025"
    }
    
    print(f"\n📝 Sample data prepared with {len(sample_data)} fields")
    
    # Create generator
    print("\n🔧 Initializing PDF generator...")
    generator = PDFFormGenerator()
    
    # Check for mapping file
    mapping_path = Path("outputs/form_mappings/Live Oak Express - Application Forms_mapping.json")
    if mapping_path.exists():
        print("  ✅ Loading existing field mapping")
        generator.filler.load_mapping(mapping_path)
    else:
        print("  ⚠️  No mapping file found, will use direct field names")
    
    # Ensure output directory exists
    output_dir = Path("outputs/filled_pdfs")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate PDF
    print("\n🚀 Generating PDF...")
    try:
        pdf_path = generator.generate_filled_pdf(
            "Live Oak",  # Use the correct template name
            sample_data,
            str(output_dir)
        )
        
        if pdf_path and Path(pdf_path).exists():
            size_kb = Path(pdf_path).stat().st_size / 1024
            print(f"\n✅ SUCCESS! PDF generated:")
            print(f"  📄 File: {pdf_path}")
            print(f"  📏 Size: {size_kb:.1f} KB")
            print(f"  📝 Fields filled: {len(sample_data)}")
        else:
            print("\n❌ PDF generation failed - file not created")
            
    except Exception as e:
        print(f"\n❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_pdf_generation()