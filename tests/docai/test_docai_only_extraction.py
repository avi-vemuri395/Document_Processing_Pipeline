#!/usr/bin/env python3
"""
DocAI-Only Extraction Test (No Claude Fallback)
Tests Google Document AI extraction with PDFs that fit within the 15-page limit.
Saves all incremental merges and master JSON for analysis.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.extraction_methods.multimodal_llm.providers import BenchmarkExtractor


async def test_docai_only():
    """Test DocAI extraction without Claude fallback."""
    
    test_id = f"docai_only_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_base = Path("outputs/test_results/docai_tests") / test_id
    output_base.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "🤖" * 35)
    print("  DOCAI-ONLY EXTRACTION TEST (NO CLAUDE FALLBACK)")
    print("🤖" * 35)
    
    # Select 6 PDFs that should work with DocAI (small files < 1.5MB)
    test_pdfs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),              # 0.49 MB - ✅
        Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf"),         # 0.10 MB - ✅
        Path("inputs/real/Brigham_dallas/Management_Bios.pdf"),                 # 0.18 MB - ✅
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf"), # 0.21 MB - ✅
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf"), # Small - ✅
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2021_Form_1065_Tax_Return.pdf"), # Small - ✅
    ]
    
    print(f"\n📋 Test Configuration:")
    print(f"  • Test ID: {test_id}")
    print(f"  • Documents: {len(test_pdfs)} PDFs (all < 1.5MB)")
    print(f"  • Output: {output_base}")
    
    # Verify documents
    print(f"\n📁 Document Verification:")
    valid_docs = []
    for i, doc in enumerate(test_pdfs, 1):
        if doc.exists():
            size_mb = doc.stat().st_size / (1024 * 1024)
            status = "✅" if size_mb < 1.5 else "⚠️"
            print(f"  {i}. {status} {doc.name[:45]:<45} ({size_mb:5.2f} MB)")
            if size_mb < 1.5:  # Only include files that DocAI can handle
                valid_docs.append(doc)
        else:
            print(f"  {i}. ❌ {doc.name} - NOT FOUND")
    
    print(f"\n🚀 Processing {len(valid_docs)} documents with DocAI...")
    
    # Initialize extractor
    extractor = BenchmarkExtractor()
    
    # Create directory for incremental results
    incremental_dir = output_base / "incremental"
    incremental_dir.mkdir(exist_ok=True)
    
    all_results = {}
    combined_data = {}
    
    for i, doc_path in enumerate(valid_docs, 1):
        print(f"\n{'='*60}")
        print(f"  Document {i}/{len(valid_docs)}: {doc_path.name}")
        print(f"{'='*60}")
        
        try:
            # Extract with DocAI
            result = await extractor.extract_all(str(doc_path))
            
            # Get the result for this specific file
            file_key = str(doc_path)
            if file_key in result:
                doc_result = result[file_key]
            else:
                doc_result = result
            
            # Save individual result
            individual_path = incremental_dir / f"{i:02d}_{doc_path.stem}_result.json"
            with open(individual_path, 'w') as f:
                json.dump(doc_result, f, indent=2, default=str)
            
            print(f"  ✅ Saved: {individual_path.name}")
            
            # Print extraction summary
            if isinstance(doc_result, dict) and doc_result.get("success"):
                print(f"\n  📊 DocAI Extraction Success:")
                print(f"    • Text extracted: {len(doc_result.get('text', ''))} chars")
                print(f"    • Form fields: {len(doc_result.get('form_fields', {}))}")
                print(f"    • Tables: {len(doc_result.get('tables', []))}")
                print(f"    • Entities: {len(doc_result.get('entities', []))}")
                print(f"    • Confidence: {doc_result.get('confidence', 0):.1%}")
                
                # Show sample form fields
                form_fields = doc_result.get('form_fields', {})
                if form_fields:
                    print(f"\n    Sample form fields:")
                    for field_name, field_data in list(form_fields.items())[:3]:
                        if isinstance(field_data, dict):
                            value = field_data.get('value', '')[:50]
                            confidence = field_data.get('confidence', 0)
                            print(f"      • {field_name}: {value} ({confidence:.1%})")
                        else:
                            print(f"      • {field_name}: {str(field_data)[:50]}")
            else:
                print(f"  ❌ Extraction failed or returned non-DocAI format")
            
            all_results[doc_path.name] = doc_result
            
            # Merge results
            if not combined_data:
                combined_data = doc_result
            else:
                # Simple merge - in real scenario would use comprehensive processor
                for key, value in doc_result.items():
                    if key not in combined_data:
                        combined_data[key] = value
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            all_results[doc_path.name] = {"error": str(e)}
    
    # Save combined results
    print(f"\n{'='*60}")
    print("  Saving Final Results")
    print("="*60)
    
    # Save all results
    all_results_path = output_base / "all_results.json"
    with open(all_results_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  ✅ All results: {all_results_path}")
    
    # Save combined data
    combined_path = output_base / "combined_data.json"
    with open(combined_path, 'w') as f:
        json.dump(combined_data, f, indent=2, default=str)
    print(f"  ✅ Combined data: {combined_path}")
    
    # Generate summary
    successful = sum(1 for r in all_results.values() 
                    if isinstance(r, dict) and r.get("success"))
    
    summary = {
        "test_id": test_id,
        "timestamp": datetime.now().isoformat(),
        "documents_tested": len(valid_docs),
        "successful_extractions": successful,
        "success_rate": successful / len(valid_docs) * 100 if valid_docs else 0,
        "output_location": str(output_base),
        "files": {
            "all_results": str(all_results_path),
            "combined_data": str(combined_path),
            "incremental_dir": str(incremental_dir)
        }
    }
    
    summary_path = output_base / "test_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  ✅ Summary: {summary_path}")
    
    # Print final statistics
    print(f"\n📈 Final Statistics:")
    print(f"  • Documents processed: {len(valid_docs)}")
    print(f"  • Successful DocAI extractions: {successful}")
    print(f"  • Success rate: {summary['success_rate']:.1f}%")
    print(f"  • Output directory: {output_base}")
    
    # Count total extracted data
    total_fields = 0
    total_tables = 0
    total_entities = 0
    
    for result in all_results.values():
        if isinstance(result, dict) and result.get("success"):
            total_fields += len(result.get('form_fields', {}))
            total_tables += len(result.get('tables', []))
            total_entities += len(result.get('entities', []))
    
    print(f"\n📊 Total Extracted Data:")
    print(f"  • Form fields: {total_fields}")
    print(f"  • Tables: {total_tables}")
    print(f"  • Entities: {total_entities}")
    
    if summary['success_rate'] >= 80:
        print(f"\n🎉 EXCELLENT: {summary['success_rate']:.0f}% DocAI success rate!")
    elif summary['success_rate'] >= 60:
        print(f"\n✅ GOOD: {summary['success_rate']:.0f}% DocAI success rate")
    else:
        print(f"\n⚠️ NEEDS IMPROVEMENT: {summary['success_rate']:.0f}% DocAI success rate")
    
    return summary


if __name__ == "__main__":
    asyncio.run(test_docai_only())