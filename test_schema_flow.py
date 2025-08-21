#!/usr/bin/env python3
"""
Test script to understand OpenAI schema-driven form mapping flow
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any

# Set environment variables for testing
os.environ['ENABLE_SCHEMA_DRIVEN'] = 'true'
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

async def test_schema_flow():
    """Test the complete schema-driven mapping flow"""
    
    print("=" * 70)
    print("TESTING OPENAI SCHEMA-DRIVEN FORM MAPPING")
    print("=" * 70)
    
    # Check environment
    print("\n📋 ENVIRONMENT CHECK:")
    print(f"  • ENABLE_SCHEMA_DRIVEN: {os.getenv('ENABLE_SCHEMA_DRIVEN')}")
    print(f"  • OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Not set'}")
    
    # Check if schemas exist
    schemas_path = Path("schemas/openai_form_schemas.json")
    if schemas_path.exists():
        with open(schemas_path, 'r') as f:
            schemas = json.load(f)
        print(f"  • Schema file: ✅ Found ({len(schemas)} schemas)")
        print(f"  • Available schemas: {', '.join(schemas.keys())}")
    else:
        print(f"  • Schema file: ❌ Not found at {schemas_path}")
        return
    
    # Check if we have an API key
    if not os.getenv('OPENAI_API_KEY'):
        print("\n❌ OPENAI_API_KEY not set. Schema-driven mapping requires OpenAI API key.")
        print("   To enable, set: export OPENAI_API_KEY='your-key-here'")
        return
    
    # Test importing the mapper
    print("\n🔧 TESTING IMPORT:")
    try:
        from src.schema_driven.openai_form_mapper import OpenAIFormMapper
        print("  • OpenAIFormMapper: ✅ Imported successfully")
    except ImportError as e:
        print(f"  • OpenAIFormMapper: ❌ Import failed: {e}")
        return
    
    # Test initializing the mapper
    print("\n🔧 TESTING INITIALIZATION:")
    try:
        mapper = OpenAIFormMapper(schemas_path)
        print(f"  • Mapper initialized: ✅ {len(mapper.schemas)} schemas loaded")
    except Exception as e:
        print(f"  • Mapper initialization: ❌ Failed: {e}")
        return
    
    # Test with sample data
    print("\n🧪 TESTING WITH SAMPLE DATA:")
    sample_master_data = {
        "personal_info": {
            "primary_applicant": {
                "full_name": "Brigham Dallas",
                "first_name": "Brigham",
                "last_name": "Dallas",
                "ssn": "XXX-XX-3074",
                "email": "brigham@example.com",
                "phone": "555-123-4567",
                "address": {
                    "street": "123 Main St",
                    "city": "Tempe",
                    "state": "AZ",
                    "zip": "85281"
                }
            }
        },
        "business_info": {
            "legal_name": "Waxxpot Group Holdings LLC",
            "dba_name": "Waxxpot",
            "ein": "12-3456789",
            "business_type": "LLC",
            "address": {
                "street": "456 Business Ave",
                "city": "Phoenix",
                "state": "AZ",
                "zip": "85001"
            },
            "phone": "555-987-6543",
            "email": "info@waxxpot.com"
        },
        "financial_info": {
            "total_assets": 4397552,
            "total_liabilities": 2044663,
            "net_worth": 2352889,
            "annual_revenue": 1500000
        }
    }
    
    # Test mapping to Live Oak Application
    test_form = "live_oak_application_v1"
    print(f"\n  Testing form: {test_form}")
    
    try:
        result = await mapper.map_to_form_schema(
            sample_master_data,
            test_form,
            max_retries=1
        )
        
        print(f"  • Mapping result: ✅ {len(result)} fields mapped")
        print("\n  Sample mapped fields:")
        for field, value in list(result.items())[:5]:
            print(f"    - {field}: {value}")
        
    except Exception as e:
        print(f"  • Mapping failed: ❌ {e}")
    
    # Test FormMappingService integration
    print("\n🔄 TESTING FORM MAPPING SERVICE INTEGRATION:")
    try:
        from src.template_extraction.form_mapping_service import FormMappingService
        service = FormMappingService()
        
        # Check if schema-driven will be used
        enable_schema = os.getenv('ENABLE_SCHEMA_DRIVEN', 'false').lower() == 'true'
        print(f"  • FormMappingService initialized: ✅")
        print(f"  • Schema-driven enabled: {'✅' if enable_schema else '❌'}")
        
        # Test the mapping method
        form_spec = service.form_specs.get(test_form, {})
        if form_spec:
            result = await service._schema_driven_mapping_with_fallback(
                sample_master_data,
                form_spec,
                test_form
            )
            
            print(f"  • Service mapping: ✅")
            print(f"    - Method used: {result.get('extraction_method')}")
            print(f"    - Fields mapped: {len(result.get('mapped_data', {}))}")
            print(f"    - Overall confidence: {result.get('overall_confidence', 0):.2f}")
        else:
            print(f"  • Service mapping: ⚠️ No form spec found for {test_form}")
            
    except Exception as e:
        print(f"  • FormMappingService test: ❌ {e}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_schema_flow())