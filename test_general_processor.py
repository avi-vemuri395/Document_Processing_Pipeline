#!/usr/bin/env python3
"""Test script for Document AI General Processor integration"""

import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_docai_configuration():
    """Test if DocAI is properly configured"""
    from src.config.docai_config import is_general_processor_configured, DOCAI_CONFIG
    
    print("\n" + "="*60)
    print("📋 DOCUMENT AI CONFIGURATION CHECK")
    print("="*60)
    
    # Check environment variables
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    processor_id = os.getenv("DOCAI_GENERAL_PROCESSOR_ID")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
    
    print(f"\n🔧 Environment Variables:")
    print(f"  • Project ID: {project_id if project_id else '❌ NOT SET'}")
    print(f"  • Processor ID: {processor_id if processor_id else '❌ NOT SET'}")
    print(f"  • Location: {location}")
    
    # Check configuration
    configured = is_general_processor_configured()
    print(f"\n✅ DocAI Configured: {configured}")
    
    if not configured:
        print("\n⚠️ DocAI is not configured. Please set:")
        print("  1. GOOGLE_CLOUD_PROJECT in .env")
        print("  2. DOCAI_GENERAL_PROCESSOR_ID in .env")
        print("  3. Ensure Google Cloud SDK is installed and authenticated")
        return False
    
    return True

async def test_single_document():
    """Test processing a single document with DocAI"""
    from src.extraction_methods.docai_general_processor import GeneralProcessorExtractor
    
    print("\n" + "="*60)
    print("📄 SINGLE DOCUMENT TEST")
    print("="*60)
    
    # Initialize processor
    try:
        processor = GeneralProcessorExtractor()
        print("✅ General Processor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        return
    
    # Test document
    test_file = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
    
    if not test_file.exists():
        # Try alternative test file
        test_files = list(Path("inputs").rglob("*.pdf"))[:1]
        if test_files:
            test_file = test_files[0]
        else:
            print(f"❌ No test PDF files found")
            return
    
    print(f"\nProcessing: {test_file.name}")
    print(f"  • Size: {test_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Process document
    result = await processor.extract(test_file)
    
    if result.get("success"):
        print(f"\n✅ Extraction successful!")
        print(f"  • Text length: {len(result.get('text', ''))} characters")
        print(f"  • Entities found: {len(result.get('entities', []))}")
        print(f"  • Tables found: {len(result.get('tables', []))}")
        print(f"  • Form fields: {len(result.get('form_fields', {}))}")
        print(f"  • Confidence: {result.get('confidence', 0):.2%}")
        
        # Show sample entities
        if result.get('entities'):
            print("\n📊 Sample Entities (first 5):")
            for entity in result['entities'][:5]:
                print(f"  • {entity.get('type', 'unknown')}: {entity.get('text', '')[:50]}")
        
        # Save result for inspection
        output_file = Path("outputs/test_docai_result.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Full result saved to: {output_file}")
    else:
        print(f"\n❌ Extraction failed: {result.get('error')}")

async def test_pipeline_integration():
    """Test the full pipeline with DocAI integration"""
    from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
    
    print("\n" + "="*60)
    print("🔄 PIPELINE INTEGRATION TEST")
    print("="*60)
    
    # Initialize extractor
    try:
        extractor = BenchmarkExtractor()
        print("✅ BenchmarkExtractor initialized")
        
        if extractor.general_processor:
            print("✅ DocAI General Processor integrated")
        else:
            print("⚠️ DocAI not available - will use Claude Vision")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Test documents
    test_dir = Path("inputs/real/Brigham_dallas")
    if not test_dir.exists():
        test_dir = Path("inputs")
    
    # Get sample files
    pdf_files = list(test_dir.rglob("*.pdf"))[:1]
    excel_files = list(test_dir.rglob("*.xlsx"))[:1]
    
    test_files = pdf_files + excel_files
    
    if not test_files:
        print("❌ No test files found")
        return
    
    print(f"\n📁 Testing with {len(test_files)} file(s):")
    for f in test_files:
        print(f"  • {f.name} ({f.suffix})")
    
    # Process files
    result = await extractor.extract_all(test_files)
    
    # Check metadata
    metadata = result.get('_metadata', {})
    print(f"\n📊 Processing Results:")
    print(f"  • Processing time: {metadata.get('processing_time', 0):.2f} seconds")
    print(f"  • DocAI enabled: {metadata.get('docai_enabled', False)}")
    print(f"  • DocAI processed: {metadata.get('docai_processed', 0)} files")
    print(f"  • Claude Vision processed: {metadata.get('claude_vision_processed', 0)} files")
    
    # Show extraction methods used
    methods = metadata.get('extraction_methods', {})
    print(f"\n🔧 Extraction Methods:")
    for method, details in methods.items():
        if details != 'none':
            print(f"  • {method}: {details}")
    
    # Save result
    output_file = Path("outputs/test_pipeline_result.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n💾 Full result saved to: {output_file}")

async def main():
    """Run all tests"""
    print("\n" + "🤖 "*20)
    print("GOOGLE DOCUMENT AI INTEGRATION TESTS")
    print("🤖 "*20)
    
    # Test 1: Configuration
    config_ok = await test_docai_configuration()
    
    if config_ok:
        # Test 2: Single document with DocAI
        await test_single_document()
        
        # Test 3: Full pipeline integration
        await test_pipeline_integration()
    else:
        print("\n⚠️ Skipping tests - DocAI not configured")
        print("\n📝 Setup Instructions:")
        print("1. Get your Google Cloud Project ID from console.cloud.google.com")
        print("2. Create a General Processor in Document AI")
        print("3. Add to .env file:")
        print("   GOOGLE_CLOUD_PROJECT=your-project-id")
        print("   DOCAI_GENERAL_PROCESSOR_ID=your-processor-id")
        print("4. Authenticate:")
        print("   gcloud auth application-default login")
    
    print("\n" + "="*60)
    print("✅ Tests complete!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())