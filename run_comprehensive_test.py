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
    print("  1. Process initial documents (Extract ONCE)")
    print("  2. Add documents incrementally (Test merging)")
    print("  3. Test conflict resolution")
    print("  4. Generate all outputs (9 forms + spreadsheets)")
    print("\nEstimated time: 1-2 minutes")
    
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
    
    doc_count = len(list(test_dir.glob("*.pdf")))
    if doc_count < 3:
        print(f"⚠️  Only {doc_count} test documents found (minimum 3 recommended)")
        print(f"  Directory: {test_dir}")
    else:
        print(f"✅ Found {doc_count} test documents")
    
    # Run the async test
    return asyncio.run(run_test())


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)