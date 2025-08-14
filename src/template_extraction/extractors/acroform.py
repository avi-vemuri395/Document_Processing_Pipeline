"""
AcroForm extractor for direct PDF form field extraction.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import time

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

from .base import BaseExtractor, ExtractionResult
from ..models import FormSpec, FieldSpec, FieldExtractionResult


class AcroFormExtractor(BaseExtractor):
    """Extract values directly from PDF AcroForm fields."""
    
    def __init__(self):
        """Initialize the AcroForm extractor."""
        super().__init__(name="acroform")
    
    def extract(self, 
                pdf_path: Path, 
                spec: FormSpec,
                target_fields: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract data from PDF AcroForm fields.
        
        Args:
            pdf_path: Path to the PDF document
            spec: Form specification
            target_fields: Optional list of specific field IDs to extract
            
        Returns:
            ExtractionResult with extracted data
        """
        start_time = time.time()
        result = self.create_extraction_result(pdf_path, spec)
        
        print(f"\n🔍 AcroForm Extraction: {pdf_path.name}")
        print("-" * 50)
        
        try:
            # Read PDF and get form fields
            reader = PdfReader(pdf_path)
            form_fields = self._get_form_fields(reader)
            
            if not form_fields:
                print("  ⚠️ No AcroForm fields found in PDF")
                result.metadata['acroform_fields'] = 0
                return result
            
            print(f"  📋 Found {len(form_fields)} AcroForm fields")
            result.metadata['acroform_fields'] = len(form_fields)
            
            # Build a lookup map for faster matching
            field_map = {name.lower(): value for name, value in form_fields.items()}
            
            # Extract fields based on spec
            fields_to_extract = spec.fields
            if target_fields:
                fields_to_extract = [f for f in spec.fields if f.id in target_fields]
            
            extracted_count = 0
            for field_spec in fields_to_extract:
                if not self._should_extract_field(field_spec):
                    continue
                
                field_result = self._extract_field(field_spec, field_map, form_fields)
                if field_result and field_result.selected_value is not None:
                    result.add_field_result(field_result)
                    self.log_extraction(field_spec.id, field_result.selected_value, "acroform")
                    extracted_count += 1
            
            print(f"\n  ✅ Extracted {extracted_count}/{len(fields_to_extract)} fields")
            
        except Exception as e:
            error_msg = f"AcroForm extraction failed: {e}"
            print(f"  ❌ {error_msg}")
            result.errors.append(error_msg)
        
        # Update stats
        elapsed = time.time() - start_time
        result.metadata['extraction_time'] = elapsed
        self.stats['documents_processed'] += 1
        self.stats['extraction_time'] += elapsed
        
        return result
    
    def _get_form_fields(self, reader: PdfReader) -> Dict[str, Any]:
        """
        Get all form fields from the PDF.
        
        Args:
            reader: PDF reader object
            
        Returns:
            Dictionary of field names to values
        """
        fields = {}
        
        try:
            if not hasattr(reader, 'get_form_text_fields'):
                # Fallback for older PyPDF2
                if hasattr(reader, 'getFormTextFields'):
                    return reader.getFormTextFields() or {}
                elif hasattr(reader, 'get_fields'):
                    return reader.get_fields() or {}
                return {}
            
            # Get all form fields (text and checkboxes)
            form_fields = reader.get_form_text_fields() or {}
            
            # Also try to get fields from the AcroForm
            if hasattr(reader, 'get_fields'):
                all_fields = reader.get_fields() or {}
                for name, field in all_fields.items():
                    if name not in form_fields:
                        # Extract value from field object
                        value = self._extract_field_value(field)
                        if value is not None:
                            form_fields[name] = value
            
            return form_fields
            
        except Exception as e:
            print(f"  ⚠️ Error reading form fields: {e}")
            return {}
    
    def _extract_field_value(self, field: Any) -> Optional[Any]:
        """
        Extract value from a field object.
        
        Args:
            field: PDF field object
            
        Returns:
            Extracted value or None
        """
        try:
            # Check for /V (value) key
            if hasattr(field, 'get') and '/V' in field:
                value = field['/V']
                if hasattr(value, 'get_object'):
                    value = value.get_object()
                return value
            
            # Check for direct value attribute
            if hasattr(field, 'value'):
                return field.value
            
            return None
            
        except Exception:
            return None
    
    def _should_extract_field(self, field_spec: FieldSpec) -> bool:
        """
        Check if this extractor should handle this field.
        
        Args:
            field_spec: Field specification
            
        Returns:
            True if field should be extracted via AcroForm
        """
        if not field_spec.extraction:
            return False
        
        # Check if field has AcroForm names defined
        return bool(field_spec.extraction.acroform)
    
    def _extract_field(self, 
                      field_spec: FieldSpec,
                      field_map: Dict[str, Any],
                      original_fields: Dict[str, Any]) -> Optional[FieldExtractionResult]:
        """
        Extract a single field based on spec.
        
        Args:
            field_spec: Field specification
            field_map: Lowercase field name map
            original_fields: Original field dictionary
            
        Returns:
            FieldExtractionResult or None
        """
        result = FieldExtractionResult(
            field_id=field_spec.id,
            field_name=field_spec.field_name
        )
        
        # Try each AcroForm name in the spec
        for acro_name in field_spec.extraction.acroform:
            # Try exact match first
            if acro_name in original_fields:
                value = original_fields[acro_name]
                if value is not None and str(value).strip():
                    candidate = self.create_candidate(
                        value=value,
                        method="acroform_exact",
                        confidence=0.95
                    )
                    result.candidates.append(candidate)
                    result.selected_value = value
                    return result
            
            # Try lowercase match
            if acro_name.lower() in field_map:
                value = field_map[acro_name.lower()]
                if value is not None and str(value).strip():
                    candidate = self.create_candidate(
                        value=value,
                        method="acroform_lower",
                        confidence=0.90
                    )
                    result.candidates.append(candidate)
                    result.selected_value = value
                    return result
            
            # Try partial match
            for field_name, value in original_fields.items():
                if acro_name.lower() in field_name.lower():
                    if value is not None and str(value).strip():
                        candidate = self.create_candidate(
                            value=value,
                            method="acroform_partial",
                            confidence=0.80
                        )
                        result.candidates.append(candidate)
                        if not result.selected_value:  # Take first match
                            result.selected_value = value
        
        # Return result if we found any candidates
        if result.candidates:
            return result
        
        return None
    
    def supports_field(self, field: FieldSpec) -> bool:
        """
        Check if this extractor can handle a specific field.
        
        Args:
            field: Field specification
            
        Returns:
            True if the extractor can handle this field
        """
        if not field.extraction:
            return False
        
        # We support fields with AcroForm names
        return bool(field.extraction.acroform)