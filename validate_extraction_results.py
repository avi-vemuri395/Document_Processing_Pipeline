#!/usr/bin/env python3
"""
Validate extraction results against expected values.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors.enhanced_extraction_pipeline import (
    EnhancedExtractionPipeline,
    EnhancedPipelineConfig,
    ExtractionMethod
)


def validate_brigham_dallas_pfs(data):
    """Validate Brigham Dallas PFS extraction."""
    print("\n📋 Validating Brigham Dallas PFS Extraction:")
    
    expected = {
        'name': 'Brigham Dallas',
        'total_assets': 4397552,
        'total_liabilities': 2044663,
        'net_worth': 2352889,
    }
    
    results = {}
    
    # Check if we have the loan application
    if hasattr(data, 'loan_application') and data.loan_application:
        app = data.loan_application
        
        # Check borrower name
        if app.primary_borrower:
            extracted_name = f"{app.primary_borrower.first_name} {app.primary_borrower.last_name}"
            results['name'] = (extracted_name, expected['name'], extracted_name == expected['name'])
        
        # Check financial position
        if app.financial_position:
            fin = app.financial_position
            
            if fin.total_assets:
                results['total_assets'] = (
                    float(fin.total_assets), 
                    expected['total_assets'],
                    abs(float(fin.total_assets) - expected['total_assets']) < 100
                )
            
            if fin.total_liabilities:
                results['total_liabilities'] = (
                    float(fin.total_liabilities),
                    expected['total_liabilities'],
                    abs(float(fin.total_liabilities) - expected['total_liabilities']) < 100
                )
            
            if fin.net_worth:
                results['net_worth'] = (
                    float(fin.net_worth),
                    expected['net_worth'],
                    abs(float(fin.net_worth) - expected['net_worth']) < 100
                )
    
    # Display results
    for field, (extracted, expected_val, is_correct) in results.items():
        status = "✅" if is_correct else "❌"
        print(f"  {status} {field}: {extracted} (expected: {expected_val})")
    
    # Overall validation
    all_correct = all(r[2] for r in results.values()) if results else False
    print(f"\n  Overall Validation: {'✅ PASSED' if all_correct else '❌ FAILED'}")
    
    return all_correct


def validate_excel_extraction(data):
    """Validate Excel extraction results."""
    print("\n📊 Validating Excel Extraction:")
    
    excel_docs = []
    
    # Find Excel documents in results
    if hasattr(data, 'documents_processed'):
        for doc in data.documents_processed:
            if doc.file_path.suffix.lower() in ['.xlsx', '.xls']:
                excel_docs.append(doc)
    
    if not excel_docs:
        print("  ⚠️ No Excel documents found in results")
        return False
    
    for doc in excel_docs:
        print(f"\n  File: {doc.file_path.name}")
        print(f"    Type: {doc.classification.primary_type.value}")
        print(f"    Method: {doc.extraction_method}")
        print(f"    Confidence: {doc.confidence_score:.2%}")
        
        if doc.extraction_data and hasattr(doc.extraction_data, 'data'):
            print(f"    Sheets: {len(doc.extraction_data.data)}")
            
            # Check if we got meaningful data
            has_data = False
            for sheet_name, sheet_data in doc.extraction_data.data.items():
                if isinstance(sheet_data, dict) and ('totals' in sheet_data or 'data' in sheet_data):
                    has_data = True
                    print(f"    ✅ Sheet '{sheet_name}' has data")
            
            if not has_data:
                print(f"    ❌ No meaningful data extracted")
    
    return len(excel_docs) > 0


def validate_classification(data):
    """Validate document classification."""
    print("\n🏷️ Validating Document Classification:")
    
    classification_results = {}
    
    if hasattr(data, 'documents_processed'):
        for doc in data.documents_processed:
            doc_type = doc.classification.primary_type.value
            confidence = doc.classification.confidence
            
            # Expected classifications
            expected_types = {
                'Brigham_Dallas_PFS.pdf': 'personal_financial_statement',
                'Dave Burlington Personal Financial Statement.pdf': 'sba_form_413',
                'Debt Schedule.xlsx': 'debt_schedule',
                'HSF_BS_as_of_20250630.xlsx': 'balance_sheet',
                'HSF_PL_as_of_20250630.xlsx': 'profit_loss',
            }
            
            file_name = doc.file_path.name
            if file_name in expected_types:
                expected = expected_types[file_name]
                is_correct = doc_type == expected or (
                    # Allow SBA Form 413 to be classified as PFS
                    expected == 'sba_form_413' and doc_type == 'personal_financial_statement'
                )
                status = "✅" if is_correct else "❌"
                print(f"  {status} {file_name}: {doc_type} (expected: {expected})")
                classification_results[file_name] = is_correct
    
    # Overall result
    if classification_results:
        success_rate = sum(classification_results.values()) / len(classification_results)
        print(f"\n  Classification Success Rate: {success_rate:.1%}")
        return success_rate >= 0.7  # 70% threshold
    
    return False


async def run_validation():
    """Run comprehensive validation tests."""
    print("="*80)
    print("EXTRACTION VALIDATION SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Test with Brigham Dallas documents
    print("Testing Brigham Dallas Package...")
    
    config = EnhancedPipelineConfig(
        extraction_method=ExtractionMethod.HYBRID,
        prefer_native_excel=True,
        enable_cross_validation=True,
        save_intermediate_results=False
    )
    
    pipeline = EnhancedExtractionPipeline(config)
    
    # Brigham Dallas documents
    brigham_docs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/HSF_BS_as_of_20250630.xlsx"),
        Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx"),
    ]
    
    # Filter to existing files
    existing_docs = [doc for doc in brigham_docs if doc.exists()]
    
    if not existing_docs:
        print("❌ No test documents found")
        return False
    
    # Process documents
    result = await pipeline.process_loan_package(
        existing_docs,
        application_id="VALIDATION-TEST"
    )
    
    # Run validations
    validation_results = []
    
    # 1. Validate PFS extraction
    pfs_valid = validate_brigham_dallas_pfs(result)
    validation_results.append(("PFS Extraction", pfs_valid))
    
    # 2. Validate Excel extraction
    excel_valid = validate_excel_extraction(result)
    validation_results.append(("Excel Extraction", excel_valid))
    
    # 3. Validate classification
    class_valid = validate_classification(result)
    validation_results.append(("Classification", class_valid))
    
    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)
    
    for test_name, passed in validation_results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    overall_passed = all(r[1] for r in validation_results)
    
    print("\n" + "="*80)
    if overall_passed:
        print("✅ ALL VALIDATIONS PASSED")
    else:
        print("❌ SOME VALIDATIONS FAILED")
    print("="*80)
    
    return overall_passed


if __name__ == "__main__":
    success = asyncio.run(run_validation())
    sys.exit(0 if success else 1)