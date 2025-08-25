#!/usr/bin/env python3
"""
Minimal DocAI debugging test - processes ONE small document to validate:
1. DocAI authentication with quota project
2. Semantic mapping functionality
3. Form coverage improvements
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

# Configure for DocAI semantic mapping
os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'true'
os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'
os.environ['DOCAI_CONFIDENCE_THRESHOLD'] = '0.6'

async def test_docai_minimal():
    """Minimal test with one document."""
    
    print("\n" + "="*70)
    print("  DOCAI DEBUG TEST - MINIMAL")
    print("="*70)
    
    # Step 1: Test DocAI authentication
    print("\n1️⃣ Testing DocAI Authentication...")
    try:
        from google.auth import default
        credentials, project = default()
        print(f"   ✅ Credentials: {type(credentials).__name__}")
        print(f"   ✅ Project: {project}")
        
        # Check quota project
        if hasattr(credentials, '_quota_project_id'):
            print(f"   ✅ Quota Project: {credentials._quota_project_id}")
        
        from google.cloud import documentai
        from google.api_core.client_options import ClientOptions
        
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        print(f"   ✅ DocAI client initialized")
        
    except Exception as e:
        print(f"   ❌ Auth failed: {e}")
        return False
    
    # Step 2: Process ONE small document
    print("\n2️⃣ Processing Single Document...")
    
    from src.template_extraction.comprehensive_processor import ComprehensiveProcessor
    processor = ComprehensiveProcessor()
    
    # Use a business tax return that has more business fields
    # This should give better coverage for Live Oak Application
    test_doc = Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf")
    
    if not test_doc.exists():
        print(f"   ❌ Test document not found: {test_doc}")
        return False
    
    app_id = f"debug_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"   📄 Document: {test_doc.name}")
    print(f"   📁 App ID: {app_id}")
    
    try:
        # Process with DocAI
        result = await processor.process_document(test_doc, app_id)
        
        # Check for DocAI fields
        docai_count = 0
        for category in ['personal_info', 'business_info', 'financial_data']:
            if category in result:
                for key in result[category].keys():
                    if key.startswith('docai_'):
                        if isinstance(result[category][key], dict):
                            docai_count += len(result[category][key])
        
        print(f"   ✅ Processing complete")
        print(f"   📊 DocAI fields extracted: {docai_count}")
        
        # Check if DocAI was actually used
        metadata = result.get('metadata', {})
        extraction_method = metadata.get('extraction_method', 'unknown')
        print(f"   🔧 Extraction method: {extraction_method}")
        
        if docai_count == 0:
            print(f"   ⚠️  No DocAI fields found - may have fallen back to Claude Vision")
        
    except Exception as e:
        print(f"   ❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 3: Test semantic mapping
    print("\n3️⃣ Testing Semantic Mapping...")
    
    from src.template_extraction.form_mapping_service import FormMappingService
    service = FormMappingService()
    
    # Load the master data
    master_file = Path(f"outputs/applications/{app_id}/part1_document_processing/master_data.json")
    
    if not master_file.exists():
        print(f"   ❌ Master data not found")
        return False
    
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    # Test on one form
    test_form_key = "live_oak_application_v1"
    form_spec = service.form_specs.get(test_form_key)
    
    if not form_spec:
        print(f"   ❌ Form spec not found")
        return False
    
    try:
        result = await service._map_fields_to_form(
            master_data, form_spec, test_form_key
        )
        
        mapped_fields = result.get('mapped_data', {})
        filled = len([v for v in mapped_fields.values() if v])
        total = len(form_spec.get('fields', []))
        coverage = (filled / total * 100) if total > 0 else 0
        
        print(f"   ✅ Mapping complete")
        print(f"   📊 Coverage: {filled}/{total} fields ({coverage:.1f}%)")
        print(f"   🔧 Method: {result.get('extraction_method', 'unknown')}")
        print(f"   📈 Confidence: {result.get('overall_confidence', 0):.2%}")
        
        # Show sample fields
        if mapped_fields:
            print(f"\n   Sample mapped fields:")
            for field, value in list(mapped_fields.items())[:3]:
                if value:
                    print(f"     • {field}: {str(value)[:50]}")
        
        # Success criteria
        if coverage >= 50:
            print(f"\n   ✅ SUCCESS: Good coverage achieved!")
            return True
        else:
            print(f"\n   ⚠️  Coverage below 50% - needs investigation")
            return False
            
    except Exception as e:
        print(f"   ❌ Mapping failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run minimal debug test."""
    success = await test_docai_minimal()
    
    print("\n" + "="*70)
    if success:
        print("  ✅ TEST PASSED")
    else:
        print("  ❌ TEST FAILED - Check logs above")
    print("="*70)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)