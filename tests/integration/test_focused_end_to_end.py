#!/usr/bin/env python3
"""
FOCUSED End-to-End Test: Extract only KEY documents → Fill Form → Generate PDF

This test uses only the essential documents to avoid API limits:
- Personal Financial Statement (PFS)
- One recent tax return

This avoids the 413 error from processing too many documents.
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


async def test_focused_extraction():
    """
    Focused test that only processes essential documents.
    """
    
    test_start = time.time()
    
    print("\n" + "=" * 70)
    print("🎯 FOCUSED END-TO-END TEST: KEY DOCUMENTS ONLY")
    print("=" * 70)
    
    # Display configuration
    print("\n⚙️  TEST CONFIGURATION:")
    print(f"  • Mode: {'Files API' if os.getenv('USE_FILES_API', 'false').lower() == 'true' else 'Image-based (Base64)'}")
    print(f"  • Expected documents: 2 (PFS + Tax Return)")
    print(f"  • Estimated tokens: ~3,000-5,000 (image mode)")
    print(f"  • Rate limit: 30,000 tokens/minute")
    print()
    
    try:
        filler = LLMFormFiller()
    except ValueError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nPlease add your Anthropic API key to the .env file:")
        print("  ANTHROPIC_API_KEY=sk-ant-api03-YOUR-KEY-HERE")
        return
    
    # Step 1: Extract from KEY documents only
    print("📂 STEP 1: EXTRACTING KEY DOCUMENTS")
    print("-" * 50)
    
    documents_folder = Path("inputs/real/Brigham_dallas")
    
    # Only use the most important documents
    key_documents = [
        documents_folder / "Brigham_Dallas_PFS.pdf",  # Personal Financial Statement
        documents_folder / "Brigham_Dallas_2024_PTR.pdf"  # Most recent tax return
    ]
    
    # Filter to existing files and show sizes
    existing_docs = []
    total_size = 0
    
    print(f"\n📄 KEY DOCUMENTS ANALYSIS:")
    for doc in key_documents:
        if doc.exists():
            size_mb = doc.stat().st_size / 1024 / 1024
            total_size += size_mb
            existing_docs.append(doc)
            print(f"  • {doc.name}: {size_mb:.2f} MB")
        else:
            print(f"  ❌ {doc.name}: NOT FOUND")
    
    print(f"\n📏 Total size: {total_size:.2f} MB")
    print(f"📄 Documents to process: {len(existing_docs)}")
    
    if not existing_docs:
        print("❌ No key documents found!")
        return
    
    # Extract data
    print("\n🤖 STARTING EXTRACTION WITH CLAUDE...")
    print("-" * 50)
    
    extraction_start = time.time()
    extracted_data = await filler.extractor.extract_all(existing_docs)
    extraction_time = time.time() - extraction_start
    
    print(f"\n✅ Extraction completed in {extraction_time:.2f} seconds")
    
    # Analyze extraction results
    if '_metadata' in extracted_data:
        meta = extracted_data['_metadata']
        print(f"\n📊 EXTRACTION METRICS:")
        print(f"  • Processing time: {meta.get('processing_time', 'N/A'):.2f}s")
        print(f"  • Documents processed: {meta.get('documents_processed', 'N/A')}")
        print(f"  • Total images: {meta.get('total_images', 'N/A')}")
        print(f"  • Model used: {meta.get('model', 'N/A')}")
        print(f"  • Files API used: {meta.get('files_api_used', False)}")
    
    # Check for extraction errors
    if extracted_data.get('_extraction_failed'):
        print(f"\n❌ EXTRACTION FAILED:")
        print(f"  Error: {extracted_data.get('error', 'Unknown error')}")
        if 'rate' in str(extracted_data.get('error', '')).lower():
            print(f"  🚫 This appears to be a rate limit error")
            print(f"     Try again in 1 minute or process fewer documents")
        return
    
    # Sample extracted data
    print("\n🔍 SAMPLE OF EXTRACTED DATA:")
    if 'financials' in extracted_data:
        fin = extracted_data['financials']
        if 'balance_sheet' in fin:
            bs = fin['balance_sheet']
            print(f"  • Total Assets: ${bs.get('total_assets', 'N/A'):,}" if isinstance(bs.get('total_assets'), (int, float)) else f"  • Total Assets: {bs.get('total_assets', 'N/A')}")
            print(f"  • Total Liabilities: ${bs.get('total_liabilities', 'N/A'):,}" if isinstance(bs.get('total_liabilities'), (int, float)) else f"  • Total Liabilities: {bs.get('total_liabilities', 'N/A')}")
            print(f"  • Net Worth: ${bs.get('net_worth', 'N/A'):,}" if isinstance(bs.get('net_worth'), (int, float)) else f"  • Net Worth: {bs.get('net_worth', 'N/A')}")
    
    # Save extracted data for debugging
    extraction_file = Path("outputs/extracted_data/focused_extraction.json")
    extraction_file.parent.mkdir(parents=True, exist_ok=True)
    with open(extraction_file, 'w') as f:
        json.dump(extracted_data, f, indent=2)
    print(f"💾 Saved extraction to: {extraction_file}")
    
    # Step 2: Read form template and fill
    print("\n📋 STEP 2: READING FORM TEMPLATE")
    print("-" * 50)
    
    form_template = Path("templates/Live Oak Express - Application Forms.pdf")
    
    print(f"\n📄 Form: {form_template.name}")
    print(f"  • Size: {form_template.stat().st_size / 1024:.1f} KB")
    
    form_start = time.time()
    form_structure = await filler._read_form_template(form_template)
    form_time = time.time() - form_start
    
    print(f"✅ Form loaded in {form_time:.2f} seconds")
    print(f"  • Total fields: {len(form_structure.get('fields', {}))}")
    
    # Show field types
    fields = form_structure.get('fields', {})
    text_fields = sum(1 for f in fields.values() if f.get('type') == 'text')
    checkbox_fields = sum(1 for f in fields.values() if f.get('type') == 'checkbox')
    
    print(f"\n📋 FORM FIELD BREAKDOWN:")
    print(f"  • Text fields: {text_fields}")
    print(f"  • Checkbox fields: {checkbox_fields}")
    print(f"  • Other fields: {len(fields) - text_fields - checkbox_fields}")
    
    # Step 3: Use LLM to map data to form
    print("\n🤖 STEP 3: MAPPING DATA TO FORM FIELDS")
    print("-" * 50)
    
    mapping_start = time.time()
    filled_form = await filler._fill_form_with_llm(form_structure, extracted_data)
    mapping_time = time.time() - mapping_start
    
    print(f"\n✅ Mapping completed in {mapping_time:.2f} seconds")
    
    # Analyze filled fields
    filled_fields = filled_form.get('filled_fields', {})
    filled_count = len([v for v in filled_fields.values() if v])
    
    # Count by type
    text_filled = 0
    checkbox_filled = 0
    
    for field_name, value in filled_fields.items():
        if value:
            if isinstance(value, bool) or value in ['Yes', 'No', '/Yes', '/No']:
                checkbox_filled += 1
            else:
                text_filled += 1
    
    print(f"\n📊 MAPPING RESULTS:")
    print(f"  • Total fields filled: {filled_count}/{len(fields)}")
    print(f"  • Fill rate: {(filled_count/len(fields)*100):.1f}%")
    print(f"  • Text fields filled: {text_filled}")
    print(f"  • Checkboxes filled: {checkbox_filled}")
    
    if filled_count > 0:
        print("\n📝 Sample of filled fields:")
        for key, value in list(filled_fields.items())[:10]:
            if value:
                print(f"   • {key}: {value}")
    
    # Save filled form data - add file name to the path
    filled_form_file = Path("outputs/filled_forms/focused_filled_form.json")
    filled_form_file.parent.mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist
    with open(filled_form_file, 'w') as f:
        json.dump(filled_form, f, indent=2)
    print(f"\n💾 Saved filled form to: {filled_form_file}")
    
    # Step 4: Generate PDF
    print("\n📄 STEP 4: GENERATING PDF")
    print("-" * 50)
    
    if filled_count > 0:
        generator = PDFFormGenerator()
        
        # Load mapping
        mapping_path = Path("outputs/form_mappings/Live Oak Express - Application Forms_mapping.json")
        if mapping_path.exists():
            generator.filler.load_mapping(mapping_path)
            print(f"  • Loaded field mapping from cache")
        
        pdf_start = time.time()
        
        # Ensure output directory exists
        pdf_output_dir = Path("outputs/filled_pdfs")
        pdf_output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_path = generator.generate_filled_pdf(
            "Live Oak",
            filled_fields,
            str(pdf_output_dir)
        )
        pdf_time = time.time() - pdf_start
        
        if pdf_path:
            size_kb = Path(pdf_path).stat().st_size / 1024
            print(f"\n🎉 SUCCESS! Generated filled PDF:")
            print(f"  📄 File: {pdf_path}")
            print(f"  📏 Size: {size_kb:.1f} KB")
            print(f"  📝 Fields filled: {filled_count}")
            print(f"  ⏱️ Generation time: {pdf_time:.2f}s")
        else:
            print("\n❌ Failed to generate PDF")
    else:
        print("\n⚠️  No fields were filled - skipping PDF generation")
        print("   This likely means the extraction failed or returned empty data")
    
    # Final summary
    total_time = time.time() - test_start
    
    print("\n" + "=" * 70)
    print("✅ FOCUSED END-TO-END TEST COMPLETE")
    print("=" * 70)
    
    print("\n📊 PERFORMANCE SUMMARY:")
    print(f"  • Total test time: {total_time:.2f} seconds")
    print(f"  • Extraction: {extraction_time:.2f}s ({extraction_time/total_time*100:.1f}% of total)")
    print(f"  • Form reading: {form_time:.2f}s")
    print(f"  • Field mapping: {mapping_time:.2f}s")
    if filled_count > 0 and pdf_path:
        print(f"  • PDF generation: {pdf_time:.2f}s")
    
    print(f"\n🎯 RESULTS:")
    print(f"  • Documents processed: {len(existing_docs)}")
    print(f"  • Fields filled: {filled_count}/{len(fields)} ({filled_count/len(fields)*100:.1f}%)")
    print(f"  • Success rate: {'100%' if pdf_path else '0%'}")
    
    # Rate limit status
    print(f"\n🚫 RATE LIMIT STATUS:")
    if extracted_data.get('_metadata', {}).get('files_api_used'):
        print(f"  ⚠️  Files API used - higher token consumption")
        print(f"     Monitor for rate limit errors with larger documents")
    else:
        print(f"  ✅ Image mode used - lower token consumption")
        print(f"     Should be well within rate limits")


if __name__ == "__main__":
    asyncio.run(test_focused_extraction())