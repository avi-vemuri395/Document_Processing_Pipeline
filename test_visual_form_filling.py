#!/usr/bin/env python3
"""
Test script for visual form filling approach.
Compares current vs visual mapping coverage.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

async def test_visual_vs_current_mapping():
    """Compare visual mapping against current approach."""
    
    print("\n" + "="*70)
    print("  VISUAL FORM FILLING TEST")
    print("="*70)
    
    # Import services
    from src.template_extraction.form_mapping_service import FormMappingService
    
    # Load existing master data for testing
    test_app_ids = []
    apps_dir = Path("outputs/applications")
    
    if apps_dir.exists():
        for app_dir in apps_dir.iterdir():
            if app_dir.is_dir():
                master_file = app_dir / "part1_document_processing" / "master_data.json"
                if master_file.exists():
                    test_app_ids.append(app_dir.name)
    
    if not test_app_ids:
        print("❌ No test applications found")
        return
    
    test_app_id = test_app_ids[0]
    print(f"📁 Using test application: {test_app_id}")
    
    # Load master data
    master_file = Path(f"outputs/applications/{test_app_id}/part1_document_processing/master_data.json")
    with open(master_file, 'r') as f:
        master_data = json.load(f)
    
    print(f"📊 Master data categories: {list(master_data.keys())}")
    
    # Initialize service
    service = FormMappingService()
    
    # Test forms to compare
    test_forms = [
        ("live_oak", "application", "live_oak_application_v1"),
        ("huntington", "business_app", "huntington_business_app_v1")
    ]
    
    results = {}
    
    for bank, form_type, form_key in test_forms:
        print(f"\n{'='*50}")
        print(f"  TESTING: {bank.upper()} - {form_type}")
        print(f"{'='*50}")
        
        # Get form spec
        form_spec = service.form_specs.get(form_key)
        if not form_spec:
            print(f"❌ Form spec not found: {form_key}")
            continue
        
        total_fields = len(form_spec.get('fields', []))
        print(f"📋 Form has {total_fields} total fields")
        
        # Test 1: Current approach
        print(f"\n1️⃣  CURRENT MAPPING APPROACH:")
        os.environ['USE_VISUAL_FORM_MAPPING'] = 'false'
        
        try:
            current_result = await service._map_fields_to_form(
                master_data, form_spec, form_key
            )
            
            current_mapped = len([v for v in current_result.get('mapped_data', {}).values() 
                                if v is not None and str(v).strip()])
            current_coverage = (current_mapped / total_fields * 100) if total_fields > 0 else 0
            
            print(f"  ✅ Current approach: {current_mapped}/{total_fields} fields ({current_coverage:.1f}%)")
            
        except Exception as e:
            print(f"  ❌ Current approach failed: {e}")
            current_mapped, current_coverage = 0, 0.0
        
        # Test 2: Visual approach
        print(f"\n2️⃣  VISUAL MAPPING APPROACH:")
        os.environ['USE_VISUAL_FORM_MAPPING'] = 'true'
        
        try:
            visual_result = await service._map_fields_to_form(
                master_data, form_spec, form_key
            )
            
            visual_mapped = len([v for v in visual_result.get('mapped_data', {}).values() 
                               if v is not None and str(v).strip()])
            visual_coverage = (visual_mapped / total_fields * 100) if total_fields > 0 else 0
            
            print(f"  ✅ Visual approach: {visual_mapped}/{total_fields} fields ({visual_coverage:.1f}%)")
            
            # Calculate improvement
            improvement = visual_coverage - current_coverage
            improvement_factor = visual_coverage / max(current_coverage, 1)
            
            print(f"\n📈 IMPROVEMENT ANALYSIS:")
            print(f"  • Absolute improvement: +{improvement:.1f} percentage points")
            print(f"  • Relative improvement: {improvement_factor:.1f}x better")
            
            if improvement > 50:
                print(f"  🚀 EXCELLENT improvement!")
            elif improvement > 20:
                print(f"  ✅ Significant improvement!")
            elif improvement > 5:
                print(f"  👍 Good improvement!")
            else:
                print(f"  ⚠️  Minimal improvement")
            
        except Exception as e:
            print(f"  ❌ Visual approach failed: {e}")
            visual_mapped, visual_coverage = 0, 0.0
            improvement = -current_coverage
        
        # Store results
        results[f"{bank}_{form_type}"] = {
            "form_key": form_key,
            "total_fields": total_fields,
            "current": {"mapped": current_mapped, "coverage": current_coverage},
            "visual": {"mapped": visual_mapped, "coverage": visual_coverage},
            "improvement": improvement
        }
    
    # Overall summary
    print(f"\n" + "="*70)
    print(f"  OVERALL TEST RESULTS")
    print(f"="*70)
    
    total_improvement = sum(r["improvement"] for r in results.values())
    avg_improvement = total_improvement / len(results) if results else 0
    
    print(f"\n📊 SUMMARY:")
    print(f"  • Forms tested: {len(results)}")
    print(f"  • Average improvement: +{avg_improvement:.1f} percentage points")
    
    for form_name, data in results.items():
        print(f"  • {form_name}: {data['current']['coverage']:.1f}% → {data['visual']['coverage']:.1f}% (+{data['improvement']:.1f}%)")
    
    # Save detailed results
    results_file = Path(f"visual_mapping_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(results_file, 'w') as f:
        json.dump({
            "test_timestamp": datetime.now().isoformat(),
            "test_app_id": test_app_id,
            "results": results,
            "summary": {
                "total_forms_tested": len(results),
                "average_improvement": avg_improvement,
                "total_improvement": total_improvement
            }
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Recommendation
    if avg_improvement > 30:
        print(f"\n🎯 RECOMMENDATION: Visual mapping shows excellent results! Deploy immediately.")
    elif avg_improvement > 10:
        print(f"\n👍 RECOMMENDATION: Visual mapping shows good improvement. Consider deployment.")
    else:
        print(f"\n🤔 RECOMMENDATION: Visual mapping needs refinement before deployment.")

if __name__ == "__main__":
    asyncio.run(test_visual_vs_current_mapping())