#!/usr/bin/env python3
"""
Test script for DocAI Semantic-First Architecture.
Verifies the new flow: DocAI extraction → Semantic mapping → Form filling
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

async def test_docai_semantic_flow():
    """Test the complete DocAI-first semantic mapping flow."""
    
    print("\n" + "="*70)
    print("  DOCAI SEMANTIC-FIRST ARCHITECTURE TEST")
    print("="*70)
    
    # Set environment for DocAI-first approach
    os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'true'
    os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'  # Disable visual as backup
    
    print("\n📊 Configuration:")
    print(f"  • DocAI Semantic Mapping: ENABLED (Priority 1)")
    print(f"  • Visual Form Mapping: DISABLED (for testing)")
    print(f"  • DocAI-First Routing: ALL documents → DocAI")
    
    # Import services
    from src.template_extraction.form_mapping_service import FormMappingService
    from src.template_extraction.comprehensive_processor import ComprehensiveProcessor
    
    # Check if we have test data
    test_app_ids = []
    apps_dir = Path("outputs/applications")
    
    if apps_dir.exists():
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir():
                master_file = app_dir / "part1_document_processing" / "master_data.json"
                if master_file.exists():
                    test_app_ids.append(app_dir.name)
    
    if not test_app_ids:
        print("\n❌ No test applications found. Running a quick extraction first...")
        
        # Run a quick extraction on a sample document
        processor = ComprehensiveProcessor()
        test_doc = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
        
        if test_doc.exists():
            print(f"\n📄 Processing test document: {test_doc.name}")
            test_app_id = f"semantic_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Process document (this will use DocAI-first routing)
            await processor.process_document(test_doc, test_app_id)
            test_app_ids = [test_app_id]
        else:
            print("❌ No test documents found")
            return
    
    # Use the first test application
    test_app_id = test_app_ids[0]
    print(f"\n📁 Using test application: {test_app_id}")
    
    # Load master data
    master_file = Path(f"outputs/applications/{test_app_id}/part1_document_processing/master_data.json")
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    # Check for DocAI data
    docai_field_count = 0
    for category in ['personal_info', 'business_info', 'financial_data', 'tax_data', 'debt_schedules']:
        if category in master_data:
            for key in master_data[category].keys():
                if key.startswith('docai_'):
                    docai_field_count += len(master_data[category][key])
    
    print(f"\n📊 Master Data Analysis:")
    print(f"  • Categories: {list(master_data.keys())}")
    print(f"  • DocAI fields extracted: {docai_field_count}")
    
    if docai_field_count == 0:
        print("\n⚠️  No DocAI fields found. The document may not have been processed with DocAI.")
        print("    Ensure Google Document AI is configured and available.")
        return
    
    # Test form mapping with semantic mapper
    print(f"\n🧠 Testing Semantic Mapping Flow:")
    service = FormMappingService()
    
    # Test on Live Oak form
    test_form_key = "live_oak_application_v1"
    test_form_spec = service.form_specs.get(test_form_key)
    
    if not test_form_spec:
        print(f"❌ Form spec not found: {test_form_key}")
        return
    
    print(f"  • Form: {test_form_key}")
    print(f"  • Total form fields: {len(test_form_spec.get('fields', []))}")
    
    # Run the mapping (should use semantic mapper as Priority 1)
    print(f"\n🔄 Executing mapping chain...")
    result = await service._map_fields_to_form(
        master_data, test_form_spec, test_form_key
    )
    
    # Analyze results
    print(f"\n📊 RESULTS:")
    print(f"  • Extraction method: {result.get('extraction_method', 'unknown')}")
    print(f"  • Fields mapped: {len(result.get('mapped_data', {}))}")
    print(f"  • Overall confidence: {result.get('overall_confidence', 0.0):.2%}")
    
    if result.get('extraction_method') == 'docai_semantic_mapping':
        print(f"\n✅ SUCCESS: DocAI Semantic Mapping was used (Priority 1)")
        
        # Show metadata if available
        metadata = result.get('metadata', {})
        if metadata:
            print(f"\n📋 Semantic Mapping Metadata:")
            print(f"  • Unmapped fields: {len(metadata.get('unmapped_fields', []))}")
            if metadata.get('consolidation_summary'):
                summary = metadata['consolidation_summary']
                print(f"  • Fields consolidated: {summary.get('fields_mapped', 0)}")
                print(f"  • Average confidence: {summary.get('avg_confidence', 0.0):.2%}")
                low_conf = summary.get('low_confidence_fields', [])
                if low_conf:
                    print(f"  • Low confidence fields: {len(low_conf)}")
    else:
        print(f"\n⚠️  Unexpected extraction method: {result.get('extraction_method')}")
        print("    Semantic mapping may have fallen back to another method.")
    
    # Show sample mapped fields
    mapped_data = result.get('mapped_data', {})
    if mapped_data:
        print(f"\n📝 Sample Mapped Fields (first 5):")
        for i, (field, value) in enumerate(list(mapped_data.items())[:5]):
            if value is not None:
                print(f"  • {field}: {value}")
    
    print("\n" + "="*70)
    print("  TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_docai_semantic_flow())