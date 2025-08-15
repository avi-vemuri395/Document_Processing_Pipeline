"""
Utilities for incremental document processing and merging.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json
from datetime import datetime


def merge_extractions(extractions: List[Dict[str, Any]], 
                     strategy: str = 'confidence_based') -> Dict[str, Any]:
    """
    Merge multiple document extractions into single application state.
    
    Args:
        extractions: List of document extraction results
        strategy: Merge strategy to use
            - 'first_wins': Keep first occurrence of each field
            - 'last_wins': Latest document overrides
            - 'confidence_based': Highest confidence wins
            - 'source_priority': Certain doc types have priority
    
    Returns:
        Merged application state with conflict tracking
    """
    if not extractions:
        raise ValueError("No extractions to merge")
    
    merged = {
        'application_id': extractions[0]['application_id'],
        'form_id': extractions[0]['form_id'],
        'last_updated': datetime.now().isoformat(),
        'documents_processed': len(extractions),
        'document_ids': [e['document_id'] for e in extractions],
        'merged_fields': {},
        'field_sources': {},
        'confidence_scores': {},
        'conflicts': [],
        'metadata': {
            'merge_strategy': strategy,
            'total_unique_fields': 0,
            'coverage_percentage': 0.0
        }
    }
    
    # Process each extraction
    for extraction in extractions:
        doc_id = extraction['document_id']
        
        for field_name, value in extraction.get('extracted_fields', {}).items():
            # Get confidence score for this field
            field_confidence = extraction.get('confidence_scores', {}).get(field_name, 0.5)
            
            if field_name not in merged['merged_fields']:
                # New field discovered
                merged['merged_fields'][field_name] = value
                merged['field_sources'][field_name] = doc_id
                merged['confidence_scores'][field_name] = field_confidence
                
            else:
                # Field already exists - apply merge strategy
                should_update = False
                existing_confidence = merged['confidence_scores'].get(field_name, 0.5)
                
                if strategy == 'first_wins':
                    # Keep existing value
                    should_update = False
                    
                elif strategy == 'last_wins':
                    # Always update with latest
                    should_update = True
                    
                elif strategy == 'confidence_based':
                    # Update if new confidence is higher
                    should_update = field_confidence > existing_confidence * 1.1  # 10% threshold
                    
                elif strategy == 'source_priority':
                    # Prioritize certain document types (can be customized)
                    priority_docs = ['tax_return', 'bank_statement', 'pfs']
                    doc_name = extraction.get('document_name', '').lower()
                    
                    is_priority = any(p in doc_name for p in priority_docs)
                    should_update = is_priority and field_confidence >= existing_confidence * 0.9
                
                # Check for conflicts
                if merged['merged_fields'][field_name] != value:
                    # Values differ - record conflict
                    conflict = {
                        'field_name': field_name,
                        'current_value': merged['merged_fields'][field_name],
                        'current_source': merged['field_sources'][field_name],
                        'current_confidence': existing_confidence,
                        'new_value': value,
                        'new_source': doc_id,
                        'new_confidence': field_confidence,
                        'resolved_to': 'current' if not should_update else 'new'
                    }
                    merged['conflicts'].append(conflict)
                
                # Update if needed
                if should_update:
                    merged['merged_fields'][field_name] = value
                    merged['field_sources'][field_name] = doc_id
                    merged['confidence_scores'][field_name] = field_confidence
    
    # Update metadata
    merged['metadata']['total_unique_fields'] = len(merged['merged_fields'])
    
    # Calculate coverage (assuming ~107 total fields across all templates)
    total_possible_fields = 107  # From our 3 bank templates
    merged['metadata']['coverage_percentage'] = (
        len(merged['merged_fields']) / total_possible_fields * 100
    )
    
    return merged


def save_incremental_state(application_id: str, 
                          document_result: Dict[str, Any],
                          merged_state: Dict[str, Any],
                          output_dir: Path = Path("outputs/applications")) -> None:
    """
    Save incremental processing results following recommended folder structure.
    
    Args:
        application_id: Application identifier
        document_result: Single document extraction result
        merged_state: Current merged application state
        output_dir: Base output directory
    """
    # Create folder structure
    app_dir = output_dir / application_id
    (app_dir / "documents").mkdir(parents=True, exist_ok=True)
    (app_dir / "extractions").mkdir(parents=True, exist_ok=True)
    (app_dir / "state").mkdir(parents=True, exist_ok=True)
    (app_dir / "state" / "history").mkdir(parents=True, exist_ok=True)
    
    doc_id = document_result['document_id']
    
    # Save document extraction
    extraction_file = app_dir / "extractions" / f"{doc_id}.json"
    with open(extraction_file, 'w') as f:
        json.dump(document_result, f, indent=2, default=str)
    
    # Save current state
    state_file = app_dir / "state" / "current.json"
    with open(state_file, 'w') as f:
        json.dump(merged_state, f, indent=2, default=str)
    
    # Save state snapshot for history
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    history_file = app_dir / "state" / "history" / f"{timestamp}.json"
    with open(history_file, 'w') as f:
        json.dump(merged_state, f, indent=2, default=str)
    
    print(f"💾 Saved incremental state:")
    print(f"   - Extraction: {extraction_file}")
    print(f"   - Current state: {state_file}")
    print(f"   - History snapshot: {history_file}")


def load_application_state(application_id: str,
                          output_dir: Path = Path("outputs/applications")) -> Optional[Dict[str, Any]]:
    """
    Load current application state if it exists.
    
    Args:
        application_id: Application identifier
        output_dir: Base output directory
        
    Returns:
        Current state or None if not found
    """
    state_file = output_dir / application_id / "state" / "current.json"
    
    if state_file.exists():
        with open(state_file, 'r') as f:
            return json.load(f)
    
    return None


def load_document_extractions(application_id: str,
                             output_dir: Path = Path("outputs/applications")) -> List[Dict[str, Any]]:
    """
    Load all document extractions for an application.
    
    Args:
        application_id: Application identifier
        output_dir: Base output directory
        
    Returns:
        List of document extraction results
    """
    extractions_dir = output_dir / application_id / "extractions"
    extractions = []
    
    if extractions_dir.exists():
        for json_file in sorted(extractions_dir.glob("*.json")):
            with open(json_file, 'r') as f:
                extractions.append(json.load(f))
    
    return extractions


def analyze_conflicts(merged_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze field conflicts and provide summary.
    
    Args:
        merged_state: Merged application state with conflicts
        
    Returns:
        Conflict analysis summary
    """
    conflicts = merged_state.get('conflicts', [])
    
    if not conflicts:
        return {
            'has_conflicts': False,
            'conflict_count': 0,
            'message': 'No field conflicts detected'
        }
    
    # Group conflicts by field
    field_conflicts = {}
    for conflict in conflicts:
        field_name = conflict['field_name']
        if field_name not in field_conflicts:
            field_conflicts[field_name] = []
        field_conflicts[field_name].append(conflict)
    
    # Analyze resolution patterns
    resolution_stats = {
        'resolved_to_current': 0,
        'resolved_to_new': 0,
        'high_confidence_wins': 0,
        'needs_manual_review': []
    }
    
    for field_name, field_conflict_list in field_conflicts.items():
        for conflict in field_conflict_list:
            if conflict['resolved_to'] == 'current':
                resolution_stats['resolved_to_current'] += 1
            else:
                resolution_stats['resolved_to_new'] += 1
            
            # Check if confidence difference is significant
            conf_diff = abs(conflict['current_confidence'] - conflict['new_confidence'])
            if conf_diff > 0.2:
                resolution_stats['high_confidence_wins'] += 1
            elif conf_diff < 0.1:
                # Low confidence difference - might need manual review
                resolution_stats['needs_manual_review'].append(field_name)
    
    return {
        'has_conflicts': True,
        'conflict_count': len(conflicts),
        'affected_fields': list(field_conflicts.keys()),
        'resolution_stats': resolution_stats,
        'details': field_conflicts
    }