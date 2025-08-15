#!/usr/bin/env python3
"""
Test incremental document processing with merging.
Demonstrates processing documents one at a time and merging results.
"""

from pathlib import Path
from src.template_extraction import ExtractionOrchestrator
from src.template_extraction.incremental_utils import (
    merge_extractions,
    save_incremental_state,
    load_application_state,
    load_document_extractions,
    analyze_conflicts
)
import json
from datetime import datetime


def test_single_document_processing():
    """Test processing documents one at a time."""
    
    print("\n" + "="*70)
    print("📄 INCREMENTAL DOCUMENT PROCESSING TEST")
    print("="*70)
    
    orchestrator = ExtractionOrchestrator()
    app_id = "incremental_test_001"
    
    # Create application folder structure
    app_dir = Path(f"outputs/applications/{app_id}")
    (app_dir / "documents").mkdir(parents=True, exist_ok=True)
    (app_dir / "extractions").mkdir(parents=True, exist_ok=True)
    (app_dir / "state").mkdir(parents=True, exist_ok=True)
    
    # Test documents to process
    test_documents = [
        {
            'path': 'templates/Live Oak Express - Application Forms.pdf',
            'doc_id': 'doc_001',
            'form_id': 'live_oak_application',
            'description': 'Live Oak Application Form'
        },
        {
            'path': 'templates/Huntington Bank Personal Financial Statement.pdf',
            'doc_id': 'doc_002',
            'form_id': 'huntington_pfs',
            'description': 'Huntington PFS Form'
        }
    ]
    
    # Process each document incrementally
    all_extractions = []
    
    for doc_info in test_documents:
        pdf_path = Path(doc_info['path'])
        
        if not pdf_path.exists():
            print(f"⚠️  Skipping {doc_info['description']}: File not found")
            continue
        
        print(f"\n📄 Processing Document {len(all_extractions) + 1}: {doc_info['description']}")
        print("-" * 50)
        
        try:
            # Process single document
            doc_result = orchestrator.process_single_document(
                pdf_path=pdf_path,
                form_id=doc_info['form_id'],
                application_id=app_id,
                document_id=doc_info['doc_id']
            )
            
            # Display extraction summary
            print(f"✅ Extracted {len(doc_result['extracted_fields'])} fields")
            print(f"   Coverage: {doc_result['metadata']['coverage']:.1f}%")
            
            # Show sample fields
            if doc_result['extracted_fields']:
                print("   Sample fields extracted:")
                for field_name, value in list(doc_result['extracted_fields'].items())[:3]:
                    confidence = doc_result['confidence_scores'].get(field_name, 0.0)
                    print(f"     - {field_name}: {value} (confidence: {confidence:.2f})")
            
            all_extractions.append(doc_result)
            
            # Merge with existing state
            if len(all_extractions) == 1:
                # First document - initialize state
                merged_state = merge_extractions([doc_result], strategy='confidence_based')
                print(f"\n📊 Initial State Created:")
                print(f"   Total fields: {len(merged_state['merged_fields'])}")
            else:
                # Subsequent documents - merge with existing
                merged_state = merge_extractions(all_extractions, strategy='confidence_based')
                print(f"\n📊 Merged State Updated:")
                print(f"   Total unique fields: {len(merged_state['merged_fields'])}")
                print(f"   Documents processed: {merged_state['documents_processed']}")
                print(f"   Overall coverage: {merged_state['metadata']['coverage_percentage']:.1f}%")
                
                # Check for conflicts
                if merged_state['conflicts']:
                    print(f"   ⚠️  Field conflicts: {len(merged_state['conflicts'])}")
            
            # Save incremental state
            save_incremental_state(app_id, doc_result, merged_state)
            
        except Exception as e:
            print(f"❌ Error processing document: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    
    if all_extractions:
        # Analyze final state
        print(f"\n✅ Successfully processed {len(all_extractions)} documents")
        print(f"📁 Application ID: {app_id}")
        print(f"📊 Total unique fields extracted: {len(merged_state['merged_fields'])}")
        print(f"📈 Overall coverage: {merged_state['metadata']['coverage_percentage']:.1f}%")
        
        # Analyze conflicts
        conflict_analysis = analyze_conflicts(merged_state)
        if conflict_analysis['has_conflicts']:
            print(f"\n⚠️  Field Conflicts Analysis:")
            print(f"   Total conflicts: {conflict_analysis['conflict_count']}")
            print(f"   Affected fields: {', '.join(conflict_analysis['affected_fields'][:5])}")
            
            resolution_stats = conflict_analysis['resolution_stats']
            print(f"   Resolution breakdown:")
            print(f"     - Kept existing: {resolution_stats['resolved_to_current']}")
            print(f"     - Updated to new: {resolution_stats['resolved_to_new']}")
            
            if resolution_stats['needs_manual_review']:
                print(f"   📝 Fields needing manual review: {', '.join(resolution_stats['needs_manual_review'][:3])}")
        
        # Show output structure
        print(f"\n📁 Output Structure Created:")
        print(f"   outputs/applications/{app_id}/")
        print(f"   ├── extractions/          # Per-document results")
        for extraction in all_extractions:
            print(f"   │   └── {extraction['document_id']}.json")
        print(f"   └── state/               # Application state")
        print(f"       ├── current.json     # Current merged state")
        print(f"       └── history/         # State snapshots")
    
    return merged_state if all_extractions else None


def test_merge_strategies():
    """Test different merge strategies with conflicting data."""
    
    print("\n" + "="*70)
    print("🔀 MERGE STRATEGY COMPARISON TEST")
    print("="*70)
    
    # Create mock extractions with conflicts
    doc1 = {
        'document_id': 'doc_001',
        'application_id': 'test_app',
        'form_id': 'live_oak_application',
        'document_name': 'pfs_2023.pdf',
        'extracted_fields': {
            'Name': 'John Doe',
            'SSN': '123-45-6789',
            'Income': 100000
        },
        'confidence_scores': {
            'Name': 0.95,
            'SSN': 0.90,
            'Income': 0.85
        }
    }
    
    doc2 = {
        'document_id': 'doc_002',
        'application_id': 'test_app',
        'form_id': 'live_oak_application',
        'document_name': 'tax_return_2023.pdf',
        'extracted_fields': {
            'Name': 'John M. Doe',  # Slight variation
            'SSN': '123-45-6789',    # Same
            'Income': 105000,        # Different
            'Address': '123 Main St'  # New field
        },
        'confidence_scores': {
            'Name': 0.88,     # Lower confidence
            'SSN': 0.95,      # Higher confidence
            'Income': 0.92,   # Higher confidence
            'Address': 0.90
        }
    }
    
    strategies = ['first_wins', 'last_wins', 'confidence_based', 'source_priority']
    
    for strategy in strategies:
        print(f"\n📋 Strategy: {strategy}")
        print("-" * 40)
        
        merged = merge_extractions([doc1, doc2], strategy=strategy)
        
        print(f"Final values:")
        print(f"  - Name: {merged['merged_fields']['Name']} (from: {merged['field_sources']['Name']})")
        print(f"  - Income: {merged['merged_fields']['Income']} (from: {merged['field_sources']['Income']})")
        print(f"  - Address: {merged['merged_fields'].get('Address', 'N/A')} (from: {merged['field_sources'].get('Address', 'N/A')})")
        print(f"  - Conflicts recorded: {len(merged['conflicts'])}")


def test_load_existing_state():
    """Test loading and updating existing application state."""
    
    print("\n" + "="*70)
    print("💾 LOAD EXISTING STATE TEST")
    print("="*70)
    
    app_id = "incremental_test_001"
    
    # Try to load existing state
    existing_state = load_application_state(app_id)
    
    if existing_state:
        print(f"✅ Loaded existing state for application: {app_id}")
        print(f"   Documents processed: {existing_state['documents_processed']}")
        print(f"   Total fields: {len(existing_state['merged_fields'])}")
        print(f"   Last updated: {existing_state['last_updated']}")
        
        # Load all document extractions
        extractions = load_document_extractions(app_id)
        print(f"\n📄 Found {len(extractions)} document extractions:")
        for extraction in extractions:
            print(f"   - {extraction['document_id']}: {extraction['document_name']} ({len(extraction['extracted_fields'])} fields)")
    else:
        print(f"ℹ️  No existing state found for application: {app_id}")
        print("   Run test_single_document_processing() first to create state")


if __name__ == "__main__":
    # Run tests
    print("\n🚀 Running Incremental Processing Tests")
    
    # Test 1: Process documents incrementally
    final_state = test_single_document_processing()
    
    # Test 2: Compare merge strategies
    test_merge_strategies()
    
    # Test 3: Load existing state
    test_load_existing_state()
    
    print("\n✅ All incremental processing tests completed!")
    
    # Save test results summary
    if final_state:
        summary_file = Path("outputs/incremental_test_summary.json")
        with open(summary_file, 'w') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'application_id': final_state['application_id'],
                'documents_processed': final_state['documents_processed'],
                'total_fields': len(final_state['merged_fields']),
                'coverage': final_state['metadata']['coverage_percentage'],
                'conflicts': len(final_state['conflicts']),
                'merge_strategy': final_state['metadata']['merge_strategy']
            }, f, indent=2)
        print(f"\n💾 Test summary saved to: {summary_file}")