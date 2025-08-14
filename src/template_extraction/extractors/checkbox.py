"""
Checkbox extractor for handling checkbox and radio button groups in PDFs.
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


class CheckboxExtractor(BaseExtractor):
    """Extract checkbox and radio button values from PDF forms."""
    
    def __init__(self):
        """Initialize the checkbox extractor."""
        super().__init__(name="checkbox")
    
    def extract(self, 
                pdf_path: Path, 
                spec: FormSpec,
                target_fields: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract checkbox values from PDF.
        
        Args:
            pdf_path: Path to the PDF document
            spec: Form specification
            target_fields: Optional list of specific field IDs to extract
            
        Returns:
            ExtractionResult with extracted checkbox values
        """
        start_time = time.time()
        result = self.create_extraction_result(pdf_path, spec)
        
        print(f"\n☑️ Checkbox Extraction: {pdf_path.name}")
        print("-" * 50)
        
        try:
            # Read PDF and get all fields (including checkboxes)
            reader = PdfReader(pdf_path)
            all_fields = self._get_all_fields(reader)
            
            if not all_fields:
                print("  ⚠️ No form fields found in PDF")
                return result
            
            # Filter checkbox fields
            checkbox_fields = self._filter_checkbox_fields(all_fields)
            print(f"  📋 Found {len(checkbox_fields)} checkbox/radio fields")
            
            # Extract checkbox group fields from spec
            fields_to_extract = spec.fields
            if target_fields:
                fields_to_extract = [f for f in spec.fields if f.id in target_fields]
            
            extracted_count = 0
            for field_spec in fields_to_extract:
                if not self._should_extract_field(field_spec):
                    continue
                
                field_result = self._extract_checkbox_group(field_spec, checkbox_fields)
                if field_result:
                    result.add_field_result(field_result)
                    if field_result.selected_value is not None:
                        self.log_extraction(field_spec.id, field_result.selected_value, "checkbox")
                        extracted_count += 1
            
            print(f"\n  ✅ Extracted {extracted_count} checkbox groups")
            
        except Exception as e:
            error_msg = f"Checkbox extraction failed: {e}"
            print(f"  ❌ {error_msg}")
            result.errors.append(error_msg)
        
        # Update stats
        elapsed = time.time() - start_time
        result.metadata['extraction_time'] = elapsed
        self.stats['documents_processed'] += 1
        self.stats['extraction_time'] += elapsed
        
        return result
    
    def _get_all_fields(self, reader: PdfReader) -> Dict[str, Any]:
        """
        Get all form fields from the PDF, including checkboxes.
        
        Args:
            reader: PDF reader object
            
        Returns:
            Dictionary of field names to field objects
        """
        fields = {}
        
        try:
            # Try to get fields using different methods
            if hasattr(reader, 'get_fields'):
                raw_fields = reader.get_fields()
            elif hasattr(reader, 'getFields'):
                raw_fields = reader.getFields()
            elif hasattr(reader, 'get_form_fields'):
                raw_fields = reader.get_form_fields()
            else:
                return {}
            
            if not raw_fields:
                return {}
            
            # Process fields
            for name, field in raw_fields.items():
                if field:
                    fields[name] = {
                        'name': name,
                        'type': self._get_field_type(field),
                        'value': self._get_field_value(field),
                        'options': self._get_field_options(field),
                        'field_object': field
                    }
            
            return fields
            
        except Exception as e:
            print(f"  ⚠️ Error reading fields: {e}")
            return {}
    
    def _get_field_type(self, field: Any) -> str:
        """Determine the type of a field."""
        try:
            if hasattr(field, 'get') and '/FT' in field:
                ft = field['/FT']
                if hasattr(ft, 'get_object'):
                    ft = ft.get_object()
                
                if ft == '/Btn':
                    # Button field - could be checkbox, radio, or pushbutton
                    if '/Ff' in field:
                        flags = field['/Ff']
                        if hasattr(flags, 'get_object'):
                            flags = flags.get_object()
                        # Check if it's a radio button (bit 16)
                        if flags & (1 << 15):
                            return 'radio'
                        # Check if it's a pushbutton (bit 17)
                        elif flags & (1 << 16):
                            return 'button'
                        else:
                            return 'checkbox'
                    return 'checkbox'
                elif ft == '/Tx':
                    return 'text'
                elif ft == '/Ch':
                    return 'choice'
            
            return 'unknown'
            
        except Exception:
            return 'unknown'
    
    def _get_field_value(self, field: Any) -> Optional[Any]:
        """Extract the value from a field."""
        try:
            # Check for /V (value) key
            if hasattr(field, 'get') and '/V' in field:
                value = field['/V']
                if hasattr(value, 'get_object'):
                    value = value.get_object()
                
                # Convert to string if it's a name object
                if hasattr(value, 'startswith') and value.startswith('/'):
                    # It's a PDF name object like /Yes or /Off
                    return value[1:]  # Remove leading /
                
                return value
            
            # Check for /AS (appearance state) for checkboxes
            if hasattr(field, 'get') and '/AS' in field:
                state = field['/AS']
                if hasattr(state, 'get_object'):
                    state = state.get_object()
                if hasattr(state, 'startswith') and state.startswith('/'):
                    return state[1:]
                return state
            
            return None
            
        except Exception:
            return None
    
    def _get_field_options(self, field: Any) -> List[str]:
        """Get available options for a field (for checkboxes/radios)."""
        options = []
        
        try:
            # Check appearance dictionary for possible states
            if hasattr(field, 'get') and '/AP' in field:
                ap = field['/AP']
                if hasattr(ap, 'get') and '/N' in ap:
                    states = ap['/N']
                    if hasattr(states, 'keys'):
                        for key in states.keys():
                            if hasattr(key, 'startswith') and key.startswith('/'):
                                option = key[1:]
                                if option != 'Off':  # Skip the Off state
                                    options.append(option)
            
            # Check for /Opt (options) for choice fields
            if hasattr(field, 'get') and '/Opt' in field:
                opts = field['/Opt']
                if hasattr(opts, '__iter__'):
                    for opt in opts:
                        if hasattr(opt, 'get_object'):
                            opt = opt.get_object()
                        options.append(str(opt))
            
            return options
            
        except Exception:
            return []
    
    def _filter_checkbox_fields(self, all_fields: Dict[str, Any]) -> Dict[str, Any]:
        """Filter only checkbox and radio button fields."""
        checkbox_fields = {}
        
        for name, field_info in all_fields.items():
            if field_info['type'] in ['checkbox', 'radio']:
                checkbox_fields[name] = field_info
                # Log the checkbox state
                value = field_info.get('value')
                if value and value != 'Off':
                    print(f"    ☑ {name}: {value}")
        
        return checkbox_fields
    
    def _should_extract_field(self, field_spec: FieldSpec) -> bool:
        """Check if this extractor should handle this field."""
        if field_spec.type not in ['checkbox', 'checkbox_group', 'radio']:
            return False
        
        if not field_spec.extraction:
            return False
        
        # Check if field has checkbox specifications
        return bool(field_spec.extraction.checkboxes)
    
    def _extract_checkbox_group(self, 
                               field_spec: FieldSpec,
                               checkbox_fields: Dict[str, Any]) -> Optional[FieldExtractionResult]:
        """
        Extract a checkbox group based on spec.
        
        Args:
            field_spec: Field specification
            checkbox_fields: Available checkbox fields
            
        Returns:
            FieldExtractionResult or None
        """
        result = FieldExtractionResult(
            field_id=field_spec.id,
            field_name=field_spec.field_name
        )
        
        # For checkbox groups, determine which option is selected
        checkbox_map = field_spec.extraction.checkboxes
        selected_option = None
        
        for option_name, field_names in checkbox_map.items():
            for field_name in field_names:
                if field_name in checkbox_fields:
                    field_info = checkbox_fields[field_name]
                    value = field_info.get('value')
                    
                    # Check if this checkbox is selected
                    if value and value not in ['Off', 'No', '0', False]:
                        selected_option = option_name
                        candidate = self.create_candidate(
                            value=option_name,
                            method="checkbox",
                            confidence=0.95
                        )
                        result.candidates.append(candidate)
                        result.selected_value = option_name
                        break
            
            if selected_option:
                break
        
        # For single checkboxes, return true/false
        if not selected_option and field_spec.type == 'checkbox':
            # Check if any of the checkbox fields are checked
            for field_names in checkbox_map.values():
                for field_name in field_names:
                    if field_name in checkbox_fields:
                        field_info = checkbox_fields[field_name]
                        value = field_info.get('value')
                        is_checked = value and value not in ['Off', 'No', '0', False]
                        
                        candidate = self.create_candidate(
                            value=is_checked,
                            method="checkbox",
                            confidence=0.95
                        )
                        result.candidates.append(candidate)
                        result.selected_value = is_checked
                        return result
        
        # Return result if we found any candidates
        if result.candidates:
            return result
        
        return None
    
    def supports_field(self, field: FieldSpec) -> bool:
        """Check if this extractor can handle a specific field."""
        if field.type not in ['checkbox', 'checkbox_group', 'radio']:
            return False
        
        if not field.extraction:
            return False
        
        # We support fields with checkbox definitions
        return bool(field.extraction.checkboxes)