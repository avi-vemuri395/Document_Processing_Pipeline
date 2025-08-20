#!/usr/bin/env python3
"""
Test runner for PDF chunking functionality.
Runs both validation and comprehensive tests.
"""

import subprocess
import sys
from pathlib import Path

def run_test(test_path: Path, description: str) -> bool:
    """Run a test and return success status"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run([
            sys.executable, str(test_path)
        ], check=True, capture_output=False)
        print(f"\n✅ {description} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} - FAILED (exit code: {e.returncode})")
        return False
    except Exception as e:
        print(f"\n❌ {description} - ERROR: {e}")
        return False

def main():
    """Run all chunking tests"""
    print("🤖 PDF Chunking Test Suite")
    print("="*60)
    
    # Define tests
    tests = [
        (
            Path("tests/unit/test_pdf_chunking_validation.py"),
            "Chunking Requirements Validation"
        ),
        (
            Path("tests/integration/test_docai_pdf_chunking.py"), 
            "Comprehensive Chunking Integration Test"
        )
    ]
    
    # Run tests
    results = []
    for test_path, description in tests:
        if test_path.exists():
            success = run_test(test_path, description)
            results.append((description, success))
        else:
            print(f"\n❌ Test file not found: {test_path}")
            results.append((description, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {status}: {description}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("🔧 Some tests failed - see output above")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)