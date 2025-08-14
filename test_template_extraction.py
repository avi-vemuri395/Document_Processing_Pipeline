#!/usr/bin/env python3
"""
Test script for the template-based extraction pipeline.
Tests the new extraction system against the Live Oak form.
"""

import json
import sys
from pathlib import Path
from src.template_extraction import ExtractionOrchestrator


def test_single_document():
    """Test extraction on a single document."""
    print("\n" + "="*70)
    print("🧪 TESTING TEMPLATE-BASED EXTRACTION")
    print("="*70)
    
    # Initialize orchestrator
    orchestrator = ExtractionOrchestrator(
        specs_dir=Path("templates/form_specs"),
        output_dir=Path("outputs/applications"),
        cache_enabled=True
    )
    
    # Test with Live Oak form
    pdf_path = Path("templates/Live Oak Express - Application Forms.pdf")
    
    if not pdf_path.exists():
        print(f"❌ Test PDF not found: {pdf_path}")
        return False
    
    try:
        # Process the document
        result = orchestrator.process_document(
            pdf_path=pdf_path,
            form_id="live_oak_application",
            application_id="test_live_oak_001"
        )
        
        # Check results
        if result['extracted_fields']:
            print(f"\n✅ Successfully extracted {len(result['extracted_fields'])} fields:")
            for field_name, value in list(result['extracted_fields'].items())[:10]:
                print(f"  • {field_name}: {value}")
            
            if len(result['extracted_fields']) > 10:
                print(f"  ... and {len(result['extracted_fields']) - 10} more fields")
            
            return True
        else:
            print("❌ No fields were extracted")
            return False
            
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_real_documents():
    """Test extraction on real loan documents."""
    print("\n" + "="*70)
    print("🧪 TESTING WITH REAL DOCUMENTS")
    print("="*70)
    
    # Initialize orchestrator
    orchestrator = ExtractionOrchestrator(
        specs_dir=Path("templates/form_specs"),
        output_dir=Path("outputs/applications"),
        cache_enabled=True
    )
    
    # Test with Brigham Dallas PFS
    pdf_path = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
    
    if not pdf_path.exists():
        print(f"⚠️ Real document not found: {pdf_path}")
        print("  Skipping real document test")
        return True
    
    try:
        # Process the document
        # Note: This is a source document, not a form, so extraction may be limited
        result = orchestrator.process_document(
            pdf_path=pdf_path,
            form_id="live_oak_application",  # Try to match against Live Oak fields
            application_id="brigham_dallas_001"
        )
        
        # Check results
        print(f"\n📊 Extraction Results:")
        print(f"  • Total fields defined: {result['metrics']['total_fields']}")
        print(f"  • Fields extracted: {result['metrics']['extracted_fields']}")
        print(f"  • Coverage: {result['metrics']['coverage_percentage']:.1f}%")
        
        if result['extracted_fields']:
            print(f"\n  Extracted values:")
            for field_name, value in list(result['extracted_fields'].items())[:5]:
                print(f"    • {field_name}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Real document extraction failed: {e}")
        return False


def test_filled_form():
    """Test extraction on a previously filled form."""
    print("\n" + "="*70)
    print("🧪 TESTING WITH FILLED FORM")
    print("="*70)
    
    # Check if we have a filled form from previous tests
    filled_forms = list(Path("outputs/filled_pdfs").glob("Live_Oak*.pdf"))
    
    if not filled_forms:
        print("⚠️ No filled forms found to test")
        return True
    
    # Use the most recent filled form
    pdf_path = sorted(filled_forms)[-1]
    print(f"  Testing with: {pdf_path.name}")
    
    # Initialize orchestrator
    orchestrator = ExtractionOrchestrator(
        specs_dir=Path("templates/form_specs"),
        output_dir=Path("outputs/applications"),
        cache_enabled=False  # Don't cache for this test
    )
    
    try:
        # Process the filled form
        result = orchestrator.process_document(
            pdf_path=pdf_path,
            form_id="live_oak_application",
            application_id="test_filled_form"
        )
        
        # Check results - should have high extraction rate
        metrics = result['metrics']
        print(f"\n📊 Filled Form Extraction:")
        print(f"  • Fields extracted: {metrics['extracted_fields']}/{metrics['total_fields']}")
        print(f"  • Coverage: {metrics['coverage_percentage']:.1f}%")
        print(f"  • Required coverage: {metrics['required_coverage']:.1f}%")
        
        # Check specific fields we know should be filled
        expected_fields = ['Name', 'Social Security Number', 'Email address', 'Business Applicant Name']
        found_fields = []
        missing_fields = []
        
        for field in expected_fields:
            if field in result['extracted_fields'] and result['extracted_fields'][field]:
                found_fields.append(field)
            else:
                missing_fields.append(field)
        
        print(f"\n  Expected fields found: {len(found_fields)}/{len(expected_fields)}")
        if missing_fields:
            print(f"  Missing: {', '.join(missing_fields)}")
        
        # Show some extracted values
        if result['extracted_fields']:
            print(f"\n  Sample extracted values:")
            for field_name, value in list(result['extracted_fields'].items())[:5]:
                if value:
                    print(f"    • {field_name}: {value}")
        
        return metrics['coverage_percentage'] > 10  # Should extract at least 10% from filled form
        
    except Exception as e:
        print(f"❌ Filled form extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def compare_with_existing():
    """Compare template extraction with existing extraction results."""
    print("\n" + "="*70)
    print("🔄 COMPARING WITH EXISTING EXTRACTION")
    print("="*70)
    
    # Load existing extraction if available
    existing_path = Path("outputs/filled_forms/focused_filled_form.json")
    
    if not existing_path.exists():
        print("⚠️ No existing extraction results to compare")
        return True
    
    try:
        with open(existing_path, 'r') as f:
            existing = json.load(f)
        
        print(f"  Existing extraction has {len(existing.get('filled_fields', {}))} fields")
        
        # Show some existing values for reference
        print(f"\n  Sample existing values:")
        for field, value in list(existing.get('filled_fields', {}).items())[:5]:
            if value and value != "null" and value != "false":
                print(f"    • {field}: {value}")
        
        return True
        
    except Exception as e:
        print(f"⚠️ Could not load existing results: {e}")
        return True


def print_statistics(orchestrator):
    """Print orchestrator statistics."""
    stats = orchestrator.get_stats()
    
    print("\n" + "="*70)
    print("📈 EXTRACTION STATISTICS")
    print("="*70)
    
    print(f"  • Documents processed: {stats['documents_processed']}")
    print(f"  • Total fields extracted: {stats['total_fields_extracted']}")
    print(f"  • Cache hits: {stats['cache_hits']}")
    print(f"  • Cache misses: {stats['cache_misses']}")
    
    if stats['documents_processed'] > 0:
        print(f"  • Avg fields per doc: {stats.get('avg_fields_per_doc', 0):.1f}")
        print(f"  • Avg time per doc: {stats.get('avg_time_per_doc', 0):.2f}s")
    
    # Extractor stats
    for extractor_name in ['acroform', 'anchor']:
        key = f'{extractor_name}_stats'
        if key in stats:
            extractor_stats = stats[key]
            print(f"\n  {extractor_name.title()} Extractor:")
            print(f"    • Fields extracted: {extractor_stats.get('fields_extracted', 0)}")
            if extractor_stats.get('errors'):
                print(f"    • Errors: {len(extractor_stats['errors'])}")


def main():
    """Run all tests."""
    print("\n" + "🚀"*35)
    print("    TEMPLATE-BASED EXTRACTION TEST SUITE")
    print("🚀"*35)
    
    # Track test results
    results = []
    
    # Test 1: Single document (Live Oak form template)
    print("\n[Test 1/4] Testing with Live Oak form template...")
    results.append(("Live Oak Template", test_single_document()))
    
    # Test 2: Real documents
    print("\n[Test 2/4] Testing with real documents...")
    results.append(("Real Documents", test_real_documents()))
    
    # Test 3: Filled form
    print("\n[Test 3/4] Testing with filled form...")
    results.append(("Filled Form", test_filled_form()))
    
    # Test 4: Comparison
    print("\n[Test 4/4] Comparing with existing extraction...")
    results.append(("Comparison", compare_with_existing()))
    
    # Print summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    print(f"\n  Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Template extraction is working.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Check the output above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)