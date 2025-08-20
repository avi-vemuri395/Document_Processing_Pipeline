#!/usr/bin/env python3
"""
Schema-Driven Form Mapping Validation Test

This test validates the schema-driven approach by comparing it against string matching
and measuring the improvement in field coverage and semantic accuracy.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple

from src.template_extraction.form_mapping_service import FormMappingService


async def test_schema_driven_vs_string_matching():
    """
    Compare schema-driven mapping against string matching approach.
    """
    print("\n" + "="*80)
    print("  SCHEMA-DRIVEN FORM MAPPING VALIDATION TEST")
    print("  Comparing AI Semantic Mapping vs String Matching")
    print("="*80)
    
    # Load a sample master data (use existing test data)
    master_data_path = Path("outputs/test_results/brigham_001_master.json")
    
    # If test data doesn't exist, create a minimal test case
    if not master_data_path.exists():
        print("\n📊 Creating test master data...")
        master_data = create_test_master_data()
    else:
        print(f"\n📊 Loading master data from: {master_data_path}")
        with open(master_data_path) as f:
            master_data = json.load(f)
    
    # Initialize form mapping service
    print("\n🔧 Initializing Form Mapping Service...")
    form_mapper = FormMappingService()
    
    # Test forms to validate
    test_forms = [
        "live_oak_application",
        "huntington_business_app", 
        "wells_fargo_financial"
    ]
    
    # Test with string matching (disable schema-driven)
    print("\n" + "-"*70)
    print("  TESTING STRING MATCHING APPROACH")
    print("-"*70)
    
    os.environ["ENABLE_SCHEMA_DRIVEN"] = "false"
    string_matching_results = await run_mapping_test(form_mapper, master_data, test_forms, "string_matching")
    
    # Test with schema-driven approach (enable)
    print("\n" + "-"*70)
    print("  TESTING SCHEMA-DRIVEN APPROACH")
    print("-"*70)
    
    os.environ["ENABLE_SCHEMA_DRIVEN"] = "true"
    schema_driven_results = await run_mapping_test(form_mapper, master_data, test_forms, "schema_driven")
    
    # Compare results
    print("\n" + "="*80)
    print("  COMPARISON RESULTS")
    print("="*80)
    
    compare_approaches(string_matching_results, schema_driven_results)
    
    # Validate semantic accuracy
    print("\n" + "-"*70)
    print("  SEMANTIC ACCURACY VALIDATION")
    print("-"*70)
    
    validate_semantic_accuracy(string_matching_results, schema_driven_results)
    
    print("\n✅ Schema-driven validation test complete!")


async def run_mapping_test(
    form_mapper: FormMappingService,
    master_data: Dict[str, Any],
    test_forms: list,
    approach_name: str
) -> Dict[str, Any]:
    """
    Run form mapping test with specified approach.
    """
    results = {
        "approach": approach_name,
        "forms": {},
        "total_mapped": 0,
        "total_fields": 0,
        "overall_coverage": 0.0,
        "semantic_errors": []
    }
    
    for form_key in test_forms:
        print(f"\n  📄 Mapping to {form_key}...")
        
        try:
            # Map using current approach - need to save master data first
            test_app_id = f"test_{approach_name}"
            
            # Save master data to expected location
            output_dir = Path(f"outputs/applications/{test_app_id}/part1_document_processing")
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(output_dir / "master_data.json", 'w') as f:
                json.dump(master_data, f, indent=2)
            
            # Now map using the public method
            bank_name = form_key.split('_')[0]  # Extract bank name from form key
            all_results = await form_mapper.map_all_forms(test_app_id)
            
            # Find the specific form result
            mapped_data = {}
            if bank_name in all_results:
                for form_type, form_result in all_results[bank_name].items():
                    if form_key in form_result.get('mapped_data_path', ''):
                        # Load the actual mapped data
                        mapped_path = Path(form_result['mapped_data_path'])
                        if mapped_path.exists():
                            with open(mapped_path) as f:
                                form_json = json.load(f)
                                mapped_data = form_json.get('mapped_data', {})
            
            # Analyze results
            mapped_count = sum(1 for v in mapped_data.values() if v not in [None, "", [], {}])
            total_fields = len(mapped_data)
            coverage = (mapped_count / total_fields * 100) if total_fields > 0 else 0
            
            # Check for semantic errors (common mismatches)
            semantic_errors = check_semantic_errors(mapped_data)
            
            results["forms"][form_key] = {
                "mapped_fields": mapped_count,
                "total_fields": total_fields,
                "coverage": coverage,
                "semantic_errors": semantic_errors
            }
            
            results["total_mapped"] += mapped_count
            results["total_fields"] += total_fields
            results["semantic_errors"].extend(semantic_errors)
            
            print(f"    ✅ Mapped: {mapped_count}/{total_fields} fields ({coverage:.1f}%)")
            if semantic_errors:
                print(f"    ⚠️  Semantic errors: {len(semantic_errors)}")
                for error in semantic_errors[:3]:  # Show first 3
                    print(f"      • {error}")
        
        except Exception as e:
            print(f"    ❌ Mapping failed: {e}")
            results["forms"][form_key] = {
                "error": str(e),
                "mapped_fields": 0,
                "total_fields": 0,
                "coverage": 0
            }
    
    # Calculate overall coverage
    if results["total_fields"] > 0:
        results["overall_coverage"] = (results["total_mapped"] / results["total_fields"]) * 100
    
    return results


def check_semantic_errors(mapped_data: Dict[str, Any]) -> list:
    """
    Check for common semantic errors in field mapping.
    """
    errors = []
    
    # Common semantic error patterns
    error_patterns = [
        # Field type mismatches
        ("email", lambda v: "@" not in str(v) if v else False, "Email field without @ symbol"),
        ("phone", lambda v: not any(c.isdigit() for c in str(v)) if v else False, "Phone field without digits"),
        ("ssn", lambda v: len(str(v).replace("-", "")) != 9 if v and "XXX" not in str(v) else False, "SSN with wrong format"),
        ("date", lambda v: "/" not in str(v) and "-" not in str(v) if v else False, "Date field without date separator"),
        
        # Value type mismatches
        ("percentage", lambda v: isinstance(v, str) and "$" in v, "Percentage field with currency value"),
        ("address", lambda v: "@" in str(v) if v else False, "Address field with email value"),
        ("state", lambda v: len(str(v)) > 50 if v else False, "State field with long text"),
        ("zip", lambda v: len(str(v)) > 10 if v else False, "ZIP code too long"),
    ]
    
    for field_name, field_value in mapped_data.items():
        if field_value not in [None, "", [], {}]:
            field_lower = field_name.lower()
            
            for pattern_name, check_func, error_msg in error_patterns:
                if pattern_name in field_lower and check_func(field_value):
                    errors.append(f"{field_name}: {error_msg} (got: {str(field_value)[:50]})")
    
    return errors


def compare_approaches(string_results: Dict[str, Any], schema_results: Dict[str, Any]):
    """
    Compare string matching vs schema-driven approaches.
    """
    print(f"\n📊 OVERALL METRICS:")
    print(f"  String Matching:")
    print(f"    • Total fields mapped: {string_results['total_mapped']}/{string_results['total_fields']}")
    print(f"    • Overall coverage: {string_results['overall_coverage']:.1f}%")
    print(f"    • Semantic errors: {len(string_results['semantic_errors'])}")
    
    print(f"\n  Schema-Driven (AI):")
    print(f"    • Total fields mapped: {schema_results['total_mapped']}/{schema_results['total_fields']}")
    print(f"    • Overall coverage: {schema_results['overall_coverage']:.1f}%")
    print(f"    • Semantic errors: {len(schema_results['semantic_errors'])}")
    
    # Calculate improvements
    coverage_improvement = schema_results['overall_coverage'] - string_results['overall_coverage']
    error_reduction = len(string_results['semantic_errors']) - len(schema_results['semantic_errors'])
    
    print(f"\n📈 IMPROVEMENTS:")
    print(f"    • Coverage increase: +{coverage_improvement:.1f}%")
    print(f"    • Error reduction: -{error_reduction} semantic errors")
    if string_results['overall_coverage'] > 0:
        print(f"    • Relative improvement: {(coverage_improvement / string_results['overall_coverage'] * 100):.1f}%")
    else:
        print(f"    • Relative improvement: N/A (baseline coverage is 0%)")
    
    # Per-form comparison
    print(f"\n📋 PER-FORM COMPARISON:")
    for form_key in string_results['forms']:
        string_form = string_results['forms'].get(form_key, {})
        schema_form = schema_results['forms'].get(form_key, {})
        
        if "error" not in string_form and "error" not in schema_form:
            improvement = schema_form['coverage'] - string_form['coverage']
            print(f"  {form_key}:")
            print(f"    • String: {string_form['coverage']:.1f}% coverage")
            print(f"    • Schema: {schema_form['coverage']:.1f}% coverage")
            print(f"    • Improvement: +{improvement:.1f}%")


def validate_semantic_accuracy(string_results: Dict[str, Any], schema_results: Dict[str, Any]):
    """
    Validate that schema-driven approach has better semantic accuracy.
    """
    print("\n🎯 SEMANTIC ACCURACY METRICS:")
    
    # Count error types
    string_error_types = categorize_errors(string_results['semantic_errors'])
    schema_error_types = categorize_errors(schema_results['semantic_errors'])
    
    print(f"\n  String Matching Errors by Type:")
    for error_type, count in string_error_types.items():
        print(f"    • {error_type}: {count} errors")
    
    print(f"\n  Schema-Driven Errors by Type:")
    for error_type, count in schema_error_types.items():
        print(f"    • {error_type}: {count} errors")
    
    # Calculate accuracy score
    string_accuracy = calculate_accuracy_score(string_results)
    schema_accuracy = calculate_accuracy_score(schema_results)
    
    print(f"\n  Accuracy Scores:")
    print(f"    • String Matching: {string_accuracy:.1f}%")
    print(f"    • Schema-Driven: {schema_accuracy:.1f}%")
    print(f"    • Improvement: +{schema_accuracy - string_accuracy:.1f}%")
    
    # Final verdict
    if schema_accuracy >= 90:
        print(f"\n  🎉 EXCELLENT: Schema-driven achieving {schema_accuracy:.1f}% accuracy!")
    elif schema_accuracy >= 80:
        print(f"\n  ✅ GOOD: Schema-driven performing well at {schema_accuracy:.1f}% accuracy")
    else:
        print(f"\n  ⚠️  NEEDS IMPROVEMENT: Schema-driven at {schema_accuracy:.1f}% accuracy")


def categorize_errors(errors: list) -> Dict[str, int]:
    """
    Categorize semantic errors by type.
    """
    categories = {
        "email_errors": 0,
        "phone_errors": 0,
        "ssn_errors": 0,
        "date_errors": 0,
        "type_mismatch": 0,
        "other": 0
    }
    
    for error in errors:
        if "email" in error.lower():
            categories["email_errors"] += 1
        elif "phone" in error.lower():
            categories["phone_errors"] += 1
        elif "ssn" in error.lower():
            categories["ssn_errors"] += 1
        elif "date" in error.lower():
            categories["date_errors"] += 1
        elif "currency" in error.lower() or "percentage" in error.lower():
            categories["type_mismatch"] += 1
        else:
            categories["other"] += 1
    
    return categories


def calculate_accuracy_score(results: Dict[str, Any]) -> float:
    """
    Calculate accuracy score based on coverage and semantic errors.
    """
    # Base score from coverage
    coverage_score = results['overall_coverage']
    
    # Penalty for semantic errors (5% per error, max 50% penalty)
    error_penalty = min(len(results['semantic_errors']) * 5, 50)
    
    # Final accuracy score
    accuracy = max(coverage_score - error_penalty, 0)
    
    return accuracy


def create_test_master_data() -> Dict[str, Any]:
    """
    Create minimal test master data for validation.
    """
    return {
        "personal_info": {
            "full_name": "John Doe",
            "ssn": "XXX-XX-1234",
            "date_of_birth": "01/15/1980",
            "email": "john.doe@example.com",
            "phone": "555-123-4567",
            "address": "123 Main St, Dallas, TX 75201"
        },
        "business_info": {
            "business_name": "Doe Enterprises LLC",
            "ein": "12-3456789",
            "business_type": "Limited Liability Company",
            "ownership_percentage": 100,
            "annual_revenue": 2500000,
            "employees": 25
        },
        "financial_data": {
            "total_assets": 1500000,
            "total_liabilities": 500000,
            "net_worth": 1000000,
            "cash_on_hand": 250000
        },
        "metadata": {
            "extraction_timestamp": datetime.now().isoformat(),
            "documents_processed": ["test_document.pdf"]
        }
    }


if __name__ == "__main__":
    asyncio.run(test_schema_driven_vs_string_matching())