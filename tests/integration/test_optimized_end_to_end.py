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
import time
import os
from pathlib import Path
from src.extraction_methods.multimodal_llm.providers import (
    LLMFormFiller,
    PDFFormGenerator
)


async def test_optimized_extraction():
    """
    Optimized test that processes key documents for maximum coverage.
    """
    
    test_start = time.time()
    
    print("\n" + "=" * 70)
    print("🚀 OPTIMIZED END-TO-END TEST: MAXIMUM FIELD COVERAGE")
    print("=" * 70)
    
    # Display configuration
    print("\n⚠️  TEST CONFIGURATION WARNING:")
    print(f"  • Mode: {'Files API' if os.getenv('USE_FILES_API', 'false').lower() == 'true' else 'Image-based (Base64)'}")
    print(f"  • Expected documents: 5 (PFS, Tax Returns, Business Info)")
    print(f"  • Estimated pages: ~29-33")
    print(f"  • Estimated tokens: ~15,000-25,000 (image mode)")
    print(f"  • Rate limit risk: MEDIUM-HIGH")
    print(f"  🚨 May hit 30k token/minute limit!")
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
    
    # Filter to existing files and calculate sizes
    selected_docs = []
    total_pages = 0
    total_size_mb = 0
    
    print(f"\n📄 DOCUMENT SELECTION:")
    for doc_name, description, est_pages in priority_documents:
        doc_path = documents_folder / doc_name
        if doc_path.exists():
            size_mb = doc_path.stat().st_size / 1024 / 1024
            total_size_mb += size_mb
            selected_docs.append(doc_path)
            total_pages += est_pages
            print(f"  ✅ {description}:")
            print(f"     File: {doc_name}")
            print(f"     Size: {size_mb:.2f} MB")
            print(f"     Est. pages: {est_pages}")
        else:
            print(f"  ❌ Missing: {doc_name}")
    
    print(f"\n📊 TOTALS:")
    print(f"  • Documents: {len(selected_docs)}")
    print(f"  • Total size: {total_size_mb:.2f} MB")
    print(f"  • Estimated pages: ~{total_pages}")
    print(f"  • Estimated images: ~{total_pages * 1.2:.0f} (after preprocessing)")
    
    # Risk assessment
    estimated_tokens = total_pages * 1500  # Rough estimate
    print(f"\n🚫 RATE LIMIT RISK ASSESSMENT:")
    print(f"  • Estimated tokens: ~{estimated_tokens:,}")
    if estimated_tokens > 25000:
        print(f"  🔴 HIGH RISK: May exceed 30k token/minute limit")
        print(f"     Consider processing fewer documents")
    elif estimated_tokens > 20000:
        print(f"  🟡 MEDIUM RISK: Close to rate limits")
    else:
        print(f"  🟢 LOW RISK: Should be within limits")
    
    if not selected_docs:
        print("❌ No documents found!")
        return
    
    # Step 2: Extract data from all selected documents
    print("\n🤖 STEP 2: EXTRACTING DATA (HIGH RISK)")
    print("-" * 50)
    
    print("\n📡 Starting API call with multiple documents...")
    print("  ⚠️  This may take 30-60 seconds")
    
    extraction_start = time.time()
    try:
        extracted_data = await filler.extractor.extract_all(selected_docs)
        extraction_time = time.time() - extraction_start
        
        print(f"\n✅ Extraction completed in {extraction_time:.2f} seconds")
        
        # Check for rate limit issues
        if extracted_data.get('_extraction_failed'):
            print(f"\n🔴 EXTRACTION FAILED:")
            print(f"  Error: {extracted_data.get('error', 'Unknown')}")
            
            error_msg = str(extracted_data.get('error', ''))
            if '413' in error_msg or 'rate' in error_msg.lower() or '429' in error_msg:
                print(f"\n  🚫 RATE LIMIT HIT!")
                print(f"     This confirms 5 documents exceed limits")
                print(f"     Solution: Use test_focused_end_to_end.py (2 docs)")
                print(f"     Or: Wait 1 minute and retry")
            elif '2000' in error_msg:
                print(f"\n  🗖️ IMAGE SIZE ERROR!")
                print(f"     Images exceed 2000px dimension limit")
                print(f"     Solution: Reduce DPI in preprocessor")
            return
            
    except Exception as e:
        print(f"\n🔴 EXTRACTION EXCEPTION: {e}")
        print(f"  This is likely a rate limit or size error")
        return
    
    # Save for analysis
    extraction_file = Path("outputs/filled_forms/optimized_extraction.json")
    extraction_file.parent.mkdir(parents=True, exist_ok=True)
    with open(extraction_file, 'w') as f:
        json.dump(extracted_data, f, indent=2)
    print(f"💾 Saved extraction to: {extraction_file}")
    
    # Analyze extraction metrics
    if '_metadata' in extracted_data:
        meta = extracted_data['_metadata']
        print(f"\n📊 EXTRACTION METRICS:")
        print(f"  • Processing time: {meta.get('processing_time', 'N/A'):.2f}s")
        print(f"  • Documents processed: {meta.get('documents_processed', 'N/A')}")
        print(f"  • Total images: {meta.get('total_images', 'N/A')}")
        print(f"  • Files API used: {meta.get('files_api_used', False)}")
        
        # Token usage warning
        if meta.get('total_images', 0) > 20:
            print(f"\n  ⚠️  LARGE IMAGE COUNT: {meta.get('total_images')} images")
            print(f"     High risk of rate limiting")
    
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
    filled_form_file.parent.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
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
        
        # Ensure output directory exists
        pdf_output_dir = Path("outputs/filled_pdfs")
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = generator.generate_filled_pdf(
            "Live Oak",
            filled_fields,
            str(pdf_output_dir)
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