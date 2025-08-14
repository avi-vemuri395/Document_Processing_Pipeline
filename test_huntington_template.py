#!/usr/bin/env python3
"""
Test the Huntington Bank template extraction.
"""

from pathlib import Path
from src.template_extraction import ExtractionOrchestrator

def test_huntington_template():
    """Test extraction using the Huntington template."""
    
    # Initialize orchestrator
    orchestrator = ExtractionOrchestrator()
    
    # Test with the Huntington template PDF
    pdf_path = Path("templates/Huntington Bank Personal Financial Statement.pdf")
    
    print("\n" + "="*70)
    print("🏦 TESTING HUNTINGTON BANK TEMPLATE")
    print("="*70)
    
    try:
        # Process the document
        result = orchestrator.process_document(
            pdf_path=pdf_path,
            form_id="huntington_pfs",
            application_id="huntington_test"
        )
        
        # Print extracted fields
        print("\n📋 Extracted Fields:")
        extracted_fields = result['extracted_fields']
        for field_name, value in extracted_fields.items():
            if value is not None:
                print(f"  ✓ {field_name}: {value}")
        
        # Print metrics
        metrics = result['metrics']
        print(f"\n📊 Metrics:")
        print(f"  - Extracted: {metrics['extracted_fields']}/{metrics['total_fields']} fields")
        print(f"  - Coverage: {metrics['coverage_percentage']:.1f}%")
        print(f"  - Required: {metrics['required_extracted']}/{metrics['required_fields']} ({metrics['required_coverage']:.1f}%)")
        
        # Check for specific important fields
        important_fields = [
            'Applicant Full Legal Name',
            'Social Security Number', 
            'Date of Birth',
            'Total Assets',
            'Total Liabilities',
            'Net Worth',
            'Annual Income'
        ]
        
        print("\n🔍 Important Fields Check:")
        for field in important_fields:
            value = extracted_fields.get(field)
            status = "✓" if value else "✗"
            print(f"  {status} {field}: {value if value else 'Not extracted'}")
        
        print("\n✅ Huntington template test completed successfully!")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error testing Huntington template: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_huntington_template()