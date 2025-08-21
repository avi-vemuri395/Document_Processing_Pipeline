#!/usr/bin/env python3
"""
Script to trace the PDF generation flow step by step.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

async def trace_pdf_generation():
    """Trace the PDF generation flow from master data to filled PDF."""
    
    print("\n" + "="*80)
    print("  TRACING PDF GENERATION FLOW")
    print("="*80)
    
    # Step 1: Import the services
    print("\n1. IMPORTING SERVICES")
    print("-" * 40)
    from src.template_extraction.form_mapping_service import FormMappingService
    from src.extraction_methods.multimodal_llm.providers.pdf_form_generator import PDFFormGenerator, AcroFormFiller
    print("  ✅ FormMappingService imported")
    print("  ✅ PDFFormGenerator imported")
    print("  ✅ AcroFormFiller imported")
    
    # Step 2: Initialize services
    print("\n2. INITIALIZING SERVICES")
    print("-" * 40)
    form_service = FormMappingService()
    pdf_generator = PDFFormGenerator()
    print(f"  ✅ FormMappingService initialized")
    print(f"  ✅ PDFFormGenerator initialized")
    print(f"  ✅ PDF library in use: {pdf_generator.filler.pdf_library}")
    
    # Step 3: Check for existing master data
    print("\n3. CHECKING MASTER DATA")
    print("-" * 40)
    # Find an existing application with master data
    apps_dir = Path("outputs/applications")
    app_ids = []
    if apps_dir.exists():
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir():
                master_file = app_dir / "part1_document_processing" / "master_data.json"
                if master_file.exists():
                    app_ids.append(app_dir.name)
    
    if app_ids:
        print(f"  ✅ Found {len(app_ids)} applications with master data")
        test_app_id = app_ids[0]
        print(f"  📁 Using application: {test_app_id}")
    else:
        print("  ❌ No existing applications found")
        print("  💡 Creating sample master data for testing...")
        test_app_id = f"trace_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create minimal sample data
        sample_master_data = {
            "personal_info": {
                "primary_applicant": {
                    "full_name": "John Doe",
                    "ssn": "123-45-6789",
                    "phone": "555-123-4567",
                    "email": "john.doe@example.com"
                }
            },
            "business_info": {
                "legal_name": "Test Company LLC",
                "ein": "12-3456789",
                "ownership_percentage": "100"
            },
            "financial_info": {
                "total_assets": "1234567",
                "total_liabilities": "234567",
                "net_worth": "1000000"
            }
        }
        
        # Save sample master data
        master_dir = Path(f"outputs/applications/{test_app_id}/part1_document_processing")
        master_dir.mkdir(parents=True, exist_ok=True)
        master_file = master_dir / "master_data.json"
        with open(master_file, 'w') as f:
            json.dump(sample_master_data, f, indent=2)
        print(f"  ✅ Created sample master data at: {master_file}")
    
    # Step 4: Load master data
    print("\n4. LOADING MASTER DATA")
    print("-" * 40)
    master_file = Path(f"outputs/applications/{test_app_id}/part1_document_processing/master_data.json")
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    field_count = sum(
        len(v) if isinstance(v, dict) else 1 
        for k, v in master_data.items() 
        if not k.startswith('_') and k != 'metadata'
    )
    print(f"  ✅ Loaded master data with ~{field_count} fields")
    
    # Step 5: Map to form fields (using Live Oak as example)
    print("\n5. MAPPING TO FORM FIELDS")
    print("-" * 40)
    print("  🏦 Target: Live Oak Application Form")
    
    # Get form specification
    spec_key = "live_oak_application_v1"
    form_spec = form_service.form_specs.get(spec_key)
    
    if form_spec:
        print(f"  ✅ Found form spec: {len(form_spec.get('fields', []))} fields")
    else:
        print(f"  ❌ Form spec not found for {spec_key}")
        print("  💡 Creating minimal form spec...")
        form_spec = {
            "form_id": spec_key,
            "form_name": "Live Oak Application",
            "fields": [
                {"name": "Name", "type": "text"},
                {"name": "Social Security Number", "type": "text"},
                {"name": "Email address", "type": "text"},
                {"name": "Mobile Telephone Number", "type": "text"},
                {"name": "Business Applicant Name", "type": "text"},
                {"name": "What percentage of the applicant business do/will you own?", "type": "text"}
            ]
        }
    
    # Perform mapping (simplified version without OpenAI)
    print("  🔄 Performing field mapping...")
    mapped_data = {}
    
    # Manual mapping for key fields
    if "personal_info" in master_data:
        personal = master_data["personal_info"].get("primary_applicant", {})
        mapped_data["Name"] = personal.get("full_name", "")
        mapped_data["Social Security Number"] = personal.get("ssn", "")
        mapped_data["Email address"] = personal.get("email", "")
        mapped_data["Mobile Telephone Number"] = personal.get("phone", "")
    
    if "business_info" in master_data:
        business = master_data["business_info"]
        mapped_data["Business Applicant Name"] = business.get("legal_name", "")
        mapped_data["What percentage of the applicant business do/will you own?"] = business.get("ownership_percentage", "")
    
    print(f"  ✅ Mapped {len(mapped_data)} fields")
    for field, value in list(mapped_data.items())[:5]:
        print(f"    • {field}: {value}")
    
    # Step 6: Generate PDF
    print("\n6. GENERATING PDF")
    print("-" * 40)
    
    # Check if template exists
    template_path = Path("templates/Live Oak Express - Application Forms.pdf")
    if not template_path.exists():
        print(f"  ❌ Template not found: {template_path}")
        print("  ℹ️  PDF generation requires the actual template file")
        return
    
    print(f"  ✅ Template found: {template_path.name}")
    
    # Initialize AcroFormFiller
    print("\n  📋 PDF Generation Steps:")
    print("  1. Initialize AcroFormFiller")
    filler = AcroFormFiller()
    print(f"     • PDF library: {filler.pdf_library}")
    
    # Load mapping if available
    print("  2. Load field mapping")
    mapping_base = Path("outputs/form_mappings/Live Oak Express - Application Forms")
    filler.load_mapping(mapping_base)
    
    # Prepare output path
    print("  3. Prepare output path")
    output_dir = Path(f"outputs/applications/{test_app_id}/part2_form_mapping/banks/live_oak")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "application_filled.pdf"
    print(f"     • Output: {output_path}")
    
    # Fill the PDF
    print("  4. Fill PDF with mapped data")
    success = filler.fill_pdf(
        template_path,
        mapped_data,
        output_path,
        flatten=False
    )
    
    if success:
        print(f"\n✅ PDF GENERATED SUCCESSFULLY!")
        print(f"  📁 Location: {output_path}")
        print(f"  📊 Size: {output_path.stat().st_size / 1024:.1f} KB")
    else:
        print(f"\n❌ PDF generation failed")
    
    # Step 7: Summary
    print("\n" + "="*80)
    print("  PDF GENERATION FLOW SUMMARY")
    print("="*80)
    print("\n  The complete flow is:")
    print("  1. Master data loaded from Part 1 extraction")
    print("  2. FormMappingService maps data to form fields")
    print("  3. AcroFormFiller loads PDF template and field mappings")
    print("  4. PDF library (PyPDFForm/pypdf) fills the actual PDF")
    print("  5. Filled PDF saved to output directory")
    print("\n  Key components:")
    print("  • FormMappingService: Orchestrates mapping process")
    print("  • AcroFormFiller: Handles PDF manipulation")
    print("  • PDF libraries: PyPDFForm (preferred) or pypdf (fallback)")
    print("  • Field mappings: Define how data maps to PDF fields")

if __name__ == "__main__":
    asyncio.run(trace_pdf_generation())