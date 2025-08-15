#!/usr/bin/env python3
"""
Runner for the fast merge validation test.
Tests with just 2 PDFs and 2 spreadsheets for quick iteration.
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.integration.test_fast_merge_validation import FastMergeValidationTest


async def run_test():
    """Run the fast test with timing"""
    import time
    
    print("\n🚀 Starting Fast Merge Validation Test")
    print("   (2 PDFs + 2 Spreadsheets)")
    print("   Expected runtime: ~2 minutes\n")
    
    start_time = time.time()
    
    test = FastMergeValidationTest()
    results = await test.run_test()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Test completed in {elapsed:.1f} seconds")
    
    return 0 if results.get("merge_success") else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_test())
    sys.exit(exit_code)