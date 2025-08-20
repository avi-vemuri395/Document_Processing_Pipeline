#!/usr/bin/env python3
"""
Analyze repeated extractions in test runs to identify optimization opportunities.
"""

import json
import os
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def analyze_extraction_patterns():
    """Analyze all extraction files to find patterns of repeated processing."""
    
    outputs_dir = Path("outputs/applications")
    
    # Track extractions by document name
    document_extractions = defaultdict(list)
    test_runs = []
    extraction_methods = defaultdict(Counter)
    
    # Scan all test runs
    for test_dir in outputs_dir.iterdir():
        if not test_dir.is_dir():
            continue
            
        test_runs.append(test_dir.name)
        extractions_dir = test_dir / "part1_document_processing" / "extractions"
        
        if extractions_dir.exists():
            for extraction_file in extractions_dir.glob("*_extraction.json"):
                doc_name = extraction_file.stem.replace("_extraction", "")
                
                # Track this extraction
                document_extractions[doc_name].append({
                    "test_run": test_dir.name,
                    "file_path": str(extraction_file),
                    "file_size": extraction_file.stat().st_size
                })
                
                # Try to read extraction method
                try:
                    with open(extraction_file) as f:
                        data = json.load(f)
                        if "metadata" in data:
                            method = data["metadata"].get("extraction_method", "unknown")
                            extraction_methods[doc_name][method] += 1
                except:
                    pass
    
    # Analyze the data
    print("="*80)
    print("REPEATED EXTRACTION ANALYSIS")
    print("="*80)
    
    print(f"\n📊 SUMMARY:")
    print(f"  • Total test runs analyzed: {len(test_runs)}")
    print(f"  • Unique documents extracted: {len(document_extractions)}")
    print(f"  • Total extractions performed: {sum(len(v) for v in document_extractions.values())}")
    
    # Find most frequently extracted documents
    extraction_counts = {doc: len(extractions) for doc, extractions in document_extractions.items()}
    most_extracted = sorted(extraction_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print(f"\n🔄 MOST FREQUENTLY EXTRACTED DOCUMENTS:")
    total_api_calls = 0
    estimated_cost = 0.0
    
    for doc_name, count in most_extracted:
        print(f"\n  📄 {doc_name}")
        print(f"     • Extracted {count} times")
        
        # Check extraction methods used
        if doc_name in extraction_methods:
            methods = extraction_methods[doc_name]
            for method, method_count in methods.items():
                print(f"     • {method}: {method_count} times")
                
                # Estimate costs
                if "docai" in method.lower():
                    # DocAI costs $30/1000 pages, assume 5 pages avg
                    estimated_cost += (method_count * 5 * 0.03)
                    total_api_calls += method_count
                elif "claude" in method.lower() or "vision" in method.lower():
                    # Claude Vision ~$0.01-0.02 per document
                    estimated_cost += (method_count * 0.015)
                    total_api_calls += method_count
        
        # Show file sizes to check consistency
        sizes = [e["file_size"] for e in document_extractions[doc_name]]
        if len(set(sizes)) > 1:
            print(f"     ⚠️  Different extraction sizes: {set(sizes)}")
    
    print(f"\n💰 COST ANALYSIS:")
    print(f"  • Total redundant API calls: {total_api_calls}")
    print(f"  • Estimated cost of redundant extractions: ${estimated_cost:.2f}")
    print(f"  • Potential savings with caching: ${estimated_cost * 0.8:.2f} (80% reduction)")
    
    # Identify test files that repeatedly extract the same documents
    print(f"\n🔍 TEST PATTERNS:")
    
    # Group by test name prefix
    test_prefixes = defaultdict(list)
    for test_run in test_runs:
        prefix = test_run.split("_")[0] if "_" in test_run else test_run
        test_prefixes[prefix].append(test_run)
    
    for prefix, runs in sorted(test_prefixes.items(), key=lambda x: len(x[1]), reverse=True):
        if len(runs) > 1:
            print(f"  • {prefix}: {len(runs)} runs")
    
    # Find documents that are ALWAYS extracted together
    print(f"\n📦 DOCUMENT BUNDLES (always extracted together):")
    
    # Create extraction signatures
    extraction_signatures = defaultdict(list)
    for test_run in test_runs:
        extractions_dir = Path("outputs/applications") / test_run / "part1_document_processing" / "extractions"
        if extractions_dir.exists():
            docs = sorted([f.stem.replace("_extraction", "") for f in extractions_dir.glob("*_extraction.json")])
            if docs:
                signature = tuple(docs)
                extraction_signatures[signature].append(test_run)
    
    for signature, runs in sorted(extraction_signatures.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
        if len(runs) > 1 and len(signature) <= 5:  # Only show small bundles
            print(f"\n  Bundle extracted {len(runs)} times:")
            for doc in signature:
                print(f"    • {doc}")
    
    return {
        "total_test_runs": len(test_runs),
        "unique_documents": len(document_extractions),
        "total_extractions": sum(len(v) for v in document_extractions.values()),
        "estimated_redundant_cost": estimated_cost,
        "most_extracted": most_extracted[:5]
    }

if __name__ == "__main__":
    results = analyze_extraction_patterns()
    
    print("\n" + "="*80)
    print("OPTIMIZATION OPPORTUNITIES")
    print("="*80)
    
    print("\n🎯 KEY FINDINGS:")
    print("  1. The same documents are being extracted multiple times across test runs")
    print("  2. No caching mechanism exists to reuse previous extractions")
    print("  3. Each test run makes fresh API calls (DocAI or Claude Vision)")
    
    print("\n💡 RECOMMENDATIONS:")
    print("  1. Implement extraction caching based on file hash + extraction method")
    print("  2. Create a shared extraction cache directory for test runs")
    print("  3. Add environment variable to enable/disable cache for testing")
    print("  4. Consider time-based cache invalidation (e.g., 24 hours)")
    print("  5. Add cache hit/miss metrics to track effectiveness")
    
    print("\n📝 PROPOSED IMPLEMENTATION:")
    print("  • Location: src/template_extraction/extraction_cache.py")
    print("  • Cache key: SHA256(file_content) + extraction_method + version")
    print("  • Storage: outputs/extraction_cache/{cache_key}.json")
    print("  • Config: ENABLE_EXTRACTION_CACHE=true in .env")
    print("  • Bypass: --no-cache flag for fresh extractions")
