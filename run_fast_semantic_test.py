#!/usr/bin/env python3
"""
Runner for the fast semantic validation test.
Tests with 3 PDFs and 2 spreadsheets for quick iteration.
Expected runtime: ~2-3 minutes
"""

import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.integration.test_fast_semantic_validation import FastSemanticValidationTest


async def run_test():
    """Run the fast test with timing"""
    import time
    
    print("\n🚀 Starting Fast Semantic Validation Test")
    print("   (3 PDFs + 2 Spreadsheets)")
    print("   Testing: DocAI → Semantic Mapping → Form Coverage")
    print("   Expected runtime: ~2-3 minutes\n")
    
    start_time = time.time()
    
    test = FastSemanticValidationTest()
    results = await test.run_test()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total test time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    
    # Return exit code based on success
    success = (
        results.get("docai_success") and 
        results.get("semantic_mapping_success") and
        not results.get("errors")
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_test())
    sys.exit(exit_code)