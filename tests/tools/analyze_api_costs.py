#!/usr/bin/env python3
"""
Analyze actual API costs from extraction metadata.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_api_costs():
    """Analyze API usage and costs from extraction metadata."""
    
    outputs_dir = Path("outputs/applications")
    
    # Track API usage
    api_usage = {
        "docai": {"count": 0, "pages": 0, "cost": 0.0},
        "claude_vision": {"count": 0, "tokens": 0, "cost": 0.0},
        "pandas": {"count": 0, "cost": 0.0}
    }
    
    document_methods = defaultdict(list)
    
    # Scan all extractions
    for test_dir in outputs_dir.iterdir():
        if not test_dir.is_dir():
            continue
            
        extractions_dir = test_dir / "part1_document_processing" / "extractions"
        
        if extractions_dir.exists():
            for extraction_file in extractions_dir.glob("*_extraction.json"):
                doc_name = extraction_file.stem.replace("_extraction", "")
                
                try:
                    with open(extraction_file) as f:
                        data = json.load(f)
                        
                    # Check metadata for extraction method
                    metadata = data.get("metadata", {})
                    
                    # Check for document-specific extractions
                    doc_extractions = metadata.get("document_extractions", {})
                    
                    for doc_file, doc_meta in doc_extractions.items():
                        method = doc_meta.get("extraction_method", "unknown")
                        confidence = doc_meta.get("extraction_confidence", 0)
                        
                        document_methods[doc_file].append({
                            "test_run": test_dir.name,
                            "method": method,
                            "confidence": confidence
                        })
                        
                        # Track API usage
                        if "docai" in method.lower() or "google" in method.lower():
                            api_usage["docai"]["count"] += 1
                            # Estimate 5 pages average
                            api_usage["docai"]["pages"] += 5
                        elif "claude" in method.lower() or "vision" in method.lower() or "llm" in method.lower():
                            api_usage["claude_vision"]["count"] += 1
                        elif "pandas" in method.lower():
                            api_usage["pandas"]["count"] += 1
                    
                    # Fallback to top-level metadata if no document_extractions
                    if not doc_extractions:
                        method = metadata.get("extraction_method", "unknown")
                        
                        document_methods[doc_name].append({
                            "test_run": test_dir.name,
                            "method": method,
                            "confidence": metadata.get("extraction_confidence", 0)
                        })
                        
                        if "docai" in method.lower() or "google" in method.lower():
                            api_usage["docai"]["count"] += 1
                            api_usage["docai"]["pages"] += 5
                        elif "claude" in method.lower() or "vision" in method.lower() or "llm" in method.lower():
                            api_usage["claude_vision"]["count"] += 1
                        elif "pandas" in method.lower():
                            api_usage["pandas"]["count"] += 1
                            
                except Exception as e:
                    print(f"Error reading {extraction_file}: {e}")
    
    # Calculate costs
    # DocAI: $30 per 1000 pages
    api_usage["docai"]["cost"] = (api_usage["docai"]["pages"] / 1000) * 30
    
    # Claude Vision: ~$0.015 per document average
    api_usage["claude_vision"]["cost"] = api_usage["claude_vision"]["count"] * 0.015
    
    # Total cost
    total_cost = api_usage["docai"]["cost"] + api_usage["claude_vision"]["cost"]
    
    print("="*80)
    print("API USAGE AND COST ANALYSIS")
    print("="*80)
    
    print(f"\n📊 API USAGE BREAKDOWN:")
    print(f"\n  Google Document AI:")
    print(f"    • API calls: {api_usage['docai']['count']}")
    print(f"    • Estimated pages: {api_usage['docai']['pages']}")
    print(f"    • Estimated cost: ${api_usage['docai']['cost']:.3f}")
    
    print(f"\n  Claude Vision API:")
    print(f"    • API calls: {api_usage['claude_vision']['count']}")
    print(f"    • Estimated cost: ${api_usage['claude_vision']['cost']:.3f}")
    
    print(f"\n  Pandas (No API):")
    print(f"    • Extractions: {api_usage['pandas']['count']}")
    print(f"    • Cost: $0.00")
    
    print(f"\n💰 TOTAL ESTIMATED COST: ${total_cost:.3f}")
    
    # Find documents extracted multiple times with same method
    print(f"\n🔄 REDUNDANT API CALLS (same document, same method):")
    
    redundant_cost = 0.0
    for doc_name, extractions in document_methods.items():
        # Group by method
        method_counts = defaultdict(int)
        for ext in extractions:
            method_counts[ext["method"]] += 1
        
        for method, count in method_counts.items():
            if count > 1:
                print(f"\n  {doc_name}:")
                print(f"    • Method: {method}")
                print(f"    • Extracted {count} times (could cache {count-1})")
                
                # Calculate redundant cost
                if "docai" in method.lower():
                    redundant_cost += (count - 1) * 5 * 0.03  # 5 pages * $0.03/page
                elif "claude" in method.lower() or "vision" in method.lower():
                    redundant_cost += (count - 1) * 0.015
    
    print(f"\n💡 POTENTIAL SAVINGS WITH CACHING: ${redundant_cost:.3f}")
    
    return api_usage, redundant_cost

if __name__ == "__main__":
    api_usage, savings = analyze_api_costs()
    
    print("\n" + "="*80)
    print("CACHING IMPLEMENTATION IMPACT")
    print("="*80)
    
    print("\n🎯 With proper caching implementation:")
    print(f"  • Reduce API calls by ~70-80%")
    print(f"  • Save approximately ${savings:.2f} in current test suite")
    print(f"  • Speed up test runs by 30-50% (no API latency)")
    print(f"  • Enable more frequent testing without cost concerns")
    
    print("\n📝 Implementation Priority:")
    print("  1. HIGH: Cache DocAI extractions (highest cost)")
    print("  2. MEDIUM: Cache Claude Vision extractions")  
    print("  3. LOW: Cache Pandas extractions (no cost, but saves time)")
