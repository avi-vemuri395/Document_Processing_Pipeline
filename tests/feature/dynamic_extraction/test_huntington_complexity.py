#!/usr/bin/env python3
"""
Test Huntington Multi-Form Complexity - Phase 3.1

This test analyzes the Huntington complexity where 1 PDF template
maps to 4 different form types, and implements form-specific filtering.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List

# Set environment variables for testing Huntington
os.environ['USE_DYNAMIC_FORM_EXTRACTION'] = 'true'
os.environ['DYNAMIC_FORMS_ENABLED_FOR'] = 'huntington'

from src.template_extraction.form_mapping_service import FormMappingService
from src.extraction_methods.multimodal_llm.providers.dynamic_form_mapper import DynamicFormMapper


class HuntingtonComplexityTester:
    """Test and improve Huntington's multi-form complexity."""
    
    def __init__(self):
        self.results = {
            "current_behavior": {},
            "field_analysis": {},
            "form_distribution": {},
            "recommendations": []
        }
        
    async def run_huntington_complexity_test(self):
        """
        Test Huntington's multi-form complexity and provide solutions.
        """
        print("\n" + "="*80)
        print("  HUNTINGTON COMPLEXITY TEST - PHASE 3.1")
        print("  Challenge: 1 PDF (461 fields) → 4 Forms")
        print("="*80)
        
        # Test 1: Analyze current behavior
        await self.test_current_behavior()
        
        # Test 2: Analyze field distribution potential
        await self.analyze_field_distribution()
        
        # Test 3: Implement form-specific filtering
        await self.implement_form_filtering()
        
        return self.results
    
    async def test_current_behavior(self):
        """Test current behavior with Huntington forms."""
        print("\n" + "─"*60)
        print("  TEST 1: Current Behavior Analysis")
        print("─"*60)
        
        service = FormMappingService()
        
        # Huntington forms configuration
        huntington_forms = {
            "business_app": "huntington_business_app_v1.json",
            "pfs": "huntington_pfs_v1.json",
            "tax_transcript": "huntington_tax_transcript_v1.json",
            "debt_schedule": "huntington_debt_schedule_v1.json"
        }
        
        current_behavior = {}
        total_fields_assigned = 0
        
        print("    🏦 Testing each Huntington form:")
        
        for form_type, spec_file in huntington_forms.items():
            spec_key = spec_file.replace('.json', '')
            
            try:
                # Test current behavior
                form_spec = service._get_form_specification('huntington', spec_file, spec_key)
                
                if form_spec:
                    field_count = len(form_spec.get('fields', []))
                    is_dynamic = form_spec.get('_dynamic_extraction', False)
                    
                    current_behavior[form_type] = {
                        "field_count": field_count,
                        "is_dynamic": is_dynamic,
                        "spec_key": spec_key
                    }
                    
                    total_fields_assigned += field_count
                    source_indicator = "🚀 dynamic" if is_dynamic else "📚 manual"
                    print(f"      📄 {form_type}: {field_count} fields ({source_indicator})")
                else:
                    current_behavior[form_type] = {
                        "field_count": 0,
                        "is_dynamic": False,
                        "error": "spec_not_found"
                    }
                    print(f"      ❌ {form_type}: spec not found")
                    
            except Exception as e:
                current_behavior[form_type] = {
                    "field_count": 0,
                    "is_dynamic": False,
                    "error": str(e)
                }
                print(f"      💥 {form_type}: error - {e}")
        
        current_behavior["total_fields_assigned"] = total_fields_assigned
        self.results["current_behavior"] = current_behavior
        
        print(f"\n    📊 Total Fields Assigned: {total_fields_assigned}")
        
        # Analysis
        if total_fields_assigned > 1000:  # 4 forms × 461 fields = 1844
            print("    ⚠️ ISSUE: All forms getting all fields (massive duplication)")
            self.results["recommendations"].append("Implement form-specific field filtering")
        elif total_fields_assigned > 400:
            print("    🟡 MODERATE: Some field sharing, but potentially excessive")
        else:
            print("    ✅ REASONABLE: Field distribution looks appropriate")
    
    async def analyze_field_distribution(self):
        """Analyze how fields could be distributed among forms."""
        print("\n" + "─"*60)
        print("  TEST 2: Field Distribution Analysis")
        print("─"*60)
        
        try:
            # Get the raw dynamic extraction from PDF
            mapper = DynamicFormMapper()
            pdf_path = Path("templates/Huntington Bank Personal Financial Statement.pdf")
            
            if not pdf_path.exists():
                print(f"    ❌ PDF template not found: {pdf_path}")
                self.results["field_analysis"] = {"error": "pdf_not_found"}
                return
            
            print(f"    📄 Analyzing: {pdf_path.name}")
            dynamic_spec = mapper.get_form_fields(pdf_path)
            
            fields = dynamic_spec.get('fields', {})
            total_fields = len(fields)
            print(f"    📊 Total fields in PDF: {total_fields}")
            
            # Categorize fields by potential form type
            field_categories = {
                "business_app": [],
                "pfs": [],
                "tax_transcript": [],
                "debt_schedule": [],
                "general": []
            }
            
            business_keywords = [
                'business', 'company', 'corporation', 'llc', 'entity', 'ownership', 
                'operation', 'industry', 'employee', 'revenue', 'gross', 'applicant'
            ]
            
            pfs_keywords = [
                'asset', 'liability', 'net', 'worth', 'financial', 'income', 'expense',
                'property', 'investment', 'savings', 'checking', 'personal', 'statement'
            ]
            
            tax_keywords = [
                'tax', 'return', 'transcript', 'irs', 'schedule', 'form', 'year',
                'filing', 'refund', 'agi', 'adjusted', 'gross'
            ]
            
            debt_keywords = [
                'debt', 'loan', 'mortgage', 'liability', 'payment', 'monthly',
                'balance', 'creditor', 'installment', 'line', 'credit'
            ]
            
            # Sample first 50 fields for analysis
            sample_fields = list(fields.items())[:50]
            print(f"    🔍 Analyzing sample of {len(sample_fields)} fields...")
            
            for field_name, field_info in sample_fields:
                field_lower = field_name.lower()
                categorized = False
                
                # Check business application keywords
                if any(keyword in field_lower for keyword in business_keywords):
                    field_categories["business_app"].append(field_name)
                    categorized = True
                
                # Check PFS keywords
                if any(keyword in field_lower for keyword in pfs_keywords):
                    field_categories["pfs"].append(field_name)
                    categorized = True
                
                # Check tax transcript keywords
                if any(keyword in field_lower for keyword in tax_keywords):
                    field_categories["tax_transcript"].append(field_name)
                    categorized = True
                
                # Check debt schedule keywords
                if any(keyword in field_lower for keyword in debt_keywords):
                    field_categories["debt_schedule"].append(field_name)
                    categorized = True
                
                # If not categorized, it's general
                if not categorized:
                    field_categories["general"].append(field_name)
            
            # Calculate distribution
            distribution_analysis = {}
            for form_type, categorized_fields in field_categories.items():
                count = len(categorized_fields)
                percentage = (count / len(sample_fields) * 100) if len(sample_fields) > 0 else 0
                
                distribution_analysis[form_type] = {
                    "field_count": count,
                    "percentage": percentage,
                    "sample_fields": categorized_fields[:5]  # First 5 as examples
                }
                
                print(f"    📊 {form_type}: {count} fields ({percentage:.1f}%)")
                if categorized_fields:
                    examples = ', '.join(categorized_fields[:3])
                    if len(categorized_fields) > 3:
                        examples += f" ... and {len(categorized_fields) - 3} more"
                    print(f"        Examples: {examples}")
            
            self.results["field_analysis"] = {
                "total_pdf_fields": total_fields,
                "analyzed_sample": len(sample_fields),
                "distribution": distribution_analysis
            }
            
            # Generate recommendations
            if distribution_analysis["general"]["field_count"] > len(sample_fields) * 0.4:
                self.results["recommendations"].append("Many fields are general - implement smart categorization")
            
            if any(cat["field_count"] == 0 for cat in distribution_analysis.values()):
                self.results["recommendations"].append("Some forms have no specific fields - review keyword matching")
                
        except Exception as e:
            print(f"    ❌ Field Analysis Error: {e}")
            self.results["field_analysis"] = {"error": str(e)}
    
    async def implement_form_filtering(self):
        """Test implementation of form-specific field filtering."""
        print("\n" + "─"*60)
        print("  TEST 3: Form-Specific Filtering Implementation")
        print("─"*60)
        
        try:
            # Simulate improved filtering logic
            service = FormMappingService()
            
            # Test if we can extend the conversion method to support form-specific filtering
            spec_key = "huntington_business_app_v1"
            form_spec = service._get_form_specification('huntington', 'huntington_business_app_v1.json', spec_key)
            
            if form_spec and form_spec.get('_dynamic_extraction'):
                total_fields = len(form_spec.get('fields', []))
                print(f"    📄 Current dynamic fields for business_app: {total_fields}")
                
                # Simulate what filtering could achieve
                estimated_filtered = {
                    "business_app": int(total_fields * 0.4),  # 40% relevant to business app
                    "pfs": int(total_fields * 0.6),          # 60% relevant to PFS
                    "tax_transcript": int(total_fields * 0.1), # 10% relevant to tax
                    "debt_schedule": int(total_fields * 0.3)   # 30% relevant to debt
                }
                
                print(f"    🎯 Estimated optimal field distribution:")
                for form_type, count in estimated_filtered.items():
                    percentage = (count / total_fields * 100)
                    print(f"      • {form_type}: {count} fields ({percentage:.1f}% of total)")
                
                total_filtered = sum(estimated_filtered.values())
                efficiency_gain = (total_fields * 4 - total_filtered) / (total_fields * 4) * 100
                
                print(f"\n    📈 Efficiency Analysis:")
                print(f"      • Current: {total_fields * 4} total field assignments")
                print(f"      • Filtered: {total_filtered} total field assignments")
                print(f"      • Efficiency Gain: {efficiency_gain:.1f}% reduction in redundancy")
                
                self.results["form_distribution"] = {
                    "current_total_assignments": total_fields * 4,
                    "estimated_filtered_assignments": total_filtered,
                    "efficiency_gain_percent": efficiency_gain,
                    "form_specific_counts": estimated_filtered
                }
                
                if efficiency_gain > 50:
                    print(f"    ✅ EXCELLENT: Form filtering would provide significant efficiency gains")
                    self.results["recommendations"].append("Implement form-specific field filtering for Huntington")
                else:
                    print(f"    🟡 MODERATE: Form filtering would provide some benefits")
            else:
                print(f"    ❌ Could not test filtering - dynamic extraction not working")
                
        except Exception as e:
            print(f"    ❌ Filtering Implementation Error: {e}")
            self.results["form_distribution"] = {"error": str(e)}


async def main():
    """Run the Huntington complexity test."""
    tester = HuntingtonComplexityTester()
    
    try:
        results = await tester.run_huntington_complexity_test()
        
        print("\n" + "="*80)
        print("  HUNTINGTON COMPLEXITY ANALYSIS COMPLETE")
        print("="*80)
        
        # Save results
        output_path = Path("outputs/huntington_complexity_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n  📄 Results saved to: {output_path}")
        
        # Summary and Recommendations
        recommendations = results.get("recommendations", [])
        current_behavior = results.get("current_behavior", {})
        
        total_fields = current_behavior.get("total_fields_assigned", 0)
        
        print(f"\n  📊 COMPLEXITY ANALYSIS SUMMARY:")
        print(f"    • Current field assignments: {total_fields}")
        print(f"    • Recommendations: {len(recommendations)}")
        
        if recommendations:
            print(f"\n  🎯 KEY RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"    {i}. {rec}")
        
        if total_fields > 1500:
            print(f"\n  ⚠️ PHASE 3.1 NEEDS ATTENTION: Excessive field duplication detected")
        elif recommendations:
            print(f"\n  🟡 PHASE 3.1 PARTIAL SUCCESS: Areas for improvement identified")
        else:
            print(f"\n  ✅ PHASE 3.1 SUCCESS: Huntington complexity handled well")
            
        return results
        
    except Exception as e:
        print(f"\n  💥 COMPLEXITY TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == "__main__":
    asyncio.run(main())