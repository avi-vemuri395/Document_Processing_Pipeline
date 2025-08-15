#!/usr/bin/env python3
"""
Test Spreadsheet Population functionality
Demonstrates populating Excel templates with master JSON data
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from src.template_extraction.pipeline_orchestrator import PipelineOrchestrator
from src.template_extraction.spreadsheet_mapping_service import SpreadsheetMappingService


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


async def test_spreadsheet_population():
    """
    Test spreadsheet population with master data from Part 1.
    
    This test:
    1. Processes documents to create master data (Part 1)
    2. Generates forms (Part 2)
    3. Populates spreadsheets (Part 2b)
    """
    
    print_section("SPREADSHEET POPULATION TEST")
    
    orchestrator = PipelineOrchestrator()
    application_id = "spreadsheet_test_001"
    
    # Source documents
    source_documents = [
        Path("inputs/real/Brigham_dallas/Brigham Personal Financial Statement 2024 (Signed).pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_2023_Tax_Return.pdf"),
    ]
    
    # Filter to existing documents
    existing_docs = [doc for doc in source_documents if doc.exists()]
    
    if not existing_docs:
        print("❌ No source documents found!")
        return
    
    print(f"\n📄 Processing {len(existing_docs)} documents:")
    for doc in existing_docs:
        print(f"  • {doc.name}")
    
    # Run full pipeline with spreadsheet generation enabled
    results = await orchestrator.process_application(
        application_id=application_id,
        documents=existing_docs,
        target_banks=["live_oak"],  # Just process one bank for speed
        generate_spreadsheets=True  # Enable spreadsheet generation
    )
    
    # Display spreadsheet results
    print_section("SPREADSHEET RESULTS")
    
    spreadsheet_results = results.get("spreadsheet_results", {})
    
    if not spreadsheet_results:
        print("  ❌ No spreadsheets generated")
        return
    
    print(f"\n  Generated {len(spreadsheet_results)} spreadsheets:")
    
    for sheet_type, result in spreadsheet_results.items():
        if result.get("status") == "success":
            print(f"\n  📊 {sheet_type}:")
            print(f"     Status: ✅ Success")
            print(f"     Output: {Path(result['output_path']).name}")
            print(f"     Template: {Path(result['template']).name}")
        else:
            print(f"\n  📊 {sheet_type}:")
            print(f"     Status: ❌ Error")
            print(f"     Error: {result.get('error', 'Unknown')}")
    
    # Check output directory
    output_dir = Path(f"outputs/applications/{application_id}/part2_spreadsheets")
    if output_dir.exists():
        files = list(output_dir.glob("*.xlsx"))
        print(f"\n  📁 Output directory contains {len(files)} Excel files:")
        for file in files:
            file_size = file.stat().st_size / 1024  # KB
            print(f"     • {file.name} ({file_size:.1f} KB)")
    
    print(f"\n✅ Spreadsheet population test complete!")
    print(f"   Check: {output_dir}")


async def test_direct_spreadsheet_service():
    """
    Test the spreadsheet service directly without full pipeline.
    Useful for debugging specific spreadsheet issues.
    """
    
    print_section("DIRECT SPREADSHEET SERVICE TEST")
    
    # Create sample master data
    sample_master_data = {
        "personal_info": {
            "name": "John Doe",
            "ssn": "XXX-XX-1234",
            "phone": "555-123-4567"
        },
        "business_info": {
            "business_name": "Acme Corporation",
            "ein": "12-3456789",
            "industry": "Manufacturing"
        },
        "financial_data": {
            "total_assets": 4397552,
            "total_liabilities": 2044663,
            "net_worth": 2352889,
            "working_capital": 150000
        },
        "debt_schedules": {
            "mortgage_1": {
                "creditor": "Wells Fargo Bank",
                "original_amount": 500000,
                "current_balance": 425000,
                "interest_rate": 4.5,
                "monthly_payment": 2533,
                "purpose": "Building purchase"
            },
            "equipment_loan": {
                "creditor": "Equipment Finance Co",
                "original_amount": 100000,
                "current_balance": 75000,
                "interest_rate": 6.0,
                "monthly_payment": 1500,
                "purpose": "Manufacturing equipment"
            }
        },
        "metadata": {
            "application_id": "direct_test_001",
            "created": datetime.now().isoformat()
        }
    }
    
    # Save sample master data
    app_id = "direct_test_001"
    master_path = Path(f"outputs/applications/{app_id}/part1_document_processing/master_data.json")
    master_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(master_path, 'w') as f:
        json.dump(sample_master_data, f, indent=2)
    
    print(f"  Created sample master data for testing")
    
    # Test spreadsheet service
    service = SpreadsheetMappingService()
    
    # Test individual spreadsheet population
    print(f"\n  Testing Debt Schedule population...")
    try:
        debt_path = service.populate_debt_schedule(sample_master_data, app_id)
        print(f"    ✅ Generated: {debt_path.name}")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    print(f"\n  Testing Use of Funds population...")
    try:
        use_path = service.populate_use_of_funds(sample_master_data, app_id)
        print(f"    ✅ Generated: {use_path.name}")
    except Exception as e:
        print(f"    ❌ Error: {e}")
    
    # Test all spreadsheets
    print(f"\n  Testing all spreadsheets...")
    results = service.populate_all_spreadsheets(app_id)
    
    print(f"\n  Results: {len(results)} spreadsheets processed")
    for sheet_type, result in results.items():
        status = "✅" if result.get("status") == "success" else "❌"
        print(f"    {status} {sheet_type}")


async def main():
    """Run all spreadsheet tests"""
    
    print("\n" + "="*70)
    print("  SPREADSHEET POPULATION TESTING")
    print("="*70)
    
    # Test 1: Full pipeline with spreadsheets
    await test_spreadsheet_population()
    
    # Test 2: Direct service test
    print("\n")
    await test_direct_spreadsheet_service()
    
    print("\n" + "="*70)
    print("  ALL SPREADSHEET TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())