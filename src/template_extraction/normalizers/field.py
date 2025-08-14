"""
Field normalizer for cleaning and formatting extracted values.
"""

import re
from typing import Any, Optional, List
from datetime import datetime
from ..models import FieldSpec, NormalizeSpec, ValidateSpec, FieldExtractionResult


class FieldNormalizer:
    """Normalize and validate extracted field values."""
    
    def __init__(self):
        """Initialize the normalizer."""
        self.stats = {
            'fields_normalized': 0,
            'validation_errors': 0,
            'fields_masked': 0
        }
    
    def normalize_field(self, 
                       field_spec: FieldSpec,
                       extraction_result: FieldExtractionResult) -> FieldExtractionResult:
        """
        Normalize a field based on its specification.
        
        Args:
            field_spec: Field specification
            extraction_result: Extraction result to normalize
            
        Returns:
            Updated FieldExtractionResult with normalized value
        """
        if not extraction_result.selected_value:
            return extraction_result
        
        value = extraction_result.selected_value
        
        # Apply normalization rules
        if field_spec.normalize:
            value = self._apply_normalization(value, field_spec.normalize, field_spec.type)
            extraction_result.normalized_value = value
        else:
            extraction_result.normalized_value = value
        
        # Validate the normalized value
        if field_spec.validate:
            errors = self._validate_value(value, field_spec.validate, field_spec.type)
            extraction_result.validation_errors = errors
            if errors:
                self.stats['validation_errors'] += len(errors)
        
        self.stats['fields_normalized'] += 1
        return extraction_result
    
    def _apply_normalization(self, value: Any, norm_spec: NormalizeSpec, field_type: str) -> Any:
        """
        Apply normalization rules to a value.
        
        Args:
            value: Value to normalize
            norm_spec: Normalization specification
            field_type: Field type
            
        Returns:
            Normalized value
        """
        if value is None:
            return None
        
        # Convert to string for processing
        str_value = str(value)
        
        # Trim whitespace
        if norm_spec.trim:
            str_value = str_value.strip()
        
        # Apply case transformation
        if norm_spec.case:
            if norm_spec.case == "upper":
                str_value = str_value.upper()
            elif norm_spec.case == "lower":
                str_value = str_value.lower()
            elif norm_spec.case == "title":
                str_value = str_value.title()
        
        # Apply pattern-based normalization
        if norm_spec.pattern:
            str_value = self._apply_pattern(str_value, norm_spec.pattern)
        
        # Apply masking
        if norm_spec.mask:
            str_value = self._mask_value(str_value, field_type)
            self.stats['fields_masked'] += 1
        
        # Type-specific normalization
        if field_type == "number" or norm_spec.number_format:
            return self._normalize_number(str_value, norm_spec.number_format)
        elif field_type == "date" or norm_spec.format:
            return self._normalize_date(str_value, norm_spec.format)
        elif field_type == "phone" or norm_spec.phone_format:
            return self._normalize_phone(str_value, norm_spec.phone_format)
        elif field_type == "email":
            return self._normalize_email(str_value)
        elif field_type == "money":
            return self._normalize_money(str_value)
        
        return str_value
    
    def _apply_pattern(self, value: str, pattern: str) -> str:
        """Apply a pattern to format the value."""
        # Handle SSN pattern
        if "XXX-XX" in pattern and re.match(r'\d{9}', value.replace('-', '')):
            # Format as XXX-XX-####
            clean = value.replace('-', '')
            if len(clean) >= 9:
                return f"XXX-XX-{clean[-4:]}"
        
        # Handle EIN pattern
        if re.match(r'\d{2}-\d{7}', pattern) and re.match(r'\d{9}', value.replace('-', '')):
            clean = value.replace('-', '')
            if len(clean) == 9:
                return f"{clean[:2]}-{clean[2:]}"
        
        return value
    
    def _mask_value(self, value: str, field_type: str) -> str:
        """Mask sensitive information."""
        # SSN masking
        if re.match(r'\d{3}-?\d{2}-?\d{4}', value):
            parts = re.findall(r'\d+', value)
            if len(parts) >= 3:
                return f"XXX-XX-{parts[-1]}"
        
        # EIN masking
        if re.match(r'\d{2}-?\d{7}', value):
            parts = re.findall(r'\d+', value)
            if len(parts) >= 2:
                return f"XX-XXX{parts[-1][-4:]}"
        
        return value
    
    def _normalize_number(self, value: str, format_type: Optional[str]) -> float:
        """Normalize numeric values."""
        try:
            # Remove common formatting
            clean = value.replace(',', '').replace('$', '').replace('%', '')
            
            # Handle percentage format
            if format_type == "percentage" or '%' in value:
                num = float(clean)
                if num > 1 and num <= 100:
                    return num  # Already a percentage
                elif num <= 1:
                    return num * 100  # Convert decimal to percentage
            
            return float(clean)
        except:
            return value
    
    def _normalize_date(self, value: str, date_format: Optional[str]) -> str:
        """Normalize date values."""
        if not date_format:
            date_format = "MM/DD/YYYY"
        
        # Try common date formats
        formats = [
            "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d",
            "%m/%d/%y", "%m-%d-%y", "%d/%m/%Y",
            "%B %d, %Y", "%b %d, %Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                # Format according to spec
                if date_format == "MM/DD/YYYY":
                    return dt.strftime("%m/%d/%Y")
                elif date_format == "YYYY-MM-DD":
                    return dt.strftime("%Y-%m-%d")
                else:
                    return dt.strftime("%m/%d/%Y")
            except:
                continue
        
        return value
    
    def _normalize_phone(self, value: str, country: Optional[str]) -> str:
        """Normalize phone numbers."""
        # Extract digits
        digits = re.findall(r'\d', value)
        
        if len(digits) == 10:
            # Format as (XXX) XXX-XXXX
            return f"({''.join(digits[:3])}) {''.join(digits[3:6])}-{''.join(digits[6:])}"
        elif len(digits) == 11 and digits[0] == '1':
            # Remove country code
            return f"({''.join(digits[1:4])}) {''.join(digits[4:7])}-{''.join(digits[7:])}"
        
        return value
    
    def _normalize_email(self, value: str) -> str:
        """Normalize email addresses."""
        return value.strip().lower()
    
    def _normalize_money(self, value: str) -> float:
        """Normalize monetary values."""
        try:
            # Remove currency symbols and formatting
            clean = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
            return float(clean)
        except:
            return value
    
    def _validate_value(self, value: Any, validate_spec: ValidateSpec, field_type: str) -> List[str]:
        """
        Validate a normalized value.
        
        Args:
            value: Value to validate
            validate_spec: Validation specification
            field_type: Field type
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if value is None:
            if validate_spec.required:
                errors.append("Required field is empty")
            return errors
        
        str_value = str(value)
        
        # Length validation
        if validate_spec.min_length and len(str_value) < validate_spec.min_length:
            errors.append(f"Value too short (min: {validate_spec.min_length})")
        if validate_spec.max_length and len(str_value) > validate_spec.max_length:
            errors.append(f"Value too long (max: {validate_spec.max_length})")
        
        # Pattern validation
        if validate_spec.pattern:
            if not re.match(validate_spec.pattern, str_value):
                errors.append(f"Value doesn't match pattern: {validate_spec.pattern}")
        
        # Numeric validation
        if field_type in ["number", "money"]:
            try:
                num_value = float(str(value).replace('$', '').replace(',', ''))
                if validate_spec.min is not None and num_value < validate_spec.min:
                    errors.append(f"Value below minimum: {validate_spec.min}")
                if validate_spec.max is not None and num_value > validate_spec.max:
                    errors.append(f"Value above maximum: {validate_spec.max}")
            except:
                errors.append("Invalid numeric value")
        
        # Email validation
        if field_type == "email":
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str_value):
                errors.append("Invalid email format")
        
        return errors
    
    def normalize_results(self, results: dict, spec: dict) -> dict:
        """
        Normalize all fields in an extraction result.
        
        Args:
            results: Extraction results
            spec: Form specification
            
        Returns:
            Normalized results
        """
        # This is a convenience method for normalizing all fields at once
        # Implementation depends on the structure of your results
        return results