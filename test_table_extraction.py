#!/usr/bin/env python3
"""
Test table extraction functionality.
Part of Phase 3 implementation.
"""

from pathlib import Path
from src.template_extraction import ExtractionOrchestrator
from src.template_extraction.exporters import DataExporter
import json


def test_table_extraction():
    """Test extraction of tables from financial documents."""
    
    print("\n" + "="*70)
    print("📊 TABLE EXTRACTION TEST")
    print("="*70)
    
    orchestrator = ExtractionOrchestrator()
    exporter = DataExporter()
    
    # Test with different documents that might contain tables
    test_cases = [
        {
            'name': 'Live Oak Bank Form',
            'pdf': 'templates/Live Oak Express - Application Forms.pdf',
            'form_id': 'live_oak_application'
        },
        {
            'name': 'Huntington Bank PFS',
            'pdf': 'templates/Huntington Bank Personal Financial Statement.pdf',
            'form_id': 'huntington_pfs'
        }
    ]
    
    # Also check for real documents that might have tables
    real_docs_path = Path("inputs/real")
    if real_docs_path.exists():
        # Look for debt schedules or financial statements
        for doc_path in real_docs_path.glob("**/*.pdf"):
            if any(keyword in doc_path.name.lower() 
                   for keyword in ['debt', 'schedule', 'financial', 'statement', 'balance']):
                test_cases.append({
                    'name': doc_path.name,
                    'pdf': str(doc_path),
                    'form_id': 'wells_fargo_loan_app'  # Use Wells Fargo template for real docs
                })
                print(f"  📄 Found potential table document: {doc_path.name}")
    
    all_results = []
    
    for test_case in test_cases:
        print(f"\n📄 Testing: {test_case['name']}")
        print("-" * 50)
        
        pdf_path = Path(test_case['pdf'])
        
        if not pdf_path.exists():
            print(f"  ⚠️  PDF not found: {pdf_path}")
            continue
        
        try:
            # Process document
            result = orchestrator.process_document(
                pdf_path=pdf_path,
                form_id=test_case['form_id'],
                application_id=f"table_test_{pdf_path.stem}"
            )
            
            # Check for extracted tables
            tables = result.get('tables', [])
            
            if tables:
                print(f"\n  ✅ Found {len(tables)} tables!")
                
                for idx, table in enumerate(tables):
                    print(f"\n  Table {idx + 1}:")
                    print(f"    Type: {table.get('type', 'unknown')}")
                    print(f"    Page: {table.get('page', '?')}")
                    print(f"    Rows: {table.get('rows', 0)}")
                    print(f"    Columns: {table.get('columns', 0)}")
                    print(f"    Strategy: {table.get('strategy', 'unknown')}")
                    
                    # Show extracted values if any
                    if 'extracted_values' in table:
                        print(f"    Extracted Values:")
                        for key, value in table['extracted_values'].items():
                            if isinstance(value, (int, float)):
                                print(f"      - {key}: ${value:,.2f}")
                            else:
                                print(f"      - {key}: {value}")
                    
                    # Show first few rows of data
                    if 'data' in table and table['data']:
                        print(f"    Sample Data (first 3 rows):")
                        for row in table['data'][:3]:
                            print(f"      {row}")
            else:
                print("  ℹ️  No tables found in this document")
            
            # Check for table-related fields
            table_fields = ['total_debt', 'total_assets', 'debt_count', 'asset_count',
                          'total_liabilities', 'net_worth']
            
            extracted_fields = result.get('extracted_fields', {})
            table_field_values = {k: v for k, v in extracted_fields.items() 
                                if any(tf in k.lower() for tf in table_fields)}
            
            if table_field_values:
                print(f"\n  💰 Table-derived field values:")
                for field, value in table_field_values.items():
                    print(f"    - {field}: {value}")
            
            # Store result for export
            all_results.append(result)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Export results if we found any tables
    if any(r.get('tables', []) for r in all_results):
        print("\n" + "="*70)
        print("📤 EXPORTING RESULTS")
        print("="*70)
        
        # Export to Excel
        excel_path = exporter.export_to_excel(
            all_results,
            "table_extraction_results",
            include_tables=True
        )
        print(f"  📊 Excel export: {excel_path}")
        
        # Export to CSV
        csv_path = exporter.export_to_csv(
            all_results,
            "table_extraction_results"
        )
        print(f"  📝 CSV export: {csv_path}")
        
        # Export to JSON for detailed analysis
        json_path = exporter.export_to_json(
            all_results,
            "table_extraction_results"
        )
        print(f"  📋 JSON export: {json_path}")
    
    # Summary
    print("\n" + "="*70)
    print("📊 TABLE EXTRACTION SUMMARY")
    print("="*70)
    
    total_tables = sum(len(r.get('tables', [])) for r in all_results)
    docs_with_tables = sum(1 for r in all_results if r.get('tables', []))
    
    print(f"\nDocuments Processed: {len(all_results)}")
    print(f"Documents with Tables: {docs_with_tables}")
    print(f"Total Tables Found: {total_tables}")
    
    if total_tables > 0:
        # Table type breakdown
        table_types = {}
        for result in all_results:
            for table in result.get('tables', []):
                t_type = table.get('type', 'unknown')
                table_types[t_type] = table_types.get(t_type, 0) + 1
        
        print(f"\nTable Types:")
        for t_type, count in table_types.items():
            print(f"  - {t_type}: {count}")
        
        # Strategy breakdown
        strategies = {}
        for result in all_results:
            for table in result.get('tables', []):
                strategy = table.get('strategy', 'unknown')
                strategies[strategy] = strategies.get(strategy, 0) + 1
        
        print(f"\nExtraction Strategies:")
        for strategy, count in strategies.items():
            print(f"  - {strategy}: {count}")
    
    print("\n" + "="*70)


def test_specific_table_document():
    """Test table extraction on a specific document with known tables."""
    
    print("\n" + "="*70)
    print("📊 SPECIFIC TABLE DOCUMENT TEST")
    print("="*70)
    
    # Try to find a document with debt schedule or financial tables
    test_paths = [
        Path("inputs/real/Brigham_dallas/Brigham Debt Schedule and Collateral.xlsx"),
        Path("inputs/real/Dave_burlington/Dave Debt Schedule_14Nov2024.xlsx"),
        Path("inputs/real/Brigham_dallas/Form 5405 - Brigham Builders - 2024.pdf"),
    ]
    
    for test_path in test_paths:
        if test_path.exists():
            print(f"\n📄 Testing: {test_path.name}")
            
            if test_path.suffix == '.xlsx':
                print("  ℹ️  Excel file - would need to convert to PDF first")
                # Note: In production, you'd convert Excel to PDF or extract directly
            else:
                # Use table extractor directly
                from src.template_extraction.extractors.table import TableExtractor
                
                extractor = TableExtractor()
                tables = extractor._extract_all_tables(test_path)
                
                if tables:
                    print(f"  ✅ Found {len(tables)} tables!")
                    for idx, table in enumerate(tables):
                        print(f"\n  Table {idx + 1}:")
                        print(f"    Type: {table.get('type', 'unknown')}")
                        print(f"    Rows: {table.get('rows', 0)}")
                        print(f"    Strategy: {table.get('strategy', 'unknown')}")
                        
                        if 'extracted_values' in table:
                            print(f"    Values:")
                            for k, v in table['extracted_values'].items():
                                print(f"      - {k}: {v}")
                else:
                    print("  ℹ️  No tables found")


if __name__ == "__main__":
    # Run main table extraction test
    test_table_extraction()
    
    # Run specific document test
    test_specific_table_document()