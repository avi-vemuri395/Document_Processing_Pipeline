#!/usr/bin/env python3
"""
Runner for the fast DocAI test.
Tests with 2 PDFs and 1 Excel for quick validation.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the fast test from smoke directory
sys.path.insert(0, str(project_root / "tests" / "smoke"))
from test_fast_docai_fix import test_fast_docai


async def run_test():
    """Run the fast test with timing"""
    import time
    
    print("\n🚀 Starting Fast DocAI Validation Test")
    print("   (2 PDFs + 1 Excel)")
    print("   Expected runtime: ~15 seconds\n")
    
    start_time = time.time()
    
    results = await test_fast_docai()
    
    elapsed = time.time() - start_time
    print(f"\n⏱️  Test completed in {elapsed:.1f} seconds")
    
    # Check if test passed based on categories populated
    success = results and results.get("overall_success_rate", 0) >= 50
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_test())
    sys.exit(exit_code)