"""
Main document processing pipeline.

This module orchestrates the complete document processing workflow from
extraction to template filling and output generation.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from datetime import datetime

from ..extractors.base import BaseExtractor, DocumentType, ExtractionResult, ExtractionStatus
from ..extractors.bank_statement import BankStatementExtractor
from ..extractors.tax_return import TaxReturnExtractor
from ..extractors.financial_statement import FinancialStatementExtractor
from ..fillers.base import BaseFiller, FillingResult, FillingStatus, FieldMapping
from ..utils.accuracy_reporter import AccuracyReporter

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Status of the processing pipeline."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class ProcessingJob:
    """Represents a document processing job."""
    job_id: str
    input_files: List[Path]
    template_path: Optional[Path]
    output_dir: Path
    document_type: Optional[DocumentType] = None
    field_mappings: Optional[List[FieldMapping]] = None
    config: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ProcessingResult:
    """Result of document processing pipeline."""
    job_id: str
    status: PipelineStatus
    extraction_results: List[ExtractionResult]
    filling_result: Optional[FillingResult]
    output_files: List[Path]
    processing_time: float
    errors: List[str]
    metadata: Dict[str, Any]


class DocumentProcessingPipeline:
    """
    Main document processing pipeline.
    
    Orchestrates the complete workflow:
    1. Document type detection
    2. Data extraction
    3. Template filling
    4. Output generation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the processing pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize extractors and fillers
        self.extractors: List[BaseExtractor] = []
        self.fillers: List[BaseFiller] = []
        
        self._setup_pipeline()
    
    def _setup_pipeline(self) -> None:
        """Setup pipeline components."""
        # Register default extractors
        extractors_config = self.config.get('extractors', {})
        self.register_extractor(BankStatementExtractor(extractors_config.get('bank_statement', {})))
        self.register_extractor(TaxReturnExtractor(extractors_config.get('tax_return', {})))
        self.register_extractor(FinancialStatementExtractor(extractors_config.get('financial_statement', {})))
        
        # Setup processing configuration
        self.max_file_size = self.config.get('max_file_size_mb', 50) * 1024 * 1024  # Convert to bytes
        self.processing_timeout = self.config.get('processing_timeout_seconds', 300)
        self.parallel_processing = self.config.get('parallel_processing', False)
        
        # Setup output configuration
        self.save_extraction_results = self.config.get('save_extraction_results', True)
        self.output_format = self.config.get('output_format', 'json')
        
        # Setup accuracy reporting
        self.enable_accuracy_reporting = self.config.get('enable_accuracy_reporting', False)
        self.accuracy_reporter = AccuracyReporter(self.config.get('accuracy_reporter', {})) if self.enable_accuracy_reporting else None
    
    def register_extractor(self, extractor: BaseExtractor) -> None:
        """Register a document extractor."""
        self.extractors.append(extractor)
        self.logger.info(f"Registered extractor: {extractor}")
    
    def register_filler(self, filler: BaseFiller) -> None:
        """Register a form filler."""
        self.fillers.append(filler)
        self.logger.info(f"Registered filler: {filler}")
    
    def get_extractor_for_document(self, file_path: Path, document_type: Optional[DocumentType] = None) -> Optional[BaseExtractor]:
        """
        Find the best extractor for a document.
        
        Args:
            file_path: Path to the document
            document_type: Optional hint about document type
            
        Returns:
            Best extractor for the document, or None if no extractor can handle it
        """
        # If document type is specified, look for exact match first
        if document_type:
            for extractor in self.extractors:
                if (document_type in extractor.supported_document_types and 
                    extractor.can_process(file_path, document_type)):
                    return extractor
        
        # Find any extractor that can process the document
        for extractor in self.extractors:
            if extractor.can_process(file_path, document_type):
                return extractor
        
        return None
    
    def get_filler_for_template(self, template_path: Path) -> Optional[BaseFiller]:
        """
        Find the best filler for a template.
        
        Args:
            template_path: Path to the template
            
        Returns:
            Best filler for the template, or None if no filler can handle it
        """
        for filler in self.fillers:
            if filler.can_fill(template_path):
                return filler
        
        return None
    
    def validate_job(self, job: ProcessingJob) -> List[str]:
        """
        Validate a processing job.
        
        Args:
            job: Processing job to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check input files
        if not job.input_files:
            errors.append("No input files specified")
        
        for file_path in job.input_files:
            if not file_path.exists():
                errors.append(f"Input file does not exist: {file_path}")
            elif file_path.stat().st_size > self.max_file_size:
                errors.append(f"File too large: {file_path} ({file_path.stat().st_size} bytes)")
        
        # Check template
        if job.template_path and not job.template_path.exists():
            errors.append(f"Template file does not exist: {job.template_path}")
        
        # Check output directory
        if not job.output_dir.exists():
            try:
                job.output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory: {e}")
        
        return errors
    
    def process_job(self, job: ProcessingJob) -> ProcessingResult:
        """
        Process a complete document processing job.
        
        Args:
            job: Processing job configuration
            
        Returns:
            Processing result
        """
        start_time = time.time()
        extraction_results = []
        filling_result = None
        output_files = []
        errors = []
        
        try:
            self.logger.info(f"Starting processing job {job.job_id}")
            
            # Validate job
            validation_errors = self.validate_job(job)
            if validation_errors:
                return ProcessingResult(
                    job_id=job.job_id,
                    status=PipelineStatus.FAILED,
                    extraction_results=[],
                    filling_result=None,
                    output_files=[],
                    processing_time=time.time() - start_time,
                    errors=validation_errors,
                    metadata={}
                )
            
            # Step 1: Extract data from input files
            for file_path in job.input_files:
                try:
                    self.logger.info(f"Processing file: {file_path}")
                    
                    # Find appropriate extractor
                    extractor = self.get_extractor_for_document(file_path, job.document_type)
                    if not extractor:
                        error = f"No extractor found for file: {file_path}"
                        errors.append(error)
                        self.logger.error(error)
                        continue
                    
                    # Extract data
                    extraction_result = extractor.extract(file_path)
                    extraction_results.append(extraction_result)
                    
                    # Save extraction result if configured
                    if self.save_extraction_results:
                        result_file = self._save_extraction_result(extraction_result, job.output_dir, file_path)
                        if result_file:
                            output_files.append(result_file)
                    
                except Exception as e:
                    error = f"Error processing file {file_path}: {e}"
                    errors.append(error)
                    self.logger.error(error)
            
            # Step 2: Fill template if provided
            if job.template_path and extraction_results:
                try:
                    # Find appropriate filler
                    filler = self.get_filler_for_template(job.template_path)
                    if not filler:
                        error = f"No filler found for template: {job.template_path}"
                        errors.append(error)
                        self.logger.error(error)
                    else:
                        # Add field mappings if provided
                        if job.field_mappings:
                            filler.add_field_mappings(job.field_mappings)
                        
                        # Use the best extraction result (highest confidence)
                        best_extraction = max(extraction_results, key=lambda r: r.confidence_score)
                        
                        # Fill template
                        output_path = job.output_dir / f"filled_{job.template_path.name}"
                        filling_result = filler.fill_template(
                            job.template_path, 
                            best_extraction, 
                            output_path
                        )
                        
                        if filling_result.output_path:
                            output_files.append(filling_result.output_path)
                        
                except Exception as e:
                    error = f"Error filling template: {e}"
                    errors.append(error)
                    self.logger.error(error)
            
            # Step 3: Generate summary report
            summary_file = self._generate_summary_report(job, extraction_results, filling_result, job.output_dir)
            if summary_file:
                output_files.append(summary_file)
            
            # Determine overall status
            status = self._determine_status(extraction_results, filling_result, errors)
            
            result = ProcessingResult(
                job_id=job.job_id,
                status=status,
                extraction_results=extraction_results,
                filling_result=filling_result,
                output_files=output_files,
                processing_time=time.time() - start_time,
                errors=errors,
                metadata={
                    'files_processed': len(job.input_files),
                    'successful_extractions': sum(1 for r in extraction_results if r.status == ExtractionStatus.SUCCESS),
                    'template_filled': filling_result is not None and filling_result.status == FillingStatus.SUCCESS
                }
            )
            
            self.logger.info(f"Completed processing job {job.job_id} with status {status.value}")
            return result
            
        except Exception as e:
            error = f"Unexpected error in processing job {job.job_id}: {e}"
            self.logger.error(error)
            
            return ProcessingResult(
                job_id=job.job_id,
                status=PipelineStatus.FAILED,
                extraction_results=extraction_results,
                filling_result=filling_result,
                output_files=output_files,
                processing_time=time.time() - start_time,
                errors=errors + [error],
                metadata={}
            )
    
    def process_single_file(
        self, 
        file_path: Path, 
        output_dir: Optional[Path] = None,
        document_type: Optional[DocumentType] = None
    ) -> ProcessingResult:
        """
        Process a single file (convenience method).
        
        Args:
            file_path: Path to the file to process
            output_dir: Output directory (defaults to file's directory)
            document_type: Optional document type hint
            
        Returns:
            Processing result
        """
        if output_dir is None:
            output_dir = file_path.parent / "output"
        
        job = ProcessingJob(
            job_id=f"single_file_{int(time.time())}",
            input_files=[file_path],
            template_path=None,
            output_dir=output_dir,
            document_type=document_type
        )
        
        return self.process_job(job)
    
    def _save_extraction_result(self, result: ExtractionResult, output_dir: Path, source_file: Path) -> Optional[Path]:
        """Save extraction result to file."""
        try:
            output_file = output_dir / f"{source_file.stem}_extraction.json"
            
            # Convert result to serializable format
            result_dict = {
                'document_type': result.document_type.value,
                'status': result.status.value,
                'confidence_score': result.confidence_score,
                'processing_time': result.processing_time,
                'errors': result.errors,
                'metadata': result.metadata,
                'extracted_fields': [
                    {
                        'name': field.name,
                        'value': field.value,
                        'confidence': field.confidence,
                        'raw_text': field.raw_text,
                        'validation_status': field.validation_status
                    }
                    for field in result.extracted_fields
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result_dict, f, indent=2, ensure_ascii=False, default=str)
            
            return output_file
            
        except Exception as e:
            self.logger.error(f"Error saving extraction result: {e}")
            return None
    
    def _generate_summary_report(
        self, 
        job: ProcessingJob, 
        extraction_results: List[ExtractionResult],
        filling_result: Optional[FillingResult],
        output_dir: Path
    ) -> Optional[Path]:
        """Generate a summary report for the processing job."""
        try:
            report_file = output_dir / f"processing_summary_{job.job_id}.json"
            
            summary = {
                'job_id': job.job_id,
                'timestamp': datetime.now().isoformat(),
                'input_files': [str(f) for f in job.input_files],
                'template_path': str(job.template_path) if job.template_path else None,
                'extraction_summary': {
                    'total_files': len(job.input_files),
                    'successful_extractions': sum(1 for r in extraction_results if r.status == ExtractionStatus.SUCCESS),
                    'failed_extractions': sum(1 for r in extraction_results if r.status == ExtractionStatus.FAILED),
                    'partial_extractions': sum(1 for r in extraction_results if r.status == ExtractionStatus.PARTIAL),
                    'average_confidence': sum(r.confidence_score for r in extraction_results) / len(extraction_results) if extraction_results else 0.0
                },
                'filling_summary': {
                    'template_filled': filling_result is not None,
                    'filling_status': filling_result.status.value if filling_result else None,
                    'filled_fields': len(filling_result.filled_fields) if filling_result else 0,
                    'filling_confidence': filling_result.confidence_score if filling_result else 0.0
                } if filling_result else None
            }
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            return report_file
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            return None
    
    def _determine_status(
        self, 
        extraction_results: List[ExtractionResult],
        filling_result: Optional[FillingResult],
        errors: List[str]
    ) -> PipelineStatus:
        """Determine overall pipeline status."""
        if not extraction_results:
            return PipelineStatus.FAILED
        
        # Check extraction results
        successful_extractions = sum(1 for r in extraction_results if r.status == ExtractionStatus.SUCCESS)
        failed_extractions = sum(1 for r in extraction_results if r.status == ExtractionStatus.FAILED)
        
        if failed_extractions == len(extraction_results):
            return PipelineStatus.FAILED
        
        # Check filling result if applicable
        filling_failed = filling_result and filling_result.status == FillingStatus.FAILED
        
        if errors or failed_extractions > 0 or filling_failed:
            return PipelineStatus.PARTIAL
        
        return PipelineStatus.SUCCESS
    
    def get_supported_document_types(self) -> List[DocumentType]:
        """Get all supported document types."""
        types = set()
        for extractor in self.extractors:
            types.update(extractor.supported_document_types)
        return list(types)
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            'extractors_registered': len(self.extractors),
            'fillers_registered': len(self.fillers),
            'supported_document_types': [t.value for t in self.get_supported_document_types()],
            'max_file_size_mb': self.max_file_size / (1024 * 1024),
            'processing_timeout_seconds': self.processing_timeout,
            'accuracy_reporting_enabled': self.enable_accuracy_reporting
        }
    
    def process_with_accuracy_reporting(
        self,
        job: ProcessingJob,
        expected_values_map: Dict[str, Dict[str, Any]]
    ) -> Tuple[ProcessingResult, List[Any]]:
        """
        Process a job with accuracy reporting against expected values.
        
        Args:
            job: Processing job configuration
            expected_values_map: Map of file paths to expected values for accuracy testing
            
        Returns:
            Tuple of (processing result, accuracy reports)
        """
        # Process the job normally
        processing_result = self.process_job(job)
        
        accuracy_reports = []
        
        if self.accuracy_reporter and expected_values_map:
            # Generate accuracy reports for extraction results
            for i, extraction_result in enumerate(processing_result.extraction_results):
                if i < len(job.input_files):
                    file_path = str(job.input_files[i])
                    expected_values = expected_values_map.get(file_path, {})
                    
                    if expected_values:
                        accuracy_report = self.accuracy_reporter.compare_extraction_results(
                            extraction_result,
                            expected_values,
                            f"{job.job_id}_{file_path}"
                        )
                        accuracy_reports.append(accuracy_report)
        
        return processing_result, accuracy_reports
    
    def get_confidence_statistics(self, extraction_results: List[ExtractionResult]) -> Dict[str, float]:
        """
        Calculate confidence statistics for extraction results.
        
        Args:
            extraction_results: List of extraction results
            
        Returns:
            Dictionary with confidence statistics
        """
        if not extraction_results:
            return {
                'avg_confidence': 0.0,
                'min_confidence': 0.0,
                'max_confidence': 0.0,
                'high_confidence_count': 0,
                'low_confidence_count': 0
            }
        
        confidences = [result.confidence_score for result in extraction_results]
        
        avg_confidence = sum(confidences) / len(confidences)
        min_confidence = min(confidences)
        max_confidence = max(confidences)
        
        # Count high/low confidence results (using 0.8 as threshold)
        high_threshold = 0.8
        low_threshold = 0.5
        
        high_confidence_count = sum(1 for c in confidences if c >= high_threshold)
        low_confidence_count = sum(1 for c in confidences if c <= low_threshold)
        
        return {
            'avg_confidence': avg_confidence,
            'min_confidence': min_confidence,
            'max_confidence': max_confidence,
            'high_confidence_count': high_confidence_count,
            'low_confidence_count': low_confidence_count,
            'high_confidence_percentage': (high_confidence_count / len(confidences)) * 100,
            'low_confidence_percentage': (low_confidence_count / len(confidences)) * 100
        }