"""
Production-ready extraction service for documents with known form types.

This service is designed for production environments where:
1. Documents are already tagged with their form type in the database
2. You need direct extraction without classification overhead
3. You want to maintain data integrity with your Prisma schema
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from extraction_methods.multimodal_llm.providers.claude_extractor import ClaudeExtractor
from extraction_methods.multimodal_llm.core.schema_generator import PrismaSchemaGenerator
from extraction_methods.multimodal_llm.core.enhanced_document_classifier import (
    EnhancedDocumentClassifier,
    DocumentType
)

logger = logging.getLogger(__name__)


class ExtractionMode(Enum):
    """Extraction mode for production."""
    DIRECT = "direct"  # Trust the database form type
    VALIDATE = "validate"  # Validate form type matches document
    HYBRID = "hybrid"  # Use both and flag mismatches


@dataclass
class ProductionExtractionRequest:
    """Request model for production extraction."""
    document_id: str
    document_path: str
    form_type: str  # From database (e.g., "PersonalFinancialStatementMetadata")
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    validate_type: bool = False
    metadata: Dict[str, Any] = None


@dataclass
class ProductionExtractionResult:
    """Result model for production extraction."""
    success: bool
    document_id: str
    form_type: str
    extracted_data: Dict[str, Any]
    confidence: float
    warnings: List[str]
    processing_time: float
    timestamp: datetime
    validation_passed: Optional[bool] = None
    detected_type: Optional[str] = None


class ProductionExtractionService:
    """Production service for document extraction with known form types."""
    
    def __init__(self, mode: ExtractionMode = ExtractionMode.DIRECT):
        """
        Initialize the production extraction service.
        
        Args:
            mode: Extraction mode (DIRECT, VALIDATE, or HYBRID)
        """
        self.mode = mode
        self.extractor = ClaudeExtractor()
        self.schema_generator = PrismaSchemaGenerator()
        
        # Only initialize classifier if validation is needed
        if mode in [ExtractionMode.VALIDATE, ExtractionMode.HYBRID]:
            self.classifier = EnhancedDocumentClassifier()
        else:
            self.classifier = None
        
        # Cache for schemas to avoid regeneration
        self._schema_cache = {}
    
    async def extract_document(
        self, 
        request: ProductionExtractionRequest
    ) -> ProductionExtractionResult:
        """
        Extract document with known form type.
        
        This is the main entry point for production extraction.
        
        Args:
            request: Production extraction request with document details
            
        Returns:
            ProductionExtractionResult with extracted data
        """
        start_time = datetime.now()
        warnings = []
        validation_passed = None
        detected_type = None
        
        try:
            document_path = Path(request.document_path)
            
            # Validate document exists
            if not document_path.exists():
                raise FileNotFoundError(f"Document not found: {request.document_path}")
            
            # Step 1: Handle form type validation if needed
            if self.mode in [ExtractionMode.VALIDATE, ExtractionMode.HYBRID]:
                detected_type = await self._validate_form_type(
                    document_path, 
                    request.form_type,
                    warnings
                )
                validation_passed = (detected_type == request.form_type)
                
                if not validation_passed and self.mode == ExtractionMode.VALIDATE:
                    warnings.append(
                        f"Document type mismatch. Expected: {request.form_type}, "
                        f"Detected: {detected_type}"
                    )
            
            # Step 2: Get or generate schema
            schema = self._get_cached_schema(request.form_type)
            
            # Step 3: Extract with LLM
            logger.info(f"Extracting document {request.document_id} "
                       f"with form type {request.form_type}")
            
            extraction_result = await self.extractor.extract_with_schema(
                document=document_path,
                schema=schema,
                document_type=request.form_type
            )
            
            # Step 4: Process extraction result
            extracted_data = self._process_extraction_result(extraction_result)
            
            # Step 5: Add metadata
            if request.metadata:
                extracted_data['_metadata'] = request.metadata
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return ProductionExtractionResult(
                success=True,
                document_id=request.document_id,
                form_type=request.form_type,
                extracted_data=extracted_data,
                confidence=extraction_result.overall_confidence,
                warnings=warnings,
                processing_time=processing_time,
                timestamp=datetime.now(),
                validation_passed=validation_passed,
                detected_type=detected_type
            )
            
        except Exception as e:
            logger.error(f"Extraction failed for document {request.document_id}: {e}")
            
            return ProductionExtractionResult(
                success=False,
                document_id=request.document_id,
                form_type=request.form_type,
                extracted_data={},
                confidence=0.0,
                warnings=[str(e)],
                processing_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
                validation_passed=validation_passed,
                detected_type=detected_type
            )
    
    async def batch_extract(
        self,
        requests: List[ProductionExtractionRequest],
        max_concurrent: int = 5
    ) -> List[ProductionExtractionResult]:
        """
        Extract multiple documents in batch.
        
        Args:
            requests: List of extraction requests
            max_concurrent: Maximum concurrent extractions
            
        Returns:
            List of extraction results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def extract_with_limit(request):
            async with semaphore:
                return await self.extract_document(request)
        
        tasks = [extract_with_limit(req) for req in requests]
        return await asyncio.gather(*tasks)
    
    def _get_cached_schema(self, form_type: str) -> Dict[str, Any]:
        """Get schema from cache or generate it."""
        if form_type not in self._schema_cache:
            self._schema_cache[form_type] = self.schema_generator.generate_extraction_schema(
                form_type
            )
        return self._schema_cache[form_type]
    
    async def _validate_form_type(
        self,
        document_path: Path,
        expected_form_type: str,
        warnings: List[str]
    ) -> Optional[str]:
        """Validate that document matches expected form type."""
        try:
            # Classify the document
            classification = self.classifier.classify_document(document_path)
            
            # Map classification to Prisma schema name
            type_mapping = {
                DocumentType.PERSONAL_FINANCIAL_STATEMENT: "PersonalFinancialStatementMetadata",
                DocumentType.SBA_FORM_413: "PersonalFinancialStatementMetadata",  # Same schema
                DocumentType.TAX_RETURN_1040: "TaxReturn1040Metadata",
                DocumentType.TAX_RETURN_1065: "TaxReturn1065Metadata",
                DocumentType.TAX_RETURN_1120S: "TaxReturn1120SMetadata",
                DocumentType.BALANCE_SHEET: "BalanceSheetMetadata",
                DocumentType.PROFIT_LOSS: "ProfitLossStatementMetadata",
                DocumentType.DEBT_SCHEDULE: "DebtScheduleMetadata",
                # Add more mappings as needed
            }
            
            detected_schema = type_mapping.get(
                classification.primary_type,
                "UnknownMetadata"
            )
            
            if detected_schema != expected_form_type:
                warnings.append(
                    f"Type validation warning: Expected {expected_form_type}, "
                    f"detected {detected_schema} with {classification.confidence:.0%} confidence"
                )
            
            return detected_schema
            
        except Exception as e:
            warnings.append(f"Type validation failed: {e}")
            return None
    
    def _process_extraction_result(self, extraction_result) -> Dict[str, Any]:
        """Process extraction result into clean dictionary."""
        extracted_data = {}
        
        # Convert fields to dictionary
        for field in extraction_result.fields:
            if field.value is not None:
                extracted_data[field.field_name] = {
                    'value': field.value,
                    'confidence': field.confidence,
                    'source_text': field.source_text if hasattr(field, 'source_text') else None
                }
        
        return extracted_data


# Convenience functions for production use

async def extract_single_document(
    document_path: str,
    form_type: str,
    document_id: str,
    validate: bool = False
) -> ProductionExtractionResult:
    """
    Simple function to extract a single document.
    
    Example:
        result = await extract_single_document(
            document_path="/path/to/document.pdf",
            form_type="PersonalFinancialStatementMetadata",
            document_id="DOC-123",
            validate=True
        )
    """
    mode = ExtractionMode.VALIDATE if validate else ExtractionMode.DIRECT
    service = ProductionExtractionService(mode=mode)
    
    request = ProductionExtractionRequest(
        document_id=document_id,
        document_path=document_path,
        form_type=form_type,
        validate_type=validate
    )
    
    return await service.extract_document(request)


async def extract_loan_package(
    documents: List[Dict[str, str]],
    validate: bool = False
) -> List[ProductionExtractionResult]:
    """
    Extract a complete loan package.
    
    Args:
        documents: List of dicts with 'path', 'form_type', and 'id'
        validate: Whether to validate form types
        
    Example:
        documents = [
            {
                'path': '/path/to/pfs.pdf',
                'form_type': 'PersonalFinancialStatementMetadata',
                'id': 'DOC-001'
            },
            {
                'path': '/path/to/tax_return.pdf',
                'form_type': 'TaxReturn1040Metadata',
                'id': 'DOC-002'
            }
        ]
        results = await extract_loan_package(documents, validate=True)
    """
    mode = ExtractionMode.VALIDATE if validate else ExtractionMode.DIRECT
    service = ProductionExtractionService(mode=mode)
    
    requests = [
        ProductionExtractionRequest(
            document_id=doc['id'],
            document_path=doc['path'],
            form_type=doc['form_type'],
            validate_type=validate
        )
        for doc in documents
    ]
    
    return await service.batch_extract(requests)


# Example usage
if __name__ == "__main__":
    async def test_production_extraction():
        """Test the production extraction service."""
        
        # Example 1: Single document with known type
        result = await extract_single_document(
            document_path="inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf",
            form_type="PersonalFinancialStatementMetadata",
            document_id="TEST-001",
            validate=True
        )
        
        print(f"Extraction {'succeeded' if result.success else 'failed'}")
        print(f"Confidence: {result.confidence:.0%}")
        print(f"Fields extracted: {len(result.extracted_data)}")
        if result.warnings:
            print(f"Warnings: {result.warnings}")
        
        # Example 2: Batch extraction
        documents = [
            {
                'path': 'inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf',
                'form_type': 'PersonalFinancialStatementMetadata',
                'id': 'DOC-001'
            },
            {
                'path': 'inputs/real/Dave Burlington - Application Packet/Business Debt Schedule/Debt Schedule.xlsx',
                'form_type': 'DebtScheduleMetadata',
                'id': 'DOC-002'
            }
        ]
        
        results = await extract_loan_package(documents, validate=True)
        for result in results:
            print(f"\nDocument {result.document_id}: "
                  f"{'✅' if result.success else '❌'} "
                  f"({result.confidence:.0%} confidence)")
    
    # Run test
    asyncio.run(test_production_extraction())