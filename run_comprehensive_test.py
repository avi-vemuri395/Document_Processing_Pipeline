#!/usr/bin/env python3
"""
Runner script for the comprehensive end-to-end test.
This script ensures all components are tested in the correct architecture.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.integration.test_comprehensive_end_to_end import ComprehensiveEndToEndTest


async def run_test():
    """Run the comprehensive test with error handling."""
    
    print("\n" + "="*80)
    print("  COMPREHENSIVE TEST RUNNER")
    print("  Testing the Complete New Architecture")
    print("="*80)
    
    print("\nThis test will:")
    print("  Phase 0: Validate DocAI with small documents (NEW!)")
    print("  Phase 1: Process initial documents (Extract ONCE)")
    print("  Phase 2: Add documents incrementally (Test merging)")
    print("  Phase 3: Test conflict resolution")
    print("  Phase 4: Generate all outputs (9 forms + spreadsheets)")
    print("\nFeatures tested:")
    print("  ✅ DocAI Integration (Form Parser + Claude Vision fallback)")
    print("  ✅ Hybrid processing with cost tracking")
    print("  ✅ Structured output validation")
    print("  ✅ Incremental document processing")
    print("\nEstimated time: 5-7 minutes")
    
    try:
        test = ComprehensiveEndToEndTest()
        results = await test.run_complete_lifecycle()
        
        # Check for errors
        errors = results.get("errors", [])
        if errors:
            print(f"\n⚠️  Test completed with {len(errors)} errors")
            return 1
        else:
            print("\n✅ All tests passed successfully!")
            return 0
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main entry point."""
    # Check for required documents
    test_dir = Path("inputs/real/Brigham_dallas")
    if not test_dir.exists():
        print(f"❌ Test documents directory not found: {test_dir}")
        print("  Please ensure test documents are available.")
        return 1
    
    # Count documents by type
    pdf_count = len(list(test_dir.glob("*.pdf")))
    excel_count = len(list(test_dir.glob("*.xlsx")))
    total_count = pdf_count + excel_count
    
    if total_count < 3:
        print(f"⚠️  Only {total_count} test documents found (minimum 3 recommended)")
        print(f"  Directory: {test_dir}")
    else:
        print(f"✅ Found {total_count} test documents ({pdf_count} PDFs, {excel_count} Excel files)")
    
    # Check DocAI status with actual availability testing
    print("\n🤖 DocAI Integration Status:")
    import os
    
    # Test actual DocAI availability (not just environment variables)
    try:
        from src.config.docai_config import is_form_parser_configured
        from src.extraction_methods.docai_form_parser import FormParserExtractor
        
        if is_form_parser_configured():
            # Try to actually initialize DocAI to verify it works
            form_parser = FormParserExtractor()
            print("  ✅ DocAI Form Parser working (authenticated via Application Default Credentials)")
            print(f"     • Processor: {form_parser.processor_name}")
        else:
            print("  ⚠️  DocAI Form Parser not configured (will use Claude Vision only)")
    except ImportError:
        print("  ⚠️  DocAI libraries not available (will use Claude Vision only)")
    except Exception as e:
        print(f"  ❌ DocAI authentication failed: {e}")
        print("     • Try running: gcloud auth application-default login")
    
    # Also show environment status for reference
    if os.environ.get("DOCAI_FORM_PARSER_ID"):
        processor_id = os.environ.get("DOCAI_FORM_PARSER_ID")
        print(f"  ℹ️  Form Parser ID: {processor_id}")
    else:
        print("  ℹ️  No Form Parser ID configured")
    
    # Run the async test
    return asyncio.run(run_test())


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)