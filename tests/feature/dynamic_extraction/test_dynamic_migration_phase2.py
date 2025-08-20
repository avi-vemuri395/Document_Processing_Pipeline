#!/usr/bin/env python3
"""
Test Dynamic Form Extraction Migration - Phase 2: Live Oak Testing

This test validates the Live Oak migration from manual specifications
to dynamic PDF field extraction, comparing coverage and functionality.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

# Set environment variables for testing
os.environ['USE_DYNAMIC_FORM_EXTRACTION'] = 'true'
os.environ['DYNAMIC_FORMS_ENABLED_FOR'] = 'live_oak'

from src.template_extraction.form_mapping_service import FormMappingService


class DynamicMigrationTester:
    """Test the dynamic migration implementation for Live Oak."""
    
    def __init__(self):
        self.results = {
            "manual": {},
            "dynamic": {},
            "comparison": {}
        }
        
    async def run_live_oak_migration_test(self):
        """
        Test Live Oak migration from manual to dynamic extraction.
        """
        print("\n" + "="*80)
        print("  DYNAMIC MIGRATION TEST - PHASE 2: LIVE OAK")
        print("  Testing: Manual Specs vs Dynamic PDF Extraction")
        print("="*80)
        
        # Test 1: Manual specifications (baseline)
        await self.test_manual_specifications()
        
        # Test 2: Dynamic extraction (new functionality)
        await self.test_dynamic_extraction()
        
        # Test 3: Compare results
        self.compare_results()
        
        # Test 4: Validate integration
        await self.test_integration()
        
        return self.results
    
    async def test_manual_specifications(self):
        """Test the current manual specifications for Live Oak."""
        print("\n" + "─"*60)
        print("  TEST 1: Manual Specifications (Baseline)")
        print("─"*60)
        
        # Temporarily disable dynamic extraction
        os.environ['USE_DYNAMIC_FORM_EXTRACTION'] = 'false'
        
        service = FormMappingService()
        
        # Test Live Oak forms
        live_oak_forms = {
            "application": "live_oak_application_v1.json",
            "pfs": "live_oak_pfs_v1.json", 
            "4506t": "live_oak_4506t_v1.json"
        }
        
        manual_results = {}
        total_manual_fields = 0
        
        for form_type, spec_file in live_oak_forms.items():
            spec_key = spec_file.replace('.json', '')
            form_spec = service.form_specs.get(spec_key)
            
            if form_spec:
                field_count = len(form_spec.get('fields', []))
                manual_results[form_type] = {
                    "spec_key": spec_key,
                    "field_count": field_count,
                    "source": "manual_json"
                }
                total_manual_fields += field_count
                print(f"    📝 {form_type}: {field_count} fields (manual)")
            else:
                manual_results[form_type] = {
                    "spec_key": spec_key,
                    "field_count": 0,
                    "source": "not_found"
                }
                print(f"    ❌ {form_type}: spec not found ({spec_key})")
        
        manual_results["total_fields"] = total_manual_fields
        self.results["manual"] = manual_results
        
        print(f"\n    📊 Total Manual Fields: {total_manual_fields}")
    
    async def test_dynamic_extraction(self):
        """Test the new dynamic PDF extraction for Live Oak."""
        print("\n" + "─"*60)
        print("  TEST 2: Dynamic PDF Extraction (New)")
        print("─"*60)
        
        # Enable dynamic extraction for Live Oak
        os.environ['USE_DYNAMIC_FORM_EXTRACTION'] = 'true'
        os.environ['DYNAMIC_FORMS_ENABLED_FOR'] = 'live_oak'
        
        service = FormMappingService()
        
        # Test the same Live Oak forms with dynamic extraction
        live_oak_forms = {
            "application": "live_oak_application_v1.json",
            "pfs": "live_oak_pfs_v1.json", 
            "4506t": "live_oak_4506t_v1.json"
        }
        
        dynamic_results = {}
        total_dynamic_fields = 0
        
        for form_type, spec_file in live_oak_forms.items():
            spec_key = spec_file.replace('.json', '')
            
            try:
                # Test our new _get_form_specification method
                form_spec = service._get_form_specification('live_oak', spec_file, spec_key)
                
                if form_spec:
                    field_count = len(form_spec.get('fields', []))
                    is_dynamic = form_spec.get('_dynamic_extraction', False)
                    source_pdf = form_spec.get('_source_pdf', 'unknown')
                    
                    dynamic_results[form_type] = {
                        "spec_key": spec_key,
                        "field_count": field_count,
                        "source": "dynamic_pdf" if is_dynamic else "manual_fallback",
                        "source_pdf": source_pdf,
                        "is_dynamic": is_dynamic
                    }
                    
                    total_dynamic_fields += field_count
                    source_indicator = "🚀 dynamic" if is_dynamic else "📚 manual fallback"
                    print(f"    📄 {form_type}: {field_count} fields ({source_indicator})")
                else:
                    dynamic_results[form_type] = {
                        "spec_key": spec_key,
                        "field_count": 0,
                        "source": "extraction_failed"
                    }
                    print(f"    ❌ {form_type}: extraction failed")
                    
            except Exception as e:
                dynamic_results[form_type] = {
                    "spec_key": spec_key,
                    "field_count": 0,
                    "source": "error",
                    "error": str(e)
                }
                print(f"    💥 {form_type}: error - {e}")
        
        dynamic_results["total_fields"] = total_dynamic_fields
        self.results["dynamic"] = dynamic_results
        
        print(f"\n    📊 Total Dynamic Fields: {total_dynamic_fields}")
    
    def compare_results(self):
        """Compare manual vs dynamic extraction results."""
        print("\n" + "─"*60)
        print("  TEST 3: Results Comparison")
        print("─"*60)
        
        manual_total = self.results["manual"]["total_fields"]
        dynamic_total = self.results["dynamic"]["total_fields"]
        
        if manual_total > 0 and dynamic_total > 0:
            improvement = (dynamic_total - manual_total) / manual_total * 100
            improvement_factor = dynamic_total / manual_total
            
            self.results["comparison"] = {
                "manual_fields": manual_total,
                "dynamic_fields": dynamic_total,
                "improvement_percent": improvement,
                "improvement_factor": improvement_factor,
                "success": dynamic_total > manual_total
            }
            
            print(f"    📊 Manual (baseline): {manual_total} fields")
            print(f"    📊 Dynamic (new): {dynamic_total} fields")
            print(f"    📈 Improvement: +{improvement:.1f}% ({improvement_factor:.1f}x increase)")
            
            if improvement > 500:  # Expected 800-1000% increase
                print(f"    ✅ SUCCESS: Field coverage increased significantly!")
            elif improvement > 100:
                print(f"    🟡 PARTIAL: Some improvement, but less than expected")
            else:
                print(f"    ❌ FAILED: No significant improvement")
        else:
            print(f"    ❌ COMPARISON FAILED: Missing data (manual={manual_total}, dynamic={dynamic_total})")
            self.results["comparison"] = {
                "manual_fields": manual_total,
                "dynamic_fields": dynamic_total,
                "success": False,
                "error": "insufficient_data"
            }
    
    async def test_integration(self):
        """Test integration with the full FormMappingService."""
        print("\n" + "─"*60)
        print("  TEST 4: Integration Testing")
        print("─"*60)
        
        try:
            # Test if FormMappingService can be initialized with dynamic extraction enabled
            service = FormMappingService()
            
            # Test PDF template availability
            pdf_path = service.PDF_TEMPLATES.get('live_oak')
            if pdf_path and Path(pdf_path).exists():
                print(f"    ✅ PDF Template Available: {Path(pdf_path).name}")
            else:
                print(f"    ❌ PDF Template Missing: {pdf_path}")
            
            # Test if DynamicFormMapper can be imported and used
            if hasattr(service, '_dynamic_mapper'):
                print(f"    ✅ DynamicFormMapper: Already initialized")
            else:
                print(f"    🔧 DynamicFormMapper: Will be lazy-loaded on first use")
            
            print(f"    ✅ FormMappingService: Successfully initialized with dynamic support")
            
        except Exception as e:
            print(f"    ❌ Integration Error: {e}")


async def main():
    """Run the Live Oak migration test."""
    tester = DynamicMigrationTester()
    
    try:
        results = await tester.run_live_oak_migration_test()
        
        print("\n" + "="*80)
        print("  MIGRATION TEST COMPLETE")
        print("="*80)
        
        # Save results to file
        output_path = Path("outputs/migration_test_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n  📄 Results saved to: {output_path}")
        
        # Summary
        comparison = results.get("comparison", {})
        if comparison.get("success", False):
            improvement = comparison.get("improvement_percent", 0)
            print(f"  ✅ MIGRATION SUCCESS: +{improvement:.1f}% field coverage improvement")
        else:
            print(f"  ⚠️ MIGRATION NEEDS ATTENTION: Check results for details")
            
        return results
        
    except Exception as e:
        print(f"\n  💥 TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == "__main__":
    asyncio.run(main())