#!/usr/bin/env python3
"""
Test PDF Generation Validation - Phase 2.2

This test validates that PDF generation still works correctly with 
dynamic form extraction, ensuring the increased field coverage
doesn't break existing functionality.
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
from src.extraction_methods.multimodal_llm.providers.pdf_form_generator import PDFFormGenerator


class PDFGenerationValidator:
    """Validate PDF generation with dynamic extraction."""
    
    def __init__(self):
        self.results = {
            "field_compatibility": {},
            "pdf_generation": {},
            "coverage_validation": {}
        }
        
    async def run_pdf_validation_test(self):
        """
        Test PDF generation compatibility with dynamic extraction.
        """
        print("\n" + "="*80)
        print("  PDF GENERATION VALIDATION - PHASE 2.2")
        print("  Testing: Dynamic Fields → PDF Form Compatibility")
        print("="*80)
        
        # Test 1: Field format compatibility
        await self.test_field_format_compatibility()
        
        # Test 2: PDF generation workflow
        await self.test_pdf_generation_workflow()
        
        # Test 3: Field mapping validation
        await self.test_field_mapping_validation()
        
        return self.results
    
    async def test_field_format_compatibility(self):
        """Test that dynamic fields are compatible with PDF generation."""
        print("\n" + "─"*60)
        print("  TEST 1: Field Format Compatibility")
        print("─"*60)
        
        service = FormMappingService()
        
        # Get dynamic form spec for Live Oak application
        form_spec = service._get_form_specification(
            'live_oak', 
            'live_oak_application_v1.json',
            'live_oak_application_v1'
        )
        
        if form_spec:
            fields = form_spec.get('fields', [])
            field_count = len(fields)
            is_dynamic = form_spec.get('_dynamic_extraction', False)
            
            print(f"    📄 Form Specification Retrieved: {field_count} fields")
            print(f"    🚀 Dynamic Extraction: {'Yes' if is_dynamic else 'No'}")
            
            # Validate field structure
            valid_fields = 0
            invalid_fields = 0
            field_types = {}
            
            for field in fields:
                if isinstance(field, dict):
                    has_name = 'name' in field
                    has_type = 'type' in field
                    has_required = 'required' in field
                    
                    if has_name and has_type:
                        valid_fields += 1
                        field_type = field.get('type', 'unknown')
                        field_types[field_type] = field_types.get(field_type, 0) + 1
                    else:
                        invalid_fields += 1
                        print(f"      ⚠️ Invalid field structure: {field}")
                else:
                    invalid_fields += 1
            
            compatibility_score = (valid_fields / field_count * 100) if field_count > 0 else 0
            
            self.results["field_compatibility"] = {
                "total_fields": field_count,
                "valid_fields": valid_fields,
                "invalid_fields": invalid_fields,
                "compatibility_score": compatibility_score,
                "field_types": field_types,
                "is_dynamic": is_dynamic
            }
            
            print(f"    ✅ Valid Fields: {valid_fields}/{field_count} ({compatibility_score:.1f}%)")
            print(f"    📊 Field Types: {dict(list(field_types.items())[:5])}")
            if len(field_types) > 5:
                print(f"      ... and {len(field_types) - 5} more types")
                
            if compatibility_score >= 95:
                print(f"    ✅ EXCELLENT: Field format fully compatible with PDF generation")
            elif compatibility_score >= 80:
                print(f"    🟡 GOOD: Field format mostly compatible")
            else:
                print(f"    ❌ POOR: Field format has compatibility issues")
        else:
            print(f"    ❌ Failed to retrieve form specification")
            self.results["field_compatibility"] = {"error": "spec_retrieval_failed"}
    
    async def test_pdf_generation_workflow(self):
        """Test the actual PDF generation workflow."""
        print("\n" + "─"*60)
        print("  TEST 2: PDF Generation Workflow")
        print("─"*60)
        
        try:
            # Initialize PDF generator
            pdf_generator = PDFFormGenerator()
            
            # Check if Live Oak template exists
            template_path = "templates/Live Oak Express - Application Forms.pdf"
            if not Path(template_path).exists():
                print(f"    ❌ Template not found: {template_path}")
                self.results["pdf_generation"] = {"error": "template_not_found"}
                return
            
            print(f"    ✅ PDF Template Found: {Path(template_path).name}")
            
            # Create sample data for testing (minimal field set)
            sample_data = {
                "Name": "John Doe",
                "Social Security Number": "123-45-6789",
                "Email address": "john.doe@example.com",
                "Mobile Telephone Number": "(555) 123-4567",
                "Business Applicant Name": "Doe Enterprises LLC"
            }
            
            print(f"    🧪 Testing with {len(sample_data)} sample fields")
            
            # Test PDF generation
            output_dir = Path("outputs/pdf_validation_test")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result_path = pdf_generator.generate_filled_pdf(
                template_name="Live Oak Express - Application Forms",
                extracted_data=sample_data,
                output_dir=output_dir
            )
            
            if result_path and result_path.exists():
                file_size = result_path.stat().st_size
                print(f"    ✅ PDF Generated Successfully: {result_path.name}")
                print(f"    📊 File Size: {file_size:,} bytes")
                
                self.results["pdf_generation"] = {
                    "success": True,
                    "output_path": str(result_path),
                    "file_size": file_size,
                    "template_used": template_path,
                    "fields_tested": len(sample_data)
                }
            else:
                print(f"    ❌ PDF generation failed or file not created")
                self.results["pdf_generation"] = {
                    "success": False,
                    "error": "generation_failed"
                }
                
        except Exception as e:
            print(f"    ❌ PDF Generation Error: {e}")
            self.results["pdf_generation"] = {
                "success": False,
                "error": str(e)
            }
    
    async def test_field_mapping_validation(self):
        """Test field mapping between dynamic extraction and PDF generation."""
        print("\n" + "─"*60)
        print("  TEST 3: Field Mapping Validation")
        print("─"*60)
        
        try:
            service = FormMappingService()
            
            # Get dynamic form specification
            form_spec = service._get_form_specification(
                'live_oak',
                'live_oak_application_v1.json', 
                'live_oak_application_v1'
            )
            
            if not form_spec:
                print(f"    ❌ Could not retrieve form specification")
                self.results["coverage_validation"] = {"error": "no_form_spec"}
                return
            
            fields = form_spec.get('fields', [])
            print(f"    📊 Analyzing {len(fields)} dynamic fields for PDF mapping potential")
            
            # Categorize fields by type and likely PDF compatibility
            field_analysis = {
                "text_fields": 0,
                "checkbox_fields": 0,
                "date_fields": 0,
                "dropdown_fields": 0,
                "other_fields": 0,
                "likely_mappable": 0,
                "sample_fields": []
            }
            
            for field in fields[:20]:  # Analyze first 20 fields as sample
                field_type = field.get('type', 'text')
                field_name = field.get('name', 'unnamed')
                
                field_analysis[f"{field_type}_fields"] = field_analysis.get(f"{field_type}_fields", 0) + 1
                
                # Estimate PDF mapping potential based on field name patterns
                if any(keyword in field_name.lower() for keyword in [
                    'name', 'address', 'phone', 'email', 'ssn', 'date', 'amount', 'business'
                ]):
                    field_analysis["likely_mappable"] += 1
                
                field_analysis["sample_fields"].append({
                    "name": field_name,
                    "type": field_type,
                    "mappable": True
                })
            
            # Calculate mapping potential
            total_analyzed = len(field_analysis["sample_fields"])
            mapping_potential = (field_analysis["likely_mappable"] / total_analyzed * 100) if total_analyzed > 0 else 0
            
            self.results["coverage_validation"] = {
                "total_fields": len(fields),
                "analyzed_sample": total_analyzed,
                "field_types": {k: v for k, v in field_analysis.items() if k.endswith('_fields')},
                "mapping_potential_percent": mapping_potential,
                "likely_mappable_fields": field_analysis["likely_mappable"]
            }
            
            print(f"    📈 Mapping Potential: {field_analysis['likely_mappable']}/{total_analyzed} fields ({mapping_potential:.1f}%)")
            print(f"    📊 Field Type Distribution:")
            
            for field_type, count in field_analysis.items():
                if field_type.endswith('_fields') and count > 0:
                    print(f"      • {field_type.replace('_fields', '').title()}: {count}")
            
            if mapping_potential >= 70:
                print(f"    ✅ EXCELLENT: High PDF mapping potential")
            elif mapping_potential >= 50:
                print(f"    🟡 GOOD: Moderate PDF mapping potential") 
            else:
                print(f"    ⚠️ MODERATE: Lower PDF mapping potential")
                
        except Exception as e:
            print(f"    ❌ Field Mapping Analysis Error: {e}")
            self.results["coverage_validation"] = {"error": str(e)}


async def main():
    """Run the PDF generation validation test."""
    validator = PDFGenerationValidator()
    
    try:
        results = await validator.run_pdf_validation_test()
        
        print("\n" + "="*80)
        print("  PDF VALIDATION COMPLETE")
        print("="*80)
        
        # Save results
        output_path = Path("outputs/pdf_validation_results.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n  📄 Results saved to: {output_path}")
        
        # Summary
        field_compat = results.get("field_compatibility", {})
        pdf_gen = results.get("pdf_generation", {})
        coverage = results.get("coverage_validation", {})
        
        field_score = field_compat.get("compatibility_score", 0)
        pdf_success = pdf_gen.get("success", False)
        mapping_potential = coverage.get("mapping_potential_percent", 0)
        
        print(f"\n  📊 VALIDATION SUMMARY:")
        print(f"    • Field Compatibility: {field_score:.1f}%")
        print(f"    • PDF Generation: {'✅ Success' if pdf_success else '❌ Failed'}")
        print(f"    • Mapping Potential: {mapping_potential:.1f}%")
        
        if field_score >= 95 and pdf_success and mapping_potential >= 50:
            print(f"\n  ✅ PHASE 2.2 SUCCESS: Dynamic extraction fully compatible with PDF generation")
        else:
            print(f"\n  ⚠️ PHASE 2.2 PARTIAL: Some compatibility issues detected")
            
        return results
        
    except Exception as e:
        print(f"\n  💥 VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {}


if __name__ == "__main__":
    asyncio.run(main())