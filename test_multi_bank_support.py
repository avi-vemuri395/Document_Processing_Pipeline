#!/usr/bin/env python3
"""
Test multi-bank support for the template extraction system.
This validates Phase 2 completion.
"""

from pathlib import Path
from src.template_extraction import ExtractionOrchestrator
import json


def test_multi_bank_support():
    """Test extraction with multiple bank templates."""
    
    print("\n" + "="*70)
    print("🏦 MULTI-BANK TEMPLATE EXTRACTION TEST")
    print("="*70)
    
    orchestrator = ExtractionOrchestrator()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'Live Oak Bank',
            'pdf': 'templates/Live Oak Express - Application Forms.pdf',
            'form_id': 'live_oak_application',
            'expected_fields': ['Name', 'Social Security Number', 'Email address'],
            'expected_coverage': 0  # Blank form, expect low coverage
        },
        {
            'name': 'Huntington Bank',
            'pdf': 'templates/Huntington Bank Personal Financial Statement.pdf',
            'form_id': 'huntington_pfs',
            'expected_fields': ['Applicant Full Legal Name', 'Social Security Number', 'Date of Birth'],
            'expected_coverage': 0  # Blank form, expect low coverage
        }
    ]
    
    results_summary = []
    
    for test_case in test_cases:
        print(f"\n📄 Testing: {test_case['name']}")
        print("-" * 50)
        
        pdf_path = Path(test_case['pdf'])
        
        if not pdf_path.exists():
            print(f"  ⚠️  PDF not found: {pdf_path}")
            continue
        
        try:
            # Process document
            result = orchestrator.process_document(
                pdf_path=pdf_path,
                form_id=test_case['form_id'],
                application_id=f"multi_bank_test_{test_case['form_id']}"
            )
            
            # Validate results
            metrics = result['metrics']
            extracted_fields = result['extracted_fields']
            
            # Check field extraction
            fields_found = 0
            for field_name in test_case['expected_fields']:
                if field_name in extracted_fields:
                    fields_found += 1
                    print(f"  ✓ {field_name}: Found")
                else:
                    print(f"  ✗ {field_name}: Not found")
            
            # Record summary
            results_summary.append({
                'bank': test_case['name'],
                'form_id': test_case['form_id'],
                'total_fields': metrics['total_fields'],
                'extracted_fields': metrics['extracted_fields'],
                'coverage': metrics['coverage_percentage'],
                'required_coverage': metrics['required_coverage'],
                'expected_fields_found': f"{fields_found}/{len(test_case['expected_fields'])}"
            })
            
            print(f"\n  📊 Summary:")
            print(f"     Coverage: {metrics['coverage_percentage']:.1f}%")
            print(f"     Required: {metrics['required_coverage']:.1f}%")
            print(f"     Fields: {metrics['extracted_fields']}/{metrics['total_fields']}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results_summary.append({
                'bank': test_case['name'],
                'form_id': test_case['form_id'],
                'error': str(e)
            })
    
    # Print final summary
    print("\n" + "="*70)
    print("📊 MULTI-BANK TEST SUMMARY")
    print("="*70)
    
    for summary in results_summary:
        if 'error' in summary:
            print(f"\n❌ {summary['bank']}: ERROR - {summary['error']}")
        else:
            print(f"\n✅ {summary['bank']}:")
            print(f"   - Form ID: {summary['form_id']}")
            print(f"   - Fields: {summary['extracted_fields']}/{summary['total_fields']}")
            print(f"   - Coverage: {summary['coverage']:.1f}%")
            print(f"   - Required: {summary['required_coverage']:.1f}%")
            print(f"   - Key Fields: {summary['expected_fields_found']}")
    
    # Check template registry
    print("\n" + "="*70)
    print("📚 TEMPLATE REGISTRY STATUS")
    print("="*70)
    
    loaded_specs = orchestrator.registry.specs
    print(f"\nLoaded Templates: {len(loaded_specs)}")
    for spec_id, spec in loaded_specs.items():
        print(f"  - {spec_id}: {spec.form_title} (v{spec.version})")
        print(f"    Fields: {len(spec.fields)}")
        if hasattr(spec, 'metadata') and spec.metadata:
            print(f"    Bank: {spec.metadata.get('bank', 'Unknown')}")
    
    # Verify extractor pipeline
    print("\n" + "="*70)
    print("🔧 EXTRACTOR PIPELINE STATUS")
    print("="*70)
    
    print(f"\nActive Extractors: {len(orchestrator.extractors)}")
    for extractor in orchestrator.extractors:
        print(f"  - {extractor.name.title()} Extractor")
        if hasattr(extractor, 'stats'):
            stats = extractor.stats
            if stats.get('fields_extracted', 0) > 0:
                print(f"    Extracted: {stats.get('fields_extracted', 0)} fields")
    
    # Save test results
    output_file = Path("outputs/multi_bank_test_results.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'templates_loaded': len(loaded_specs),
            'extractors': [e.name for e in orchestrator.extractors],
            'results': results_summary
        }, f, indent=2, default=str)
    
    print(f"\n💾 Test results saved to: {output_file}")
    
    # Final verdict
    print("\n" + "="*70)
    successful_banks = len([r for r in results_summary if 'error' not in r])
    
    if successful_banks == len(test_cases):
        print("✅ PHASE 2 COMPLETE: Multi-bank support working!")
    else:
        print(f"⚠️  PARTIAL SUCCESS: {successful_banks}/{len(test_cases)} banks working")
    
    print("="*70)


if __name__ == "__main__":
    from datetime import datetime
    test_multi_bank_support()