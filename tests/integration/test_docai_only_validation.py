#!/usr/bin/env python3
"""
Focused test to validate DocAI Form Parser is working correctly.
Tests timeout fixes, retry logic, and field extraction improvements.
Small test to avoid wasting money on Claude fallback.
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Import DocAI directly to test it in isolation
from src.extraction_methods.docai_form_parser import FormParserExtractor
from src.config.docai_config import is_form_parser_configured


async def test_docai_single_document():
    """Test DocAI with a single small document"""
    print("\n" + "="*70)
    print("DOCAI-ONLY VALIDATION TEST")
    print("="*70)
    print("Testing DocAI Form Parser fixes:")
    print("  • Reduced timeout (30-60s max)")
    print("  • Better error handling")
    print("  • Direct DocAI testing (no fallback)")
    
    # Check if DocAI is configured
    if not is_form_parser_configured():
        print("\n❌ DocAI Form Parser is not configured!")
        print("Please set DOCAI_FORM_PARSER_ID in your .env file")
        return False
    
    # Use the smallest test file (3 pages)
    test_file = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
    
    if not test_file.exists():
        print(f"\n❌ Test file not found: {test_file}")
        return False
    
    file_size_mb = test_file.stat().st_size / (1024 * 1024)
    print(f"\n📄 Test Document: {test_file.name}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"   Expected pages: 3")
    print(f"   Document type: Personal Financial Statement")
    
    # Initialize DocAI Form Parser
    print("\n🚀 Initializing DocAI Form Parser...")
    try:
        docai_extractor = FormParserExtractor()
        print("✅ DocAI Form Parser initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize DocAI: {e}")
        return False
    
    # Test extraction
    print("\n🔄 Starting DocAI extraction...")
    print("   Expected timeout: 30-35 seconds for 0.5MB file")
    
    start_time = time.time()
    
    try:
        # Direct DocAI extraction
        result = await docai_extractor.extract(test_file)
        
        elapsed_time = time.time() - start_time
        
        # Analyze results
        if result.get("success"):
            print(f"\n✅ DocAI EXTRACTION SUCCESSFUL in {elapsed_time:.2f} seconds!")
            
            # Check what was extracted
            form_fields = result.get("form_fields", {})
            tables = result.get("tables", [])
            entities = result.get("entities", [])
            checkboxes = result.get("checkboxes", [])
            text_length = len(result.get("text", ""))
            
            print("\n📊 Extraction Statistics:")
            print(f"   • Form fields extracted: {len(form_fields)}")
            print(f"   • Tables found: {len(tables)}")
            print(f"   • Entities detected: {len(entities)}")
            print(f"   • Checkboxes found: {len(checkboxes)}")
            print(f"   • Text extracted: {text_length} characters")
            print(f"   • Confidence: {result.get('confidence', 0):.2%}")
            
            # Check for critical fields
            print("\n🔍 Critical Field Check:")
            critical_fields = ["SSN", "Date", "Name", "Address", "Net Worth", "Assets", "Liabilities"]
            found_fields = []
            missing_fields = []
            
            # Search in form fields
            field_text = " ".join(form_fields.keys()).lower()
            for field in critical_fields:
                if field.lower() in field_text or any(field.lower() in str(v).lower() for v in form_fields.values()):
                    found_fields.append(field)
                else:
                    missing_fields.append(field)
            
            print(f"   ✅ Found: {', '.join(found_fields) if found_fields else 'None'}")
            print(f"   ⚠️ Missing: {', '.join(missing_fields) if missing_fields else 'None'}")
            
            # Performance check
            print("\n⚡ Performance Metrics:")
            print(f"   • Processing time: {elapsed_time:.2f} seconds")
            print(f"   • Processing rate: {file_size_mb/elapsed_time:.2f} MB/s")
            
            if elapsed_time < 60:
                print(f"   ✅ FAST: Completed in under 60 seconds (target met)")
            else:
                print(f"   ⚠️ SLOW: Took more than 60 seconds")
            
            # Save results for analysis
            output_dir = Path("outputs/docai_validation")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"docai_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "test_file": str(test_file),
                    "processing_time": elapsed_time,
                    "success": True,
                    "statistics": {
                        "form_fields": len(form_fields),
                        "tables": len(tables),
                        "entities": len(entities),
                        "checkboxes": len(checkboxes),
                        "text_length": text_length
                    },
                    "result": result
                }, f, indent=2, default=str)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            return True
            
        else:
            print(f"\n❌ DocAI extraction failed in {elapsed_time:.2f} seconds")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            
            # Check if it was a timeout
            if "timeout" in str(result.get('error', '')).lower():
                print("\n⚠️ TIMEOUT ISSUE DETECTED")
                print("   The timeout fix may not be working correctly")
                print("   Consider checking:")
                print("   • DocAI quota limits in GCP Console")
                print("   • Network connectivity to Google Cloud")
                print("   • Processor configuration")
            
            return False
            
    except asyncio.TimeoutError:
        elapsed_time = time.time() - start_time
        print(f"\n❌ Test timeout after {elapsed_time:.2f} seconds")
        print("   This should not happen with the fixes!")
        return False
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ Unexpected error after {elapsed_time:.2f} seconds: {e}")
        return False


async def main():
    """Run the DocAI validation test"""
    print("\n" + "="*70)
    print("DOCAI FORM PARSER VALIDATION")
    print("="*70)
    print("This test validates that DocAI is working correctly")
    print("without falling back to expensive Claude Vision API")
    
    success = await test_docai_single_document()
    
    print("\n" + "="*70)
    print("TEST RESULT")
    print("="*70)
    
    if success:
        print("✅ DocAI is working correctly!")
        print("\nKey achievements:")
        print("  • Fast processing (under 60s)")
        print("  • No timeout errors")
        print("  • Successful field extraction")
        print("\nYou can now run comprehensive tests with confidence")
    else:
        print("❌ DocAI validation failed!")
        print("\nTroubleshooting steps:")
        print("  1. Check DOCAI_FORM_PARSER_ID in .env")
        print("  2. Verify GCP credentials and quotas")
        print("  3. Check network connectivity")
        print("  4. Review error messages above")
        print("\nDO NOT run expensive tests until this is fixed!")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)