"""
Enhanced extraction pipeline with comprehensive document support.
Integrates all new extractors, validators, and the unified loan package model.
"""

import asyncio
import logging
import concurrent.futures
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import time
import os

# Import enhanced components
from ..extraction_methods.multimodal_llm.core.enhanced_document_classifier import (
    EnhancedDocumentClassifier, DocumentType, ClassificationResult
)
from ..extraction_methods.multimodal_llm.extractors.tax_return_extractor import (
    TaxReturnExtractor, TaxReturnData
)
from ..extraction_methods.multimodal_llm.extractors.excel_native_extractor import (
    ExcelNativeExtractor, ExcelExtractionResult
)
from ..extraction_methods.multimodal_llm.core.cross_document_validator import (
    CrossDocumentValidator, ValidationResult
)
from ..extraction_methods.multimodal_llm.models.loan_application_package import (
    LoanApplicationPackage, BorrowerInfo, BusinessEntity, FinancialPosition,
    DebtSchedule, DebtItem, LoanRequest, LoanType, ApplicationStatus,
    DocumentMetadata
)
from ..extraction_methods.multimodal_llm.utils.enhanced_prompt_builder import EnhancedPromptBuilder

# Import existing components
from .base import BaseExtractor, ExtractionResult, ExtractedField, ExtractionStatus
from .confidence_scorer import ConfidenceScorer, DocumentConfidenceReport

# Import LLM extractor if available
try:
    from ..extraction_methods.multimodal_llm.providers.claude_extractor import ClaudeExtractor
    from ..extraction_methods.multimodal_llm.core.schema_generator import PrismaSchemaGenerator
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExtractionMethod(Enum):
    """Extraction method selection."""
    LLM = "llm"
    NATIVE = "native"  # For Excel
    HYBRID = "hybrid"  # Use LLM with native Excel support


@dataclass
class EnhancedPipelineConfig:
    """Configuration for enhanced extraction pipeline."""
    # Processing options
    max_workers: int = 4
    enable_parallel_processing: bool = True
    batch_size: int = 10
    timeout_per_document: int = 300  # seconds
    
    # Extraction method selection
    extraction_method: ExtractionMethod = ExtractionMethod.HYBRID
    prefer_native_excel: bool = True  # Use native Excel reading when possible
    
    # Classification options
    classification_confidence_threshold: float = 0.7
    
    # Extraction options
    extraction_confidence_threshold: float = 0.6
    enable_cross_validation: bool = True
    
    # LLM options (if available)
    use_llm_for_complex_docs: bool = True
    llm_confidence_threshold: float = 0.85
    
    # Validation options
    validation_tolerance: float = 0.05  # 5% variance allowed
    require_validation_pass: bool = False  # Whether to block on validation failures
    
    # Output options
    save_intermediate_results: bool = True
    output_directory: Path = Path("outputs/enhanced_extraction")


@dataclass
class EnhancedDocumentResult:
    """Result of processing a single document with enhanced extraction."""
    file_path: Path
    classification: ClassificationResult
    extraction_method: str
    extraction_data: Any  # Can be ExtractionResult, TaxReturnData, ExcelExtractionResult, etc.
    confidence_score: float
    processing_time: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedPipelineResult:
    """Result of the enhanced pipeline execution."""
    loan_application: Optional[LoanApplicationPackage]
    documents_processed: List[EnhancedDocumentResult]
    validation_result: Optional[ValidationResult]
    summary_statistics: Dict[str, Any]
    total_processing_time: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class EnhancedExtractionPipeline:
    """Enhanced extraction pipeline with comprehensive document support."""
    
    def __init__(self, config: Optional[EnhancedPipelineConfig] = None):
        """Initialize enhanced pipeline."""
        self.config = config or EnhancedPipelineConfig()
        
        # Initialize components
        self.classifier = EnhancedDocumentClassifier()
        self.tax_extractor = TaxReturnExtractor()
        self.excel_extractor = ExcelNativeExtractor()
        self.validator = CrossDocumentValidator(tolerance=self.config.validation_tolerance)
        self.prompt_builder = EnhancedPromptBuilder()
        
        # Initialize confidence scorer
        self.confidence_scorer = ConfidenceScorer()
        
        # Initialize LLM components if available
        self.llm_extractor = None
        self.schema_generator = None
        if LLM_AVAILABLE and os.getenv("ANTHROPIC_API_KEY"):
            try:
                self.llm_extractor = ClaudeExtractor()
                self.schema_generator = PrismaSchemaGenerator()
                logger.info("LLM extraction enabled")
            except Exception as e:
                logger.warning(f"LLM extraction not available: {e}")
        
        # Create output directory
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
    
    async def process_loan_package(
        self,
        document_paths: List[Path],
        application_id: Optional[str] = None
    ) -> EnhancedPipelineResult:
        """
        Process complete loan application package.
        
        Args:
            document_paths: List of document paths to process
            application_id: Optional application ID
            
        Returns:
            EnhancedPipelineResult with complete loan package
        """
        start_time = time.time()
        
        # Generate application ID if not provided
        if not application_id:
            application_id = f"APP-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        print(f"Processing loan package: {application_id}")
        print(f"Documents to process: {len(document_paths)}")
        
        # Phase 1: Classify all documents
        print("Phase 1: Document classification")
        classification_results = await self._classify_documents(document_paths)
        
        # Phase 2: Extract data from each document
        print("Phase 2: Document extraction")
        extraction_results = await self._extract_documents(
            document_paths, 
            classification_results
        )
        
        # Phase 3: Build loan application package
        print("Phase 3: Building loan application")
        loan_application = self._build_loan_application(
            application_id,
            extraction_results
        )
        
        # Phase 4: Cross-document validation
        validation_result = None
        if self.config.enable_cross_validation:
            print("Phase 4: Cross-document validation")
            validation_result = self._validate_documents(extraction_results)
            
            # Add validation to loan application
            if loan_application and validation_result:
                loan_application.validation_status = self._convert_validation_status(
                    validation_result
                )
        
        # Phase 5: Calculate metrics and assess risk
        if loan_application:
            print("Phase 5: Risk assessment")
            loan_application.calculate_metrics()
            loan_application.assess_risk()
        
        # Calculate statistics
        total_time = time.time() - start_time
        statistics = self._calculate_statistics(extraction_results, validation_result)
        
        # Save results if configured
        if self.config.save_intermediate_results:
            self._save_results(application_id, loan_application, extraction_results, validation_result)
        
        return EnhancedPipelineResult(
            loan_application=loan_application,
            documents_processed=extraction_results,
            validation_result=validation_result,
            summary_statistics=statistics,
            total_processing_time=total_time
        )
    
    async def _classify_documents(
        self,
        document_paths: List[Path]
    ) -> Dict[Path, ClassificationResult]:
        """Classify all documents."""
        results = {}
        
        for doc_path in document_paths:
            if not doc_path.exists():
                print(f"Document not found: {doc_path}")
                continue
            
            try:
                # Use enhanced classifier
                result = self.classifier.classify_document(document_path=doc_path)
                results[doc_path] = result
                print(f"Classified {doc_path.name} as {result.primary_type.value} "
                          f"(confidence: {result.confidence:.2%})")
            except Exception as e:
                print(f"Classification failed for {doc_path}: {e}")
                results[doc_path] = ClassificationResult(
                    primary_type=DocumentType.UNKNOWN,
                    confidence=0.0
                )
        
        return results
    
    async def _extract_documents(
        self,
        document_paths: List[Path],
        classifications: Dict[Path, ClassificationResult]
    ) -> List[EnhancedDocumentResult]:
        """Extract data from all documents."""
        results = []
        
        # Group documents by type for batch processing
        documents_by_type = {}
        for doc_path, classification in classifications.items():
            doc_type = classification.primary_type
            if doc_type not in documents_by_type:
                documents_by_type[doc_type] = []
            documents_by_type[doc_type].append(doc_path)
        
        # Process each document type
        for doc_type, paths in documents_by_type.items():
            for doc_path in paths:
                start_time = time.time()
                
                try:
                    # Route to appropriate extractor
                    result = await self._extract_single_document(
                        doc_path,
                        doc_type,
                        classifications[doc_path]
                    )
                    
                    results.append(result)
                    
                except Exception as e:
                    print(f"Extraction failed for {doc_path}: {e}")
                    results.append(EnhancedDocumentResult(
                        file_path=doc_path,
                        classification=classifications[doc_path],
                        extraction_method="failed",
                        extraction_data=None,
                        confidence_score=0.0,
                        processing_time=time.time() - start_time,
                        errors=[str(e)]
                    ))
        
        return results
    
    async def _extract_single_document(
        self,
        doc_path: Path,
        doc_type: DocumentType,
        classification: ClassificationResult
    ) -> EnhancedDocumentResult:
        """Extract data from a single document."""
        start_time = time.time()
        
        # Route based on document type and format
        extraction_method = self._determine_extraction_method(doc_path, doc_type)
        
        # Excel files - use native extraction
        if doc_path.suffix.lower() in ['.xlsx', '.xls']:
            if self.config.prefer_native_excel:
                extraction_data = self.excel_extractor.extract(doc_path)
                confidence = extraction_data.confidence
                method = "native_excel"
            else:
                # Fall back to LLM if configured
                extraction_data, confidence, method = await self._extract_with_llm(
                    doc_path, doc_type
                )
        
        # Tax returns - use specialized extractor
        elif doc_type in [DocumentType.TAX_RETURN_1040, DocumentType.TAX_RETURN_1065, 
                         DocumentType.TAX_RETURN_1120S]:
            # Try to extract text first
            text = self._extract_text(doc_path)
            if text:
                extraction_data = self.tax_extractor.extract(
                    text, 
                    doc_type.value.split('_')[-1]  # Get form type
                )
                confidence = 0.8  # Default confidence for regex
                method = "tax_extractor"
            else:
                # Fall back to LLM
                extraction_data, confidence, method = await self._extract_with_llm(
                    doc_path, doc_type
                )
        
        # PFS - use LLM extraction
        elif doc_type == DocumentType.PERSONAL_FINANCIAL_STATEMENT:
            extraction_data, confidence, method = await self._extract_with_llm(
                doc_path, doc_type
            )
        
        # All other documents - use LLM if available
        else:
            if self.llm_extractor and self.config.use_llm_for_complex_docs:
                extraction_data, confidence, method = await self._extract_with_llm(
                    doc_path, doc_type
                )
            else:
                # Basic extraction
                extraction_data = {"message": "Extraction not implemented for this type"}
                confidence = 0.0
                method = "unsupported"
        
        return EnhancedDocumentResult(
            file_path=doc_path,
            classification=classification,
            extraction_method=method,
            extraction_data=extraction_data,
            confidence_score=confidence,
            processing_time=time.time() - start_time,
            metadata={
                "document_type": doc_type.value,
                "tax_year": classification.tax_year,
                "entity_name": classification.entity_name
            }
        )
    
    async def _extract_with_llm(
        self,
        doc_path: Path,
        doc_type: DocumentType
    ) -> Tuple[Any, float, str]:
        """Extract using LLM with enhanced prompts."""
        if not self.llm_extractor:
            return None, 0.0, "llm_unavailable"
        
        try:
            # Generate appropriate schema
            schema = self._get_schema_for_type(doc_type)
            
            # Build enhanced prompt
            prompt = self.prompt_builder.build_extraction_prompt(
                document_type=doc_type,
                schema=schema,
                include_examples=True
            )
            
            # Extract with LLM
            result = await self.llm_extractor.extract_with_schema(
                document=doc_path,
                schema=schema,
                document_type=doc_type.value
            )
            
            return result, result.overall_confidence, "llm_enhanced"
            
        except Exception as e:
            print(f"LLM extraction failed: {e}")
            return None, 0.0, "llm_failed"
    
    def _determine_extraction_method(
        self,
        doc_path: Path,
        doc_type: DocumentType
    ) -> ExtractionMethod:
        """Determine best extraction method for document."""
        # Excel files should use native extraction
        if doc_path.suffix.lower() in ['.xlsx', '.xls']:
            return ExtractionMethod.NATIVE
        
        # Use LLM for all other documents
        return ExtractionMethod.LLM if self.llm_extractor else ExtractionMethod.NATIVE
    
    def _extract_text(self, doc_path: Path) -> Optional[str]:
        """Extract text from PDF document."""
        try:
            import pdfplumber
            
            with pdfplumber.open(doc_path) as pdf:
                text = ""
                for page in pdf.pages[:10]:  # Limit to first 10 pages
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text if text else None
                
        except Exception as e:
            print(f"Text extraction failed for {doc_path}: {e}")
            return None
    
    def _get_schema_for_type(self, doc_type: DocumentType) -> Dict[str, Any]:
        """Get extraction schema for document type."""
        if not self.schema_generator:
            return {}
        
        # Map document types to schema names
        schema_mapping = {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: "PersonalFinancialStatementMetadata",
            DocumentType.TAX_RETURN_1040: "TaxReturnMetadata",
            DocumentType.BALANCE_SHEET: "BalanceSheetMetadata",
            DocumentType.PROFIT_LOSS: "ProfitLossMetadata",
            DocumentType.DEBT_SCHEDULE: "DebtScheduleMetadata",
        }
        
        schema_name = schema_mapping.get(doc_type)
        if schema_name:
            try:
                return self.schema_generator.generate_extraction_schema(schema_name)
            except:
                pass
        
        # Default schema
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def _build_loan_application(
        self,
        application_id: str,
        extraction_results: List[EnhancedDocumentResult]
    ) -> Optional[LoanApplicationPackage]:
        """Build unified loan application from extraction results."""
        try:
            # Initialize components
            borrower = BorrowerInfo(first_name="", last_name="")
            business = None
            financial_position = FinancialPosition()
            debt_schedule = DebtSchedule()
            
            # Process each extraction result
            for result in extraction_results:
                if not result.extraction_data:
                    continue
                
                doc_type = result.classification.primary_type
                data = result.extraction_data
                
                # Extract borrower info from PFS
                if doc_type == DocumentType.PERSONAL_FINANCIAL_STATEMENT:
                    self._extract_borrower_info(borrower, data)
                    self._extract_financial_position(financial_position, data)
                
                # Extract tax data
                elif doc_type in [DocumentType.TAX_RETURN_1040]:
                    self._extract_tax_data(financial_position, data)
                
                # Extract business data
                elif doc_type in [DocumentType.TAX_RETURN_1065, DocumentType.TAX_RETURN_1120S]:
                    if not business:
                        business = BusinessEntity(business_name="")
                    self._extract_business_data(business, financial_position, data)
                
                # Extract debt schedule
                elif doc_type == DocumentType.DEBT_SCHEDULE:
                    self._extract_debt_schedule(debt_schedule, data)
                
                # Extract financial statements
                elif doc_type in [DocumentType.BALANCE_SHEET, DocumentType.PROFIT_LOSS]:
                    self._extract_financial_statements(financial_position, data)
            
            # Create loan request (would need user input in real scenario)
            loan_request = LoanRequest(
                loan_type=LoanType.SBA,
                requested_amount=0,  # Would be provided by user
                loan_purpose="Business expansion"
            )
            
            # Build application
            application = LoanApplicationPackage(
                application_id=application_id,
                application_date=datetime.now(),
                status=ApplicationStatus.READY_FOR_REVIEW if borrower.first_name else ApplicationStatus.INCOMPLETE,
                primary_borrower=borrower,
                business_entity=business,
                financial_position=financial_position,
                debt_schedule=debt_schedule,
                loan_request=loan_request
            )
            
            # Add document metadata
            for result in extraction_results:
                application.documents_metadata.append(DocumentMetadata(
                    document_type=result.classification.primary_type.value,
                    file_name=result.file_path.name,
                    extraction_date=datetime.now(),
                    extraction_method=result.extraction_method,
                    confidence_score=result.confidence_score,
                    pages_processed=1,  # Would need actual count
                    extraction_time=result.processing_time,
                    errors=result.errors
                ))
            
            return application
            
        except Exception as e:
            logger.error(f"Failed to build loan application: {e}")
            return None
    
    def _extract_borrower_info(self, borrower: BorrowerInfo, data: Any):
        """Extract borrower information from document data."""
        if hasattr(data, 'fields'):
            # From LLM extraction
            for field in data.fields:
                if field.field_name == 'firstName':
                    borrower.first_name = field.value
                elif field.field_name == 'lastName':
                    borrower.last_name = field.value
                elif field.field_name == 'email':
                    borrower.email = field.value
                elif field.field_name in ['phone', 'residencePhone']:
                    borrower.phone = field.value
                elif field.field_name == 'businessPhone':
                    borrower.business_phone = field.value
                elif field.field_name == 'streetAddress':
                    borrower.street_address = field.value
                elif field.field_name == 'city':
                    borrower.city = field.value
                elif field.field_name == 'state':
                    borrower.state = field.value
                elif field.field_name == 'zipCode':
                    borrower.zip_code = field.value
                elif field.field_name == 'ssn':
                    borrower.ssn = field.value
                elif field.field_name == 'dateOfBirth':
                    borrower.date_of_birth = field.value
    
    def _extract_financial_position(self, financial: FinancialPosition, data: Any):
        """Extract financial position from document data."""
        if hasattr(data, 'fields'):
            # From LLM extraction
            for field in data.fields:
                if field.field_name == 'totalAssets':
                    financial.total_assets = field.value
                elif field.field_name == 'totalLiabilities':
                    financial.total_liabilities = field.value
                elif field.field_name == 'netWorth':
                    financial.net_worth = field.value
                elif field.field_name == 'salaryIncome':
                    financial.salary_income = field.value
                elif field.field_name == 'cashOnHand':
                    financial.cash_on_hand = field.value
                elif field.field_name == 'savingsAccounts':
                    # Map to appropriate field if exists
                    pass  # Could add to a cash_on_hand or liquid_assets field
                elif field.field_name == 'accountsPayable':
                    financial.accounts_payable = field.value
                elif field.field_name == 'netInvestmentIncome':
                    financial.investment_income = field.value
                elif field.field_name == 'realEstateIncome':
                    financial.real_estate_income = field.value
                elif field.field_name == 'realEstateValue':
                    financial.real_estate_value = field.value
                elif field.field_name == 'stocksBonds':
                    # Could map to investment assets
                    pass
                elif field.field_name == 'totalAnnualIncome':
                    financial.total_income = field.value
    
    def _extract_tax_data(self, financial: FinancialPosition, data: Any):
        """Extract tax return data."""
        if isinstance(data, TaxReturnData):
            financial.adjusted_gross_income = data.adjusted_gross_income
            financial.taxable_income = data.taxable_income
            if data.wages_salaries:
                financial.salary_income = data.wages_salaries
            if data.business_income:
                financial.business_income = data.business_income
    
    def _extract_business_data(self, business: BusinessEntity, financial: FinancialPosition, data: Any):
        """Extract business data from tax returns."""
        if isinstance(data, TaxReturnData):
            if data.business_name:
                business.business_name = data.business_name
            if data.business_ein:
                business.ein = data.business_ein
            if data.gross_receipts:
                financial.gross_revenue = data.gross_receipts
            if data.ordinary_business_income:
                financial.net_income = data.ordinary_business_income
    
    def _extract_debt_schedule(self, debt_schedule: DebtSchedule, data: Any):
        """Extract debt schedule data."""
        if isinstance(data, ExcelExtractionResult):
            # From native Excel extraction
            for sheet_data in data.data.values():
                if isinstance(sheet_data, dict) and 'debts' in sheet_data:
                    for debt_item in sheet_data['debts']:
                        debt = DebtItem(
                            creditor_name=debt_item.get('creditor_name', 'Unknown'),
                            current_balance=debt_item.get('current_balance', 0),
                            monthly_payment=debt_item.get('monthly_payment'),
                            interest_rate=debt_item.get('interest_rate')
                        )
                        debt_schedule.debts.append(debt)
        elif hasattr(data, 'fields'):
            # From LLM extraction
            for field in data.fields:
                if field.field_name == 'debts' and isinstance(field.value, list):
                    for debt_item in field.value:
                        if isinstance(debt_item, dict):
                            debt = DebtItem(
                                creditor_name=debt_item.get('creditor_name', 'Unknown'),
                                current_balance=debt_item.get('current_balance', 0),
                                monthly_payment=debt_item.get('monthly_payment'),
                                interest_rate=debt_item.get('interest_rate')
                            )
                            debt_schedule.debts.append(debt)
    
    def _extract_financial_statements(self, financial: FinancialPosition, data: Any):
        """Extract data from financial statements."""
        if isinstance(data, ExcelExtractionResult):
            for sheet_data in data.data.values():
                if isinstance(sheet_data, dict):
                    totals = sheet_data.get('totals', {})
                    # Balance sheet
                    if 'total_assets' in totals:
                        financial.total_assets = totals['total_assets']
                    if 'total_liabilities' in totals:
                        financial.total_liabilities = totals['total_liabilities']
                    # P&L
                    if 'revenue' in totals:
                        financial.gross_revenue = totals['revenue']
                    if 'net_income' in totals:
                        financial.net_income = totals['net_income']
    
    def _validate_documents(
        self,
        extraction_results: List[EnhancedDocumentResult]
    ) -> Optional[ValidationResult]:
        """Validate consistency across documents."""
        # Build document set for validation
        documents = {}
        
        # Group by type
        pfs_data = None
        tax_returns = []
        debt_schedule_data = None
        business_financials = {}
        
        for result in extraction_results:
            if not result.extraction_data:
                continue
            
            doc_type = result.classification.primary_type
            
            if doc_type == DocumentType.PERSONAL_FINANCIAL_STATEMENT:
                pfs_data = self._convert_to_validation_format(result.extraction_data)
            elif doc_type in [DocumentType.TAX_RETURN_1040, DocumentType.TAX_RETURN_1065]:
                tax_data = self._convert_to_validation_format(result.extraction_data)
                if tax_data:
                    tax_returns.append(tax_data)
            elif doc_type == DocumentType.DEBT_SCHEDULE:
                debt_schedule_data = self._convert_to_validation_format(result.extraction_data)
            elif doc_type in [DocumentType.BALANCE_SHEET, DocumentType.PROFIT_LOSS]:
                financial_data = self._convert_to_validation_format(result.extraction_data)
                if financial_data:
                    business_financials[doc_type.value] = financial_data
        
        # Build validation document set
        if pfs_data:
            documents['pfs'] = pfs_data
        if tax_returns:
            documents['tax_returns'] = tax_returns
        if debt_schedule_data:
            documents['debt_schedule'] = debt_schedule_data
        if business_financials:
            documents['business_financials'] = business_financials
        
        # Run validation if we have documents to validate
        if len(documents) >= 2:
            return self.validator.validate_loan_package(documents)
        
        return None
    
    def _convert_to_validation_format(self, data: Any) -> Optional[Dict]:
        """Convert extraction data to validation format."""
        try:
            if hasattr(data, 'fields'):
                # LLM extraction result
                result = {}
                for field in data.fields:
                    result[field.field_name] = field.value
                return result
            elif isinstance(data, TaxReturnData):
                # Tax return data
                return data.__dict__
            elif isinstance(data, ExcelExtractionResult):
                # Excel extraction
                return data.data
            elif isinstance(data, dict):
                return data
        except:
            pass
        
        return None
    
    def _convert_validation_status(self, validation_result: ValidationResult):
        """Convert validation result to application validation status."""
        from ..extraction_methods.multimodal_llm.models.loan_application_package import ValidationStatus
        
        return ValidationStatus(
            overall_status=validation_result.overall_status,
            validation_date=datetime.now(),
            passed_checks=validation_result.passed_checks,
            failed_checks=validation_result.failed_checks,
            warnings=validation_result.warnings,
            manual_review_required=validation_result.needs_review
        )
    
    def _get_field_value(self, data: Dict, *keys) -> Any:
        """Get field value trying multiple keys."""
        for key in keys:
            if key in data:
                value = data[key]
                if isinstance(value, dict) and 'value' in value:
                    return value['value']
                return value
        return None
    
    def _get_decimal_value(self, data: Dict, *keys):
        """Get decimal value from field."""
        from decimal import Decimal
        value = self._get_field_value(data, *keys)
        if value is not None:
            try:
                return Decimal(str(value))
            except:
                pass
        return None
    
    def _calculate_statistics(
        self,
        extraction_results: List[EnhancedDocumentResult],
        validation_result: Optional[ValidationResult]
    ) -> Dict[str, Any]:
        """Calculate pipeline statistics."""
        total_docs = len(extraction_results)
        successful = sum(1 for r in extraction_results if r.confidence_score > 0.5)
        
        avg_confidence = 0
        if extraction_results:
            confidences = [r.confidence_score for r in extraction_results if r.confidence_score > 0]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
        
        method_counts = {}
        for result in extraction_results:
            method = result.extraction_method
            method_counts[method] = method_counts.get(method, 0) + 1
        
        return {
            'total_documents': total_docs,
            'successful_extractions': successful,
            'average_confidence': avg_confidence,
            'extraction_methods': method_counts,
            'validation_passed': validation_result.is_valid if validation_result else None,
            'validation_confidence': validation_result.confidence if validation_result else None
        }
    
    def _save_results(
        self,
        application_id: str,
        loan_application: Optional[LoanApplicationPackage],
        extraction_results: List[EnhancedDocumentResult],
        validation_result: Optional[ValidationResult]
    ):
        """Save all results to files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save loan application
        if loan_application:
            app_file = self.config.output_directory / f"{application_id}_application_{timestamp}.json"
            with open(app_file, 'w') as f:
                json.dump(loan_application.to_json(), f, indent=2, default=str)
            logger.info(f"Saved loan application to {app_file}")
        
        # Save extraction results
        results_file = self.config.output_directory / f"{application_id}_extractions_{timestamp}.json"
        results_data = []
        for result in extraction_results:
            results_data.append({
                'file': str(result.file_path),
                'document_type': result.classification.primary_type.value,
                'extraction_method': result.extraction_method,
                'confidence': result.confidence_score,
                'processing_time': result.processing_time,
                'errors': result.errors,
                'warnings': result.warnings
            })
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        print(f"Saved extraction results to {results_file}")
        
        # Save validation report
        if validation_result:
            report = self.validator.generate_validation_report(validation_result)
            report_file = self.config.output_directory / f"{application_id}_validation_{timestamp}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            print(f"Saved validation report to {report_file}")