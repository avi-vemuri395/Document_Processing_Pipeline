"""
Data models for template-based extraction.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class FieldType(Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    EMAIL = "email"
    PHONE = "phone"
    CHECKBOX = "checkbox"
    CHECKBOX_GROUP = "checkbox_group"
    MONEY = "money"


class ExtractionStrategy(Enum):
    ACROFORM = "acroform"
    ANCHOR = "anchor"
    ZONE = "zone"
    TABLE = "table"
    OCR = "ocr"


@dataclass
class AnchorSpec:
    """Specification for anchor-based extraction."""
    text: str
    strategy: str = "right"  # right, below, above, left
    offset: int = 100  # pixels
    occurrence: int = 1  # which occurrence if multiple matches
    page_hint: Optional[int] = None


@dataclass
class ExtractionSpec:
    """Extraction configuration for a field."""
    acroform: List[str] = field(default_factory=list)
    anchors: List[Dict[str, Any]] = field(default_factory=list)
    zones: List[Dict[str, Any]] = field(default_factory=list)
    checkboxes: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class NormalizeSpec:
    """Normalization rules for a field."""
    case: Optional[str] = None  # upper, lower, title, preserve
    trim: bool = True
    pattern: Optional[str] = None
    mask: bool = False
    format: Optional[str] = None
    phone_format: Optional[str] = None
    number_format: Optional[str] = None


@dataclass
class ValidateSpec:
    """Validation rules for a field."""
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    date_format: Optional[List[str]] = None
    required: bool = False


@dataclass
class FieldSpec:
    """Complete specification for a form field."""
    id: str
    field_name: str
    type: str
    required: bool = False
    page: Optional[int] = None
    extraction: Optional[Dict[str, Any]] = None
    normalize: Optional[Dict[str, Any]] = None
    validate: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # Convert extraction dict to ExtractionSpec if needed
        if isinstance(self.extraction, dict):
            self.extraction = ExtractionSpec(**self.extraction)
        # Convert normalize dict to NormalizeSpec if needed  
        if isinstance(self.normalize, dict):
            self.normalize = NormalizeSpec(**self.normalize)
        # Convert validate dict to ValidateSpec if needed
        if isinstance(self.validate, dict):
            self.validate = ValidateSpec(**self.validate)


@dataclass
class FormSpec:
    """Complete specification for a form template."""
    form_id: str
    version: str
    form_title: str
    fingerprint: Dict[str, Any]
    sections: List[str]
    fields: List[FieldSpec]
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Convert field dicts to FieldSpec objects
        if self.fields and isinstance(self.fields[0], dict):
            self.fields = [FieldSpec(**f) for f in self.fields]
    
    def get_field_by_id(self, field_id: str) -> Optional[FieldSpec]:
        """Get field spec by ID."""
        for field in self.fields:
            if field.id == field_id:
                return field
        return None
    
    def get_field_by_name(self, field_name: str) -> Optional[FieldSpec]:
        """Get field spec by field name."""
        for field in self.fields:
            if field.field_name == field_name:
                return field
        return None


@dataclass 
class ExtractionCandidate:
    """A candidate value extracted from a document."""
    value: Any
    confidence: float = 0.0
    source: Dict[str, Any] = field(default_factory=dict)  # doc_id, page, bbox, method
    
    def __post_init__(self):
        # Ensure source has required fields
        if 'method' not in self.source:
            self.source['method'] = 'unknown'
        if 'confidence' not in self.source:
            self.source['confidence'] = self.confidence


@dataclass
class FieldExtractionResult:
    """Result of extracting a single field."""
    field_id: str
    field_name: str
    candidates: List[ExtractionCandidate] = field(default_factory=list)
    selected_value: Optional[Any] = None
    normalized_value: Optional[Any] = None
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)