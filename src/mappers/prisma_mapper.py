"""
Prisma mapper for converting extracted data to Prisma schema structures.

This module provides comprehensive mapping functionality to convert extracted
document data into Prisma-compatible schema structures, handle relationships
between entities, and validate required fields and data types.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union, Type
from dataclasses import dataclass, field, fields
from enum import Enum
from decimal import Decimal
from datetime import datetime, date
import uuid
from pathlib import Path

from ..extractors.base import ExtractedField, ExtractionResult, DocumentType
from ..extractors.pfs_extractor import PersonalFinancialStatementMetadata

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status for mapped fields."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    MISSING_REQUIRED = "missing_required"


@dataclass
class ValidationResult:
    """Result of field validation."""
    status: ValidationStatus
    message: str
    field_name: str
    expected_type: Optional[Type] = None
    actual_value: Any = None


@dataclass
class BeneficialOwnerMetadata:
    """Beneficial owner metadata structure."""
    id: Optional[str] = None
    name: Optional[str] = None
    social_security_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    ownership_percentage: Optional[Decimal] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_control_person: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class BusinessFinancialStatementMetadata:
    """Business financial statement metadata structure."""
    id: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    tax_id: Optional[str] = None
    
    # Balance Sheet Data
    total_assets: Optional[Decimal] = None
    current_assets: Optional[Decimal] = None
    fixed_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    current_liabilities: Optional[Decimal] = None
    long_term_liabilities: Optional[Decimal] = None
    total_equity: Optional[Decimal] = None
    
    # Income Statement Data
    gross_revenue: Optional[Decimal] = None
    net_revenue: Optional[Decimal] = None
    cost_of_goods_sold: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    operating_expenses: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    
    # Cash Flow Data
    operating_cash_flow: Optional[Decimal] = None
    investing_cash_flow: Optional[Decimal] = None
    financing_cash_flow: Optional[Decimal] = None
    net_cash_flow: Optional[Decimal] = None
    
    # Metadata
    statement_date: Optional[date] = None
    fiscal_year_end: Optional[date] = None
    statement_type: Optional[str] = None  # audited, reviewed, compiled, internal
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class LoanApplicationMetadata:
    """Loan application metadata structure."""
    id: Optional[str] = None
    application_number: Optional[str] = None
    loan_type: Optional[str] = None
    loan_amount: Optional[Decimal] = None
    loan_purpose: Optional[str] = None
    
    # Borrower Information
    primary_borrower_name: Optional[str] = None
    primary_borrower_ssn: Optional[str] = None
    co_borrower_name: Optional[str] = None
    co_borrower_ssn: Optional[str] = None
    
    # Business Information
    business_name: Optional[str] = None
    business_address: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_zip: Optional[str] = None
    years_in_business: Optional[int] = None
    
    # Financial Summary
    requested_amount: Optional[Decimal] = None
    annual_revenue: Optional[Decimal] = None
    monthly_revenue: Optional[Decimal] = None
    debt_to_income_ratio: Optional[Decimal] = None
    collateral_value: Optional[Decimal] = None
    
    # Application Status
    application_status: Optional[str] = None
    submission_date: Optional[date] = None
    decision_date: Optional[date] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DebtScheduleMetadata:
    """Debt schedule metadata structure."""
    id: Optional[str] = None
    borrower_name: Optional[str] = None
    
    # Individual Debt Items
    creditor_name: Optional[str] = None
    debt_type: Optional[str] = None
    original_amount: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    monthly_payment: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    maturity_date: Optional[date] = None
    collateral_description: Optional[str] = None
    
    # Summary Information
    total_debt: Optional[Decimal] = None
    total_monthly_payments: Optional[Decimal] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class DocumentMetadata:
    """Generic document metadata structure."""
    id: Optional[str] = None
    document_type: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    content_hash: Optional[str] = None
    
    # Extraction Information
    extraction_method: Optional[str] = None
    extraction_confidence: Optional[float] = None
    extraction_status: Optional[str] = None
    extraction_errors: List[str] = field(default_factory=list)
    
    # Processing Information
    processing_time: Optional[float] = None
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    
    # Classification Information
    classified_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PrismaMapper:
    """
    Comprehensive mapper for converting extracted data to Prisma schema structures.
    
    Handles validation, type conversion, relationship mapping, and data integrity checks.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the Prisma mapper."""
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Type mapping configuration
        self._setup_type_mappings()
        
        # Validation rules
        self._setup_validation_rules()
    
    def _setup_type_mappings(self):
        """Setup type mappings for different data types."""
        self.type_mappings = {
            'string': str,
            'integer': int,
            'decimal': Decimal,
            'float': float,
            'boolean': bool,
            'date': date,
            'datetime': datetime,
            'uuid': str,  # UUIDs are stored as strings
        }
        
        # Field type mappings for different schemas
        self.schema_field_types = {
            'PersonalFinancialStatementMetadata': {
                'name': str,
                'social_security_number': str,
                'date_of_birth': date,
                'residence_address': str,
                'total_assets': Decimal,
                'total_liabilities': Decimal,
                'net_worth': Decimal,
                'cash_on_hand': Decimal,
                'salary': Decimal,
                'is_sba_form_413': bool,
                'extraction_confidence': float,
            },
            'BeneficialOwnerMetadata': {
                'name': str,
                'social_security_number': str,
                'date_of_birth': date,
                'ownership_percentage': Decimal,
                'address': str,
                'is_control_person': bool,
            },
            'BusinessFinancialStatementMetadata': {
                'business_name': str,
                'total_assets': Decimal,
                'total_liabilities': Decimal,
                'total_equity': Decimal,
                'gross_revenue': Decimal,
                'net_income': Decimal,
                'statement_date': date,
            },
            'LoanApplicationMetadata': {
                'application_number': str,
                'loan_amount': Decimal,
                'requested_amount': Decimal,
                'primary_borrower_name': str,
                'business_name': str,
                'submission_date': date,
            },
            'DebtScheduleMetadata': {
                'creditor_name': str,
                'current_balance': Decimal,
                'monthly_payment': Decimal,
                'interest_rate': Decimal,
                'maturity_date': date,
            }
        }
    
    def _setup_validation_rules(self):
        """Setup validation rules for different schemas."""
        self.validation_rules = {
            'PersonalFinancialStatementMetadata': {
                'required_fields': ['name', 'total_assets', 'total_liabilities', 'net_worth'],
                'conditional_required': {},  # Field required if another field has certain value
                'value_constraints': {
                    'total_assets': {'min': 0},
                    'total_liabilities': {'min': 0},
                    'extraction_confidence': {'min': 0.0, 'max': 1.0},
                    'ownership_percentage': {'min': 0.0, 'max': 100.0},
                },
                'format_constraints': {
                    'social_security_number': r'^\d{3}-\d{2}-\d{4}$',
                    'email': r'^[^@]+@[^@]+\.[^@]+$',
                    'phone': r'^\(\d{3}\) \d{3}-\d{4}$',
                    'zip_code': r'^\d{5}(-\d{4})?$',
                }
            },
            'BeneficialOwnerMetadata': {
                'required_fields': ['name', 'ownership_percentage'],
                'value_constraints': {
                    'ownership_percentage': {'min': 0.0, 'max': 100.0},
                },
                'format_constraints': {
                    'social_security_number': r'^\d{3}-\d{2}-\d{4}$',
                }
            },
            'BusinessFinancialStatementMetadata': {
                'required_fields': ['business_name', 'total_assets', 'total_liabilities'],
                'value_constraints': {
                    'total_assets': {'min': 0},
                    'total_liabilities': {'min': 0},
                }
            },
            'LoanApplicationMetadata': {
                'required_fields': ['application_number', 'loan_amount', 'primary_borrower_name'],
                'value_constraints': {
                    'loan_amount': {'min': 0},
                    'requested_amount': {'min': 0},
                    'debt_to_income_ratio': {'min': 0.0, 'max': 10.0},  # Reasonable DTI range
                }
            }
        }
    
    def map_extraction_result_to_schema(
        self, 
        extraction_result: ExtractionResult,
        target_schema: Type,
        **kwargs
    ) -> Tuple[Any, List[ValidationResult]]:
        """
        Map extraction result to target Prisma schema.
        
        Args:
            extraction_result: The extraction result to map
            target_schema: Target schema class
            **kwargs: Additional mapping parameters
            
        Returns:
            Tuple of (mapped_object, validation_results)
        """
        schema_name = target_schema.__name__
        validation_results = []
        
        # Create instance of target schema
        mapped_object = target_schema()
        
        # Set default timestamps
        if hasattr(mapped_object, 'created_at'):
            mapped_object.created_at = datetime.utcnow()
        if hasattr(mapped_object, 'updated_at'):
            mapped_object.updated_at = datetime.utcnow()
        if hasattr(mapped_object, 'id') and not getattr(mapped_object, 'id'):
            mapped_object.id = str(uuid.uuid4())
        
        # Map fields from extraction result
        field_mapping = self._get_field_mapping(extraction_result.document_type, schema_name)
        
        for extracted_field in extraction_result.extracted_fields:
            target_field_name = field_mapping.get(extracted_field.name, extracted_field.name)
            
            if hasattr(mapped_object, target_field_name):
                # Convert and validate the value
                converted_value, field_validation = self._convert_and_validate_field(
                    extracted_field.value,
                    target_field_name,
                    schema_name,
                    extracted_field
                )
                
                # Set the value
                setattr(mapped_object, target_field_name, converted_value)
                
                # Add validation result
                if field_validation:
                    validation_results.append(field_validation)
        
        # Validate required fields
        required_validation = self._validate_required_fields(mapped_object, schema_name)
        validation_results.extend(required_validation)
        
        # Cross-field validation
        cross_validation = self._validate_cross_field_constraints(mapped_object, schema_name)
        validation_results.extend(cross_validation)
        
        return mapped_object, validation_results
    
    def map_pfs_to_schema(
        self, 
        pfs_metadata: PersonalFinancialStatementMetadata
    ) -> Tuple[PersonalFinancialStatementMetadata, List[ValidationResult]]:
        """
        Map PFS metadata to validated Prisma schema.
        
        Args:
            pfs_metadata: PFS metadata object
            
        Returns:
            Tuple of (validated_pfs, validation_results)
        """
        validation_results = []
        
        # Create a copy for modification
        validated_pfs = PersonalFinancialStatementMetadata()
        
        # Copy all fields
        for field_info in fields(pfs_metadata):
            value = getattr(pfs_metadata, field_info.name)
            
            # Convert and validate each field
            converted_value, field_validation = self._convert_and_validate_field(
                value,
                field_info.name,
                'PersonalFinancialStatementMetadata'
            )
            
            setattr(validated_pfs, field_info.name, converted_value)
            
            if field_validation:
                validation_results.append(field_validation)
        
        # Validate required fields
        required_validation = self._validate_required_fields(
            validated_pfs, 
            'PersonalFinancialStatementMetadata'
        )
        validation_results.extend(required_validation)
        
        # PFS-specific validation
        pfs_validation = self._validate_pfs_calculations(validated_pfs)
        validation_results.extend(pfs_validation)
        
        return validated_pfs, validation_results
    
    def map_multiple_beneficial_owners(
        self, 
        owner_data: List[Dict[str, Any]]
    ) -> Tuple[List[BeneficialOwnerMetadata], List[ValidationResult]]:
        """
        Map multiple beneficial owner records.
        
        Args:
            owner_data: List of owner data dictionaries
            
        Returns:
            Tuple of (owner_list, validation_results)
        """
        owners = []
        all_validation_results = []
        
        for i, owner_dict in enumerate(owner_data):
            owner = BeneficialOwnerMetadata()
            owner.id = str(uuid.uuid4())
            owner.created_at = datetime.utcnow()
            owner.updated_at = datetime.utcnow()
            
            validation_results = []
            
            # Map each field
            for field_name, value in owner_dict.items():
                if hasattr(owner, field_name):
                    converted_value, field_validation = self._convert_and_validate_field(
                        value,
                        field_name,
                        'BeneficialOwnerMetadata'
                    )
                    
                    setattr(owner, field_name, converted_value)
                    
                    if field_validation:
                        field_validation.field_name = f"owner_{i}_{field_validation.field_name}"
                        validation_results.append(field_validation)
            
            # Validate required fields for this owner
            required_validation = self._validate_required_fields(
                owner, 
                'BeneficialOwnerMetadata'
            )
            for validation in required_validation:
                validation.field_name = f"owner_{i}_{validation.field_name}"
            validation_results.extend(required_validation)
            
            owners.append(owner)
            all_validation_results.extend(validation_results)
        
        # Validate ownership percentages sum to reasonable total
        if owners:
            total_ownership = sum(
                owner.ownership_percentage or Decimal('0') 
                for owner in owners 
                if owner.ownership_percentage
            )
            
            if total_ownership > Decimal('100.0'):
                all_validation_results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Total ownership percentage ({total_ownership}%) exceeds 100%",
                    field_name="total_ownership_percentage"
                ))
            elif total_ownership < Decimal('75.0') and len(owners) > 1:
                all_validation_results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Total ownership percentage ({total_ownership}%) seems low for {len(owners)} owners",
                    field_name="total_ownership_percentage"
                ))
        
        return owners, all_validation_results
    
    def create_document_metadata(
        self, 
        file_path: Path,
        extraction_result: ExtractionResult,
        **kwargs
    ) -> DocumentMetadata:
        """
        Create document metadata from extraction result.
        
        Args:
            file_path: Path to the original document
            extraction_result: Extraction result
            **kwargs: Additional metadata
            
        Returns:
            DocumentMetadata object
        """
        metadata = DocumentMetadata()
        metadata.id = str(uuid.uuid4())
        metadata.created_at = datetime.utcnow()
        metadata.updated_at = datetime.utcnow()
        
        # File information
        metadata.file_name = file_path.name
        metadata.file_path = str(file_path.absolute())
        if file_path.exists():
            metadata.file_size = file_path.stat().st_size
        
        # Document type and classification
        metadata.document_type = extraction_result.document_type.value
        metadata.classified_type = extraction_result.document_type.value
        
        # Extraction information
        metadata.extraction_confidence = extraction_result.confidence_score
        metadata.extraction_status = extraction_result.status.value
        metadata.extraction_errors = extraction_result.errors.copy()
        metadata.processing_time = extraction_result.processing_time
        metadata.processed_at = datetime.utcnow()
        
        # Additional metadata from kwargs
        for key, value in kwargs.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        return metadata
    
    def _get_field_mapping(self, document_type: DocumentType, schema_name: str) -> Dict[str, str]:
        """Get field mapping for document type to schema."""
        # Define mappings between extraction field names and schema field names
        mappings = {
            (DocumentType.PERSONAL_FINANCIAL_STATEMENT, 'PersonalFinancialStatementMetadata'): {
                'name': 'name',
                'social_security_number': 'social_security_number',
                'date_of_birth': 'date_of_birth',
                'residence_address': 'residence_address',
                'business_address': 'business_address',
                'cash_on_hand': 'cash_on_hand',
                'savings_accounts': 'savings_accounts',
                'ira_retirement_accounts': 'ira_retirement_accounts',
                'total_assets': 'total_assets',
                'total_liabilities': 'total_liabilities',
                'net_worth': 'net_worth',
                'salary': 'salary',
                'statement_date': 'statement_date',
                'is_sba_form_413': 'is_sba_form_413',
            },
            (DocumentType.SBA_FORM_413, 'PersonalFinancialStatementMetadata'): {
                # Same mapping as PFS
                'name': 'name',
                'social_security_number': 'social_security_number',
                'total_assets': 'total_assets',
                'total_liabilities': 'total_liabilities',
                'net_worth': 'net_worth',
                'is_sba_form_413': 'is_sba_form_413',
            },
        }
        
        return mappings.get((document_type, schema_name), {})
    
    def _convert_and_validate_field(
        self, 
        value: Any, 
        field_name: str, 
        schema_name: str,
        extracted_field: Optional[ExtractedField] = None
    ) -> Tuple[Any, Optional[ValidationResult]]:
        """
        Convert and validate a field value.
        
        Args:
            value: The value to convert and validate
            field_name: Name of the target field
            schema_name: Name of the target schema
            extracted_field: Optional extracted field for additional context
            
        Returns:
            Tuple of (converted_value, validation_result)
        """
        if value is None:
            return None, None
        
        # Get expected type for this field
        expected_type = self.schema_field_types.get(schema_name, {}).get(field_name)
        
        if not expected_type:
            # No specific type requirement, return as-is
            return value, None
        
        try:
            # Type conversion
            if expected_type == str:
                converted_value = str(value)
            elif expected_type == int:
                converted_value = int(float(value)) if isinstance(value, (str, float, Decimal)) else int(value)
            elif expected_type == float:
                converted_value = float(value)
            elif expected_type == Decimal:
                converted_value = Decimal(str(value)) if not isinstance(value, Decimal) else value
            elif expected_type == bool:
                if isinstance(value, str):
                    converted_value = value.lower() in ('true', 'yes', '1', 'on')
                else:
                    converted_value = bool(value)
            elif expected_type == date:
                if isinstance(value, date):
                    converted_value = value
                elif isinstance(value, datetime):
                    converted_value = value.date()
                else:
                    # Try to parse string date
                    from datetime import datetime
                    try:
                        parsed_date = datetime.strptime(str(value), '%Y-%m-%d')
                        converted_value = parsed_date.date()
                    except ValueError:
                        try:
                            parsed_date = datetime.strptime(str(value), '%m/%d/%Y')
                            converted_value = parsed_date.date()
                        except ValueError:
                            raise ValueError(f"Cannot parse date: {value}")
            elif expected_type == datetime:
                if isinstance(value, datetime):
                    converted_value = value
                elif isinstance(value, date):
                    converted_value = datetime.combine(value, datetime.min.time())
                else:
                    converted_value = datetime.fromisoformat(str(value))
            else:
                converted_value = value
            
            # Validate the converted value
            validation_result = self._validate_field_value(
                converted_value, field_name, schema_name
            )
            
            return converted_value, validation_result
            
        except (ValueError, TypeError, AttributeError) as e:
            return value, ValidationResult(
                status=ValidationStatus.INVALID,
                message=f"Type conversion failed: {str(e)}",
                field_name=field_name,
                expected_type=expected_type,
                actual_value=value
            )
    
    def _validate_field_value(
        self, 
        value: Any, 
        field_name: str, 
        schema_name: str
    ) -> Optional[ValidationResult]:
        """Validate a field value against constraints."""
        rules = self.validation_rules.get(schema_name, {})
        
        # Value constraints
        value_constraints = rules.get('value_constraints', {}).get(field_name, {})
        if value_constraints and isinstance(value, (int, float, Decimal)):
            if 'min' in value_constraints and value < value_constraints['min']:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"Value {value} is below minimum {value_constraints['min']}",
                    field_name=field_name,
                    actual_value=value
                )
            if 'max' in value_constraints and value > value_constraints['max']:
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"Value {value} is above maximum {value_constraints['max']}",
                    field_name=field_name,
                    actual_value=value
                )
        
        # Format constraints
        format_constraints = rules.get('format_constraints', {}).get(field_name)
        if format_constraints and isinstance(value, str):
            import re
            if not re.match(format_constraints, value):
                return ValidationResult(
                    status=ValidationStatus.INVALID,
                    message=f"Value does not match required format",
                    field_name=field_name,
                    actual_value=value
                )
        
        return None
    
    def _validate_required_fields(
        self, 
        obj: Any, 
        schema_name: str
    ) -> List[ValidationResult]:
        """Validate that required fields are present."""
        validation_results = []
        rules = self.validation_rules.get(schema_name, {})
        required_fields = rules.get('required_fields', [])
        
        for field_name in required_fields:
            if not hasattr(obj, field_name):
                continue
                
            value = getattr(obj, field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                validation_results.append(ValidationResult(
                    status=ValidationStatus.MISSING_REQUIRED,
                    message=f"Required field is missing or empty",
                    field_name=field_name
                ))
        
        return validation_results
    
    def _validate_cross_field_constraints(
        self, 
        obj: Any, 
        schema_name: str
    ) -> List[ValidationResult]:
        """Validate cross-field constraints."""
        validation_results = []
        
        # PFS-specific validations
        if schema_name == 'PersonalFinancialStatementMetadata':
            validation_results.extend(self._validate_pfs_calculations(obj))
        
        # Business financial statement validations
        elif schema_name == 'BusinessFinancialStatementMetadata':
            validation_results.extend(self._validate_business_financial_calculations(obj))
        
        return validation_results
    
    def _validate_pfs_calculations(
        self, 
        pfs: PersonalFinancialStatementMetadata
    ) -> List[ValidationResult]:
        """Validate PFS calculation consistency."""
        validation_results = []
        
        # Net worth calculation: Assets - Liabilities = Net Worth
        if (pfs.total_assets is not None and 
            pfs.total_liabilities is not None and 
            pfs.net_worth is not None):
            
            calculated_net_worth = pfs.total_assets - pfs.total_liabilities
            difference = abs(calculated_net_worth - pfs.net_worth)
            
            # Allow for small rounding differences
            if difference > Decimal('1.00'):
                validation_results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Net worth calculation mismatch: Assets ({pfs.total_assets}) - Liabilities ({pfs.total_liabilities}) = {calculated_net_worth}, but stated net worth is {pfs.net_worth}",
                    field_name="net_worth"
                ))
        
        # Check for negative assets (unusual but possible)
        if pfs.total_assets is not None and pfs.total_assets < 0:
            validation_results.append(ValidationResult(
                status=ValidationStatus.WARNING,
                message="Negative total assets detected",
                field_name="total_assets"
            ))
        
        # Check for reasonable asset values
        asset_fields = [
            'cash_on_hand', 'savings_accounts', 'ira_retirement_accounts',
            'life_insurance_cash_value', 'stocks_bonds', 'real_estate_owned',
            'automobile_present_value', 'other_personal_property'
        ]
        
        total_individual_assets = Decimal('0')
        for field_name in asset_fields:
            if hasattr(pfs, field_name):
                value = getattr(pfs, field_name)
                if value is not None:
                    if value < 0:
                        validation_results.append(ValidationResult(
                            status=ValidationStatus.WARNING,
                            message=f"Negative asset value detected",
                            field_name=field_name
                        ))
                    total_individual_assets += value
        
        # Check if individual assets sum roughly matches total assets
        if (pfs.total_assets is not None and 
            total_individual_assets > 0 and
            abs(pfs.total_assets - total_individual_assets) > pfs.total_assets * Decimal('0.1')):
            validation_results.append(ValidationResult(
                status=ValidationStatus.WARNING,
                message=f"Sum of individual assets ({total_individual_assets}) differs significantly from total assets ({pfs.total_assets})",
                field_name="total_assets"
            ))
        
        return validation_results
    
    def _validate_business_financial_calculations(
        self, 
        bfs: BusinessFinancialStatementMetadata
    ) -> List[ValidationResult]:
        """Validate business financial statement calculations."""
        validation_results = []
        
        # Balance sheet equation: Assets = Liabilities + Equity
        if (bfs.total_assets is not None and 
            bfs.total_liabilities is not None and 
            bfs.total_equity is not None):
            
            calculated_equity = bfs.total_assets - bfs.total_liabilities
            difference = abs(calculated_equity - bfs.total_equity)
            
            if difference > Decimal('1.00'):
                validation_results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Balance sheet equation mismatch: Assets ({bfs.total_assets}) - Liabilities ({bfs.total_liabilities}) = {calculated_equity}, but stated equity is {bfs.total_equity}",
                    field_name="total_equity"
                ))
        
        # Gross profit calculation
        if (bfs.gross_revenue is not None and 
            bfs.cost_of_goods_sold is not None and 
            bfs.gross_profit is not None):
            
            calculated_gross_profit = bfs.gross_revenue - bfs.cost_of_goods_sold
            difference = abs(calculated_gross_profit - bfs.gross_profit)
            
            if difference > Decimal('1.00'):
                validation_results.append(ValidationResult(
                    status=ValidationStatus.WARNING,
                    message=f"Gross profit calculation mismatch",
                    field_name="gross_profit"
                ))
        
        return validation_results
    
    def get_validation_summary(self, validation_results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate a summary of validation results.
        
        Args:
            validation_results: List of validation results
            
        Returns:
            Dictionary with validation summary
        """
        summary = {
            'total_validations': len(validation_results),
            'valid_count': 0,
            'invalid_count': 0,
            'warning_count': 0,
            'missing_required_count': 0,
            'has_critical_errors': False,
            'critical_errors': [],
            'warnings': [],
            'missing_required_fields': []
        }
        
        for result in validation_results:
            if result.status == ValidationStatus.VALID:
                summary['valid_count'] += 1
            elif result.status == ValidationStatus.INVALID:
                summary['invalid_count'] += 1
                summary['has_critical_errors'] = True
                summary['critical_errors'].append({
                    'field': result.field_name,
                    'message': result.message
                })
            elif result.status == ValidationStatus.WARNING:
                summary['warning_count'] += 1
                summary['warnings'].append({
                    'field': result.field_name,
                    'message': result.message
                })
            elif result.status == ValidationStatus.MISSING_REQUIRED:
                summary['missing_required_count'] += 1
                summary['has_critical_errors'] = True
                summary['missing_required_fields'].append(result.field_name)
        
        # Calculate overall validation score
        if summary['total_validations'] > 0:
            valid_ratio = (summary['valid_count'] + summary['warning_count']) / summary['total_validations']
            summary['validation_score'] = valid_ratio
        else:
            summary['validation_score'] = 1.0
        
        return summary