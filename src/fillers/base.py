"""
Base abstract class for form fillers.

This module defines the abstract interface that all form fillers must implement
for populating templates with extracted document data.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

from ..extractors.base import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)


class TemplateFormat(Enum):
    """Supported template formats."""
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    CSV = "csv"


class FillingStatus(Enum):
    """Status of form filling process."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class FieldMapping:
    """Mapping between extracted field and template field."""
    source_field: str  # Field name from extraction
    target_field: str  # Field name in template
    transformation: Optional[str] = None  # Optional transformation function name
    required: bool = True
    default_value: Any = None


@dataclass
class FilledField:
    """Represents a filled field in the template."""
    field_name: str
    original_value: Any
    filled_value: Any
    confidence: float
    transformation_applied: Optional[str] = None
    validation_status: Optional[str] = None


@dataclass
class FillingResult:
    """Result of template filling process."""
    template_path: Path
    output_path: Optional[Path]
    status: FillingStatus
    filled_fields: List[FilledField]
    confidence_score: float
    processing_time: float
    errors: List[str]
    metadata: Dict[str, Any]


class BaseFiller(ABC):
    """
    Abstract base class for all form fillers.
    
    This class defines the interface that all specific fillers must implement.
    It provides common functionality for template processing and form filling.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the filler.
        
        Args:
            config: Configuration dictionary for the filler
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self.field_mappings: Dict[str, FieldMapping] = {}
        self._setup_filler()
    
    def _setup_filler(self) -> None:
        """Setup filler-specific configuration and resources."""
        pass
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[TemplateFormat]:
        """Return list of template formats this filler can process."""
        pass
    
    @property
    @abstractmethod
    def template_fields(self) -> List[str]:
        """Return list of fields available in the template."""
        pass
    
    @abstractmethod
    def can_fill(self, template_path: Path, template_format: Optional[TemplateFormat] = None) -> bool:
        """
        Check if this filler can process the given template.
        
        Args:
            template_path: Path to the template file
            template_format: Optional hint about the template format
            
        Returns:
            True if this filler can process the template
        """
        pass
    
    @abstractmethod
    def fill_template(
        self, 
        template_path: Path, 
        extraction_result: ExtractionResult,
        output_path: Optional[Path] = None,
        **kwargs
    ) -> FillingResult:
        """
        Fill the template with extracted data.
        
        Args:
            template_path: Path to the template file
            extraction_result: Result from document extraction
            output_path: Optional path for the filled template
            **kwargs: Additional filling parameters
            
        Returns:
            FillingResult containing filling information
        """
        pass
    
    def add_field_mapping(self, mapping: FieldMapping) -> None:
        """Add a field mapping for this filler."""
        self.field_mappings[mapping.source_field] = mapping
    
    def add_field_mappings(self, mappings: List[FieldMapping]) -> None:
        """Add multiple field mappings."""
        for mapping in mappings:
            self.add_field_mapping(mapping)
    
    def get_field_mapping(self, source_field: str) -> Optional[FieldMapping]:
        """Get field mapping for a source field."""
        return self.field_mappings.get(source_field)
    
    def map_extraction_to_template(self, extraction_result: ExtractionResult) -> Dict[str, Any]:
        """
        Map extracted fields to template fields using field mappings.
        
        Args:
            extraction_result: Result from document extraction
            
        Returns:
            Dictionary mapping template fields to values
        """
        mapped_data = {}
        
        for field in extraction_result.extracted_fields:
            mapping = self.get_field_mapping(field.name)
            if mapping:
                try:
                    # Apply transformation if specified
                    value = field.value
                    if mapping.transformation:
                        value = self.apply_transformation(value, mapping.transformation)
                    
                    mapped_data[mapping.target_field] = value
                    
                except Exception as e:
                    self.logger.error(f"Error mapping field {field.name}: {e}")
                    if mapping.default_value is not None:
                        mapped_data[mapping.target_field] = mapping.default_value
        
        # Add default values for unmapped required fields
        for mapping in self.field_mappings.values():
            if mapping.required and mapping.target_field not in mapped_data:
                if mapping.default_value is not None:
                    mapped_data[mapping.target_field] = mapping.default_value
        
        return mapped_data
    
    def apply_transformation(self, value: Any, transformation: str) -> Any:
        """
        Apply transformation to a field value.
        
        Args:
            value: Original value
            transformation: Name of transformation to apply
            
        Returns:
            Transformed value
        """
        # Get transformation function
        transform_func = getattr(self, f"_transform_{transformation}", None)
        if transform_func:
            return transform_func(value)
        
        # Built-in transformations
        if transformation == "upper":
            return str(value).upper()
        elif transformation == "lower":
            return str(value).lower()
        elif transformation == "strip":
            return str(value).strip()
        elif transformation == "format_currency":
            return self._format_currency(value)
        elif transformation == "format_date":
            return self._format_date(value)
        elif transformation == "format_phone":
            return self._format_phone(value)
        elif transformation == "format_ssn":
            return self._format_ssn(value)
        else:
            self.logger.warning(f"Unknown transformation: {transformation}")
            return value
    
    def _format_currency(self, value: Any) -> str:
        """Format value as currency."""
        try:
            amount = float(value)
            return f"${amount:,.2f}"
        except (ValueError, TypeError):
            return str(value)
    
    def _format_date(self, value: Any, format_str: str = "%m/%d/%Y") -> str:
        """Format date value."""
        if isinstance(value, str):
            try:
                # Try to parse ISO format
                date_obj = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return date_obj.strftime(format_str)
            except ValueError:
                return value
        return str(value)
    
    def _format_phone(self, value: Any) -> str:
        """Format phone number."""
        phone_str = str(value)
        # Remove non-digits
        digits = ''.join(c for c in phone_str if c.isdigit())
        
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            return f"1-({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            return phone_str
    
    def _format_ssn(self, value: Any) -> str:
        """Format Social Security Number."""
        ssn_str = str(value)
        # Remove non-digits
        digits = ''.join(c for c in ssn_str if c.isdigit())
        
        if len(digits) == 9:
            return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
        else:
            return ssn_str
    
    def validate_template(self, template_path: Path) -> List[str]:
        """
        Validate that the template has all required fields.
        
        Args:
            template_path: Path to the template file
            
        Returns:
            List of validation errors
        """
        errors = []
        
        if not template_path.exists():
            errors.append(f"Template file does not exist: {template_path}")
            return errors
        
        # Check file format
        format_supported = False
        for fmt in self.supported_formats:
            if template_path.suffix.lower() == f".{fmt.value}":
                format_supported = True
                break
        
        if not format_supported:
            errors.append(f"Unsupported template format: {template_path.suffix}")
        
        return errors
    
    def get_confidence_threshold(self) -> float:
        """Get the confidence threshold for filling."""
        return self.config.get('confidence_threshold', 0.7)
    
    def calculate_filling_confidence(self, filled_fields: List[FilledField]) -> float:
        """Calculate overall confidence score for filling."""
        if not filled_fields:
            return 0.0
        
        total_confidence = sum(field.confidence for field in filled_fields)
        avg_confidence = total_confidence / len(filled_fields)
        
        # Consider the number of fields filled vs total template fields
        fill_ratio = len(filled_fields) / max(1, len(self.template_fields))
        
        return min(1.0, avg_confidence * 0.8 + fill_ratio * 0.2)
    
    def validate_filled_data(self, mapped_data: Dict[str, Any]) -> List[str]:
        """
        Validate the mapped data before filling.
        
        Args:
            mapped_data: Mapped template data
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check for required fields
        for mapping in self.field_mappings.values():
            if mapping.required and mapping.target_field not in mapped_data:
                errors.append(f"Required field missing: {mapping.target_field}")
        
        return errors
    
    def generate_output_path(self, template_path: Path, output_dir: Optional[Path] = None) -> Path:
        """Generate output path for filled template."""
        if output_dir is None:
            output_dir = template_path.parent
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = template_path.stem
        extension = template_path.suffix
        
        output_filename = f"{base_name}_filled_{timestamp}{extension}"
        return output_dir / output_filename
    
    def __str__(self) -> str:
        """String representation of the filler."""
        return f"{self.__class__.__name__}(formats={[f.value for f in self.supported_formats]})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the filler."""
        return (f"{self.__class__.__name__}("
                f"supported_formats={[f.value for f in self.supported_formats]}, "
                f"template_fields={len(self.template_fields)}, "
                f"field_mappings={len(self.field_mappings)})")