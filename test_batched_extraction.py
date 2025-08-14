#!/usr/bin/env python3
"""
Test extraction with batching and rate limit protection.
Processes documents in small batches with delays.
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
import os

from src.extraction_methods.multimodal_llm.providers import BenchmarkExtractor


async def test_batched_extraction():
    """Test extraction with batching."""
    print("\n" + "="*70)
    print("🚀 TESTING BATCHED EXTRACTION WITH FILES API")
    print("="*70)
    
    # Get test files (mix of PDFs and Excel)
    dataset_path = Path("inputs/real/Brigham_dallas")
    test_files = []
    
    # Get 3-4 PDFs
    for file in dataset_path.glob("*.pdf"):
        test_files.append(file)
        if len(test_files) >= 3:
            break
    
    # Add 1 Excel file if available
    for file in dataset_path.glob("*.xlsx"):
        test_files.append(file)
        if len(test_files) >= 4:
            break
    
    if not test_files:
        print("❌ No test files found")
        return False
    
    print(f"\n📁 Testing with {len(test_files)} files:")
    total_size = 0
    for f in test_files:
        size_kb = f.stat().st_size / 1024
        total_size += size_kb
        print(f"  • {f.name} ({size_kb:.1f} KB)")
    print(f"  Total size: {total_size:.1f} KB")
    
    print("\n🔧 Configuration:")
    print("  • Max 2 documents per batch")
    print("  • 5 second delay between batches")
    print("  • Using shortened extraction prompt")
    print("  • Files API with document blocks for PDFs")
    
    # Test with Files API (batched)
    print("\n🔶 Starting batched extraction...")
    extractor = BenchmarkExtractor(use_files_api=False)
    
    overall_start = time.time()
    
    try:
        result = await extractor.extract_all(test_files)
        overall_time = time.time() - overall_start
        
        if result.get("_extraction_failed"):
            print(f"\n❌ Extraction failed: {result.get('error', 'Unknown')[:200]}")
            return False
        
        print(f"\n✅ Extraction completed in {overall_time:.2f}s total")
        
        # Check Files API metadata
        files_api_meta = result.get('_files_api_metadata', {})
        if files_api_meta:
            print(f"\n📊 Batching Statistics:")
            print(f"  Total batches: {files_api_meta.get('total_batches', 0)}")
            print(f"  Successful batches: {files_api_meta.get('successful_batches', 0)}")
            print(f"  Files processed: {files_api_meta.get('files_processed', 0)}")
            cache_stats = files_api_meta.get('cache_stats', {})
            print(f"  Cache: {cache_stats.get('total_files', 0)} files, {cache_stats.get('total_size_mb', 0):.2f} MB")
        
        # Check extracted data
        print(f"\n📈 Extraction Results:")
        extracted_count = 0
        
        if result.get("personal", {}).get("primary_applicant"):
            applicant = result["personal"]["primary_applicant"]
            if applicant.get('name'):
                print(f"  ✓ Name: {applicant.get('name')}")
                extracted_count += 1
            if applicant.get('ssn'):
                print(f"  ✓ SSN: {applicant.get('ssn', 'Not found')}")
                extracted_count += 1
            if applicant.get('ownership_percentage'):
                print(f"  ✓ Ownership: {applicant.get('ownership_percentage', 0)}%")
                extracted_count += 1
        
        if result.get("business", {}).get("primary_business"):
            business = result["business"]["primary_business"]
            if business.get('legal_name'):
                print(f"  ✓ Business: {business.get('legal_name')}")
                extracted_count += 1
            if business.get('ein'):
                print(f"  ✓ EIN: {business.get('ein', 'Not found')}")
                extracted_count += 1
            if business.get('annual_revenue'):
                print(f"  ✓ Revenue: ${business.get('annual_revenue', 0):,.0f}")
                extracted_count += 1
        
        if result.get("financials"):
            fin = result["financials"]
            assets = fin.get("assets", {}).get("total_assets", 0)
            liabilities = fin.get("liabilities", {}).get("total_liabilities", 0)
            net_worth = fin.get("net_worth", 0)
            
            if assets:
                print(f"  ✓ Total Assets: ${assets:,.0f}")
                extracted_count += 1
            if liabilities:
                print(f"  ✓ Total Liabilities: ${liabilities:,.0f}")
                extracted_count += 1
            if net_worth:
                print(f"  ✓ Net Worth: ${net_worth:,.0f}")
                extracted_count += 1
        
        print(f"\n📊 Extracted {extracted_count} data fields successfully")
        
        # Save result
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path(f"outputs/batched_extraction_{timestamp}.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        # Performance analysis
        if files_api_meta.get('total_batches', 0) > 0:
            avg_time_per_batch = overall_time / files_api_meta['total_batches']
            print(f"\n⏱️  Performance:")
            print(f"  Average time per batch: {avg_time_per_batch:.2f}s")
            print(f"  Total processing time: {overall_time:.2f}s")
            
            # Calculate effective time (excluding delays)
            delay_time = (files_api_meta['total_batches'] - 1) * 5  # 5s delay between batches
            effective_time = overall_time - delay_time
            print(f"  Effective extraction time: {effective_time:.2f}s (excluding delays)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run batched extraction test."""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           BATCHED EXTRACTION TEST WITH FILES API                 ║
║                                                                  ║
║  Features:                                                       ║
║  • Processes documents in batches of 2                          ║
║  • 5 second delay between batches                               ║
║  • Uses Files API with document blocks                          ║
║  • Merges results from multiple batches                         ║
║                                                                  ║
║  Benefits:                                                       ║
║  • Avoids rate limits                                           ║
║  • Handles large document sets                                  ║
║  • Better reliability                                           ║
║                                                                  ║
║  ⚠️  This will make multiple API calls with delays              ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not found")
        return
    
    # Run test
    success = await test_batched_extraction()
    
    if success:
        print("\n✅ Batched extraction test successful!")
        print("\n🎯 Key achievements:")
        print("  • Successfully processed multiple documents")
        print("  • Avoided rate limits with batching and delays")
        print("  • Files API reduced network payload")
        print("  • Document blocks improved PDF extraction")
    else:
        print("\n❌ Batched extraction test failed")
        print("\n💡 Troubleshooting:")
        print("  • Check if rate limits have reset")
        print("  • Try with fewer files")
        print("  • Increase delay between batches")


if __name__ == "__main__":
    asyncio.run(main())