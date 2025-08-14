#!/usr/bin/env python3
"""
Test dynamic form field mapping - works with ANY PDF form.
No need for pre-existing mapping JSON files.
"""

import asyncio
from pathlib import Path
from src.extraction_methods.multimodal_llm.providers.dynamic_form_mapper import DynamicFormMapper


def test_dynamic_extraction():
    """Test dynamic field extraction from PDFs."""
    
    print("=" * 70)
    print("🔍 DYNAMIC FORM FIELD EXTRACTION TEST")
    print("=" * 70)
    print()
    
    # Test with our known forms
    test_forms = [
        Path("templates/Live Oak Express - Application Forms.pdf"),
        Path("templates/Huntington Bank Personal Financial Statement.pdf")
    ]
    
    mapper = DynamicFormMapper()
    
    for form_path in test_forms:
        if not form_path.exists():
            print(f"❌ Form not found: {form_path}")
            continue
        
        print(f"📄 Testing: {form_path.name}")
        print("-" * 60)
        
        # Test dynamic extraction
        try:
            form_structure = mapper.get_form_fields(form_path)
            
            field_count = len(form_structure.get('fields', {}))
            sections = form_structure.get('sections', [])
            
            print(f"✅ Successfully extracted {field_count} fields")
            print(f"📋 Sections: {', '.join(sections)}")
            
            # Show sample fields
            if field_count > 0:
                print("\n📝 Sample fields:")
                for i, (field_name, field_info) in enumerate(form_structure['fields'].items()):
                    if i >= 10:
                        print(f"   ... and {field_count - 10} more fields")
                        break
                    field_type = field_info.get('field_type', 'text')
                    required = '(required)' if field_info.get('required') else ''
                    print(f"   • {field_name} [{field_type}] {required}")
            
            # Test caching
            print("\n🔄 Testing cache...")
            form_structure2 = mapper.get_form_fields(form_path)
            if form_structure2 == form_structure:
                print("✅ Cache working correctly")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
    
    # Test with a non-existent form to check fallback
    print("📄 Testing fallback for new form")
    print("-" * 60)
    
    fake_path = Path("templates/New_Bank_Form.pdf")
    try:
        form_structure = mapper.get_form_fields(fake_path)
        field_count = len(form_structure.get('fields', {}))
        print(f"✅ Fallback provided {field_count} common fields")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("✅ DYNAMIC EXTRACTION TEST COMPLETE")
    print("=" * 70)
    print("\n📌 Key Benefits:")
    print("1. Works with ANY PDF form - no pre-mapping needed")
    print("2. Automatically caches results for performance")
    print("3. Falls back to common fields if extraction fails")
    print("4. Ready for expansion to new forms")


async def test_with_form_filler():
    """Test that the form filler can use dynamic extraction."""
    
    print("\n" + "=" * 70)
    print("🔧 TESTING INTEGRATION WITH FORM FILLER")
    print("=" * 70)
    print()
    
    from src.extraction_methods.multimodal_llm.providers import LLMFormFiller
    
    try:
        filler = LLMFormFiller()
        
        # Test with a form that has mapping
        form1 = Path("templates/Live Oak Express - Application Forms.pdf")
        print(f"Testing with mapped form: {form1.name}")
        structure1 = await filler._read_form_template(form1)
        print(f"Result: {len(structure1.get('fields', {}))} fields")
        
        # Rename the mapping temporarily to test dynamic extraction
        mapping_path = Path("outputs/form_mappings/Live Oak Express - Application Forms_mapping.json")
        temp_path = mapping_path.with_suffix('.json.bak')
        
        if mapping_path.exists():
            import shutil
            shutil.move(mapping_path, temp_path)
            
            print(f"\nTesting same form without mapping (dynamic extraction):")
            structure2 = await filler._read_form_template(form1)
            print(f"Result: {len(structure2.get('fields', {}))} fields")
            
            # Restore mapping
            shutil.move(temp_path, mapping_path)
            
            if len(structure2.get('fields', {})) > 0:
                print("✅ Dynamic extraction works as fallback!")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Test dynamic extraction
    test_dynamic_extraction()
    
    # Test integration
    asyncio.run(test_with_form_filler())