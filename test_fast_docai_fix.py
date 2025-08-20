#!/usr/bin/env python3
"""
Fast DocAI Structure Processing Test
Tests the DocAI format detection and structure mapping fix with small document set.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from src.template_extraction.comprehensive_processor import ComprehensiveProcessor

async def test_fast_docai():
    """Fast test with 2 PDFs and 1 Excel file"""
    
    test_name = "fast_docai_fix_test"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_id = f"{test_name}_{timestamp}"
    
    print("🚀" + "="*70)
    print(f"  FAST DOCAI STRUCTURE PROCESSING TEST")
    print(f"  Test ID: {test_id}")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("🚀" + "="*70)
    
    # Select small test documents
    test_docs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),          # PDF 1 - Personal Financial Statement
        Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf"),     # PDF 2 - Organization Chart  
        Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx")       # Excel - Profit & Loss
    ]
    
    print(f"\n📋 TEST DOCUMENTS ({len(test_docs)} files):")
    for i, doc in enumerate(test_docs, 1):
        if doc.exists():
            size_mb = doc.stat().st_size / (1024 * 1024)
            print(f"  {i}. ✅ {doc.name} ({size_mb:.2f} MB)")
        else:
            print(f"  {i}. ❌ {doc.name} (NOT FOUND)")
            return
    
    # Initialize processor
    print(f"\n🔧 INITIALIZING COMPREHENSIVE PROCESSOR...")
    processor = ComprehensiveProcessor()
    
    # Create output directory
    output_base = Path("outputs/test_results") / test_id
    output_base.mkdir(parents=True, exist_ok=True)
    print(f"📁 Output directory: {output_base}")
    
    # Process each document individually to see detailed results
    results = {}
    total_categories_populated = 0
    total_fields_extracted = 0
    
    print(f"\n" + "="*50)
    print("  DOCUMENT PROCESSING")
    print("="*50)
    
    for i, doc_path in enumerate(test_docs, 1):
        print(f"\n📄 PROCESSING DOCUMENT {i}/{len(test_docs)}: {doc_path.name}")
        print(f"   File size: {doc_path.stat().st_size / (1024 * 1024):.2f} MB")
        print(f"   File type: {doc_path.suffix}")
        
        try:
            # Process single document
            result = await processor.process_document(doc_path, test_id)
            
            # Analyze results with recursive field counting
            categories = ["personal_info", "business_info", "financial_data", "tax_data", "debt_schedules", "other_data"]
            doc_populated = 0
            doc_fields = 0
            
            def count_nested_fields(data, depth=0, max_depth=3):
                """Recursively count nested fields."""
                if depth > max_depth:
                    return 0
                
                count = 0
                if isinstance(data, dict):
                    for value in data.values():
                        if isinstance(value, (dict, list)):
                            count += count_nested_fields(value, depth + 1, max_depth)
                        elif value not in [None, "", [], {}]:
                            count += 1
                elif isinstance(data, list):
                    for item in data:
                        count += count_nested_fields(item, depth + 1, max_depth)
                return count
            
            print(f"\n   📊 EXTRACTION RESULTS:")
            for category in categories:
                if category in result and result[category]:
                    doc_populated += 1
                    if isinstance(result[category], dict):
                        # Count top-level sections
                        section_count = len(result[category])
                        # Count nested fields recursively
                        nested_field_count = count_nested_fields(result[category])
                        doc_fields += nested_field_count
                        
                        print(f"     ✅ {category}: {section_count} sections, {nested_field_count} total fields")
                        
                        # Show sample data for first few sections
                        for key, value in list(result[category].items())[:2]:
                            if isinstance(value, dict):
                                nested_count = count_nested_fields(value)
                                print(f"        • {key}: {len(value)} keys, {nested_count} fields")
                            elif isinstance(value, list):
                                print(f"        • {key}: {len(value)} entries")
                            else:
                                print(f"        • {key}: {type(value).__name__}")
                    else:
                        doc_fields += 1
                        print(f"     ✅ {category}: {type(result[category]).__name__}")
                else:
                    print(f"     ❌ {category}: EMPTY")
            
            # Check extraction method and confidence from per-document metadata
            if "metadata" in result and "document_extractions" in result["metadata"]:
                doc_extractions = result["metadata"]["document_extractions"]
                if doc_path.name in doc_extractions:
                    doc_meta = doc_extractions[doc_path.name]
                    extraction_method = doc_meta.get("extraction_method", "unknown")
                    extraction_confidence = doc_meta.get("extraction_confidence", 0)
                    
                    print(f"\n   🔍 EXTRACTION METADATA:")
                    print(f"     • Method: {extraction_method}")
                    print(f"     • Confidence: {extraction_confidence:.1%}")
                    
                    # Check for DocAI specific metadata
                    if "docai_metadata" in doc_meta:
                        print(f"     • DocAI processor used: ✅")
                    else:
                        print(f"     • DocAI processor used: ❌")
                else:
                    # Fallback to direct metadata (shouldn't happen with new structure)
                    extraction_method = result["metadata"].get("extraction_method", "unknown")
                    extraction_confidence = result["metadata"].get("extraction_confidence", 0)
                    print(f"\n   🔍 EXTRACTION METADATA:")
                    print(f"     • Method: {extraction_method}")
                    print(f"     • Confidence: {extraction_confidence:.1%}")
                    print(f"     • DocAI processor used: ❌")
            else:
                extraction_method = "unknown"
                extraction_confidence = 0
                print(f"\n   🔍 EXTRACTION METADATA:")
                print(f"     • Method: {extraction_method}")
                print(f"     • Confidence: {extraction_confidence:.1%}")
                print(f"     • DocAI processor used: ❌")
            
            print(f"\n   📈 DOCUMENT SUMMARY:")
            print(f"     • Categories populated: {doc_populated}/{len(categories)} ({doc_populated/len(categories)*100:.1f}%)")
            print(f"     • Total fields extracted: {doc_fields}")
            
            total_categories_populated += doc_populated
            total_fields_extracted += doc_fields
            
            # Store results using new per-document metadata structure
            if "metadata" in result and "document_extractions" in result["metadata"]:
                doc_extractions = result["metadata"]["document_extractions"]
                if doc_path.name in doc_extractions:
                    doc_meta = doc_extractions[doc_path.name]
                    extraction_method = doc_meta.get("extraction_method", "unknown")
                    extraction_confidence = doc_meta.get("extraction_confidence", 0)
                else:
                    extraction_method = "unknown"
                    extraction_confidence = 0
            else:
                extraction_method = "unknown"  
                extraction_confidence = 0
            
            results[doc_path.name] = {
                "categories_populated": doc_populated,
                "total_categories": len(categories),
                "fields_extracted": doc_fields,
                "extraction_method": extraction_method,
                "extraction_confidence": extraction_confidence
            }
            
            print(f"   ✅ Document processed successfully!")
            
        except Exception as e:
            print(f"   ❌ PROCESSING FAILED: {e}")
            results[doc_path.name] = {
                "error": str(e),
                "categories_populated": 0,
                "fields_extracted": 0
            }
    
    # Generate test summary
    print(f"\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    successful_docs = sum(1 for r in results.values() if "error" not in r)
    avg_categories = total_categories_populated / len(test_docs) if test_docs else 0
    
    print(f"\n📊 OVERALL RESULTS:")
    print(f"   • Documents processed: {successful_docs}/{len(test_docs)}")
    print(f"   • Total categories populated: {total_categories_populated}")
    print(f"   • Average categories per doc: {avg_categories:.1f}/6")
    print(f"   • Total fields extracted: {total_fields_extracted}")
    print(f"   • Overall success rate: {avg_categories/6*100:.1f}%")
    
    print(f"\n📋 INDIVIDUAL DOCUMENT RESULTS:")
    for doc_name, result in results.items():
        if "error" in result:
            print(f"   ❌ {doc_name}: FAILED - {result['error']}")
        else:
            success_rate = result['categories_populated'] / result['total_categories'] * 100
            print(f"   ✅ {doc_name}: {result['categories_populated']}/6 categories ({success_rate:.1f}%), {result['fields_extracted']} fields")
            print(f"      Method: {result['extraction_method']}, Confidence: {result['extraction_confidence']:.1%}")
    
    # Save test results
    test_summary = {
        "test_id": test_id,
        "timestamp": datetime.now().isoformat(),
        "test_type": "fast_docai_structure_processing",
        "documents_tested": [str(doc) for doc in test_docs],
        "total_documents": len(test_docs),
        "successful_documents": successful_docs,
        "total_categories_populated": total_categories_populated,
        "total_fields_extracted": total_fields_extracted,
        "average_categories_per_doc": avg_categories,
        "overall_success_rate": avg_categories/6*100,
        "individual_results": results
    }
    
    # Save summary to output folder
    summary_path = output_base / "test_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(test_summary, f, indent=2, default=str)
    
    print(f"\n💾 TEST RESULTS SAVED:")
    print(f"   • Summary: {summary_path}")
    print(f"   • Individual extractions: {output_base.parent / test_id / 'part1_document_processing' / 'extractions'}")
    print(f"   • Master data: {output_base.parent / test_id / 'part1_document_processing' / 'master_data.json'}")
    
    # Performance assessment
    if avg_categories >= 4:
        print(f"\n🎉 TEST RESULT: EXCELLENT - DocAI structure processing working correctly!")
    elif avg_categories >= 3:
        print(f"\n✅ TEST RESULT: GOOD - Most categories populated, minor improvements possible")
    elif avg_categories >= 2:
        print(f"\n⚠️  TEST RESULT: PARTIAL - Some categories working, needs investigation")
    else:
        print(f"\n❌ TEST RESULT: POOR - DocAI structure processing needs debugging")
    
    print(f"\n🏁 Fast test complete! Check {output_base} for detailed results.")
    return test_summary

if __name__ == "__main__":
    asyncio.run(test_fast_docai())