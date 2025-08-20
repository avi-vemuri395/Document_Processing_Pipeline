#!/usr/bin/env python3
"""
Analyze actual redundant API calls and costs.
"""

import json
from pathlib import Path
from collections import defaultdict

def analyze_redundant_calls():
    """Identify actual redundant API calls."""
    
    # Track which documents have been extracted with which methods
    extraction_history = defaultdict(lambda: defaultdict(list))
    
    outputs_dir = Path("outputs/applications")
    test_runs_chronological = sorted(outputs_dir.iterdir(), key=lambda x: x.stat().st_mtime)
    
    total_api_calls = 0
    redundant_api_calls = 0
    total_cost = 0.0
    redundant_cost = 0.0
    
    print("="*80)
    print("REDUNDANT API CALL ANALYSIS")
    print("="*80)
    
    for test_dir in test_runs_chronological:
        if not test_dir.is_dir():
            continue
            
        extractions_dir = test_dir / "part1_document_processing" / "extractions"
        
        if not extractions_dir.exists():
            continue
            
        print(f"\n📁 Test Run: {test_dir.name}")
        test_redundant = 0
        
        for extraction_file in extractions_dir.glob("*_extraction.json"):
            doc_name = extraction_file.stem.replace("_extraction", "")
            
            try:
                with open(extraction_file) as f:
                    data = json.load(f)
                    
                metadata = data.get("metadata", {})
                
                # Check document-specific extractions
                doc_extractions = metadata.get("document_extractions", {})
                
                for doc_file, doc_meta in doc_extractions.items():
                    method = doc_meta.get("extraction_method", "unknown")
                    
                    # Skip pandas (no API cost)
                    if "pandas" in method.lower():
                        continue
                    
                    # Check if this is redundant
                    if doc_file in extraction_history[method]:
                        # This is a redundant extraction!
                        redundant_api_calls += 1
                        test_redundant += 1
                        
                        # Calculate redundant cost
                        if "docai" in method.lower() or "google" in method.lower():
                            redundant_cost += 0.15  # Assume 5 pages * $0.03
                        elif "claude" in method.lower() or "vision" in method.lower() or "llm" in method.lower():
                            redundant_cost += 0.015
                            
                        print(f"  ⚠️  REDUNDANT: {doc_file} already extracted with {method}")
                    else:
                        # First time extraction
                        extraction_history[method][doc_file].append(test_dir.name)
                        
                    # Count total API calls
                    total_api_calls += 1
                    
                    # Calculate total cost
                    if "docai" in method.lower() or "google" in method.lower():
                        total_cost += 0.15  # Assume 5 pages * $0.03
                    elif "claude" in method.lower() or "vision" in method.lower() or "llm" in method.lower():
                        total_cost += 0.015
                    
                # Fallback to top-level metadata
                if not doc_extractions:
                    method = metadata.get("extraction_method", "unknown")
                    
                    if "pandas" not in method.lower() and method != "unknown":
                        if doc_name in extraction_history[method]:
                            redundant_api_calls += 1
                            test_redundant += 1
                            
                            if "docai" in method.lower() or "google" in method.lower():
                                redundant_cost += 0.15
                            elif "claude" in method.lower() or "vision" in method.lower() or "llm" in method.lower():
                                redundant_cost += 0.015
                                
                            print(f"  ⚠️  REDUNDANT: {doc_name} already extracted with {method}")
                        else:
                            extraction_history[method][doc_name].append(test_dir.name)
                            
                        total_api_calls += 1
                        
                        if "docai" in method.lower() or "google" in method.lower():
                            total_cost += 0.15
                        elif "claude" in method.lower() or "vision" in method.lower() or "llm" in method.lower():
                            total_cost += 0.015
                            
            except Exception as e:
                print(f"  Error reading {extraction_file.name}: {e}")
        
        if test_redundant > 0:
            print(f"  📊 Redundant API calls in this test: {test_redundant}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print(f"\n📊 API CALL STATISTICS:")
    print(f"  • Total API calls made: {total_api_calls}")
    print(f"  • Redundant API calls: {redundant_api_calls}")
    print(f"  • Redundancy rate: {(redundant_api_calls/total_api_calls*100):.1f}%" if total_api_calls > 0 else "N/A")
    
    print(f"\n💰 COST ANALYSIS:")
    print(f"  • Total API cost: ${total_cost:.2f}")
    print(f"  • Redundant API cost: ${redundant_cost:.2f}")
    print(f"  • Potential savings: ${redundant_cost:.2f} ({(redundant_cost/total_cost*100):.1f}% reduction)" if total_cost > 0 else "N/A")
    
    print(f"\n⏱️  TIME IMPACT:")
    print(f"  • Average API latency: ~3-5 seconds per call")
    print(f"  • Time wasted on redundant calls: {redundant_api_calls * 4} seconds (~{redundant_api_calls * 4 / 60:.1f} minutes)")
    
    return {
        "total_api_calls": total_api_calls,
        "redundant_api_calls": redundant_api_calls,
        "total_cost": total_cost,
        "redundant_cost": redundant_cost
    }

if __name__ == "__main__":
    results = analyze_redundant_calls()
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    print("\n🎯 IMMEDIATE ACTIONS:")
    print("  1. Implement content-based caching for extractions")
    print("  2. Add file hash calculation to detect unchanged documents")
    print("  3. Create extraction cache that persists between test runs")
    
    print("\n💡 CACHE IMPLEMENTATION STRATEGY:")
    print("""
  class ExtractionCache:
      def __init__(self, cache_dir="outputs/extraction_cache"):
          self.cache_dir = Path(cache_dir)
          self.cache_dir.mkdir(exist_ok=True)
          
      def get_cache_key(self, file_path, extraction_method):
          # Calculate file hash
          file_hash = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
          return f"{file_hash}_{extraction_method}"
          
      def get(self, file_path, extraction_method):
          cache_key = self.get_cache_key(file_path, extraction_method)
          cache_file = self.cache_dir / f"{cache_key}.json"
          
          if cache_file.exists():
              # Check if cache is still valid (e.g., < 24 hours old)
              if (time.time() - cache_file.stat().st_mtime) < 86400:
                  return json.loads(cache_file.read_text())
          return None
          
      def set(self, file_path, extraction_method, data):
          cache_key = self.get_cache_key(file_path, extraction_method)
          cache_file = self.cache_dir / f"{cache_key}.json"
          cache_file.write_text(json.dumps(data, indent=2))
    """)
    
    print("\n📝 INTEGRATION POINTS:")
    print("  • BenchmarkExtractor.extract_all() - Check cache before API call")
    print("  • ComprehensiveProcessor.process_document() - Use cached extractions")
    print("  • Add ENABLE_EXTRACTION_CACHE environment variable")
    print("  • Add --fresh flag to bypass cache when needed")
