"""
Main extraction pipeline orchestrating the document processing workflow.

This module provides the primary pipeline for document discovery, classification,
parallel extraction, consolidation, validation, and error handling with comprehensive logging.
"""

import asyncio
import logging
import concurrent.futures
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib
from collections import defaultdict
import time

# Import our custom modules
from .base import BaseExtractor, DocumentType, ExtractionResult, ExtractedField, ExtractionStatus
from .document_classifier import DocumentClassifier, ClassificationResult
from .pfs_extractor import PFSExtractor, PersonalFinancialStatementMetadata
from .confidence_scorer import ConfidenceScorer, DocumentConfidenceReport
from .value_parser import ValueParser
from ..mappers.prisma_mapper import (
    PrismaMapper, ValidationResult, DocumentMetadata,
    BeneficialOwnerMetadata, BusinessFinancialStatementMetadata,
    LoanApplicationMetadata, DebtScheduleMetadata
)

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline processing stages."""
    DISCOVERY = "discovery"
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    MAPPING = "mapping"
    CONSOLIDATION = "consolidation"
    FINALIZATION = "finalization"


class ProcessingStatus(Enum):
    """Overall processing status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


@dataclass
class DocumentProcessingResult:
    """Result of processing a single document."""
    file_path: Path
    classification: ClassificationResult
    extraction: Optional[ExtractionResult] = None
    confidence_report: Optional[DocumentConfidenceReport] = None
    mapped_data: Any = None
    validation_results: List[ValidationResult] = field(default_factory=list)
    processing_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of the entire pipeline execution."""
    processing_status: ProcessingStatus
    documents_processed: List[DocumentProcessingResult]
    summary_statistics: Dict[str, Any]
    consolidated_data: Dict[str, Any]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_processing_time: float = 0.0
    pipeline_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Configuration for the extraction pipeline."""
    # Processing options
    max_workers: int = 4
    enable_parallel_processing: bool = True
    batch_size: int = 10
    timeout_per_document: int = 300  # seconds
    
    # Classification options
    classification_confidence_threshold: float = 0.5
    enable_ocr_fallback: bool = True
    text_extraction_method: str = 'auto'
    
    # Extraction options
    extraction_confidence_threshold: float = 0.6
    enable_cross_validation: bool = True
    retry_failed_extractions: bool = True
    max_extraction_retries: int = 2
    
    # Validation options
    strict_validation: bool = False
    skip_validation_on_low_confidence: bool = False
    
    # Output options
    save_intermediate_results: bool = True
    output_format: str = 'json'  # json, csv, excel
    include_raw_text: bool = False
    include_confidence_details: bool = True
    
    # Logging options
    log_level: str = 'INFO'
    enable_detailed_logging: bool = True
    save_processing_logs: bool = True
    
    # Custom extractors
    custom_extractors: Dict[DocumentType, BaseExtractor] = field(default_factory=dict)
    
    # File filtering
    supported_extensions: Set[str] = field(default_factory=lambda: {'.pdf', '.png', '.jpg', '.jpeg', '.tiff'})
    exclude_patterns: List[str] = field(default_factory=list)


class ExtractionPipeline:
    """
    Comprehensive document extraction pipeline.
    
    Orchestrates document discovery, classification, extraction, validation,
    and consolidation with parallel processing and error handling.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize the extraction pipeline."""
        self.config = config or PipelineConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize components
        self.document_classifier = DocumentClassifier()
        self.confidence_scorer = ConfidenceScorer()
        self.prisma_mapper = PrismaMapper()
        self.value_parser = ValueParser()
        
        # Initialize extractors
        self._setup_extractors()
        
        # Processing state
        self.current_stage = PipelineStage.DISCOVERY
        self.processing_start_time = None
        self.processed_documents = []
        
    def _setup_logging(self):
        """Setup pipeline logging configuration."""
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        
        if self.config.enable_detailed_logging:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
    
    def _setup_extractors(self):
        """Initialize document extractors."""
        self.extractors = {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: PFSExtractor(),
            DocumentType.SBA_FORM_413: PFSExtractor(),
            # Add other extractors as needed
        }
        
        # Add custom extractors from config
        self.extractors.update(self.config.custom_extractors)
    
    async def process_documents(
        self, 
        input_paths: List[Path],
        output_path: Optional[Path] = None
    ) -> PipelineResult:
        """
        Process documents through the complete extraction pipeline.
        
        Args:
            input_paths: List of file/directory paths to process
            output_path: Optional path to save results
            
        Returns:
            PipelineResult with processing results
        """
        self.processing_start_time = datetime.utcnow()
        self.logger.info(f"Starting document processing pipeline with {len(input_paths)} input paths")
        
        try:
            # Stage 1: Document Discovery
            self.current_stage = PipelineStage.DISCOVERY
            discovered_files = await self._discover_documents(input_paths)
            self.logger.info(f"Discovered {len(discovered_files)} documents for processing")
            
            # Stage 2: Classification
            self.current_stage = PipelineStage.CLASSIFICATION
            classification_results = await self._classify_documents(discovered_files)
            
            # Stage 3: Extraction
            self.current_stage = PipelineStage.EXTRACTION
            extraction_results = await self._extract_from_documents(classification_results)
            
            # Stage 4: Validation and Confidence Analysis
            self.current_stage = PipelineStage.VALIDATION
            validated_results = await self._validate_extractions(extraction_results)
            
            # Stage 5: Data Mapping
            self.current_stage = PipelineStage.MAPPING
            mapped_results = await self._map_extracted_data(validated_results)
            
            # Stage 6: Consolidation
            self.current_stage = PipelineStage.CONSOLIDATION
            consolidated_data = await self._consolidate_results(mapped_results)
            
            # Stage 7: Finalization
            self.current_stage = PipelineStage.FINALIZATION
            pipeline_result = await self._finalize_results(
                mapped_results, consolidated_data, output_path
            )
            
            total_time = (datetime.utcnow() - self.processing_start_time).total_seconds()
            pipeline_result.total_processing_time = total_time
            
            self.logger.info(f"Pipeline completed in {total_time:.2f} seconds")
            return pipeline_result
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            total_time = (datetime.utcnow() - self.processing_start_time).total_seconds()
            
            return PipelineResult(
                processing_status=ProcessingStatus.FAILED,
                documents_processed=[],
                summary_statistics={},
                consolidated_data={},
                errors=[f"Pipeline failure: {str(e)}"],
                total_processing_time=total_time,
                pipeline_metadata={'failure_stage': self.current_stage.value}
            )
    
    async def _discover_documents(self, input_paths: List[Path]) -> List[Path]:
        """Discover all documents to process from input paths."""
        discovered_files = []
        
        for input_path in input_paths:
            if input_path.is_file():
                if self._should_process_file(input_path):
                    discovered_files.append(input_path)
            elif input_path.is_dir():
                # Recursively find files in directory
                for file_path in input_path.rglob('*'):
                    if file_path.is_file() and self._should_process_file(file_path):
                        discovered_files.append(file_path)
            else:
                self.logger.warning(f"Path not found or not accessible: {input_path}")
        
        # Remove duplicates and sort
        discovered_files = sorted(list(set(discovered_files)))
        
        self.logger.info(f"File discovery completed: {len(discovered_files)} files found")
        return discovered_files
    
    def _should_process_file(self, file_path: Path) -> bool:
        """Check if a file should be processed based on filters."""
        # Check file extension
        if file_path.suffix.lower() not in self.config.supported_extensions:
            return False
        
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if pattern in str(file_path):
                return False
        
        # Check file size (skip very large files that might cause issues)
        try:
            file_size = file_path.stat().st_size
            if file_size > 100 * 1024 * 1024:  # 100MB limit
                self.logger.warning(f"Skipping large file: {file_path} ({file_size / 1024 / 1024:.1f}MB)")
                return False
        except OSError:
            return False
        
        return True
    
    async def _classify_documents(self, file_paths: List[Path]) -> List[Tuple[Path, ClassificationResult]]:
        """Classify all discovered documents."""
        self.logger.info(f"Starting classification of {len(file_paths)} documents")
        
        if self.config.enable_parallel_processing and len(file_paths) > 1:
            # Parallel classification
            classification_results = await self._classify_documents_parallel(file_paths)
        else:
            # Sequential classification
            classification_results = []
            for file_path in file_paths:
                try:
                    classification = self.document_classifier.classify_document(
                        file_path, self.config.text_extraction_method
                    )
                    classification_results.append((file_path, classification))
                except Exception as e:
                    self.logger.error(f"Classification failed for {file_path}: {e}")
                    # Create a failed classification result
                    failed_classification = ClassificationResult(
                        document_type=DocumentType.UNKNOWN,
                        confidence=0.0,
                        reasoning=f"Classification error: {str(e)}",
                        alternative_types=[],
                        fingerprint=self.document_classifier._create_fingerprint("", {}),
                        metadata={'file_path': str(file_path), 'error': str(e)}
                    )
                    classification_results.append((file_path, failed_classification))
        
        self.logger.info(f"Classification completed: {len(classification_results)} results")
        return classification_results
    
    async def _classify_documents_parallel(self, file_paths: List[Path]) -> List[Tuple[Path, ClassificationResult]]:
        """Classify documents in parallel using ThreadPoolExecutor."""
        classification_results = []
        
        def classify_single(file_path: Path) -> Tuple[Path, ClassificationResult]:
            try:
                classification = self.document_classifier.classify_document(
                    file_path, self.config.text_extraction_method
                )
                return (file_path, classification)
            except Exception as e:
                self.logger.error(f"Classification failed for {file_path}: {e}")
                failed_classification = ClassificationResult(
                    document_type=DocumentType.UNKNOWN,
                    confidence=0.0,
                    reasoning=f"Classification error: {str(e)}",
                    alternative_types=[],
                    fingerprint=self.document_classifier._create_fingerprint("", {}),
                    metadata={'file_path': str(file_path), 'error': str(e)}
                )
                return (file_path, failed_classification)
        
        # Process in batches
        for i in range(0, len(file_paths), self.config.batch_size):
            batch = file_paths[i:i + self.config.batch_size]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                batch_results = list(executor.map(classify_single, batch))
                classification_results.extend(batch_results)
            
            self.logger.info(f"Classified batch {i // self.config.batch_size + 1}: {len(batch)} documents")
        
        return classification_results
    
    async def _extract_from_documents(
        self, 
        classification_results: List[Tuple[Path, ClassificationResult]]
    ) -> List[DocumentProcessingResult]:
        """Extract data from classified documents."""
        self.logger.info(f"Starting extraction from {len(classification_results)} documents")
        
        extraction_results = []
        
        for file_path, classification in classification_results:
            start_time = time.time()
            
            try:
                # Check if we have an extractor for this document type
                extractor = self.extractors.get(classification.document_type)
                
                if not extractor:
                    # No specific extractor available
                    processing_result = DocumentProcessingResult(
                        file_path=file_path,
                        classification=classification,
                        processing_time=time.time() - start_time,
                        errors=[f"No extractor available for document type: {classification.document_type}"]
                    )
                    extraction_results.append(processing_result)
                    continue
                
                # Check if extractor can process this document
                if not extractor.can_process(file_path, classification.document_type):
                    processing_result = DocumentProcessingResult(
                        file_path=file_path,
                        classification=classification,
                        processing_time=time.time() - start_time,
                        errors=[f"Extractor cannot process document: {file_path}"]
                    )
                    extraction_results.append(processing_result)
                    continue
                
                # Perform extraction
                extraction_result = extractor.extract(file_path)
                
                # Create processing result
                processing_result = DocumentProcessingResult(
                    file_path=file_path,
                    classification=classification,
                    extraction=extraction_result,
                    processing_time=time.time() - start_time,
                    metadata={
                        'extractor_used': extractor.__class__.__name__,
                        'extraction_status': extraction_result.status.value
                    }
                )
                
                # Add any extraction errors
                if extraction_result.errors:
                    processing_result.errors.extend(extraction_result.errors)
                
                extraction_results.append(processing_result)
                
                self.logger.info(f"Extracted from {file_path.name}: {extraction_result.status.value}")
                
            except Exception as e:
                self.logger.error(f"Extraction failed for {file_path}: {e}")
                processing_result = DocumentProcessingResult(
                    file_path=file_path,
                    classification=classification,
                    processing_time=time.time() - start_time,
                    errors=[f"Extraction error: {str(e)}"]
                )
                extraction_results.append(processing_result)
        
        self.logger.info(f"Extraction completed: {len(extraction_results)} results")
        return extraction_results
    
    async def _validate_extractions(
        self, 
        processing_results: List[DocumentProcessingResult]
    ) -> List[DocumentProcessingResult]:
        """Validate extractions and generate confidence reports."""
        self.logger.info(f"Starting validation of {len(processing_results)} extraction results")
        
        for result in processing_results:
            if result.extraction is None:
                continue
            
            try:
                # Generate confidence report
                confidence_report = self.confidence_scorer.generate_document_confidence_report(
                    result.extraction,
                    result.extraction.raw_text or ""
                )
                result.confidence_report = confidence_report
                
                # Add warnings for low confidence fields
                for field_name in confidence_report.manual_review_fields:
                    result.warnings.append(f"Field '{field_name}' requires manual review")
                
                # Update metadata with confidence information
                result.metadata.update({
                    'overall_confidence': confidence_report.overall_confidence,
                    'manual_review_required': len(confidence_report.manual_review_fields) > 0,
                    'confidence_distribution': confidence_report.confidence_distribution
                })
                
            except Exception as e:
                self.logger.error(f"Validation failed for {result.file_path}: {e}")
                result.errors.append(f"Validation error: {str(e)}")
        
        self.logger.info("Validation completed")
        return processing_results
    
    async def _map_extracted_data(
        self, 
        processing_results: List[DocumentProcessingResult]
    ) -> List[DocumentProcessingResult]:
        """Map extracted data to Prisma schema structures."""
        self.logger.info(f"Starting data mapping for {len(processing_results)} results")
        
        for result in processing_results:
            if result.extraction is None:
                continue
            
            try:
                # Determine target schema based on document type
                target_schema = self._get_target_schema(result.classification.document_type)
                
                if target_schema:
                    # Map to schema
                    mapped_data, validation_results = self.prisma_mapper.map_extraction_result_to_schema(
                        result.extraction,
                        target_schema
                    )
                    
                    result.mapped_data = mapped_data
                    result.validation_results = validation_results
                    
                    # Add validation errors/warnings
                    for validation in validation_results:
                        if validation.status.value in ['invalid', 'missing_required']:
                            result.errors.append(f"Validation error for {validation.field_name}: {validation.message}")
                        elif validation.status.value == 'warning':
                            result.warnings.append(f"Validation warning for {validation.field_name}: {validation.message}")
                
                # Create document metadata
                doc_metadata = self.prisma_mapper.create_document_metadata(
                    result.file_path,
                    result.extraction,
                    classification_confidence=result.classification.confidence
                )
                
                result.metadata['document_metadata'] = doc_metadata
                
            except Exception as e:
                self.logger.error(f"Data mapping failed for {result.file_path}: {e}")
                result.errors.append(f"Mapping error: {str(e)}")
        
        self.logger.info("Data mapping completed")
        return processing_results
    
    def _get_target_schema(self, document_type: DocumentType) -> Optional[type]:
        """Get the target Prisma schema for a document type."""
        schema_mapping = {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: PersonalFinancialStatementMetadata,
            DocumentType.SBA_FORM_413: PersonalFinancialStatementMetadata,
            # Add other mappings as needed
        }
        
        return schema_mapping.get(document_type)
    
    async def _consolidate_results(
        self, 
        processing_results: List[DocumentProcessingResult]
    ) -> Dict[str, Any]:
        """Consolidate processing results into structured data."""
        self.logger.info("Starting results consolidation")
        
        consolidated = {
            'documents_by_type': defaultdict(list),
            'extraction_summary': {},
            'validation_summary': {},
            'confidence_summary': {},
            'errors_summary': {},
            'processing_statistics': {}
        }
        
        # Group documents by type
        for result in processing_results:
            doc_type = result.classification.document_type.value
            consolidated['documents_by_type'][doc_type].append({
                'file_path': str(result.file_path),
                'classification_confidence': result.classification.confidence,
                'extraction_status': result.extraction.status.value if result.extraction else 'not_extracted',
                'extraction_confidence': result.extraction.confidence_score if result.extraction else 0.0,
                'has_errors': len(result.errors) > 0,
                'has_warnings': len(result.warnings) > 0,
                'mapped_data': result.mapped_data
            })
        
        # Generate summary statistics
        total_docs = len(processing_results)
        successful_extractions = sum(1 for r in processing_results 
                                   if r.extraction and r.extraction.status != ExtractionStatus.FAILED)
        
        consolidated['extraction_summary'] = {
            'total_documents': total_docs,
            'successful_extractions': successful_extractions,
            'failed_extractions': total_docs - successful_extractions,
            'success_rate': successful_extractions / total_docs if total_docs > 0 else 0.0
        }
        
        # Confidence statistics
        confidence_scores = [r.extraction.confidence_score for r in processing_results 
                           if r.extraction and r.extraction.confidence_score is not None]
        
        if confidence_scores:
            consolidated['confidence_summary'] = {
                'average_confidence': sum(confidence_scores) / len(confidence_scores),
                'min_confidence': min(confidence_scores),
                'max_confidence': max(confidence_scores),
                'high_confidence_count': sum(1 for c in confidence_scores if c >= 0.8),
                'medium_confidence_count': sum(1 for c in confidence_scores if 0.5 <= c < 0.8),
                'low_confidence_count': sum(1 for c in confidence_scores if c < 0.5)
            }
        
        # Error summary
        all_errors = [error for r in processing_results for error in r.errors]
        error_types = defaultdict(int)
        for error in all_errors:
            # Categorize errors
            if 'classification' in error.lower():
                error_types['classification'] += 1
            elif 'extraction' in error.lower():
                error_types['extraction'] += 1
            elif 'validation' in error.lower():
                error_types['validation'] += 1
            else:
                error_types['other'] += 1
        
        consolidated['errors_summary'] = {
            'total_errors': len(all_errors),
            'error_types': dict(error_types),
            'documents_with_errors': sum(1 for r in processing_results if r.errors)
        }
        
        # Processing statistics
        processing_times = [r.processing_time for r in processing_results if r.processing_time > 0]
        if processing_times:
            consolidated['processing_statistics'] = {
                'total_processing_time': sum(processing_times),
                'average_processing_time': sum(processing_times) / len(processing_times),
                'min_processing_time': min(processing_times),
                'max_processing_time': max(processing_times)
            }
        
        self.logger.info("Results consolidation completed")
        return consolidated
    
    async def _finalize_results(
        self, 
        processing_results: List[DocumentProcessingResult],
        consolidated_data: Dict[str, Any],
        output_path: Optional[Path]
    ) -> PipelineResult:
        """Finalize and optionally save pipeline results."""
        self.logger.info("Finalizing pipeline results")
        
        # Determine overall processing status
        total_docs = len(processing_results)
        successful_docs = sum(1 for r in processing_results 
                            if r.extraction and r.extraction.status == ExtractionStatus.SUCCESS)
        failed_docs = sum(1 for r in processing_results if r.errors)
        
        if failed_docs == 0:
            status = ProcessingStatus.COMPLETED
        elif successful_docs == 0:
            status = ProcessingStatus.FAILED
        else:
            status = ProcessingStatus.PARTIALLY_COMPLETED
        
        # Create pipeline result
        pipeline_result = PipelineResult(
            processing_status=status,
            documents_processed=processing_results,
            summary_statistics=consolidated_data,
            consolidated_data=consolidated_data,
            pipeline_metadata={
                'pipeline_version': '1.0.0',
                'processing_stages_completed': [stage.value for stage in PipelineStage],
                'configuration': {
                    'max_workers': self.config.max_workers,
                    'batch_size': self.config.batch_size,
                    'parallel_processing': self.config.enable_parallel_processing,
                    'text_extraction_method': self.config.text_extraction_method
                }
            }
        )
        
        # Collect overall errors and warnings
        pipeline_result.errors = [error for r in processing_results for error in r.errors]
        pipeline_result.warnings = [warning for r in processing_results for warning in r.warnings]
        
        # Save results if output path specified
        if output_path:
            await self._save_results(pipeline_result, output_path)
        
        self.logger.info(f"Pipeline finalized with status: {status.value}")
        return pipeline_result
    
    async def _save_results(self, pipeline_result: PipelineResult, output_path: Path):
        """Save pipeline results to specified output path."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare serializable data
            serializable_data = {
                'processing_status': pipeline_result.processing_status.value,
                'summary_statistics': pipeline_result.summary_statistics,
                'total_processing_time': pipeline_result.total_processing_time,
                'pipeline_metadata': pipeline_result.pipeline_metadata,
                'errors': pipeline_result.errors,
                'warnings': pipeline_result.warnings,
                'documents': []
            }
            
            # Add document data
            for doc_result in pipeline_result.documents_processed:
                doc_data = {
                    'file_path': str(doc_result.file_path),
                    'document_type': doc_result.classification.document_type.value,
                    'classification_confidence': doc_result.classification.confidence,
                    'processing_time': doc_result.processing_time,
                    'errors': doc_result.errors,
                    'warnings': doc_result.warnings,
                    'metadata': doc_result.metadata
                }
                
                if doc_result.extraction:
                    doc_data['extraction'] = {
                        'status': doc_result.extraction.status.value,
                        'confidence_score': doc_result.extraction.confidence_score,
                        'extracted_fields': [
                            {
                                'name': field.name,
                                'value': str(field.value) if field.value is not None else None,
                                'confidence': field.confidence
                            }
                            for field in doc_result.extraction.extracted_fields
                        ]
                    }
                
                if self.config.include_raw_text and doc_result.extraction and doc_result.extraction.raw_text:
                    doc_data['raw_text'] = doc_result.extraction.raw_text
                
                serializable_data['documents'].append(doc_data)
            
            # Save as JSON
            if self.config.output_format == 'json' or output_path.suffix.lower() == '.json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(serializable_data, f, indent=2, default=str)
            
            self.logger.info(f"Results saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")
            pipeline_result.errors.append(f"Failed to save results: {str(e)}")
    
    def process_single_document(self, file_path: Path) -> DocumentProcessingResult:
        """
        Process a single document synchronously.
        
        Args:
            file_path: Path to document to process
            
        Returns:
            DocumentProcessingResult
        """
        start_time = time.time()
        
        try:
            # Classification
            classification = self.document_classifier.classify_document(file_path)
            
            # Create base result
            result = DocumentProcessingResult(
                file_path=file_path,
                classification=classification,
                processing_time=0.0  # Will be updated at the end
            )
            
            # Check if we can extract from this document
            extractor = self.extractors.get(classification.document_type)
            if not extractor:
                result.errors.append(f"No extractor available for {classification.document_type}")
                result.processing_time = time.time() - start_time
                return result
            
            if not extractor.can_process(file_path, classification.document_type):
                result.errors.append("Extractor cannot process this document")
                result.processing_time = time.time() - start_time
                return result
            
            # Extraction
            extraction_result = extractor.extract(file_path)
            result.extraction = extraction_result
            
            if extraction_result.errors:
                result.errors.extend(extraction_result.errors)
            
            # Confidence analysis
            if extraction_result.raw_text:
                confidence_report = self.confidence_scorer.generate_document_confidence_report(
                    extraction_result,
                    extraction_result.raw_text
                )
                result.confidence_report = confidence_report
                
                for field_name in confidence_report.manual_review_fields:
                    result.warnings.append(f"Field '{field_name}' requires manual review")
            
            # Data mapping
            target_schema = self._get_target_schema(classification.document_type)
            if target_schema:
                mapped_data, validation_results = self.prisma_mapper.map_extraction_result_to_schema(
                    extraction_result,
                    target_schema
                )
                result.mapped_data = mapped_data
                result.validation_results = validation_results
            
            result.processing_time = time.time() - start_time
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            return DocumentProcessingResult(
                file_path=file_path,
                classification=ClassificationResult(
                    document_type=DocumentType.UNKNOWN,
                    confidence=0.0,
                    reasoning=f"Processing error: {str(e)}",
                    alternative_types=[],
                    fingerprint=self.document_classifier._create_fingerprint("", {}),
                    metadata={'error': str(e)}
                ),
                processing_time=time.time() - start_time,
                errors=[f"Processing error: {str(e)}"]
            )