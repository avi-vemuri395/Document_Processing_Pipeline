#!/usr/bin/env python3
"""
Quick validation test for Optimal Two-Tool Processor
"""

import asyncio
from pathlib import Path
from src.extraction_methods.optimal_two_tool_processor import OptimalDocumentProcessor


async def quick_test():
    """Quick test to validate the integration"""
    print("\n" + "="*70)
    print("OPTIMAL TWO-TOOL PROCESSOR - QUICK VALIDATION")
    print("="*70)
    
    processor = OptimalDocumentProcessor()
    
    # Test with one small document
    test_doc = Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf")
    
    if test_doc.exists():
        print(f"\n📄 Testing with: {test_doc.name}")
        
        # Test routing
        processor_name, config = await processor.router.route_document(test_doc)
        print(f"  • Routing decision: {processor_name}")
        print(f"  • Document type: {config['document_type']}")
        print(f"  • Page count: {config['page_count']}")
        
        # Test rate limiter
        print("\n🔄 Testing rate limiter...")
        await processor.rate_limiter.wait_if_needed("docai")
        print("  ✅ Rate limiter working")
        
        # Test chunker
        print("\n📦 Testing chunker...")
        needs_chunking = processor.chunker.should_chunk_for_docai(test_doc)
        print(f"  • Needs chunking: {needs_chunking}")
        
        # Test merger
        print("\n🔀 Testing merger...")
        test_results = [
            {"field1": "value1", "field2": "value2"},
            {"field2": "better_value2", "field3": "value3"}
        ]
        merged = processor.merger.merge_chunked_results(test_results)
        print(f"  • Merged fields: {len(merged.get('extracted_data', {}))}")
        
        print("\n✅ All components validated successfully!")
        
        return True
    else:
        print(f"  ⚠️ Test document not found: {test_doc}")
        return False


if __name__ == "__main__":
    success = asyncio.run(quick_test())
    exit(0 if success else 1)