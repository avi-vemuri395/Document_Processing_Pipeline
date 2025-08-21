#!/usr/bin/env python3
"""
Quick test script for enhanced BenchmarkExtractor - tests initialization only.
"""

import sys
from pathlib import Path

# Test imports
try:
    from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import (
        BenchmarkExtractor, 
        NARRATIVE_DOCUMENT_TYPES, 
        STRUCTURED_DOCUMENT_TYPES
    )
    from src.extraction_methods.multimodal_llm.providers.rate_limiter import RateLimitHandler
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_initialization():
    """Test extractor initialization without API calls"""
    print("\n" + "="*50)
    print("TESTING INITIALIZATION")
    print("="*50)
    
    try:
        extractor = BenchmarkExtractor()
        print("✅ BenchmarkExtractor initialized")
        
        # Check rate limiter
        if hasattr(extractor, 'rate_limiter'):
            print(f"✅ Rate limiter available: {type(extractor.rate_limiter).__name__}")
        else:
            print("❌ Rate limiter not found")
            
        return True
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return False


def test_document_types():
    """Test document type constants"""
    print("\n" + "="*50)
    print("TESTING DOCUMENT TYPE CONSTANTS")
    print("="*50)
    
    print(f"📝 Narrative types: {len(NARRATIVE_DOCUMENT_TYPES)}")
    for doc_type in list(NARRATIVE_DOCUMENT_TYPES)[:3]:
        print(f"   • {doc_type}")
    if len(NARRATIVE_DOCUMENT_TYPES) > 3:
        print(f"   ... and {len(NARRATIVE_DOCUMENT_TYPES) - 3} more")
    
    print(f"\n📊 Structured types: {len(STRUCTURED_DOCUMENT_TYPES)}")
    for doc_type in list(STRUCTURED_DOCUMENT_TYPES)[:3]:
        print(f"   • {doc_type}")
    if len(STRUCTURED_DOCUMENT_TYPES) > 3:
        print(f"   ... and {len(STRUCTURED_DOCUMENT_TYPES) - 3} more")
    
    # Check for overlaps
    overlaps = NARRATIVE_DOCUMENT_TYPES.intersection(STRUCTURED_DOCUMENT_TYPES)
    if overlaps:
        print(f"❌ Overlapping types: {overlaps}")
        return False
    else:
        print("✅ No overlapping document types")
        return True


def test_method_signature():
    """Test that extract_all has the new signature"""
    print("\n" + "="*50)
    print("TESTING METHOD SIGNATURE")
    print("="*50)
    
    try:
        import inspect
        
        # Get method signature
        sig = inspect.signature(BenchmarkExtractor.extract_all)
        params = list(sig.parameters.keys())
        
        print(f"extract_all parameters: {params}")
        
        # Check for expected parameters
        if 'file_paths' in params and 'document_types' in params:
            print("✅ Method signature updated correctly")
            
            # Check if document_types is optional
            doc_types_param = sig.parameters['document_types']
            if doc_types_param.default is not inspect.Parameter.empty:
                print("✅ document_types parameter is optional (backward compatible)")
                return True
            else:
                print("❌ document_types parameter is not optional")
                return False
        else:
            print(f"❌ Expected parameters not found")
            return False
            
    except Exception as e:
        print(f"❌ Signature test failed: {e}")
        return False


def test_rate_limiter():
    """Test rate limiter functionality"""
    print("\n" + "="*50)
    print("TESTING RATE LIMITER")
    print("="*50)
    
    try:
        rate_limiter = RateLimitHandler()
        
        print(f"✅ RateLimitHandler created")
        print(f"   • DocAI min interval: {rate_limiter.docai_min_interval}s")
        print(f"   • Claude min interval: {rate_limiter.claude_min_interval}s")
        print(f"   • Max retries: {rate_limiter.max_retries}")
        print(f"   • Base delay: {rate_limiter.base_delay}s")
        print(f"   • Max delay: {rate_limiter.max_delay}s")
        
        return True
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        return False


def main():
    """Run quick validation tests"""
    print("ENHANCED BENCHMARKEXTRACTOR - QUICK VALIDATION")
    print("=" * 70)
    
    tests = [
        ("Initialization", test_initialization),
        ("Document Types", test_document_types),
        ("Method Signature", test_method_signature),
        ("Rate Limiter", test_rate_limiter)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTests passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED - Implementation looks good!")
        print("\nKey features validated:")
        print("• Document type constants defined")
        print("• Rate limiter properly configured")
        print("• Method signature updated with backward compatibility")
        print("• BenchmarkExtractor initializes successfully")
        return True
    else:
        print(f"\n⚠️ {len(results) - passed} tests failed - check implementation")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)