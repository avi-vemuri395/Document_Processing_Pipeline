"""
Field Consolidator - Confidence-Aware Field Consolidation Service
Consolidates fragmented DocAI fields using confidence thresholds and semantic rules.

Implements research-backed consolidation patterns:
- Threshold-based consolidation with fallback strategies
- Semantic field grouping for related fields
- Confidence-weighted value merging
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict


class ConfidenceAwareFieldConsolidator:
    """
    Consolidates fragmented DocAI fields using confidence thresholds
    and semantic rules. Implements research-based consolidation patterns.
    
    Handles common DocAI fragmentation issues:
    - Split names: "ROBERT L." and "WHARTON" → "ROBERT L. WHARTON"
    - Mixed labels: "INCOME" with value "$\n116,296\nMISC" → clean value
    - Duplicate fields with different confidence scores
    """
    
    def __init__(self):
        """Initialize consolidator with semantic patterns."""
        # Patterns for identifying related fields that should be consolidated
        self.consolidation_patterns = {
            'name_fields': [
                r'.*name.*', r'.*applicant.*', r'.*owner.*', 
                r'.*partner.*', r'.*member.*'
            ],
            'address_fields': [
                r'.*address.*', r'.*street.*', r'.*city.*', 
                r'.*state.*', r'.*zip.*', r'.*location.*'
            ],
            'business_fields': [
                r'.*business.*', r'.*company.*', r'.*entity.*',
                r'.*employer.*', r'.*organization.*'
            ],
            'financial_fields': [
                r'.*asset.*', r'.*liability.*', r'.*income.*',
                r'.*expense.*', r'.*revenue.*', r'.*cost.*'
            ],
            'identification_fields': [
                r'.*ssn.*', r'.*ein.*', r'.*tax.*id.*', 
                r'.*identification.*', r'.*number.*'
            ]
        }
        
        # Statistics tracking
        self.stats = {
            'fields_processed': 0,
            'fields_consolidated': 0,
            'groups_created': 0
        }
    
    def consolidate_fragmented_fields(
        self, 
        docai_fields: Dict[str, Any],
        confidence_threshold: float = 0.6
    ) -> Dict[str, Any]:
        """
        Apply threshold-based consolidation with fallback rules.
        
        Research finding: Use confidence thresholds to determine
        whether to consolidate fields or mark as unresolved.
        
        Args:
            docai_fields: Raw DocAI fields with confidence scores
            confidence_threshold: Minimum confidence for consolidation
            
        Returns:
            Consolidated fields with cleaned values and confidence scores
        """
        print(f"      🔄 Consolidating {len(docai_fields)} DocAI fields...")
        
        # Step 1: Clean and normalize field values
        cleaned_fields = self._clean_field_values(docai_fields)
        
        # Step 2: Group semantically related fields
        field_groups = self._group_semantic_fields(cleaned_fields)
        
        # Step 3: Consolidate each group
        consolidated = {}
        for group_name, fields in field_groups.items():
            if len(fields) == 1:
                # Single field, use as-is
                field_name, field_data = fields[0]
                consolidated[field_name] = field_data
            else:
                # Multiple related fields, apply consolidation logic
                consolidated_field = self._consolidate_field_group(
                    fields, confidence_threshold, group_name
                )
                if consolidated_field:
                    # Use the consolidated field name
                    consolidated[consolidated_field['name']] = consolidated_field['data']
        
        self.stats['fields_processed'] += len(docai_fields)
        self.stats['fields_consolidated'] += len(field_groups) - len(consolidated)
        
        print(f"      ✅ Consolidated to {len(consolidated)} fields")
        return consolidated
    
    def _clean_field_values(self, docai_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean and normalize DocAI field values.
        
        Handles common issues:
        - Remove line breaks and extra whitespace
        - Clean currency formatting
        - Normalize numbers
        """
        cleaned = {}
        
        for field_name, field_data in docai_fields.items():
            # Handle both formats: simple value or {"value": ..., "confidence": ...}
            if isinstance(field_data, dict) and "value" in field_data:
                value = field_data.get("value", "")
                confidence = field_data.get("confidence", 0.5)
            else:
                value = field_data
                confidence = 0.5  # Default confidence if not provided
            
            # Skip empty values
            if not value or value == "":
                continue
            
            # Clean the value
            cleaned_value = self._clean_value(str(value))
            
            # Skip if cleaning resulted in empty value
            if not cleaned_value:
                continue
            
            cleaned[field_name] = {
                "value": cleaned_value,
                "confidence": confidence,
                "original_value": value
            }
        
        return cleaned
    
    def _clean_value(self, value: str) -> str:
        """
        Clean a single field value.
        
        Removes common artifacts from DocAI extraction:
        - Line breaks within values
        - Extra whitespace
        - Mixed labels and values
        """
        # Remove line breaks and normalize whitespace
        cleaned = re.sub(r'\n+', ' ', value)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        # Handle currency values with line breaks (e.g., "$\n116,296\nMISC")
        if '$' in cleaned:
            # Extract just the numeric part
            match = re.search(r'\$?\s*([\d,]+(?:\.\d{2})?)', cleaned)
            if match:
                cleaned = match.group(1)
        
        # Handle percentages (e.g., "50.000000")
        if re.match(r'^\d+\.0+$', cleaned):
            cleaned = str(int(float(cleaned)))
        
        return cleaned
    
    def _group_semantic_fields(self, cleaned_fields: Dict[str, Any]) -> Dict[str, List]:
        """
        Group semantically related fields for consolidation.
        
        Uses regex patterns to identify fields that likely belong together.
        """
        groups = defaultdict(list)
        used_fields = set()
        
        # First pass: Group by semantic patterns
        for pattern_type, patterns in self.consolidation_patterns.items():
            for field_name, field_data in cleaned_fields.items():
                if field_name in used_fields:
                    continue
                
                field_lower = field_name.lower()
                for pattern in patterns:
                    if re.match(pattern, field_lower):
                        groups[pattern_type].append((field_name, field_data))
                        used_fields.add(field_name)
                        break
        
        # Second pass: Fields that don't match patterns go in their own groups
        for field_name, field_data in cleaned_fields.items():
            if field_name not in used_fields:
                # Use field name as group name for ungrouped fields
                groups[f"field_{field_name}"].append((field_name, field_data))
        
        self.stats['groups_created'] = len(groups)
        return dict(groups)
    
    def _consolidate_field_group(
        self, 
        fields: List[Tuple[str, Dict]], 
        threshold: float,
        group_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Consolidate a group of related fields using confidence-aware rules.
        
        Implementation of research finding: threshold-based consolidation
        with fallback strategies for low-confidence fields.
        """
        if not fields:
            return None
        
        # Calculate average confidence for the group
        confidences = [field[1].get('confidence', 0.0) for field in fields]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Find the field with highest confidence as the primary field
        primary_field = max(fields, key=lambda x: x[1].get('confidence', 0.0))
        field_name, field_data = primary_field
        
        if avg_confidence >= threshold:
            # High confidence: merge values intelligently
            merged_value = self._merge_field_values(fields, group_name)
            
            # Use the most confident field's name, but cleaned up
            consolidated_name = self._clean_field_name(field_name)
            
            return {
                'name': consolidated_name,
                'data': {
                    "value": merged_value,
                    "confidence": avg_confidence,
                    "consolidation_method": "confidence_merge",
                    "source_fields": len(fields),
                    "original_fields": [f[0] for f in fields]
                }
            }
        else:
            # Low confidence: apply fallback strategy
            fallback_value = self._apply_fallback_strategy(fields)
            consolidated_name = self._clean_field_name(field_name)
            
            return {
                'name': consolidated_name,
                'data': {
                    "value": fallback_value,
                    "confidence": avg_confidence,
                    "consolidation_method": "fallback_strategy",
                    "needs_review": True,
                    "source_fields": len(fields),
                    "original_fields": [f[0] for f in fields]
                }
            }
    
    def _merge_field_values(self, fields: List[Tuple[str, Dict]], group_name: str) -> str:
        """
        Intelligently merge values from related fields.
        
        Different strategies based on field type:
        - Names: Concatenate parts
        - Addresses: Build complete address
        - Numbers: Use highest confidence value
        """
        values = [f[1].get('value', '') for f in fields]
        
        # Special handling for name fields
        if 'name' in group_name:
            # Check if values look like name parts
            if all(len(v.split()) <= 2 for v in values):
                # Likely name parts, concatenate
                return ' '.join(values).strip()
        
        # Special handling for address fields
        if 'address' in group_name:
            # Build complete address from parts
            return ', '.join(v for v in values if v).strip()
        
        # For other fields, use the value with highest confidence
        best_field = max(fields, key=lambda x: x[1].get('confidence', 0.0))
        return best_field[1].get('value', '')
    
    def _apply_fallback_strategy(self, fields: List[Tuple[str, Dict]]) -> str:
        """
        Apply fallback strategy for low-confidence consolidation.
        
        Strategy: Use the most frequent value, or the one with highest confidence
        if all values are unique.
        """
        # Count value frequencies
        value_counts = defaultdict(int)
        value_confidences = {}
        
        for field_name, field_data in fields:
            value = field_data.get('value', '')
            confidence = field_data.get('confidence', 0.0)
            
            value_counts[value] += 1
            if value not in value_confidences or confidence > value_confidences[value]:
                value_confidences[value] = confidence
        
        # Find most frequent value
        if value_counts:
            # If there's a tie, use confidence as tiebreaker
            sorted_values = sorted(
                value_counts.items(),
                key=lambda x: (x[1], value_confidences.get(x[0], 0.0)),
                reverse=True
            )
            return sorted_values[0][0]
        
        return ""
    
    def _clean_field_name(self, field_name: str) -> str:
        """
        Clean and standardize field names.
        
        Converts DocAI field names to cleaner format:
        - Remove special characters
        - Proper capitalization
        """
        # Remove special characters except spaces and basic punctuation
        cleaned = re.sub(r'[^\w\s-]', '', field_name)
        
        # Convert to title case
        cleaned = cleaned.title()
        
        # Remove redundant words
        redundant = ['Field', 'Value', 'Text', 'Input']
        for word in redundant:
            cleaned = cleaned.replace(word, '')
        
        return cleaned.strip() or field_name