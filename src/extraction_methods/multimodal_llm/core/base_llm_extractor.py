"""
Base abstract class for LLM-based document extractors.
Defines the interface that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from enum import Enum


class ExtractionConfidence(Enum):
    """Confidence levels for extraction results."""
    HIGH = "high"        # 85-100% confidence
    MEDIUM = "medium"    # 65-85% confidence  
    LOW = "low"          # Below 65% confidence


@dataclass
class BoundingBox:
    """Represents a bounding box location in the document."""
    page: int
    x: float
    y: float
    width: float
    height: float
    text: str


@dataclass
class FieldExtraction:
    """Represents a single extracted field."""
    field_name: str
    value: Any
    confidence: float
    raw_text: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None
    
    @property
    def confidence_level(self) -> ExtractionConfidence:
        """Get confidence level category."""
        if self.confidence >= 0.85:
            return ExtractionConfidence.HIGH
        elif self.confidence >= 0.65:
            return ExtractionConfidence.MEDIUM
        else:
            return ExtractionConfidence.LOW


@dataclass
class ExtractionResult:
    """Complete extraction result from a document."""
    document_type: str
    fields: List[FieldExtraction]
    overall_confidence: float
    processing_time: float
    model_used: str
    needs_review: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    @property
    def high_confidence_fields(self) -> List[FieldExtraction]:
        """Get only high confidence fields."""
        return [f for f in self.fields if f.confidence_level == ExtractionConfidence.HIGH]
    
    @property
    def fields_dict(self) -> Dict[str, Any]:
        """Convert fields to dictionary format."""
        return {f.field_name: f.value for f in self.fields}
    
    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None and len(self.fields) > 0


class BaseLLMExtractor(ABC):
    """Abstract base class for LLM-based document extractors."""
    
    def __init__(self, confidence_threshold: float = 0.85):
        """
        Initialize the extractor.
        
        Args:
            confidence_threshold: Minimum confidence for automatic processing
        """
        self.confidence_threshold = confidence_threshold
        self.model_name = "unknown"
    
    @abstractmethod
    async def extract_with_schema(
        self,
        document: Union[Path, bytes],
        schema: Dict[str, Any],
        document_type: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract structured data from a document using schema constraints.
        
        Args:
            document: Path to document or document bytes
            schema: JSON Schema defining expected structure
            document_type: Optional document type hint
            
        Returns:
            ExtractionResult with extracted fields and confidence scores
        """
        pass
    
    @abstractmethod
    async def classify_document(
        self,
        document: Union[Path, bytes]
    ) -> Tuple[str, float]:
        """
        Classify the document type using vision capabilities.
        
        Args:
            document: Path to document or document bytes
            
        Returns:
            Tuple of (document_type, confidence)
        """
        pass
    
    def validate_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Validate that the schema is properly formatted.
        
        Args:
            schema: JSON Schema to validate
            
        Returns:
            True if valid, raises ValueError if not
        """
        required_keys = ["type", "properties"]
        if not all(key in schema for key in required_keys):
            raise ValueError(f"Schema must contain keys: {required_keys}")
        
        if schema["type"] != "object":
            raise ValueError("Schema type must be 'object'")
        
        if not isinstance(schema["properties"], dict):
            raise ValueError("Schema properties must be a dictionary")
        
        return True
    
    def aggregate_confidence(self, field_confidences: List[float]) -> float:
        """
        Aggregate multiple confidence scores into overall confidence.
        
        Args:
            field_confidences: List of individual field confidence scores
            
        Returns:
            Overall confidence score
        """
        if not field_confidences:
            return 0.0
        
        # Weighted average with penalty for low confidence fields
        total_weight = 0
        weighted_sum = 0
        
        for conf in field_confidences:
            # Higher weight for high confidence fields
            weight = conf ** 2
            weighted_sum += conf * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def should_review(self, result: ExtractionResult) -> bool:
        """
        Determine if extraction result needs human review.
        
        Args:
            result: Extraction result to evaluate
            
        Returns:
            True if review needed, False otherwise
        """
        # Review needed if:
        # 1. Overall confidence below threshold
        # 2. Any critical field has low confidence
        # 3. Extraction had errors
        
        if result.error is not None:
            return True
        
        if result.overall_confidence < self.confidence_threshold:
            return True
        
        # Check for critical fields (can be customized)
        critical_fields = ["firstName", "lastName", "totalAssets", "totalLiabilities"]
        for field in result.fields:
            if field.field_name in critical_fields and field.confidence < 0.7:
                return True
        
        return False
    
    @abstractmethod
    def get_api_cost(self, document_pages: int) -> float:
        """
        Estimate API cost for processing document.
        
        Args:
            document_pages: Number of pages in document
            
        Returns:
            Estimated cost in USD
        """
        pass