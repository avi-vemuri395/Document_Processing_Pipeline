"""
Base extractor class for all extraction strategies.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import hashlib
from datetime import datetime

from ..models import FormSpec, FieldSpec, ExtractionCandidate, FieldExtractionResult


@dataclass
class ExtractionResult:
    """Complete extraction result for a document."""
    doc_id: str
    doc_path: str
    form_id: str
    fields: Dict[str, FieldExtractionResult] = field(default_factory=dict)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_field_result(self, result: FieldExtractionResult) -> None:
        """Add a field extraction result."""
        self.fields[result.field_id] = result
    
    def get_field_value(self, field_id: str) -> Optional[Any]:
        """Get the selected value for a field."""
        if field_id in self.fields:
            return self.fields[field_id].selected_value
        return None
    
    def get_all_values(self) -> Dict[str, Any]:
        """Get all field values as a flat dictionary."""
        values = {}
        for field_id, result in self.fields.items():
            if result.normalized_value is not None:
                values[result.field_name] = result.normalized_value
            elif result.selected_value is not None:
                values[result.field_name] = result.selected_value
        return values
    
    def get_confidence_scores(self) -> Dict[str, float]:
        """Get confidence scores for all fields."""
        scores = {}
        for field_id, result in self.fields.items():
            if result.candidates:
                scores[field_id] = max(c.confidence for c in result.candidates)
            else:
                scores[field_id] = 0.0
        return scores
    
    def get_coverage(self, required_only: bool = False) -> float:
        """Calculate field coverage percentage."""
        if not self.fields:
            return 0.0
        
        if required_only:
            # TODO: Need FormSpec reference to determine required fields
            total = len([f for f in self.fields.values() if f.metadata.get('required', False)])
        else:
            total = len(self.fields)
        
        if total == 0:
            return 0.0
        
        filled = len([f for f in self.fields.values() if f.selected_value is not None])
        return (filled / total) * 100


class BaseExtractor(ABC):
    """Base class for all extraction strategies."""
    
    def __init__(self, name: str = "base"):
        """
        Initialize the extractor.
        
        Args:
            name: Name of the extraction strategy
        """
        self.name = name
        self.stats = {
            'documents_processed': 0,
            'fields_extracted': 0,
            'extraction_time': 0.0,
            'errors': []
        }
    
    @abstractmethod
    def extract(self, 
                pdf_path: Path, 
                spec: FormSpec,
                target_fields: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract data from a document using the form spec.
        
        Args:
            pdf_path: Path to the PDF document
            spec: Form specification
            target_fields: Optional list of specific field IDs to extract
            
        Returns:
            ExtractionResult with extracted data
        """
        pass
    
    def supports_field(self, field: FieldSpec) -> bool:
        """
        Check if this extractor can handle a specific field.
        
        Args:
            field: Field specification
            
        Returns:
            True if the extractor can handle this field
        """
        # Override in subclasses to indicate support
        return True
    
    def generate_doc_id(self, pdf_path: Path) -> str:
        """
        Generate a unique document ID.
        
        Args:
            pdf_path: Path to the document
            
        Returns:
            Unique document ID
        """
        # Use file hash for consistent IDs
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        return f"{pdf_path.stem}_{file_hash}"
    
    def create_extraction_result(self, pdf_path: Path, spec: FormSpec) -> ExtractionResult:
        """
        Create an empty extraction result.
        
        Args:
            pdf_path: Path to the document
            spec: Form specification
            
        Returns:
            Empty ExtractionResult
        """
        return ExtractionResult(
            doc_id=self.generate_doc_id(pdf_path),
            doc_path=str(pdf_path),
            form_id=spec.form_id,
            metadata={
                'extractor': self.name,
                'form_version': spec.version,
                'extraction_method': self.__class__.__name__
            }
        )
    
    def create_candidate(self, 
                        value: Any,
                        page: Optional[int] = None,
                        bbox: Optional[List[float]] = None,
                        method: str = "unknown",
                        confidence: float = 0.5) -> ExtractionCandidate:
        """
        Create an extraction candidate.
        
        Args:
            value: Extracted value
            page: Page number (1-indexed)
            bbox: Bounding box [x1, y1, x2, y2]
            method: Extraction method used
            confidence: Confidence score (0-1)
            
        Returns:
            ExtractionCandidate object
        """
        source = {
            'method': method,
            'extractor': self.name,
            'confidence': confidence
        }
        
        if page is not None:
            source['page'] = page
        if bbox is not None:
            source['bbox'] = bbox
        
        return ExtractionCandidate(
            value=value,
            confidence=confidence,
            source=source
        )
    
    def log_extraction(self, field_id: str, value: Any, method: str) -> None:
        """Log successful extraction for debugging."""
        print(f"  📝 {field_id}: '{value}' (via {method})")
        self.stats['fields_extracted'] += 1
    
    def log_error(self, field_id: str, error: str) -> None:
        """Log extraction error."""
        error_msg = f"Field {field_id}: {error}"
        print(f"  ❌ {error_msg}")
        self.stats['errors'].append(error_msg)