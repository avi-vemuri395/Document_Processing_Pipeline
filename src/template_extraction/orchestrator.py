"""
Orchestrator for the template-based extraction pipeline.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from .registry import TemplateRegistry
from .extractors import AcroFormExtractor, AnchorExtractor, CheckboxExtractor, DateExtractor
from .extractors.base import ExtractionResult
from .normalizers import FieldNormalizer
from .models import FormSpec


class ExtractionOrchestrator:
    """
    Orchestrates the complete extraction pipeline.
    Manages extractors, normalizers, and result persistence.
    """
    
    def __init__(self, 
                 specs_dir: Optional[Path] = None,
                 output_dir: Optional[Path] = None,
                 cache_enabled: bool = True):
        """
        Initialize the orchestrator.
        
        Args:
            specs_dir: Directory containing form specs
            output_dir: Directory for output files
            cache_enabled: Whether to enable caching
        """
        self.registry = TemplateRegistry(specs_dir)
        self.output_dir = output_dir or Path("outputs/applications")
        self.cache_enabled = cache_enabled
        
        # Initialize extractors
        self.extractors = [
            AcroFormExtractor(),  # Try AcroForm first (fastest)
            CheckboxExtractor(),  # Handle checkboxes/radio buttons
            DateExtractor(),      # Extract date fields
            AnchorExtractor(),    # Then try anchor-based
        ]
        
        # Initialize normalizer
        self.normalizer = FieldNormalizer()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Stats tracking
        self.stats = {
            'documents_processed': 0,
            'total_fields_extracted': 0,
            'total_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def process_document(self,
                        pdf_path: Path,
                        form_id: Optional[str] = None,
                        application_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single document through the extraction pipeline.
        
        Args:
            pdf_path: Path to the PDF document
            form_id: Optional form ID (auto-detected if not provided)
            application_id: Optional application ID for grouping
            
        Returns:
            Complete extraction results
        """
        start_time = time.time()
        pdf_path = Path(pdf_path)
        
        print(f"\n{'='*70}")
        print(f"📋 TEMPLATE-BASED EXTRACTION PIPELINE")
        print(f"{'='*70}")
        print(f"Document: {pdf_path.name}")
        
        # Check cache first
        if self.cache_enabled:
            cached = self._check_cache(pdf_path)
            if cached:
                print(f"✅ Using cached results")
                self.stats['cache_hits'] += 1
                return cached
        
        self.stats['cache_misses'] += 1
        
        # Get or detect form spec
        if form_id:
            spec = self.registry.get_spec(form_id)
            if not spec:
                raise ValueError(f"Form spec not found: {form_id}")
        else:
            spec = self.registry.match_form(pdf_path)
            if not spec:
                raise ValueError(f"Could not match form spec for: {pdf_path.name}")
        
        print(f"Form: {spec.form_title} (v{spec.version})")
        print(f"Fields: {len(spec.fields)} defined")
        print("-" * 70)
        
        # Run extraction pipeline
        extraction_result = self._run_extraction_pipeline(pdf_path, spec)
        
        # Normalize all fields
        print(f"\n📝 Normalizing fields...")
        for field_id, field_result in extraction_result.fields.items():
            field_spec = spec.get_field_by_id(field_id)
            if field_spec:
                self.normalizer.normalize_field(field_spec, field_result)
        
        # Create final result
        result = self._create_final_result(extraction_result, spec, application_id)
        
        # Save results
        self._save_results(result, pdf_path, application_id)
        
        # Cache results
        if self.cache_enabled:
            self._cache_results(pdf_path, result)
        
        # Update stats
        elapsed = time.time() - start_time
        self.stats['documents_processed'] += 1
        self.stats['total_fields_extracted'] += len(extraction_result.fields)
        self.stats['total_time'] += elapsed
        
        # Print summary
        self._print_summary(result, elapsed)
        
        return result
    
    def _run_extraction_pipeline(self, pdf_path: Path, spec: FormSpec) -> ExtractionResult:
        """
        Run all extractors in sequence, merging results.
        
        Args:
            pdf_path: Path to PDF
            spec: Form specification
            
        Returns:
            Merged extraction results
        """
        # Create base result
        merged_result = ExtractionResult(
            doc_id=self._generate_doc_id(pdf_path),
            doc_path=str(pdf_path),
            form_id=spec.form_id
        )
        
        # Track which fields have been extracted
        extracted_fields = set()
        
        # Run each extractor
        for extractor in self.extractors:
            print(f"\n🔧 Running {extractor.name} extractor...")
            
            # Only extract fields not yet extracted
            remaining_fields = [
                f.id for f in spec.fields 
                if f.id not in extracted_fields and extractor.supports_field(f)
            ]
            
            if not remaining_fields:
                print(f"  ⏭️  No remaining fields for this extractor")
                continue
            
            # Run extraction
            result = extractor.extract(pdf_path, spec, remaining_fields)
            
            # Merge results
            for field_id, field_result in result.fields.items():
                if field_result.selected_value is not None:
                    merged_result.add_field_result(field_result)
                    extracted_fields.add(field_id)
            
            # Merge errors
            merged_result.errors.extend(result.errors)
        
        return merged_result
    
    def _create_final_result(self, 
                           extraction_result: ExtractionResult,
                           spec: FormSpec,
                           application_id: Optional[str]) -> Dict[str, Any]:
        """
        Create the final result dictionary.
        
        Args:
            extraction_result: Raw extraction results
            spec: Form specification  
            application_id: Application ID
            
        Returns:
            Final result dictionary
        """
        # Get all values
        values = {}
        for field_id, field_result in extraction_result.fields.items():
            if field_result.normalized_value is not None:
                values[field_result.field_name] = field_result.normalized_value
            elif field_result.selected_value is not None:
                values[field_result.field_name] = field_result.selected_value
        
        # Calculate metrics
        total_fields = len(spec.fields)
        extracted_fields = len([f for f in extraction_result.fields.values() if f.selected_value])
        required_fields = [f for f in spec.fields if f.required]
        required_extracted = len([
            f for f in extraction_result.fields.values() 
            if f.field_id in [rf.id for rf in required_fields] and f.selected_value
        ])
        
        return {
            'application_id': application_id or extraction_result.doc_id,
            'document': {
                'path': extraction_result.doc_path,
                'id': extraction_result.doc_id,
                'processed_at': extraction_result.timestamp
            },
            'form': {
                'id': spec.form_id,
                'title': spec.form_title,
                'version': spec.version
            },
            'extracted_fields': values,
            'field_details': {
                field_id: {
                    'value': field_result.normalized_value or field_result.selected_value,
                    'candidates': [
                        {
                            'value': c.value,
                            'confidence': c.confidence,
                            'method': c.source.get('method')
                        } for c in field_result.candidates
                    ],
                    'validation_errors': field_result.validation_errors
                }
                for field_id, field_result in extraction_result.fields.items()
            },
            'metrics': {
                'total_fields': total_fields,
                'extracted_fields': extracted_fields,
                'coverage_percentage': (extracted_fields / total_fields * 100) if total_fields > 0 else 0,
                'required_fields': len(required_fields),
                'required_extracted': required_extracted,
                'required_coverage': (required_extracted / len(required_fields) * 100) if required_fields else 100
            },
            'errors': extraction_result.errors,
            'metadata': extraction_result.metadata
        }
    
    def _save_results(self, result: Dict[str, Any], pdf_path: Path, application_id: Optional[str]) -> None:
        """Save extraction results to JSON files."""
        # Create application directory
        app_id = application_id or result['application_id']
        app_dir = self.output_dir / app_id
        app_dir.mkdir(exist_ok=True)
        
        # Save raw extraction
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_file = app_dir / f"extraction_{pdf_path.stem}_{timestamp}.json"
        with open(raw_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        # Save/update canonical JSON
        canonical_file = app_dir / "canonical.json"
        if canonical_file.exists():
            with open(canonical_file, 'r') as f:
                canonical = json.load(f)
        else:
            canonical = {
                'application_id': app_id,
                'created_at': datetime.now().isoformat(),
                'documents': [],
                'merged_data': {}
            }
        
        # Add this document
        canonical['documents'].append({
            'filename': pdf_path.name,
            'processed_at': result['document']['processed_at'],
            'extracted_fields': len(result['extracted_fields'])
        })
        
        # Merge extracted data (simple overwrite for now)
        canonical['merged_data'].update(result['extracted_fields'])
        canonical['last_updated'] = datetime.now().isoformat()
        
        with open(canonical_file, 'w') as f:
            json.dump(canonical, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {app_dir}")
    
    def _check_cache(self, pdf_path: Path) -> Optional[Dict[str, Any]]:
        """Check if results are cached."""
        if not self.cache_enabled:
            return None
        
        cache_dir = self.output_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        # Generate cache key
        cache_key = self._get_cache_key(pdf_path)
        cache_file = cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return None
    
    def _cache_results(self, pdf_path: Path, result: Dict[str, Any]) -> None:
        """Cache extraction results."""
        cache_dir = self.output_dir / "cache"
        cache_dir.mkdir(exist_ok=True)
        
        cache_key = self._get_cache_key(pdf_path)
        cache_file = cache_dir / f"{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
    
    def _get_cache_key(self, pdf_path: Path) -> str:
        """Generate cache key for a PDF."""
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
        return f"{pdf_path.stem}_{file_hash[:8]}"
    
    def _generate_doc_id(self, pdf_path: Path) -> str:
        """Generate unique document ID."""
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        return f"{pdf_path.stem}_{file_hash}"
    
    def _print_summary(self, result: Dict[str, Any], elapsed: float) -> None:
        """Print extraction summary."""
        metrics = result['metrics']
        
        print(f"\n{'='*70}")
        print(f"📊 EXTRACTION SUMMARY")
        print(f"{'='*70}")
        print(f"✅ Extracted: {metrics['extracted_fields']}/{metrics['total_fields']} fields")
        print(f"📈 Coverage: {metrics['coverage_percentage']:.1f}%")
        print(f"⭐ Required: {metrics['required_extracted']}/{metrics['required_fields']} ({metrics['required_coverage']:.1f}%)")
        print(f"⏱️  Time: {elapsed:.2f} seconds")
        
        if result['errors']:
            print(f"\n⚠️  Errors:")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        print(f"{'='*70}\n")
    
    def process_batch(self, 
                     pdf_paths: List[Path],
                     form_id: Optional[str] = None,
                     application_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process multiple documents.
        
        Args:
            pdf_paths: List of PDF paths
            form_id: Optional form ID
            application_id: Optional application ID
            
        Returns:
            List of extraction results
        """
        results = []
        for pdf_path in pdf_paths:
            try:
                result = self.process_document(pdf_path, form_id, application_id)
                results.append(result)
            except Exception as e:
                print(f"❌ Failed to process {pdf_path.name}: {e}")
                results.append({
                    'document': str(pdf_path),
                    'error': str(e)
                })
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        stats = dict(self.stats)
        
        # Add extractor stats
        for extractor in self.extractors:
            stats[f'{extractor.name}_stats'] = extractor.stats
        
        # Add normalizer stats
        stats['normalizer_stats'] = self.normalizer.stats
        
        # Calculate averages
        if stats['documents_processed'] > 0:
            stats['avg_fields_per_doc'] = stats['total_fields_extracted'] / stats['documents_processed']
            stats['avg_time_per_doc'] = stats['total_time'] / stats['documents_processed']
        
        return stats