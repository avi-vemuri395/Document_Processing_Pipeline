#!/usr/bin/env python3
"""
Test the Two-Part Pipeline Architecture - CORRECTED VERSION

CORRECT FLOW:
Part 1: Extract data ONCE from source documents
Part 2: Map extracted data to multiple bank forms

OLD (WRONG) FLOW:
Part 1: Process documents with all 9 templates (extracting 9 times)
Part 2: Map to bank forms (redundant)
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime

# Import the CORRECT implementation
from src.template_extraction.pipeline_orchestrator import PipelineOrchestrator

# The old wrong implementation (kept for comparison)
try:
    from src.template_extraction.multi_template_processor_WRONG import MultiTemplateProcessor
except ImportError:
    MultiTemplateProcessor = None


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


async def test_correct_part1_document_processing():
    """
    Test Part 1: CORRECT Document Processing (Extract ONCE)
    
    This processes REAL source documents and extracts data comprehensively,
    not using form templates for extraction.
    """
    
    print_section("PART 1: CORRECT DOCUMENT PROCESSING (Extract ONCE)")
    
    orchestrator = PipelineOrchestrator()
    application_id = "correct_two_part_test_001"
    
    # Use REAL source documents from inputs/real/
    real_documents = [
        Path("inputs/real/Brigham_dallas/Brigham Personal Financial Statement 2024 (Signed).pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_2023_Tax_Return.pdf"),
    ]
    
    # Filter to existing documents
    existing_docs = [doc for doc in real_documents if doc.exists()]
    
    if not existing_docs:
        print("❌ No real source documents found!")
        print("  Please ensure inputs/real/Brigham_dallas/ contains documents")
        return None
    
    print(f"\nProcessing {len(existing_docs)} real documents:")
    for doc in existing_docs:
        print(f"  ✅ {doc.name}")
    
    # Process documents ONCE comprehensively
    master_data = await orchestrator.part1_processor.process_documents(
        existing_docs,
        application_id
    )
    
    # Show extraction summary
    print(f"\n  Extraction Summary:")
    print(f"    Documents processed: {len(existing_docs)}")
    print(f"    Data categories extracted:")
    
    for category, fields in master_data.items():
        if isinstance(fields, dict) and category != "metadata":
            count = len(fields)
            if count > 0:
                print(f"      • {category}: {count} fields")
    
    total_fields = sum(
        len(fields) for category, fields in master_data.items()
        if isinstance(fields, dict) and category != "metadata"
    )
    print(f"    Total fields extracted: {total_fields}")
    
    return application_id


def test_correct_part2_form_mapping(application_id: str):
    """
    Test Part 2: CORRECT Form Mapping (Map to Many)
    
    This maps the SINGLE master data from Part 1 to multiple bank forms.
    """
    
    print_section("PART 2: CORRECT FORM MAPPING (Map to Many)")
    
    if not application_id:
        print("❌ No application ID provided. Run Part 1 first.")
        return
    
    mapper = FormMappingService()
    
    print("\nMapping master data to 9 forms across 3 banks...")
    print("  Note: Only Live Oak and Huntington have PDF templates")
    print("  Wells Fargo will have JSON mapping only\n")
    
    # Process all banks
    results = mapper.map_all_forms(application_id)
    
    # Display results
    total_pdfs = 0
    total_forms = 0
    
    for bank, bank_results in results.items():
        print(f"\n🏦 {bank.upper()} Bank:")
        
        for form_type, form_data in bank_results.items():
            total_forms += 1
            coverage = form_data.get('coverage', 0)
            mapped = form_data.get('mapped_fields', 0)
            total = form_data.get('total_fields', 0)
            
            print(f"  📝 {form_type}:")
            print(f"     Mapped: {mapped}/{total} fields ({coverage}% coverage)")
            
            if form_data.get('pdf_path'):
                total_pdfs += 1
                pdf_path = Path(form_data['pdf_path'])
                print(f"     PDF: ✅ {pdf_path.name}")
            else:
                print(f"     PDF: ⚠️  No template available")
    
    print(f"\n  Summary:")
    print(f"    Total forms mapped: {total_forms}")
    print(f"    PDFs generated: {total_pdfs}")
    print(f"    JSON mappings: {total_forms}")


def test_incremental_document_addition(application_id: str):
    """Test adding a document incrementally"""
    
    print_section("INCREMENTAL DOCUMENT ADDITION")
    
    processor = MultiTemplateProcessor()
    
    # Add Wells Fargo template as a new document
    new_doc = Path("templates/form_specs/wells_fargo_loan_app_v1.json")
    
    if new_doc.exists():
        print(f"\nAdding new document: {new_doc.name}")
        
        result = processor.process_document_all_templates(
            document_path=new_doc,
            application_id=application_id
        )
        
        print(f"  Document ID: {result['document_id']}")
        print(f"  Templates Applied: {len(result['metadata']['templates_applied'])}")
        
        # Re-run Part 2 to update forms with new data
        print("\n  Re-mapping forms with updated data...")
        processor.map_to_bank_forms(application_id, "wells_fargo")
        
        # Show updated state
        state_file = Path(f"outputs/applications/{application_id}/part1_document_processing/state/current.json")
        if state_file.exists():
            with open(state_file, 'r') as f:
                state = json.load(f)
                
            print(f"\n  Updated State:")
            print(f"    Total Documents: {state['documents_processed']}")
            print(f"    Fields Extracted: {state['field_coverage']['fields_extracted']}")
            print(f"    Coverage: {state['field_coverage']['coverage_percentage']:.1f}%")


def test_conflict_analysis(application_id: str):
    """Analyze field conflicts in master data"""
    
    print_section("CONFLICT ANALYSIS")
    
    state_file = Path(f"outputs/applications/{application_id}/part1_document_processing/state/current.json")
    
    if state_file.exists():
        with open(state_file, 'r') as f:
            state = json.load(f)
            
        conflicts_found = 0
        print("\nAnalyzing field conflicts...")
        
        for category, fields in state['master_data'].items():
            for field_name, field_data in fields.items():
                if isinstance(field_data, dict) and 'conflicts' in field_data:
                    conflicts_found += 1
                    print(f"\n  Conflict in {category}.{field_name}:")
                    print(f"    Current: {field_data['value']} (from {field_data['source_template']})")
                    for conflict in field_data['conflicts']:
                        print(f"    Previous: {conflict['value']} (from {conflict['source']})")
        
        if conflicts_found == 0:
            print("  No conflicts found in master data")
        else:
            print(f"\n  Total conflicts: {conflicts_found}")


def test_state_history(application_id: str):
    """Review state history for audit trail"""
    
    print_section("STATE HISTORY AUDIT TRAIL")
    
    history_dir = Path(f"outputs/applications/{application_id}/part1_document_processing/state/history")
    
    if history_dir.exists():
        history_files = sorted(history_dir.glob("*.json"))
        
        print(f"\nFound {len(history_files)} state snapshots")
        
        for i, history_file in enumerate(history_files[-3:], 1):  # Show last 3
            with open(history_file, 'r') as f:
                state = json.load(f)
                
            print(f"\n  Snapshot {i}: {history_file.name}")
            print(f"    Timestamp: {state['last_updated']}")
            print(f"    Documents: {state['documents_processed']}")
            print(f"    Fields: {state['field_coverage']['fields_extracted']}")
            print(f"    Coverage: {state['field_coverage']['coverage_percentage']:.1f}%")


async def main():
    """Run complete two-part pipeline test - CORRECTED VERSION"""
    
    print("\n" + "="*70)
    print("  TWO-PART PIPELINE ARCHITECTURE TEST - CORRECTED")
    print("="*70)
    print("\n🎯 CORRECT IMPLEMENTATION:")
    print("  1. Extract data ONCE from source documents")
    print("  2. Map extracted data to 9 forms across 3 banks")
    print("  3. Generate PDFs where templates exist (Live Oak, Huntington)")
    print("\n❌ OLD (WRONG) IMPLEMENTATION:")
    print("  - Extracted with 9 templates from each document")
    print("  - Redundant processing and mapping")
    
    # Import the correct form mapping service
    from src.template_extraction.form_mapping_service import FormMappingService
    
    # Part 1: Process documents CORRECTLY
    application_id = await test_correct_part1_document_processing()
    
    if application_id:
        # Part 2: Map to bank forms CORRECTLY
        test_correct_part2_form_mapping(application_id)
        
        # Final summary
        print_section("TEST COMPLETE")
        
        print(f"\nApplication ID: {application_id}")
        print(f"Output Directory: outputs/applications/{application_id}/")
        print("\nKey directories created:")
        print("  - part1_document_processing/")
        print("    - master_data.json (single extraction)")
        print("    - extractions/ (individual document extractions)")
        print("    - state/ (processing state)")
        print("  - part2_form_mapping/")
        print("    - banks/")
        print("      - live_oak/ (3 forms + PDFs)")
        print("      - huntington/ (4 forms + PDFs)")
        print("      - wells_fargo/ (2 forms, JSON only)")
        
        print("\n✅ CORRECT Two-part pipeline successfully demonstrated!")
        print("   Extract ONCE → Map to MANY")
    else:
        print("\n❌ Test failed: Could not process documents")


if __name__ == "__main__":
    asyncio.run(main())