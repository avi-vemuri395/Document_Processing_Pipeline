#!/usr/bin/env python3
"""
Focused test to evaluate semantic mapping quality using existing DocAI data.
Tests the mapping accuracy and coverage improvements.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Configure semantic mapping
os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'true'
os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'
os.environ['DOCAI_CONFIDENCE_THRESHOLD'] = '0.6'


async def evaluate_semantic_mapping():
    """Evaluate semantic mapping with existing DocAI data."""
    
    print("\n" + "="*80)
    print("  SEMANTIC MAPPING EVALUATION TEST")
    print("="*80)
    print(f"  Start Time: {datetime.now().isoformat()}")
    
    # Use existing master data with DocAI fields
    test_app_id = "comprehensive_test_20250821_055835"
    master_file = Path(f"outputs/applications/{test_app_id}/part1_document_processing/master_data.json")
    
    if not master_file.exists():
        print(f"❌ Master data not found: {master_file}")
        return
    
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    # Count DocAI fields
    docai_count = 0
    for category in ['personal_info', 'business_info', 'financial_data', 'tax_data']:
        if category in master_data:
            for key in master_data[category].keys():
                if key.startswith('docai_'):
                    if isinstance(master_data[category][key], dict):
                        docai_count += len(master_data[category][key])
    
    print(f"\n📊 Input Data Analysis:")
    print(f"  • Application ID: {test_app_id}")
    print(f"  • DocAI fields available: {docai_count}")
    print(f"  • Data categories: {list(master_data.keys())}")
    
    # Import mapping service
    from src.template_extraction.form_mapping_service import FormMappingService
    service = FormMappingService()
    
    # Test forms to evaluate
    test_forms = [
        ("live_oak_application_v1", "Live Oak Application"),
        ("huntington_business_app_v1", "Huntington Business Application"),
        ("wells_fargo_loan_app_v1", "Wells Fargo Loan Application")
    ]
    
    results_comparison = {}
    
    for form_key, form_name in test_forms:
        print(f"\n{'='*70}")
        print(f"  Testing: {form_name}")
        print("="*70)
        
        form_spec = service.form_specs.get(form_key)
        if not form_spec:
            print(f"  ❌ Form spec not found: {form_key}")
            continue
        
        total_fields = len(form_spec.get('fields', []))
        print(f"  📋 Form has {total_fields} total fields")
        
        # Test WITH semantic mapping
        print(f"\n  1️⃣ WITH Semantic Mapping (DocAI-First):")
        os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'true'
        
        # Force service to reinitialize semantic mapper
        if hasattr(service, '_semantic_mapper'):
            service._semantic_mapper = None
        
        try:
            result_with = await service._map_fields_to_form(
                master_data, form_spec, form_key
            )
            
            mapped_fields = result_with.get('mapped_data', {})
            filled_count = len([v for v in mapped_fields.values() if v is not None and v != ''])
            coverage = (filled_count / total_fields * 100) if total_fields > 0 else 0
            
            print(f"     ✅ Mapping successful")
            print(f"     • Method: {result_with.get('extraction_method', 'unknown')}")
            print(f"     • Fields filled: {filled_count}/{total_fields} ({coverage:.1f}%)")
            print(f"     • Confidence: {result_with.get('overall_confidence', 0.0):.2%}")
            
            # Sample some mapped fields
            sample_fields = []
            for field, value in mapped_fields.items():
                if value and len(sample_fields) < 5:
                    sample_fields.append(f"       - {field}: {str(value)[:50]}")
            
            if sample_fields:
                print(f"     • Sample mappings:")
                for field_str in sample_fields:
                    print(field_str)
            
            with_stats = {
                'filled': filled_count,
                'total': total_fields,
                'coverage': coverage,
                'confidence': result_with.get('overall_confidence', 0.0),
                'method': result_with.get('extraction_method', 'unknown')
            }
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
            with_stats = {'filled': 0, 'total': total_fields, 'coverage': 0, 'confidence': 0, 'method': 'error'}
        
        # Test WITHOUT semantic mapping (fallback)
        print(f"\n  2️⃣ WITHOUT Semantic Mapping (Fallback):")
        os.environ['USE_DOCAI_SEMANTIC_MAPPING'] = 'false'
        os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'
        
        # Force service to reinitialize
        if hasattr(service, '_semantic_mapper'):
            service._semantic_mapper = None
        
        try:
            result_without = await service._map_fields_to_form(
                master_data, form_spec, form_key
            )
            
            mapped_fields = result_without.get('mapped_data', {})
            filled_count = len([v for v in mapped_fields.values() if v is not None and v != ''])
            coverage = (filled_count / total_fields * 100) if total_fields > 0 else 0
            
            print(f"     ✅ Mapping successful")
            print(f"     • Method: {result_without.get('extraction_method', 'unknown')}")
            print(f"     • Fields filled: {filled_count}/{total_fields} ({coverage:.1f}%)")
            print(f"     • Confidence: {result_without.get('overall_confidence', 0.0):.2%}")
            
            without_stats = {
                'filled': filled_count,
                'total': total_fields,
                'coverage': coverage,
                'confidence': result_without.get('overall_confidence', 0.0),
                'method': result_without.get('extraction_method', 'unknown')
            }
            
        except Exception as e:
            print(f"     ❌ Error: {e}")
            without_stats = {'filled': 0, 'total': total_fields, 'coverage': 0, 'confidence': 0, 'method': 'error'}
        
        # Calculate improvement
        if without_stats['filled'] > 0:
            improvement = ((with_stats['filled'] - without_stats['filled']) / without_stats['filled']) * 100
        else:
            improvement = 100 if with_stats['filled'] > 0 else 0
        
        print(f"\n  📈 COMPARISON:")
        print(f"     • With semantic: {with_stats['filled']} fields ({with_stats['coverage']:.1f}%)")
        print(f"     • Without semantic: {without_stats['filled']} fields ({without_stats['coverage']:.1f}%)")
        print(f"     • Improvement: {improvement:+.1f}%")
        
        if improvement > 20:
            print(f"     🚀 Significant improvement with semantic mapping!")
        elif improvement > 0:
            print(f"     ✅ Positive improvement with semantic mapping")
        else:
            print(f"     ⚠️ No improvement detected")
        
        results_comparison[form_key] = {
            'form_name': form_name,
            'with_semantic': with_stats,
            'without_semantic': without_stats,
            'improvement_percentage': improvement
        }
    
    # Final analysis
    print(f"\n" + "="*80)
    print("  FINAL ANALYSIS")
    print("="*80)
    
    avg_improvement = sum(r['improvement_percentage'] for r in results_comparison.values()) / len(results_comparison)
    avg_coverage_with = sum(r['with_semantic']['coverage'] for r in results_comparison.values()) / len(results_comparison)
    avg_coverage_without = sum(r['without_semantic']['coverage'] for r in results_comparison.values()) / len(results_comparison)
    
    print(f"\n📊 Average Results Across All Forms:")
    print(f"  • WITH semantic mapping: {avg_coverage_with:.1f}% average coverage")
    print(f"  • WITHOUT semantic mapping: {avg_coverage_without:.1f}% average coverage")
    print(f"  • Average improvement: {avg_improvement:+.1f}%")
    
    if avg_coverage_with >= 70:
        print(f"\n✅ SUCCESS: Achieved target coverage of 70-85%!")
    elif avg_coverage_with >= 50:
        print(f"\n⚠️ PARTIAL SUCCESS: Improved coverage but below 70% target")
    else:
        print(f"\n❌ NEEDS IMPROVEMENT: Coverage below expectations")
    
    # Save results
    results_file = Path(f"semantic_evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(results_file, 'w') as f:
        json.dump({
            'test_app_id': test_app_id,
            'docai_fields_count': docai_count,
            'forms_tested': results_comparison,
            'averages': {
                'improvement': avg_improvement,
                'coverage_with': avg_coverage_with,
                'coverage_without': avg_coverage_without
            }
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    
    return avg_coverage_with >= 50  # Return success if we achieved at least 50% coverage


if __name__ == "__main__":
    success = asyncio.run(evaluate_semantic_mapping())
    exit(0 if success else 1)