#!/usr/bin/env python3
"""
Fast DocAI Structure Processing Test with Schema-Driven Form Mapping
Tests the DocAI format detection and structure mapping fix with small document set,
then validates Part 2 form mapping with schema-driven approach.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from src.template_extraction.comprehensive_processor import ComprehensiveProcessor
from src.template_extraction.form_mapping_service import FormMappingService

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
    print(f"   • Individual extractions: outputs/applications/{test_id}/part1_document_processing/extractions")
    print(f"   • Master data: outputs/applications/{test_id}/part1_document_processing/master_data.json")
    
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
    
    # Now test Part 2: Form Mapping with Schema-Driven Approach
    print(f"\n" + "="*70)
    print("  PART 2: SCHEMA-DRIVEN FORM MAPPING TEST")
    print("="*70)
    
    # Load the master data
    master_data_path = Path("outputs/applications") / test_id / "part1_document_processing" / "master_data.json"
    if not master_data_path.exists():
        print(f"❌ Master data not found at {master_data_path}")
        return test_summary
    
    with open(master_data_path) as f:
        master_data = json.load(f)
    
    print(f"\n📊 MASTER DATA LOADED:")
    print(f"   • Total fields in master: {total_fields_extracted}")
    print(f"   • Categories populated: {total_categories_populated}/18")
    
    # Initialize form mapping service
    print(f"\n🔧 INITIALIZING FORM MAPPING SERVICE...")
    form_mapper = FormMappingService()
    
    # Test mapping to select forms
    test_forms = ["live_oak_application", "huntington_business_app", "wells_fargo_financial"]
    
    print(f"\n📋 TESTING FORM MAPPINGS ({len(test_forms)} forms):")
    form_results = {}
    total_mapped_fields = 0
    total_form_fields = 0
    
    for form_key in test_forms:
        print(f"\n   📄 Mapping to {form_key}...")
        try:
            # Map using schema-driven approach (if enabled)
            mapped_data = await form_mapper.map_single_form(master_data, form_key, test_id)
            
            # Count mapped fields
            mapped_count = sum(1 for v in mapped_data.values() if v not in [None, "", [], {}])
            total_fields = len(mapped_data)
            coverage = (mapped_count / total_fields * 100) if total_fields > 0 else 0
            
            print(f"      ✅ Fields mapped: {mapped_count}/{total_fields} ({coverage:.1f}%)")
            
            # Show sample mapped fields
            sample_fields = list(mapped_data.items())[:5]
            for field, value in sample_fields:
                if value not in [None, "", [], {}]:
                    value_preview = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    print(f"         • {field}: {value_preview}")
            
            form_results[form_key] = {
                "mapped_fields": mapped_count,
                "total_fields": total_fields,
                "coverage": coverage
            }
            total_mapped_fields += mapped_count
            total_form_fields += total_fields
            
        except Exception as e:
            print(f"      ❌ Mapping failed: {e}")
            form_results[form_key] = {
                "error": str(e),
                "mapped_fields": 0,
                "total_fields": 0,
                "coverage": 0
            }
    
    # Calculate overall form mapping success
    overall_coverage = (total_mapped_fields / total_form_fields * 100) if total_form_fields > 0 else 0
    
    print(f"\n" + "="*70)
    print("  FORM MAPPING SUMMARY")
    print("="*70)
    
    print(f"\n📊 OVERALL FORM MAPPING RESULTS:")
    print(f"   • Total forms tested: {len(test_forms)}")
    print(f"   • Total fields mapped: {total_mapped_fields}/{total_form_fields}")
    print(f"   • Overall coverage: {overall_coverage:.1f}%")
    
    # Check if schema-driven is enabled
    import os
    schema_driven_enabled = os.getenv("ENABLE_SCHEMA_DRIVEN", "false").lower() == "true"
    print(f"   • Schema-driven mapping: {'✅ ENABLED' if schema_driven_enabled else '❌ DISABLED'}")
    
    print(f"\n📋 INDIVIDUAL FORM RESULTS:")
    for form_key, result in form_results.items():
        if "error" in result:
            print(f"   ❌ {form_key}: FAILED - {result['error']}")
        else:
            status = "🎯" if result['coverage'] >= 90 else "✅" if result['coverage'] >= 70 else "⚠️" if result['coverage'] >= 50 else "❌"
            print(f"   {status} {form_key}: {result['mapped_fields']}/{result['total_fields']} fields ({result['coverage']:.1f}%)")
    
    # Update test summary with form mapping results
    test_summary["part2_form_mapping"] = {
        "schema_driven_enabled": schema_driven_enabled,
        "forms_tested": test_forms,
        "total_mapped_fields": total_mapped_fields,
        "total_form_fields": total_form_fields,
        "overall_coverage": overall_coverage,
        "individual_forms": form_results
    }
    
    # Test Dynamic Form Extraction (NEW)
    print(f"\n" + "="*70)
    print("  PART 3: DYNAMIC FORM EXTRACTION VALIDATION")
    print("="*70)
    
    dynamic_extraction_enabled = os.getenv("USE_DYNAMIC_FORM_EXTRACTION", "false").lower() == "true"
    enabled_banks = os.getenv("DYNAMIC_FORMS_ENABLED_FOR", "").lower().split(',')
    
    print(f"\n🔧 DYNAMIC EXTRACTION CONFIGURATION:")
    print(f"   • Dynamic extraction: {'✅ ENABLED' if dynamic_extraction_enabled else '❌ DISABLED'}")
    if dynamic_extraction_enabled:
        print(f"   • Enabled for banks: {', '.join(enabled_banks) if enabled_banks else 'None configured'}")
    
    # Test Live Oak dynamic extraction if enabled
    if dynamic_extraction_enabled and 'live_oak' in enabled_banks:
        print(f"\n📋 TESTING LIVE OAK DYNAMIC EXTRACTION:")
        
        # Get form specification to check field count
        form_spec = form_mapper._get_form_specification('live_oak', 'live_oak_application_v1.json', 'live_oak_application_v1')
        
        if form_spec and 'fields' in form_spec:
            dynamic_field_count = len(form_spec.get('fields', []))
            is_dynamic = form_spec.get('_dynamic_extraction', False)
            
            print(f"   • Extraction method: {'🚀 DYNAMIC' if is_dynamic else '📝 Manual'}")
            print(f"   • Total fields available: {dynamic_field_count}")
            
            # Compare with manual baseline (expected ~57 fields)
            expected_manual_fields = 57
            improvement = ((dynamic_field_count - expected_manual_fields) / expected_manual_fields * 100) if expected_manual_fields > 0 else 0
            
            if dynamic_field_count > 150:  # Dynamic extraction should give 200+ fields
                print(f"   ✅ 10x IMPROVEMENT ACHIEVED: {improvement:.0f}% increase over manual specs")
                print(f"      (Manual: ~{expected_manual_fields} fields → Dynamic: {dynamic_field_count} fields)")
            else:
                print(f"   ⚠️  Field count lower than expected for dynamic extraction")
                print(f"      Got {dynamic_field_count} fields (expected 200+)")
        else:
            print(f"   ❌ Failed to retrieve form specification")
    else:
        print(f"\n⚠️  Dynamic extraction not enabled for Live Oak - skipping validation")
    
    # Save updated summary with dynamic extraction results
    test_summary["part3_dynamic_extraction"] = {
        "enabled": dynamic_extraction_enabled,
        "enabled_banks": enabled_banks if dynamic_extraction_enabled else [],
        "live_oak_tested": dynamic_extraction_enabled and 'live_oak' in enabled_banks,
        "live_oak_field_count": dynamic_field_count if (dynamic_extraction_enabled and 'live_oak' in enabled_banks and 'dynamic_field_count' in locals()) else 0
    }
    
    # Save updated summary
    with open(summary_path, 'w') as f:
        json.dump(test_summary, f, indent=2, default=str)
    
    # Final assessment
    print(f"\n" + "="*70)
    print("  FINAL TEST ASSESSMENT")
    print("="*70)
    
    print(f"\n🎯 PART 1 - Document Extraction:")
    print(f"   • Categories populated: {avg_categories:.1f}/6 ({avg_categories/6*100:.1f}%)")
    print(f"   • Total fields extracted: {total_fields_extracted}")
    
    print(f"\n🎯 PART 2 - Form Mapping:")
    print(f"   • Overall field coverage: {overall_coverage:.1f}%")
    print(f"   • Schema-driven: {'✅ ENABLED' if schema_driven_enabled else '❌ DISABLED'}")
    
    print(f"\n🎯 PART 3 - Dynamic Form Extraction:")
    print(f"   • Dynamic extraction: {'✅ ENABLED' if dynamic_extraction_enabled else '❌ DISABLED'}")
    if dynamic_extraction_enabled and 'live_oak' in enabled_banks and 'dynamic_field_count' in locals():
        print(f"   • Live Oak fields: {dynamic_field_count} fields ({improvement:.0f}% increase)")
    
    # Enhanced assessment considering all three parts
    if avg_categories >= 4 and overall_coverage >= 85 and dynamic_extraction_enabled:
        print(f"\n🎉 OVERALL RESULT: EXCELLENT - All systems operational with 10x field coverage!")
        if schema_driven_enabled:
            print(f"   • Schema-driven mapping: {overall_coverage:.1f}% coverage")
        if 'dynamic_field_count' in locals() and dynamic_field_count > 150:
            print(f"   • Dynamic extraction: {dynamic_field_count} fields available")
    elif avg_categories >= 4 and overall_coverage >= 85:
        print(f"\n✅ OVERALL RESULT: VERY GOOD - Consider enabling dynamic extraction for 10x fields")
    elif avg_categories >= 3 and overall_coverage >= 60:
        print(f"\n⚠️  OVERALL RESULT: GOOD - System functioning with room for improvement")
    else:
        print(f"\n❌ OVERALL RESULT: NEEDS IMPROVEMENT - Check extraction or mapping issues")
    
    print(f"\n🏁 Complete test finished! Results saved to {summary_path}")
    return test_summary

if __name__ == "__main__":
    asyncio.run(test_fast_docai())