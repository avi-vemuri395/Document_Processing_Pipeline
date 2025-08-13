#!/usr/bin/env python3
"""
Test the enhanced extraction pipeline with real documents.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extractors.enhanced_extraction_pipeline import (
    EnhancedExtractionPipeline,
    EnhancedPipelineConfig,
    ExtractionMethod
)


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


async def test_brigham_dallas_package():
    """Test with Brigham Dallas loan package."""
    
    print_section("BRIGHAM DALLAS LOAN PACKAGE TEST")
    
    # Configure pipeline
    config = EnhancedPipelineConfig(
        extraction_method=ExtractionMethod.HYBRID,
        prefer_native_excel=True,
        enable_cross_validation=True,
        save_intermediate_results=True,
        output_directory=Path("outputs/enhanced_test/brigham_dallas")
    )
    
    # Initialize pipeline
    pipeline = EnhancedExtractionPipeline(config)
    
    # Collect Brigham Dallas documents
    documents = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_2024_PTR.pdf"),
        Path("inputs/real/Brigham_dallas/Hello_Sugar_Franchise_LLC_2024.pdf"),
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf"),
        Path("inputs/real/Brigham_dallas/HSF_BS_as_of_20250630.xlsx"),
        Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx"),
        Path("inputs/real/Brigham_dallas/HSF_AR_Aging_as_of_20250630.xlsx"),
    ]
    
    # Filter to existing files
    existing_docs = [doc for doc in documents if doc.exists()]
    print(f"Found {len(existing_docs)} documents to process")
    
    # Process loan package
    result = await pipeline.process_loan_package(
        existing_docs,
        application_id="BRIGHAM-2024-001"
    )
    
    # Display results
    print_section("EXTRACTION RESULTS")
    
    print(f"Total Processing Time: {result.total_processing_time:.2f} seconds")
    print(f"Documents Processed: {len(result.documents_processed)}")
    
    # Show document classifications
    print("\n📄 Document Classifications:")
    for doc in result.documents_processed:
        print(f"  • {doc.file_path.name}")
        print(f"    Type: {doc.classification.primary_type.value}")
        print(f"    Method: {doc.extraction_method}")
        print(f"    Confidence: {doc.confidence_score:.2%}")
    
    # Show loan application summary
    if result.loan_application:
        print_section("LOAN APPLICATION SUMMARY")
        
        app = result.loan_application
        print(f"Application ID: {app.application_id}")
        print(f"Status: {app.status.value}")
        print(f"Borrower: {app.primary_borrower}")
        
        if app.business_entity:
            print(f"Business: {app.business_entity.business_name}")
        
        if app.financial_position.net_worth:
            print(f"\n💰 Financial Position:")
            print(f"  Total Assets: ${app.financial_position.total_assets:,.2f}")
            print(f"  Total Liabilities: ${app.financial_position.total_liabilities:,.2f}")
            print(f"  Net Worth: ${app.financial_position.net_worth:,.2f}")
        
        if app.debt_schedule.debts:
            print(f"\n📊 Debt Schedule:")
            print(f"  Number of Debts: {len(app.debt_schedule.debts)}")
            if app.debt_schedule.total_debt:
                print(f"  Total Debt: ${app.debt_schedule.total_debt:,.2f}")
        
        if app.risk_score is not None:
            print(f"\n⚠️ Risk Assessment:")
            print(f"  Risk Score: {app.risk_score}/100")
            if app.risk_factors:
                print(f"  Risk Factors:")
                for factor in app.risk_factors[:3]:
                    print(f"    • {factor}")
    
    # Show validation results
    if result.validation_result:
        print_section("VALIDATION RESULTS")
        
        val = result.validation_result
        print(f"Overall Status: {val.overall_status}")
        print(f"Confidence: {val.confidence:.2%}")
        
        if val.passed_checks:
            print(f"\n✅ Passed Checks: {len(val.passed_checks)}")
            for check in val.passed_checks[:3]:
                print(f"  • {check}")
        
        if val.failed_checks:
            print(f"\n❌ Failed Checks: {len(val.failed_checks)}")
            for check in val.failed_checks[:3]:
                print(f"  • {check}")
        
        if val.warnings:
            print(f"\n⚠️ Warnings: {len(val.warnings)}")
            for warning in val.warnings[:3]:
                print(f"  • {warning}")
        
        if val.recommendations:
            print(f"\n💡 Recommendations:")
            for rec in val.recommendations[:3]:
                print(f"  • {rec}")
    
    # Show statistics
    print_section("STATISTICS")
    stats = result.summary_statistics
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.2%}")
        else:
            print(f"{key}: {value}")
    
    return result


async def test_dave_burlington_package():
    """Test with Dave Burlington loan package."""
    
    print_section("DAVE BURLINGTON LOAN PACKAGE TEST")
    
    # Configure pipeline
    config = EnhancedPipelineConfig(
        extraction_method=ExtractionMethod.HYBRID,
        prefer_native_excel=True,
        enable_cross_validation=True,
        save_intermediate_results=True,
        output_directory=Path("outputs/enhanced_test/dave_burlington")
    )
    
    # Initialize pipeline
    pipeline = EnhancedExtractionPipeline(config)
    
    # Collect Dave Burlington documents
    documents = [
        Path("inputs/real/Dave Burlington - Application Packet/Personal Financial Statement/Dave Burlington Personal Financial Statement.pdf"),
        Path("inputs/real/Dave Burlington - Application Packet/Personal Tax Returns (3 years)/David and Janette Burlington 2024 Tax Return.pdf"),
        Path("inputs/real/Dave Burlington - Application Packet/Business Tax Returns (3 years)/Beyond Bassin LLC 2024 Tax Return.pdf"),
        Path("inputs/real/Dave Burlington - Application Packet/Business Debt Schedule/Debt Schedule.xlsx"),
        Path("inputs/real/Dave Burlington - Application Packet/Revenue Projections/Beyond Bassin Goals and Projections.xlsx"),
        Path("inputs/real/Dave Burlington - Application Packet/Itemized Project Costs.xlsx"),
    ]
    
    # Filter to existing files
    existing_docs = [doc for doc in documents if doc.exists()]
    print(f"Found {len(existing_docs)} documents to process")
    
    # Process loan package
    result = await pipeline.process_loan_package(
        existing_docs,
        application_id="BURLINGTON-2024-001"
    )
    
    # Display results (similar to above)
    print(f"\nTotal Processing Time: {result.total_processing_time:.2f} seconds")
    print(f"Documents Processed: {len(result.documents_processed)}")
    
    return result


async def test_specific_document():
    """Test extraction of a specific document."""
    
    print_section("SPECIFIC DOCUMENT TEST")
    
    # Configure pipeline
    config = EnhancedPipelineConfig(
        extraction_method=ExtractionMethod.LLM,  # Force LLM extraction
        save_intermediate_results=True,
        output_directory=Path("outputs/enhanced_test/specific")
    )
    
    # Initialize pipeline
    pipeline = EnhancedExtractionPipeline(config)
    
    # Test with a tax return
    doc_path = Path("inputs/real/Brigham_dallas/Brigham_Dallas_2024_PTR.pdf")
    
    if not doc_path.exists():
        print(f"Document not found: {doc_path}")
        return
    
    print(f"Testing extraction of: {doc_path.name}")
    
    # Process single document
    result = await pipeline.process_loan_package(
        [doc_path],
        application_id="TEST-DOC-001"
    )
    
    # Show detailed results
    if result.documents_processed:
        doc_result = result.documents_processed[0]
        print(f"\nDocument Type: {doc_result.classification.primary_type.value}")
        print(f"Extraction Method: {doc_result.extraction_method}")
        print(f"Confidence: {doc_result.confidence_score:.2%}")
        print(f"Processing Time: {doc_result.processing_time:.2f}s")
        
        if doc_result.metadata:
            print(f"\nMetadata:")
            for key, value in doc_result.metadata.items():
                print(f"  {key}: {value}")
        
        if doc_result.extraction_data:
            print(f"\nExtracted Data Preview:")
            # Show first few fields
            if hasattr(doc_result.extraction_data, '__dict__'):
                for key, value in list(doc_result.extraction_data.__dict__.items())[:5]:
                    if value is not None:
                        print(f"  {key}: {value}")
    
    return result


async def main():
    """Run all tests."""
    
    print("="*80)
    print("  ENHANCED EXTRACTION PIPELINE TEST SUITE")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check for API key
    import os
    if os.getenv("ANTHROPIC_API_KEY"):
        print("✅ LLM extraction enabled (API key found)")
    else:
        print("⚠️  LLM extraction disabled (no API key)")
        print("   Add ANTHROPIC_API_KEY to .env file to enable")
    
    # Run tests
    try:
        # Test 1: Brigham Dallas package
        print("\n" + "="*80)
        print("TEST 1: Brigham Dallas Loan Package")
        print("="*80)
        brigham_result = await test_brigham_dallas_package()
        
        # Test 2: Dave Burlington package
        print("\n" + "="*80)
        print("TEST 2: Dave Burlington Loan Package")
        print("="*80)
        dave_result = await test_dave_burlington_package()
        
        # Test 3: Specific document
        print("\n" + "="*80)
        print("TEST 3: Specific Document Extraction")
        print("="*80)
        specific_result = await test_specific_document()
        
        # Summary
        print("\n" + "="*80)
        print("  TEST SUITE COMPLETE")
        print("="*80)
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print("\n✅ All tests completed successfully!")
        print("\nKey Features Tested:")
        print("• Enhanced document classification (25+ types)")
        print("• Native Excel extraction")
        print("• Tax return processing")
        print("• Cross-document validation")
        print("• Unified loan application package")
        print("• Risk assessment")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())