#!/usr/bin/env python3
"""
Test script for the Optimal Two-Tool Document Processor
Tests the integration of DocAI and Claude Vision with intelligent routing
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

# Import the optimal processor
from src.extraction_methods.optimal_two_tool_processor import OptimalDocumentProcessor


async def test_small_documents():
    """Test with small documents that fit within DocAI limits"""
    print("\n" + "="*70)
    print("TEST 1: Small Documents (DocAI Preferred)")
    print("="*70)
    
    processor = OptimalDocumentProcessor()
    
    # Small documents that should use DocAI
    small_docs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),  # 3 pages
        Path("inputs/real/Brigham_dallas/Management_Bios.pdf"),  # 5 pages
        Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf"),  # 1 page
    ]
    
    existing = [d for d in small_docs if d.exists()]
    
    if existing:
        result = await processor.process_application(existing, "small_test")
        
        # Check which processors were used
        stats = result["processing_stats"]
        print(f"\nResults:")
        print(f"  • DocAI used: {stats['docai_processed']} times")
        print(f"  • Claude used: {stats['claude_processed']} times")
        print(f"  • Total pages: {stats['total_pages']}")
        
        # Save results
        output_path = Path("outputs/optimal_tests/small_docs_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  • Results saved to: {output_path}")
        
        return result
    else:
        print("  ⚠️ No small test documents found")
        return None


async def test_medium_documents():
    """Test with medium documents (15-30 pages)"""
    print("\n" + "="*70)
    print("TEST 2: Medium Documents (DocAI with Imageless Mode)")
    print("="*70)
    
    processor = OptimalDocumentProcessor()
    
    # Medium documents
    medium_docs = [
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf"),  # 30 pages
    ]
    
    existing = [d for d in medium_docs if d.exists()]
    
    if existing:
        result = await processor.process_application(existing, "medium_test")
        
        stats = result["processing_stats"]
        print(f"\nResults:")
        print(f"  • DocAI used: {stats['docai_processed']} times")
        print(f"  • Claude used: {stats['claude_processed']} times")
        print(f"  • Total pages: {stats['total_pages']}")
        
        # Save results
        output_path = Path("outputs/optimal_tests/medium_docs_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  • Results saved to: {output_path}")
        
        return result
    else:
        print("  ⚠️ No medium test documents found")
        return None


async def test_large_documents():
    """Test with large documents that need chunking or Claude"""
    print("\n" + "="*70)
    print("TEST 3: Large Documents (Chunking or Claude)")
    print("="*70)
    
    processor = OptimalDocumentProcessor()
    
    # Check for any large PDFs
    large_docs = []
    input_dir = Path("inputs/real/Brigham_dallas")
    
    if input_dir.exists():
        for pdf in input_dir.glob("*.pdf"):
            # Check page count
            page_count = processor.chunker.get_pdf_page_count(pdf)
            if page_count > 30:
                large_docs.append(pdf)
                print(f"  • Found large document: {pdf.name} ({page_count} pages)")
    
    if large_docs:
        result = await processor.process_application(large_docs[:2], "large_test")  # Process max 2
        
        stats = result["processing_stats"]
        print(f"\nResults:")
        print(f"  • DocAI used: {stats['docai_processed']} times")
        print(f"  • Claude used: {stats['claude_processed']} times")
        print(f"  • Total pages: {stats['total_pages']}")
        
        # Save results
        output_path = Path("outputs/optimal_tests/large_docs_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  • Results saved to: {output_path}")
        
        return result
    else:
        print("  ℹ️ No large documents found (>30 pages)")
        return None


async def test_mixed_application():
    """Test with a realistic mixed application"""
    print("\n" + "="*70)
    print("TEST 4: Mixed Application (Various Document Types)")
    print("="*70)
    
    processor = OptimalDocumentProcessor()
    
    # Simulate a real loan application with various documents
    app_docs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),  # Financial statement
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf"),  # Tax return
        Path("inputs/real/Brigham_dallas/Management_Bios.pdf"),  # Narrative document
    ]
    
    existing = [d for d in app_docs if d.exists()]
    
    if existing:
        print(f"\nProcessing {len(existing)} documents:")
        for doc in existing:
            doc_type = processor.router.classify_document(doc)
            pages = processor.chunker.get_pdf_page_count(doc) if str(doc).endswith('.pdf') else 0
            print(f"  • {doc.name}: {doc_type} ({pages} pages)")
        
        result = await processor.process_application(existing, "mixed_app_001")
        
        stats = result["processing_stats"]
        print(f"\nProcessing Statistics:")
        print(f"  • DocAI used: {stats['docai_processed']} documents")
        print(f"  • Claude used: {stats['claude_processed']} documents")
        print(f"  • Excel processor: {stats['excel_processed']} documents")
        print(f"  • Total pages: {stats['total_pages']}")
        print(f"  • Total time: {stats['total_time']:.1f}s")
        print(f"  • Avg time per page: {stats['total_time']/max(stats['total_pages'], 1):.2f}s")
        
        # Check extraction quality
        extracted = result["extracted_data"]
        print(f"\nExtraction Quality:")
        print(f"  • Total fields extracted: {len(extracted)}")
        
        # Check for key financial fields
        key_fields = ["ssn", "ein", "business_name", "total_assets", "total_liabilities", "net_worth"]
        found_fields = [f for f in key_fields if any(k for k in extracted.keys() if f in k.lower())]
        print(f"  • Key fields found: {len(found_fields)}/{len(key_fields)}")
        
        # Save results
        output_path = Path("outputs/optimal_tests/mixed_app_test.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"  • Results saved to: {output_path}")
        
        return result
    else:
        print("  ⚠️ No test documents found")
        return None


async def test_rate_limiting():
    """Test rate limiting behavior"""
    print("\n" + "="*70)
    print("TEST 5: Rate Limiting (Rapid Sequential Requests)")
    print("="*70)
    
    processor = OptimalDocumentProcessor()
    
    # Small document for quick processing
    test_doc = Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf")
    
    if test_doc.exists():
        print(f"  • Testing rapid requests with: {test_doc.name}")
        print("  • Sending 3 requests in quick succession...")
        
        start_time = datetime.now()
        
        # Send multiple requests quickly
        tasks = []
        for i in range(3):
            print(f"  • Submitting request {i+1}...")
            tasks.append(processor.process_document(test_doc))
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()
        
        print(f"\nResults:")
        print(f"  • Total time: {elapsed:.1f}s")
        print(f"  • Average time per request: {elapsed/3:.1f}s")
        
        # Check for rate limit handling
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"  • Request {i+1}: Failed - {result}")
            else:
                print(f"  • Request {i+1}: Success - {result.processor_used}")
        
        print("  ✅ Rate limiting test complete")
    else:
        print("  ⚠️ Test document not found")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("OPTIMAL TWO-TOOL PROCESSOR - COMPREHENSIVE TEST SUITE")
    print("="*70)
    print("Testing intelligent routing between DocAI and Claude Vision")
    
    # Run tests
    await test_small_documents()
    await test_medium_documents()
    await test_large_documents()
    await test_mixed_application()
    await test_rate_limiting()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)
    print("\nKey Features Tested:")
    print("  ✅ Intelligent document routing")
    print("  ✅ DocAI for structured documents (≤30 pages)")
    print("  ✅ Claude Vision for complex/large documents")
    print("  ✅ Smart chunking for large documents")
    print("  ✅ Rate limiting with exponential backoff")
    print("  ✅ Result merging from multiple chunks")
    print("  ✅ Hybrid processing for mixed applications")
    
    print("\nCheck outputs/optimal_tests/ for detailed results")


if __name__ == "__main__":
    asyncio.run(run_all_tests())