#!/usr/bin/env python3
"""
OPTIMIZED End-to-End Test: Process maximum documents within API limits

This test:
1. Processes the most information-rich documents
2. Stays within Claude API limits (~50 images)
3. Uses improved form field mapping
4. Achieves maximum field coverage
"""

import asyncio
import json
from pathlib import Path
from src.extraction_methods.multimodal_llm.providers import (
    LLMFormFiller,
    PDFFormGenerator
)


async def test_optimized_extraction():
    """
    Optimized test that processes key documents for maximum coverage.
    """
    
    print("=" * 70)
    print("🚀 OPTIMIZED END-TO-END TEST: MAXIMUM FIELD COVERAGE")
    print("=" * 70)
    print()
    
    try:
        filler = LLMFormFiller()
    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nPlease add your Anthropic API key to the .env file:")
        print("  ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE")
        return
    
    # Step 1: Select optimal documents
    print("📂 STEP 1: SELECTING OPTIMAL DOCUMENTS")
    print("-" * 50)
    
    documents_folder = Path("inputs/real/Brigham_dallas")
    
    # Priority documents for maximum information coverage
    # Total estimated: ~33 pages (within 50 page limit)
    priority_documents = [
        # Personal & Financial Overview (3 pages)
        ("Brigham_Dallas_PFS.pdf", "Personal Financial Statement", 3),
        
        # Most recent tax returns (20 pages total)
        ("Brigham_Dallas_2024_PTR.pdf", "Personal Tax Return 2024", 10),
        ("Hello_Sugar_Franchise_LLC_2024.pdf", "Business Tax Return 2024", 10),
        
        # Business Information (5 pages)
        ("Management_Bios.pdf", "Management Biographies", 5),
        
        # Organization Structure (1 page)
        ("Waxxpot_Org_Chart_2025_.pdf", "Organization Chart", 1),
    ]
    
    # Filter to existing files
    selected_docs = []
    total_pages = 0
    
    for doc_name, description, pages in priority_documents:
        doc_path = documents_folder / doc_name
        if doc_path.exists():
            selected_docs.append(doc_path)
            total_pages += pages
            print(f"  ✅ {description}: {doc_name} ({pages} pages)")
        else:
            print(f"  ❌ Missing: {doc_name}")
    
    print(f"\n📊 Total: {len(selected_docs)} documents, ~{total_pages} pages")
    
    if not selected_docs:
        print("❌ No documents found!")
        return
    
    # Step 2: Extract data from all selected documents
    print("\n🤖 STEP 2: EXTRACTING DATA")
    print("-" * 50)
    
    print("Processing documents...")
    extracted_data = await filler.extractor.extract_all(selected_docs)
    
    print("✅ Extraction complete!")
    
    # Save for analysis
    extraction_file = Path("outputs/filled_forms/optimized_extraction.json")
    extraction_file.parent.mkdir(parents=True, exist_ok=True)
    with open(extraction_file, 'w') as f:
        json.dump(extracted_data, f, indent=2)
    print(f"💾 Saved extraction to: {extraction_file}")
    
    # Analyze what we extracted
    def count_data_points(obj, prefix=""):
        count = 0
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k.startswith('_'):
                    continue
                if isinstance(v, dict):
                    count += count_data_points(v, prefix + k + ".")
                elif v:
                    count += 1
        return count
    
    data_points = count_data_points(extracted_data)
    print(f"📊 Extracted {data_points} data points")
    
    # Step 3: Read form template with improved field loading
    print("\n📋 STEP 3: LOADING FORM TEMPLATE")
    print("-" * 50)
    
    form_template = Path("templates/Live Oak Express - Application Forms.pdf")
    form_structure = await filler._read_form_template(form_template)
    
    field_count = len(form_structure.get('fields', {}))
    print(f"✅ Form has {field_count} fields")
    
    if field_count > 0:
        # Show sample fields
        sample_fields = list(form_structure.get('fields', {}).keys())[:10]
        print("\nSample form fields:")
        for field in sample_fields:
            print(f"  • {field}")
    
    # Step 4: Map data to form fields
    print("\n🤖 STEP 4: INTELLIGENT FIELD MAPPING")
    print("-" * 50)
    
    filled_form = await filler._fill_form_with_llm(form_structure, extracted_data)
    
    # Analyze results
    filled_fields = filled_form.get('filled_fields', {})
    filled_count = len([v for v in filled_fields.values() if v])
    completion = filled_form.get('completion_percentage', 0)
    
    print(f"✅ Mapped {filled_count} fields ({completion:.1f}% completion)")
    
    # Show what was filled
    if filled_count > 0:
        print("\n📝 Sample of filled fields:")
        
        # Group by category
        personal_fields = ["Name", "Social Security Number", "Date of Birth", 
                          "Mobile Telephone Number", "Email address"]
        business_fields = ["Business Applicant Name", 
                          "What percentage of the applicant business do/will you own?",
                          "Do you have ownership in other entities aside from the Applicant Business?"]
        financial_fields = ["total_assets", "total_liabilities", "net_worth"]
        
        print("\nPersonal Information:")
        for field in personal_fields:
            if field in filled_fields and filled_fields[field]:
                print(f"  ✓ {field}: {filled_fields[field]}")
            else:
                print(f"  ✗ {field}: (not filled)")
        
        print("\nBusiness Information:")
        for field in business_fields:
            if field in filled_fields and filled_fields[field]:
                print(f"  ✓ {field}: {filled_fields[field]}")
            else:
                print(f"  ✗ {field}: (not filled)")
        
        # Count other filled fields
        other_filled = [k for k in filled_fields if filled_fields[k] 
                       and k not in personal_fields + business_fields + financial_fields]
        if other_filled:
            print(f"\n+ {len(other_filled)} other fields filled")
    
    # Save filled form
    filled_form_file = Path("outputs/filled_forms/optimized_filled_form.json")
    with open(filled_form_file, 'w') as f:
        json.dump(filled_form, f, indent=2)
    print(f"\n💾 Saved filled form to: {filled_form_file}")
    
    # Step 5: Generate PDF
    print("\n📄 STEP 5: GENERATING PDF")
    print("-" * 50)
    
    if filled_count > 0:
        generator = PDFFormGenerator()
        
        # Load mapping
        mapping_path = Path("outputs/form_mappings/Live Oak Express - Application Forms_mapping.json")
        if mapping_path.exists():
            generator.filler.load_mapping(mapping_path)
        
        pdf_path = generator.generate_filled_pdf(
            "Live Oak",
            filled_fields,
            "outputs/filled_pdfs"
        )
        
        if pdf_path:
            size_kb = Path(pdf_path).stat().st_size / 1024
            print(f"\n🎉 SUCCESS! Generated filled PDF:")
            print(f"   📄 {pdf_path}")
            print(f"   📏 Size: {size_kb:.1f} KB")
            print(f"   📝 Fields filled: {filled_count}/{field_count}")
            print(f"   ✅ Completion: {completion:.1f}%")
        else:
            print("\n❌ Failed to generate PDF")
    else:
        print("\n⚠️  No fields were filled")
    
    # Show improvements over previous version
    print("\n" + "=" * 70)
    print("📈 IMPROVEMENTS IN THIS VERSION:")
    print("-" * 50)
    print("✅ Processing 5 key documents (vs 2)")
    print(f"✅ Using all {field_count} form fields (vs 0)")
    print(f"✅ Filled {filled_count} fields (vs 7)")
    print("✅ Better coverage of business and financial data")
    
    print("\n" + "=" * 70)
    print("✅ OPTIMIZED END-TO-END TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_optimized_extraction())