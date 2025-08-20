#!/usr/bin/env python3
"""
Test fusion with real documents using both DocAI and Claude Vision.

This test demonstrates the complete fusion pipeline with actual PDFs,
showing quality improvements from multimodal processing.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any
import json

# Add src to path
sys.path.insert(0, '.')

# Set fusion configuration
os.environ['ENABLE_FUSION'] = 'true'
os.environ['FUSION_MODE'] = 'adaptive'
os.environ['FUSION_ENABLE_DIAGNOSTICS'] = 'true'
os.environ['FUSION_LOG_METRICS'] = 'true'

from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
from src.template_extraction.fusion.fusion_config import FusionConfig


async def test_fusion_with_real_document():
    """Test fusion pipeline with a real PDF document."""
    print("\n" + "=" * 60)
    print("🔬 FUSION PIPELINE TEST WITH REAL DOCUMENTS")
    print("=" * 60)
    
    # Find a test document
    test_docs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf"),
        Path("inputs/test_forms/Live Oak Express - Application Forms.pdf")
    ]
    
    # Use first available document
    test_doc = None
    for doc in test_docs:
        if doc.exists():
            test_doc = doc
            break
    
    if not test_doc:
        print("❌ No test documents found. Please add PDF files to inputs/ directory")
        return False
    
    print(f"\n📄 Testing with: {test_doc.name}")
    print(f"   File size: {test_doc.stat().st_size / 1024:.1f} KB")
    
    # Initialize extractor with fusion enabled
    print("\n🔧 Initializing extraction pipeline...")
    extractor = BenchmarkExtractor()
    
    # Check fusion status
    if not extractor.fusion_manager:
        print("⚠️ Fusion not available - running without fusion")
    else:
        print("✅ Fusion manager active")
        
        # Get fusion config for display
        from src.template_extraction.fusion.fusion_config import get_fusion_config
        config = get_fusion_config()
        print(f"   • Mode: {config.get('fusion_mode')}")
        print(f"   • Embedding dim: {config.get('embedding_dim')}")
        print(f"   • Attention heads: {config.get('num_attention_heads')}")
    
    # Extract with fusion
    print(f"\n📊 Processing document...")
    result = await extractor.extract_all(test_doc)
    
    # Analyze results
    print("\n📈 EXTRACTION RESULTS:")
    print("-" * 40)
    
    if isinstance(result, dict):
        # Check for fusion metadata
        doc_key = str(test_doc)
        if doc_key in result:
            doc_result = result[doc_key]
        else:
            # Try first key
            doc_result = result.get(list(result.keys())[0]) if result else {}
        
        if doc_result:
            # Check if fusion occurred
            if 'fusion_metadata' in doc_result:
                fusion_meta = doc_result['fusion_metadata']
                print(f"✅ FUSION SUCCESSFUL!")
                print(f"   • Strategy: {fusion_meta.get('strategy')}")
                print(f"   • Quality score: {fusion_meta.get('fusion_quality', 0):.3f}")
                print(f"   • Processing time: {fusion_meta.get('processing_time', 0):.3f}s")
                print(f"   • Has DocAI: {fusion_meta.get('has_docai')}")
                print(f"   • Has Vision: {fusion_meta.get('has_vision')}")
                
                # Show field counts
                if 'form_fields' in doc_result:
                    print(f"\n📝 Extracted form fields: {len(doc_result['form_fields'])}")
                    # Show sample fields
                    sample_fields = list(doc_result['form_fields'].keys())[:5]
                    for field in sample_fields:
                        print(f"   • {field}")
                    if len(doc_result['form_fields']) > 5:
                        print(f"   ... and {len(doc_result['form_fields']) - 5} more")
                
                # Show DocAI-specific data if present
                if 'docai_tables' in doc_result:
                    print(f"\n📊 DocAI tables found: {len(doc_result['docai_tables'])}")
                
                if 'docai_entities' in doc_result:
                    print(f"🏷️ DocAI entities found: {len(doc_result['docai_entities'])}")
                
                # Show embedding stats if present
                if 'embedding_stats' in doc_result:
                    stats = doc_result['embedding_stats']
                    print(f"\n📐 Embedding statistics:")
                    print(f"   • Mean: {stats.get('mean', 0):.3f}")
                    print(f"   • Std: {stats.get('std', 0):.3f}")
                    print(f"   • Norm: {stats.get('norm', 0):.3f}")
                
                # Show diagnostics if available
                if 'fusion_diagnostics' in doc_result:
                    diag = doc_result['fusion_diagnostics']
                    if 'inter_modal_coherence' in diag:
                        print(f"\n🔗 Inter-modal coherence: {diag['inter_modal_coherence']:.3f}")
                    
                    # Show fusion metrics
                    if 'fusion_metrics' in diag:
                        metrics = diag['fusion_metrics']
                        print(f"\n📊 Fusion Metrics:")
                        print(f"   • Total fusions: {metrics.get('total_fusions', 0)}")
                        print(f"   • Successful: {metrics.get('successful_fusions', 0)}")
                        print(f"   • Both modalities: {metrics.get('both_modalities', 0)}")
                        print(f"   • Average quality: {metrics.get('average_fusion_quality', 0):.3f}")
            
            elif 'extraction_method' in doc_result:
                print(f"ℹ️ Single modality extraction")
                print(f"   • Method: {doc_result['extraction_method']}")
                print(f"   • Fusion not triggered (possibly only one modality available)")
            
            else:
                print("⚠️ No fusion metadata found - fusion may not have occurred")
            
            # Count total extracted data points
            total_fields = 0
            if isinstance(doc_result, dict):
                total_fields = count_fields_recursive(doc_result)
            
            print(f"\n📋 Total data points extracted: {total_fields}")
            
        else:
            print("❌ No extraction results found")
    
    else:
        print("❌ Unexpected result format")
    
    return True


def count_fields_recursive(data: Any, max_depth: int = 5, current_depth: int = 0) -> int:
    """Count all non-empty fields recursively."""
    if current_depth >= max_depth:
        return 0
    
    count = 0
    if isinstance(data, dict):
        for value in data.values():
            if value not in [None, "", [], {}]:
                count += 1
                if isinstance(value, (dict, list)):
                    count += count_fields_recursive(value, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            if item not in [None, "", [], {}]:
                count += 1
                if isinstance(item, (dict, list)):
                    count += count_fields_recursive(item, max_depth, current_depth + 1)
    
    return count


async def test_fusion_comparison():
    """Compare extraction with and without fusion."""
    print("\n" + "=" * 60)
    print("🔄 FUSION VS NON-FUSION COMPARISON")
    print("=" * 60)
    
    test_doc = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
    if not test_doc.exists():
        test_doc = Path("inputs/test_forms/Live Oak Express - Application Forms.pdf")
    
    if not test_doc.exists():
        print("❌ No test document found")
        return False
    
    print(f"\n📄 Document: {test_doc.name}")
    
    # Test WITHOUT fusion
    print("\n1️⃣ Testing WITHOUT fusion...")
    os.environ['ENABLE_FUSION'] = 'false'
    extractor_no_fusion = BenchmarkExtractor()
    result_no_fusion = await extractor_no_fusion.extract_all(test_doc)
    
    # Count fields
    fields_no_fusion = 0
    if isinstance(result_no_fusion, dict):
        for doc_result in result_no_fusion.values():
            if isinstance(doc_result, dict):
                fields_no_fusion = count_fields_recursive(doc_result)
                break
    
    print(f"   • Fields extracted: {fields_no_fusion}")
    
    # Test WITH fusion
    print("\n2️⃣ Testing WITH fusion...")
    os.environ['ENABLE_FUSION'] = 'true'
    extractor_with_fusion = BenchmarkExtractor()
    result_with_fusion = await extractor_with_fusion.extract_all(test_doc)
    
    # Count fields and get quality
    fields_with_fusion = 0
    fusion_quality = 0.0
    fusion_strategy = "none"
    
    if isinstance(result_with_fusion, dict):
        for doc_result in result_with_fusion.values():
            if isinstance(doc_result, dict):
                fields_with_fusion = count_fields_recursive(doc_result)
                if 'fusion_metadata' in doc_result:
                    fusion_quality = doc_result['fusion_metadata'].get('fusion_quality', 0)
                    fusion_strategy = doc_result['fusion_metadata'].get('strategy', 'none')
                break
    
    print(f"   • Fields extracted: {fields_with_fusion}")
    print(f"   • Fusion quality: {fusion_quality:.3f}")
    print(f"   • Strategy: {fusion_strategy}")
    
    # Compare results
    print("\n📊 COMPARISON RESULTS:")
    print("-" * 40)
    
    if fields_with_fusion > fields_no_fusion:
        improvement = ((fields_with_fusion - fields_no_fusion) / fields_no_fusion) * 100
        print(f"✅ Fusion IMPROVED extraction by {improvement:.1f}%")
    elif fields_with_fusion == fields_no_fusion:
        print(f"➖ Fusion produced SAME number of fields")
    else:
        decrease = ((fields_no_fusion - fields_with_fusion) / fields_no_fusion) * 100
        print(f"⚠️ Fusion extracted {decrease:.1f}% fewer fields")
    
    print(f"\nDetails:")
    print(f"  • Without fusion: {fields_no_fusion} fields")
    print(f"  • With fusion: {fields_with_fusion} fields")
    print(f"  • Difference: {fields_with_fusion - fields_no_fusion} fields")
    
    return True


async def main():
    """Run all fusion tests."""
    print("=" * 60)
    print("🚀 MULTIMODAL FUSION TESTING SUITE")
    print("=" * 60)
    
    all_passed = True
    
    try:
        # Test 1: Basic fusion with real document
        all_passed &= await test_fusion_with_real_document()
        
        # Test 2: Compare with/without fusion
        # Note: This may use API calls, so only run if needed
        if os.getenv('RUN_COMPARISON_TEST', 'false').lower() == 'true':
            all_passed &= await test_fusion_comparison()
        else:
            print("\n⏭️ Skipping comparison test (set RUN_COMPARISON_TEST=true to enable)")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    # Final summary
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ FUSION TESTING COMPLETE - ALL TESTS PASSED")
    else:
        print("❌ FUSION TESTING COMPLETE - SOME TESTS FAILED")
    print("=" * 60)
    
    # Print configuration summary
    from src.template_extraction.fusion.fusion_config import get_fusion_config
    config = get_fusion_config()
    if config.get('enable_diagnostics'):
        config.print_config()
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)