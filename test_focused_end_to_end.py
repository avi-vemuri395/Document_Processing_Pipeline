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
from pathlib import Path
from src.extraction_methods.multimodal_llm.providers import (
    LLMFormFiller,
    PDFFormGenerator
)


async def test_focused_extraction():
    """
    Focused test that only processes essential documents.
    """
    
    print("=" * 70)
    print("🎯 FOCUSED END-TO-END TEST: KEY DOCUMENTS ONLY")
    print("=" * 70)
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
    
    # Filter to existing files
    existing_docs = [d for d in key_documents if d.exists()]
    
    print(f"📄 Processing {len(existing_docs)} key documents:")
    for doc in existing_docs:
        print(f"   • {doc.name}")
    
    if not existing_docs:
        print("❌ No key documents found!")
        return
    
    # Extract data
    print("\n🤖 Extracting data with Claude...")
    extracted_data = await filler.extractor.extract_all(existing_docs)
    print("================================================")
    print("Extracted data: \n")
    print("================================================")
    print(extracted_data)
    print("✅ Extraction complete!")
    
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
    form_structure = await filler._read_form_template(form_template)
    print("================================================")
    print("Form structure: \n")
    print("================================================")
    print(form_structure)
    print(f"✅ Form has {len(form_structure.get('fields', {}))} fields")
    
    # Step 3: Use LLM to map data to form
    print("\n🤖 STEP 3: MAPPING DATA TO FORM FIELDS")
    print("-" * 50)
    
    filled_form = await filler._fill_form_with_llm(form_structure, extracted_data)
    print("================================================")
    print("Filled form: \n")
    print("================================================")
    print(filled_form)
    # Check what was filled
    filled_fields = filled_form.get('filled_fields', {})
    print("Filled fields: \n")
    print(filled_fields)
    filled_count = len([v for v in filled_fields.values() if v])
    
    print(f"✅ Mapped {filled_count} fields")
    
    if filled_count > 0:
        print("\n📝 Sample of filled fields:")
        for key, value in list(filled_fields.items())[:10]:
            if value:
                print(f"   • {key}: {value}")
    
    # Save filled form data - add file name to the path
    filled_form_file = Path("outputs/filled_forms/focused_filled_form.json")
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
            print(f"   📝 Fields filled: {filled_count}")
        else:
            print("\n❌ Failed to generate PDF")
    else:
        print("\n⚠️  No fields were filled - skipping PDF generation")
        print("   This likely means the extraction failed or returned empty data")
    
    print("\n" + "=" * 70)
    print("✅ FOCUSED END-TO-END TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_focused_extraction())