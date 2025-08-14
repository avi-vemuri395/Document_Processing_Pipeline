#!/usr/bin/env python3
"""
Test the date extractor functionality.
"""

from pathlib import Path
from datetime import date
from src.template_extraction import ExtractionOrchestrator
from src.template_extraction.extractors.date import DateExtractor


def test_date_parsing():
    """Test date parsing functionality."""
    print("\n" + "="*70)
    print("🧪 TESTING DATE PARSING")
    print("="*70)
    
    extractor = DateExtractor()
    
    test_dates = [
        ("01/15/2025", date(2025, 1, 15)),
        ("2025-01-15", date(2025, 1, 15)),
        ("January 15, 2025", date(2025, 1, 15)),
        ("15 January 2025", date(2025, 1, 15)),
        ("Jan 15, 2025", date(2025, 1, 15)),
        ("01/15/25", date(2025, 1, 15)),
        ("12-31-2024", date(2024, 12, 31)),
    ]
    
    for date_str, expected in test_dates:
        parsed = extractor._parse_date(date_str)
        if parsed == expected:
            print(f"  ✓ '{date_str}' -> {parsed}")
        else:
            print(f"  ✗ '{date_str}' -> {parsed} (expected {expected})")
    
    print("\n✅ Date parsing test completed!")


def test_huntington_dates():
    """Test date extraction with Huntington template."""
    print("\n" + "="*70)
    print("📅 TESTING DATE EXTRACTION - HUNTINGTON")
    print("="*70)
    
    orchestrator = ExtractionOrchestrator()
    
    # Test with Huntington PDF
    pdf_path = Path("templates/Huntington Bank Personal Financial Statement.pdf")
    
    result = orchestrator.process_document(
        pdf_path=pdf_path,
        form_id="huntington_pfs",
        application_id="date_test"
    )
    
    # Check date fields
    date_fields = ['Date of Birth', 'Issue Date', 'Exp Date', 'Spouse Date of Birth']
    
    print("\n📅 Date Fields Status:")
    for field_name in date_fields:
        value = result['extracted_fields'].get(field_name)
        if value:
            print(f"  ✓ {field_name}: {value}")
        else:
            print(f"  ✗ {field_name}: Not extracted")
    
    print("\n✅ Date extraction test completed!")


def test_live_oak_dates():
    """Test date extraction with Live Oak template."""
    print("\n" + "="*70)
    print("📅 TESTING DATE EXTRACTION - LIVE OAK")
    print("="*70)
    
    orchestrator = ExtractionOrchestrator()
    
    # Find a filled Live Oak PDF if available
    filled_pdfs = list(Path("outputs/filled_pdfs").glob("Live_Oak_*.pdf"))
    
    if filled_pdfs:
        pdf_path = filled_pdfs[0]
        print(f"Testing with: {pdf_path.name}")
        
        result = orchestrator.process_document(
            pdf_path=pdf_path,
            form_id="live_oak_application",
            application_id="date_test_live_oak"
        )
        
        # Check date field
        date_value = result['extracted_fields'].get('Date of Birth')
        if date_value:
            print(f"  ✓ Date of Birth: {date_value}")
        else:
            print(f"  ✗ Date of Birth: Not extracted")
    else:
        print("  ⚠️  No filled Live Oak PDFs found for testing")
    
    print("\n✅ Live Oak date test completed!")


if __name__ == "__main__":
    # Test date parsing
    test_date_parsing()
    
    # Test with templates
    test_huntington_dates()
    test_live_oak_dates()