"""
Data models for extraction results.
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExtractionConfidence(Enum):
    """Confidence levels for extraction."""
    HIGH = "high"        # > 85%
    MEDIUM = "medium"    # 60-85%
    LOW = "low"          # < 60%


@dataclass
class ExtractedField:
    """Single extracted field with metadata."""
    field_name: str
    value: Any
    confidence: float
    source_text: Optional[str] = None
    page_number: Optional[int] = None
    bounding_box: Optional[Dict] = None
    validation_notes: Optional[str] = None
    
    @property
    def confidence_level(self) -> ExtractionConfidence:
        """Get confidence level category."""
        if self.confidence >= 0.85:
            return ExtractionConfidence.HIGH
        elif self.confidence >= 0.60:
            return ExtractionConfidence.MEDIUM
        else:
            return ExtractionConfidence.LOW


@dataclass
class ExtractionResult:
    """Result of document extraction."""
    document_path: str
    document_type: str
    extraction_method: str
    fields: List[ExtractedField]
    overall_confidence: float
    processing_time: float
    page_count: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return len(self.fields) > 0 and len(self.errors) == 0
    
    @property
    def requires_review(self) -> bool:
        """Check if manual review is recommended."""
        return (
            self.overall_confidence < 0.70 or 
            len(self.warnings) > 0 or
            any(f.confidence < 0.60 for f in self.fields)
        )
    
    def get_field(self, field_name: str) -> Optional[ExtractedField]:
        """Get field by name."""
        for field in self.fields:
            if field.field_name == field_name:
                return field
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'document_path': self.document_path,
            'document_type': self.document_type,
            'extraction_method': self.extraction_method,
            'overall_confidence': self.overall_confidence,
            'processing_time': self.processing_time,
            'page_count': self.page_count,
            'fields': {
                f.field_name: {
                    'value': f.value,
                    'confidence': f.confidence,
                    'source_text': f.source_text
                }
                for f in self.fields
            },
            'warnings': self.warnings,
            'errors': self.errors,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass 
class SchemaValidationResult:
    """Result of schema validation."""
    is_valid: bool
    missing_required_fields: List[str] = field(default_factory=list)
    invalid_fields: List[str] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    confidence_score: float = 1.0


@dataclass
class PersonalFinancialStatementExtraction:
    """Extraction model for Personal Financial Statements."""
    # Personal Information
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    ssn: Optional[str] = None
    dateOfBirth: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    businessPhone: Optional[str] = None
    
    # Address
    streetAddress: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zipCode: Optional[str] = None
    
    # Financial Summary
    totalAssets: Optional[int] = None  # in dollars
    totalLiabilities: Optional[int] = None  # in dollars
    netWorth: Optional[int] = None  # in dollars
    
    # Income
    salaryIncome: Optional[int] = None  # annual in dollars
    netInvestmentIncome: Optional[int] = None
    realEstateIncome: Optional[int] = None
    otherIncome: Optional[int] = None
    totalAnnualIncome: Optional[int] = None
    
    # Assets Detail
    cashOnHand: Optional[int] = None
    savingsAccounts: Optional[int] = None
    stocksBonds: Optional[int] = None
    realEstate: Optional[int] = None
    automobileValue: Optional[int] = None
    otherAssets: Optional[int] = None
    
    # Liabilities Detail
    accountsPayable: Optional[int] = None
    notesPayable: Optional[int] = None
    mortgagesPayable: Optional[int] = None
    installmentAccountAuto: Optional[int] = None
    installmentAccountOther: Optional[int] = None
    loanOnLifeInsurance: Optional[int] = None
    
    # Other Information
    asOfDate: Optional[str] = None
    statementDate: Optional[str] = None
    signature: Optional[str] = None
    jointSignature: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}