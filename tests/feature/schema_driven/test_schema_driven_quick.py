#!/usr/bin/env python3
"""
Quick Schema-Driven Test
Tests schema-driven form mapping using existing master data.
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from src.template_extraction.form_mapping_service import FormMappingService


async def quick_schema_test():
    """Quick test of schema-driven mapping using existing data."""
    
    print("\n" + "="*80)
    print("  QUICK SCHEMA-DRIVEN MAPPING TEST")
    print("  Using existing master data to test form mapping")
    print("="*80)
    
    # Use the most recent master data
    app_id = "comprehensive_test_20250819_220656"
    master_path = Path(f"outputs/applications/{app_id}/part1_document_processing/master_data.json")
    
    if not master_path.exists():
        print(f"❌ Master data not found at {master_path}")
        return
    
    # Load master data
    print(f"\n📊 Loading master data from: {master_path}")
    with open(master_path) as f:
        master_data = json.load(f)
    
    # Count fields in master
    total_master_fields = count_fields(master_data)
    print(f"   • Total fields in master: {total_master_fields}")
    
    # Initialize form mapper
    print(f"\n🔧 Initializing Form Mapping Service...")
    form_mapper = FormMappingService()
    
    # Test with string matching first
    print("\n" + "-"*70)
    print("  BASELINE: STRING MATCHING")
    print("-"*70)
    
    os.environ["ENABLE_SCHEMA_DRIVEN"] = "false"
    test_id_string = f"test_string_{datetime.now().strftime('%H%M%S')}"
    
    # Copy master data to test location
    test_dir = Path(f"outputs/applications/{test_id_string}/part1_document_processing")
    test_dir.mkdir(parents=True, exist_ok=True)
    with open(test_dir / "master_data.json", 'w') as f:
        json.dump(master_data, f)
    
    # Map forms with string matching
    string_results = await form_mapper.map_all_forms(test_id_string)
    
    # Analyze string matching results
    string_stats = analyze_results(string_results, "String Matching")
    
    # Now test with schema-driven
    print("\n" + "-"*70)
    print("  ENHANCED: SCHEMA-DRIVEN (OpenAI)")
    print("-"*70)
    
    os.environ["ENABLE_SCHEMA_DRIVEN"] = "true"
    test_id_schema = f"test_schema_{datetime.now().strftime('%H%M%S')}"
    
    # Copy master data to test location
    test_dir = Path(f"outputs/applications/{test_id_schema}/part1_document_processing")
    test_dir.mkdir(parents=True, exist_ok=True)
    with open(test_dir / "master_data.json", 'w') as f:
        json.dump(master_data, f)
    
    # Map forms with schema-driven
    schema_results = await form_mapper.map_all_forms(test_id_schema)
    
    # Analyze schema-driven results
    schema_stats = analyze_results(schema_results, "Schema-Driven")
    
    # Compare results
    print("\n" + "="*80)
    print("  COMPARISON RESULTS")
    print("="*80)
    
    compare_results(string_stats, schema_stats)
    
    print("\n✅ Quick test complete!")
    print(f"   • String matching results: outputs/applications/{test_id_string}/")
    print(f"   • Schema-driven results: outputs/applications/{test_id_schema}/")


def count_fields(data, depth=0, max_depth=5):
    """Recursively count non-null fields."""
    if depth > max_depth:
        return 0
    
    count = 0
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ["metadata", "_metadata"]:
                continue
            if value not in [None, "", [], {}]:
                if isinstance(value, (dict, list)):
                    count += count_fields(value, depth + 1, max_depth)
                else:
                    count += 1
    elif isinstance(data, list):
        for item in data:
            count += count_fields(item, depth + 1, max_depth)
    
    return count


def analyze_results(results, approach_name):
    """Analyze form mapping results."""
    stats = {
        "approach": approach_name,
        "total_forms": 0,
        "total_fields": 0,
        "mapped_fields": 0,
        "coverage_by_bank": {},
        "overall_coverage": 0
    }
    
    print(f"\n📊 {approach_name} Results:")
    
    for bank_name, bank_results in results.items():
        bank_mapped = 0
        bank_total = 0
        
        print(f"\n  🏦 {bank_name.upper()}:")
        
        for form_type, form_result in bank_results.items():
            mapped = form_result.get('mapped_fields', 0)
            total = form_result.get('total_fields', 0)
            coverage = form_result.get('coverage', 0)
            
            bank_mapped += mapped
            bank_total += total
            stats["total_forms"] += 1
            
            status = "🎯" if coverage >= 90 else "✅" if coverage >= 70 else "⚠️" if coverage >= 50 else "❌"
            print(f"    {status} {form_type}: {mapped}/{total} fields ({coverage:.1f}%)")
        
        if bank_total > 0:
            bank_coverage = (bank_mapped / bank_total) * 100
            stats["coverage_by_bank"][bank_name] = bank_coverage
            stats["total_fields"] += bank_total
            stats["mapped_fields"] += bank_mapped
            print(f"    📈 Bank total: {bank_mapped}/{bank_total} ({bank_coverage:.1f}%)")
    
    if stats["total_fields"] > 0:
        stats["overall_coverage"] = (stats["mapped_fields"] / stats["total_fields"]) * 100
    
    print(f"\n  📊 Overall: {stats['mapped_fields']}/{stats['total_fields']} fields ({stats['overall_coverage']:.1f}%)")
    
    return stats


def compare_results(string_stats, schema_stats):
    """Compare string matching vs schema-driven results."""
    
    improvement = schema_stats["overall_coverage"] - string_stats["overall_coverage"]
    fields_gained = schema_stats["mapped_fields"] - string_stats["mapped_fields"]
    
    print(f"\n📈 IMPROVEMENT METRICS:")
    print(f"  • String Matching: {string_stats['overall_coverage']:.1f}% coverage ({string_stats['mapped_fields']}/{string_stats['total_fields']} fields)")
    print(f"  • Schema-Driven: {schema_stats['overall_coverage']:.1f}% coverage ({schema_stats['mapped_fields']}/{schema_stats['total_fields']} fields)")
    print(f"  • Improvement: +{improvement:.1f}% coverage")
    print(f"  • Additional fields mapped: +{fields_gained}")
    
    if string_stats["overall_coverage"] > 0:
        relative_improvement = (improvement / string_stats["overall_coverage"]) * 100
        print(f"  • Relative improvement: {relative_improvement:.1f}%")
    
    print(f"\n📊 PER-BANK IMPROVEMENTS:")
    for bank in string_stats["coverage_by_bank"]:
        string_cov = string_stats["coverage_by_bank"].get(bank, 0)
        schema_cov = schema_stats["coverage_by_bank"].get(bank, 0)
        bank_improvement = schema_cov - string_cov
        
        print(f"  • {bank}: {string_cov:.1f}% → {schema_cov:.1f}% (+{bank_improvement:.1f}%)")
    
    # Final assessment
    if schema_stats["overall_coverage"] >= 90:
        print(f"\n🎉 EXCELLENT: Schema-driven achieving {schema_stats['overall_coverage']:.1f}% coverage!")
    elif schema_stats["overall_coverage"] >= 80:
        print(f"\n✅ GOOD: Schema-driven performing well at {schema_stats['overall_coverage']:.1f}%")
    elif improvement > 30:
        print(f"\n📈 SIGNIFICANT: {improvement:.1f}% improvement over baseline")
    else:
        print(f"\n⚠️  MODERATE: {improvement:.1f}% improvement")


if __name__ == "__main__":
    asyncio.run(quick_schema_test())