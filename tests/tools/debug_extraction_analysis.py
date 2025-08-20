#!/usr/bin/env python3
"""
Detailed Analysis Script for DocAI Extraction Results
Analyzes the test output to identify data quality issues and categorization problems.
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

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

def analyze_field_distribution(data, category, prefix=""):
    """Analyze field distribution within a category."""
    results = defaultdict(int)
    
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                results[f"{full_key} (section)"] = len(value)
                # Recurse into nested dictionaries
                nested = analyze_field_distribution(value, category, full_key)
                for nested_key, nested_count in nested.items():
                    results[nested_key] += nested_count
            elif isinstance(value, list):
                results[f"{full_key} (list)"] = len(value)
            elif value not in [None, "", [], {}]:
                results[f"{full_key} (field)"] = 1
    
    return results

def analyze_docai_patterns(form_fields):
    """Analyze DocAI form field patterns to suggest better categorization."""
    personal_patterns = {
        'name', 'first', 'last', 'ssn', 'social', 'dob', 'birth', 'date_of_birth',
        'phone', 'email', 'address', 'city', 'state', 'zip', 'postal',
        'marital', 'spouse', 'citizen', 'personal'
    }
    
    business_patterns = {
        'business', 'company', 'corporation', 'llc', 'inc', 'entity', 'ein',
        'tax_id', 'employer', 'revenue', 'income', 'sales', 'employees',
        'established', 'naics', 'industry', 'ownership'
    }
    
    tax_patterns = {
        'tax', 'return', '1040', '1065', '1120', 'schedule', 'form',
        'agi', 'adjusted_gross', 'taxable', 'withholding', 'refund',
        'deduction', 'exemption', 'filing', 'year'
    }
    
    debt_patterns = {
        'debt', 'loan', 'mortgage', 'liability', 'payable', 'credit',
        'balance', 'payment', 'installment', 'principal', 'interest',
        'line_of_credit', 'note', 'borrowing'
    }
    
    categorization = {
        'personal': [],
        'business': [],
        'tax': [],
        'debt': [],
        'other': []
    }
    
    for field_name, field_data in form_fields.items():
        field_lower = field_name.lower()
        
        if any(pattern in field_lower for pattern in personal_patterns):
            categorization['personal'].append(field_name)
        elif any(pattern in field_lower for pattern in business_patterns):
            categorization['business'].append(field_name)
        elif any(pattern in field_lower for pattern in tax_patterns):
            categorization['tax'].append(field_name)
        elif any(pattern in field_lower for pattern in debt_patterns):
            categorization['debt'].append(field_name)
        else:
            categorization['other'].append(field_name)
    
    return categorization

def main():
    """Analyze the test output directory."""
    if len(sys.argv) != 2:
        print("Usage: python3 debug_extraction_analysis.py <test_output_directory>")
        print("Example: python3 debug_extraction_analysis.py outputs/applications/fast_docai_fix_test_20250819_192205")
        sys.exit(1)
    
    test_dir = Path(sys.argv[1])
    if not test_dir.exists():
        print(f"❌ Directory not found: {test_dir}")
        sys.exit(1)
    
    print("🔍 DETAILED EXTRACTION ANALYSIS")
    print("=" * 50)
    print(f"Analyzing: {test_dir}")
    
    # Load master data
    master_path = test_dir / "part1_document_processing" / "master_data.json"
    if not master_path.exists():
        print(f"❌ Master data not found: {master_path}")
        sys.exit(1)
    
    with open(master_path) as f:
        master_data = json.load(f)
    
    # Load individual extractions
    extractions_dir = test_dir / "part1_document_processing" / "extractions"
    individual_extractions = {}
    
    if extractions_dir.exists():
        for extraction_file in extractions_dir.glob("*_extraction.json"):
            with open(extraction_file) as f:
                doc_name = extraction_file.stem.replace("_extraction", "")
                individual_extractions[doc_name] = json.load(f)
    
    print(f"\n📊 OVERALL STATISTICS")
    print("-" * 30)
    
    # Analyze master data
    categories = ["personal_info", "business_info", "financial_data", "tax_data", "debt_schedules", "other_data"]
    total_fields = 0
    
    for category in categories:
        if category in master_data and master_data[category]:
            field_count = count_nested_fields(master_data[category])
            total_fields += field_count
            print(f"  {category}: {field_count} fields")
        else:
            print(f"  {category}: 0 fields")
    
    print(f"\nTotal fields in master data: {total_fields}")
    
    # Analyze document metadata
    if "metadata" in master_data and "document_extractions" in master_data["metadata"]:
        doc_extractions = master_data["metadata"]["document_extractions"]
        print(f"\n📋 DOCUMENT BREAKDOWN")
        print("-" * 30)
        
        for doc_name, doc_meta in doc_extractions.items():
            method = doc_meta.get("extraction_method", "unknown")
            confidence = doc_meta.get("extraction_confidence", 0)
            print(f"  {doc_name}:")
            print(f"    Method: {method}")
            print(f"    Confidence: {confidence:.1%}")
    
    # Detailed category analysis
    print(f"\n🔬 DETAILED CATEGORY ANALYSIS")
    print("-" * 40)
    
    for category in categories:
        if category in master_data and master_data[category]:
            print(f"\n{category.upper()}:")
            distribution = analyze_field_distribution(master_data[category], category)
            
            # Sort by field count (descending)
            sorted_items = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
            
            for field_path, count in sorted_items[:10]:  # Show top 10
                print(f"  • {field_path}: {count}")
            
            if len(sorted_items) > 10:
                print(f"  ... and {len(sorted_items) - 10} more items")
    
    # Analyze DocAI extractions for better categorization
    print(f"\n🤖 DOCAI CATEGORIZATION ANALYSIS")
    print("-" * 40)
    
    docai_fields_found = False
    for doc_name, extraction in individual_extractions.items():
        if extraction.get("metadata", {}).get("extraction_method") == "google_document_ai":
            print(f"\nDocument: {doc_name}")
            
            # Look for DocAI form fields in different locations
            form_fields = None
            if "other_data" in extraction and "docai_processing_info" in extraction["other_data"]:
                # Check if we can find raw DocAI data
                pass
            
            # Check personal_info for docai_personal
            if "personal_info" in extraction and "docai_personal" in extraction["personal_info"]:
                personal_fields = extraction["personal_info"]["docai_personal"]
                print(f"  Personal fields extracted: {len(personal_fields)}")
                for field_name in list(personal_fields.keys())[:5]:
                    print(f"    • {field_name}")
                if len(personal_fields) > 5:
                    print(f"    ... and {len(personal_fields) - 5} more")
                docai_fields_found = True
            
            # Check business_info for docai_business
            if "business_info" in extraction and "docai_business" in extraction["business_info"]:
                business_fields = extraction["business_info"]["docai_business"]
                print(f"  Business fields extracted: {len(business_fields)}")
                for field_name in list(business_fields.keys())[:5]:
                    print(f"    • {field_name}")
                if len(business_fields) > 5:
                    print(f"    ... and {len(business_fields) - 5} more")
                docai_fields_found = True
                
                # Analyze categorization patterns
                if len(business_fields) > 10:
                    print(f"\n  Categorization analysis for {doc_name}:")
                    categorization = analyze_docai_patterns(business_fields)
                    
                    for cat_type, fields in categorization.items():
                        if fields:
                            print(f"    {cat_type}: {len(fields)} fields")
                            if cat_type in ['tax', 'debt'] and fields:
                                print(f"      Should be in {cat_type}_data category:")
                                for field in fields[:3]:
                                    print(f"        • {field}")
    
    if not docai_fields_found:
        print("  No DocAI extractions found for detailed analysis")
    
    # Missing categories analysis
    print(f"\n⚠️  MISSING CATEGORIES ANALYSIS")
    print("-" * 40)
    
    empty_categories = [cat for cat in categories if not master_data.get(cat)]
    if empty_categories:
        print(f"Empty categories: {', '.join(empty_categories)}")
        print("\nPossible reasons:")
        print("  1. DocAI not extracting these types of fields")
        print("  2. Categorization patterns need improvement")
        print("  3. Documents don't contain this type of data")
        print("  4. Fields being miscategorized into other categories")
    else:
        print("All categories have data ✅")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 20)
    print("1. Field counting: Use recursive counting (fixed in updated test)")
    print("2. Add tax patterns: 'tax', 'return', 'schedule', 'form', '1040', '1065'")
    print("3. Add debt patterns: 'debt', 'loan', 'mortgage', 'liability', 'payable'")
    print("4. Consider field value analysis for better categorization")
    print("5. Test with actual tax returns to verify tax_data category")

if __name__ == "__main__":
    main()