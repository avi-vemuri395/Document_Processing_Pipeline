"""
Base abstract class for document extractors.

This module defines the abstract interface that all document extractors must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types for extraction."""
    PERSONAL_FINANCIAL_STATEMENT = "personal_financial_statement"
    SBA_FORM_413 = "sba_form_413"
    TAX_RETURN = "tax_return"
    TAX_RETURN_1040 = "tax_return_1040"
    TAX_RETURN_1065 = "tax_return_1065"
    TAX_RETURN_1120S = "tax_return_1120s"
    BALANCE_SHEET = "balance_sheet"
    PROFIT_LOSS = "profit_loss"
    DEBT_SCHEDULE = "debt_schedule"
    BANK_STATEMENT = "bank_statement"
    PAY_STUB = "pay_stub"
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    INSURANCE_POLICY = "insurance_policy"
    UTILITY_BILL = "utility_bill"
    UNKNOWN = "unknown"


class ExtractionStatus(Enum):
    """Status of document extraction."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class ExtractedField:
    """Represents a single extracted field from a document."""
    name: str
    value: Any
    confidence: float
    source_location: Optional[Dict[str, Any]] = None  # Bounding box, page number, etc.
    raw_text: Optional[str] = None
    validation_status: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result of document extraction process."""
    document_type: DocumentType
    status: ExtractionStatus
    extracted_fields: List[ExtractedField]
    confidence_score: float
    processing_time: float
    errors: List[str]
    metadata: Dict[str, Any]
    raw_text: Optional[str] = None


class BaseExtractor(ABC):
    """
    Abstract base class for all document extractors.
    
    This class defines the interface that all specific extractors must implement.
    It provides common functionality for document processing and extraction.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the extractor.
        
        Args:
            config: Configuration dictionary for the extractor
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_extractor()
    
    def _setup_extractor(self) -> None:
        """Setup extractor-specific configuration and resources."""
        pass
    
    @property
    @abstractmethod
    def supported_document_types(self) -> List[DocumentType]:
        """Return list of document types this extractor can process."""
        pass
    
    @property
    @abstractmethod
    def required_fields(self) -> List[str]:
        """Return list of required fields this extractor should extract."""
        pass
    
    @abstractmethod
    def can_process(self, file_path: Path, document_type: Optional[DocumentType] = None) -> bool:
        """
        Check if this extractor can process the given document.
        
        Args:
            file_path: Path to the document file
            document_type: Optional hint about the document type
            
        Returns:
            True if this extractor can process the document
        """
        pass
    
    @abstractmethod
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract data from the document.
        
        Args:
            file_path: Path to the document file
            **kwargs: Additional extraction parameters
            
        Returns:
            ExtractionResult containing extracted data
        """
        pass
    
    def validate_extraction(self, result: ExtractionResult) -> ExtractionResult:
        """
        Validate the extraction result.
        
        Args:
            result: The extraction result to validate
            
        Returns:
            Updated extraction result with validation information
        """
        # Default validation - check if required fields are present
        missing_fields = []
        for required_field in self.required_fields:
            if not any(field.name == required_field for field in result.extracted_fields):
                missing_fields.append(required_field)
        
        if missing_fields:
            result.errors.append(f"Missing required fields: {', '.join(missing_fields)}")
            if result.status == ExtractionStatus.SUCCESS:
                result.status = ExtractionStatus.PARTIAL
        
        return result
    
    def preprocess_document(self, file_path: Path) -> Optional[Path]:
        """
        Preprocess the document before extraction.
        
        Args:
            file_path: Path to the original document
            
        Returns:
            Path to the preprocessed document, or None if preprocessing failed
        """
        # Default implementation - no preprocessing
        return file_path
    
    def postprocess_result(self, result: ExtractionResult) -> ExtractionResult:
        """
        Postprocess the extraction result.
        
        Args:
            result: The extraction result to postprocess
            
        Returns:
            Postprocessed extraction result
        """
        # Default implementation - no postprocessing
        return result
    
    def get_confidence_threshold(self) -> float:
        """Get the confidence threshold for this extractor."""
        return self.config.get('confidence_threshold', 0.8)
    
    def is_high_confidence(self, field: ExtractedField) -> bool:
        """Check if a field has high confidence."""
        return field.confidence >= self.get_confidence_threshold()
    
    def filter_low_confidence_fields(self, fields: List[ExtractedField]) -> List[ExtractedField]:
        """Filter out fields with low confidence."""
        return [field for field in fields if self.is_high_confidence(field)]
    
    def __str__(self) -> str:
        """String representation of the extractor."""
        return f"{self.__class__.__name__}(types={[t.value for t in self.supported_document_types]})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the extractor."""
        return (f"{self.__class__.__name__}("
                f"supported_types={[t.value for t in self.supported_document_types]}, "
                f"required_fields={self.required_fields})")