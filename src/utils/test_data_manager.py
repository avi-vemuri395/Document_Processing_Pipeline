"""
Test data manager for synthetic data generation and management.

This module provides utilities for managing synthetic test datasets,
including generation, storage, retrieval, and cleanup operations.
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

from ..generators.base import DocumentSet, GenerationResult

logger = logging.getLogger(__name__)


class TestDataManager:
    """Manager for synthetic test data lifecycle."""
    
    def __init__(self, base_path: Path, config: Optional[Dict[str, Any]] = None):
        """
        Initialize test data manager.
        
        Args:
            base_path: Base directory for test data storage
            config: Configuration options
        """
        self.base_path = Path(base_path)
        self.config = config or {}
        
        # Create base directory structure
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Configure retention settings
        self.max_datasets = self.config.get('max_datasets', 50)
        self.retention_days = self.config.get('retention_days', 30)
        
        # Create subdirectories
        self.datasets_dir = self.base_path / "datasets"
        self.reports_dir = self.base_path / "reports"
        self.metadata_dir = self.base_path / "metadata"
        
        for dir_path in [self.datasets_dir, self.reports_dir, self.metadata_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def store_generated_data(
        self, 
        generation_result: GenerationResult,
        dataset_name: Optional[str] = None
    ) -> str:
        """
        Store generated data and return dataset ID.
        
        Args:
            generation_result: Result from data generation
            dataset_name: Optional name for the dataset
            
        Returns:
            Unique dataset ID
        """
        # Generate unique dataset ID
        if dataset_name:
            dataset_id = f"{dataset_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            dataset_id = f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        dataset_dir = self.datasets_dir / dataset_id
        dataset_dir.mkdir(exist_ok=True)
        
        try:
            # Store dataset metadata
            dataset_metadata = {
                'dataset_id': dataset_id,
                'creation_timestamp': datetime.now().isoformat(),
                'generation_status': generation_result.status.value,
                'generation_time': generation_result.generation_time,
                'num_document_sets': len(generation_result.document_sets),
                'errors': generation_result.errors,
                'metadata': generation_result.metadata,
                'document_sets': []
            }
            
            # Process each document set
            for doc_set in generation_result.document_sets:
                doc_set_info = self._store_document_set(doc_set, dataset_dir)
                dataset_metadata['document_sets'].append(doc_set_info)
            
            # Save dataset metadata
            metadata_file = dataset_dir / "dataset_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(dataset_metadata, f, indent=2, ensure_ascii=False, default=str)
            
            # Update index
            self._update_dataset_index(dataset_id, dataset_metadata)
            
            logger.info(f"Stored dataset {dataset_id} with {len(generation_result.document_sets)} document sets")
            return dataset_id
            
        except Exception as e:
            logger.error(f"Error storing dataset {dataset_id}: {e}")
            # Clean up partial dataset
            if dataset_dir.exists():
                shutil.rmtree(dataset_dir)
            raise
    
    def _store_document_set(self, doc_set: DocumentSet, dataset_dir: Path) -> Dict[str, Any]:
        """Store individual document set within dataset."""
        doc_set_dir = dataset_dir / doc_set.application_id
        doc_set_dir.mkdir(exist_ok=True)
        
        # Copy or move files to dataset directory
        stored_files = {}
        for doc_name, file_path in doc_set.files.items():
            if file_path.exists():
                target_path = doc_set_dir / file_path.name
                shutil.copy2(file_path, target_path)
                stored_files[doc_name] = str(target_path.relative_to(dataset_dir))
            else:
                logger.warning(f"Source file does not exist: {file_path}")
        
        # Store document set metadata
        doc_set_metadata = {
            'application_id': doc_set.application_id,
            'document_type': doc_set.document_type,
            'files': stored_files,
            'metadata': doc_set.metadata,
            'expected_values': doc_set.expected_values,
            'generation_timestamp': doc_set.generation_timestamp.isoformat()
        }
        
        metadata_file = doc_set_dir / "document_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(doc_set_metadata, f, indent=2, ensure_ascii=False, default=str)
        
        return {
            'application_id': doc_set.application_id,
            'document_type': doc_set.document_type,
            'num_files': len(stored_files),
            'directory': str(doc_set_dir.relative_to(dataset_dir))
        }
    
    def _update_dataset_index(self, dataset_id: str, metadata: Dict[str, Any]) -> None:
        """Update the dataset index file."""
        index_file = self.metadata_dir / "dataset_index.json"
        
        # Load existing index
        index_data = {}
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load dataset index: {e}")
        
        # Add new dataset
        index_data[dataset_id] = {
            'creation_timestamp': metadata['creation_timestamp'],
            'generation_status': metadata['generation_status'],
            'num_document_sets': metadata['num_document_sets'],
            'has_errors': len(metadata['errors']) > 0,
            'dataset_path': str(self.datasets_dir / dataset_id)
        }
        
        # Save updated index
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False, default=str)
    
    def list_datasets(self, include_metadata: bool = False) -> List[Dict[str, Any]]:
        """
        List available datasets.
        
        Args:
            include_metadata: Whether to include detailed metadata
            
        Returns:
            List of dataset information
        """
        datasets = []
        
        index_file = self.metadata_dir / "dataset_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                for dataset_id, info in index_data.items():
                    dataset_info = {
                        'dataset_id': dataset_id,
                        **info
                    }
                    
                    if include_metadata:
                        metadata_file = Path(info['dataset_path']) / "dataset_metadata.json"
                        if metadata_file.exists():
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                detailed_metadata = json.load(f)
                                dataset_info['detailed_metadata'] = detailed_metadata
                    
                    datasets.append(dataset_info)
                
            except Exception as e:
                logger.error(f"Error loading dataset index: {e}")
        
        # Sort by creation time (newest first)
        datasets.sort(key=lambda x: x['creation_timestamp'], reverse=True)
        
        return datasets
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific dataset.
        
        Args:
            dataset_id: ID of the dataset to retrieve
            
        Returns:
            Dataset information or None if not found
        """
        dataset_dir = self.datasets_dir / dataset_id
        metadata_file = dataset_dir / "dataset_metadata.json"
        
        if not metadata_file.exists():
            logger.warning(f"Dataset metadata not found: {dataset_id}")
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading dataset {dataset_id}: {e}")
            return None
    
    def get_document_set(self, dataset_id: str, application_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific document set.
        
        Args:
            dataset_id: ID of the dataset
            application_id: ID of the application/document set
            
        Returns:
            Document set information or None if not found
        """
        doc_set_dir = self.datasets_dir / dataset_id / application_id
        metadata_file = doc_set_dir / "document_metadata.json"
        
        if not metadata_file.exists():
            logger.warning(f"Document set metadata not found: {dataset_id}/{application_id}")
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                doc_set_data = json.load(f)
            
            # Add full file paths
            for doc_name, relative_path in doc_set_data['files'].items():
                full_path = doc_set_dir / Path(relative_path).name
                doc_set_data['files'][doc_name] = str(full_path)
            
            return doc_set_data
            
        except Exception as e:
            logger.error(f"Error loading document set {dataset_id}/{application_id}: {e}")
            return None
    
    def get_expected_values(self, dataset_id: str, application_id: str) -> Optional[Dict[str, Any]]:
        """
        Get expected values for a document set (for testing).
        
        Args:
            dataset_id: ID of the dataset
            application_id: ID of the application/document set
            
        Returns:
            Expected values or None if not found
        """
        doc_set_data = self.get_document_set(dataset_id, application_id)
        if doc_set_data:
            return doc_set_data.get('expected_values')
        return None
    
    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset and all its files.
        
        Args:
            dataset_id: ID of the dataset to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            dataset_dir = self.datasets_dir / dataset_id
            if dataset_dir.exists():
                shutil.rmtree(dataset_dir)
            
            # Update index
            index_file = self.metadata_dir / "dataset_index.json"
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                if dataset_id in index_data:
                    del index_data[dataset_id]
                    
                    with open(index_file, 'w', encoding='utf-8') as f:
                        json.dump(index_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Deleted dataset {dataset_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting dataset {dataset_id}: {e}")
            return False
    
    def cleanup_old_datasets(self) -> int:
        """
        Clean up old datasets based on retention settings.
        
        Returns:
            Number of datasets cleaned up
        """
        datasets = self.list_datasets()
        cleaned_count = 0
        
        # Sort by creation time (oldest first)
        datasets.sort(key=lambda x: x['creation_timestamp'])
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for dataset in datasets:
            creation_time = datetime.fromisoformat(dataset['creation_timestamp'].replace('Z', '+00:00'))
            
            # Delete if older than retention period or if we exceed max datasets
            should_delete = (
                creation_time < cutoff_date or 
                (len(datasets) - cleaned_count > self.max_datasets)
            )
            
            if should_delete:
                if self.delete_dataset(dataset['dataset_id']):
                    cleaned_count += 1
                    logger.info(f"Cleaned up old dataset: {dataset['dataset_id']}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old datasets")
        
        return cleaned_count
    
    def get_dataset_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored datasets.
        
        Returns:
            Statistics dictionary
        """
        datasets = self.list_datasets(include_metadata=True)
        
        total_datasets = len(datasets)
        total_document_sets = sum(d['num_document_sets'] for d in datasets)
        
        # Calculate storage usage
        total_size = 0
        for dataset in datasets:
            dataset_path = Path(dataset['dataset_path'])
            if dataset_path.exists():
                for file_path in dataset_path.rglob('*'):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
        
        # Generation status breakdown
        status_counts = {}
        for dataset in datasets:
            status = dataset['generation_status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Document type breakdown
        document_type_counts = {}
        for dataset in datasets:
            if 'detailed_metadata' in dataset:
                for doc_set in dataset['detailed_metadata'].get('document_sets', []):
                    doc_type = doc_set.get('document_type', 'unknown')
                    document_type_counts[doc_type] = document_type_counts.get(doc_type, 0) + 1
        
        return {
            'total_datasets': total_datasets,
            'total_document_sets': total_document_sets,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'status_breakdown': status_counts,
            'document_type_breakdown': document_type_counts,
            'oldest_dataset': min((d['creation_timestamp'] for d in datasets), default=None),
            'newest_dataset': max((d['creation_timestamp'] for d in datasets), default=None)
        }
    
    def export_dataset_manifest(self, dataset_id: str, output_path: Path) -> bool:
        """
        Export a complete manifest of a dataset.
        
        Args:
            dataset_id: ID of the dataset to export
            output_path: Path to save the manifest
            
        Returns:
            True if export was successful
        """
        try:
            dataset_data = self.get_dataset(dataset_id)
            if not dataset_data:
                logger.error(f"Dataset not found: {dataset_id}")
                return False
            
            # Enhance with file information
            dataset_dir = self.datasets_dir / dataset_id
            enhanced_data = dataset_data.copy()
            
            for doc_set_info in enhanced_data['document_sets']:
                app_id = doc_set_info['application_id']
                doc_set_data = self.get_document_set(dataset_id, app_id)
                
                if doc_set_data:
                    # Add file sizes and checksums
                    file_details = {}
                    for doc_name, file_path in doc_set_data['files'].items():
                        file_path_obj = Path(file_path)
                        if file_path_obj.exists():
                            import hashlib
                            
                            # Calculate file size and checksum
                            file_size = file_path_obj.stat().st_size
                            
                            with open(file_path_obj, 'rb') as f:
                                checksum = hashlib.md5(f.read()).hexdigest()
                            
                            file_details[doc_name] = {
                                'path': str(file_path),
                                'size_bytes': file_size,
                                'md5_checksum': checksum
                            }
                    
                    doc_set_info['file_details'] = file_details
            
            # Save manifest
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported dataset manifest: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting dataset manifest: {e}")
            return False
    
    def validate_dataset_integrity(self, dataset_id: str) -> Dict[str, Any]:
        """
        Validate the integrity of a dataset.
        
        Args:
            dataset_id: ID of the dataset to validate
            
        Returns:
            Validation report
        """
        validation_report = {
            'dataset_id': dataset_id,
            'validation_timestamp': datetime.now().isoformat(),
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'statistics': {}
        }
        
        try:
            dataset_data = self.get_dataset(dataset_id)
            if not dataset_data:
                validation_report['is_valid'] = False
                validation_report['errors'].append("Dataset metadata not found")
                return validation_report
            
            dataset_dir = self.datasets_dir / dataset_id
            total_files = 0
            missing_files = 0
            empty_files = 0
            
            # Validate each document set
            for doc_set_info in dataset_data.get('document_sets', []):
                app_id = doc_set_info['application_id']
                doc_set_data = self.get_document_set(dataset_id, app_id)
                
                if not doc_set_data:
                    validation_report['errors'].append(f"Document set metadata missing: {app_id}")
                    validation_report['is_valid'] = False
                    continue
                
                # Check files exist
                for doc_name, file_path in doc_set_data.get('files', {}).items():
                    total_files += 1
                    file_path_obj = Path(file_path)
                    
                    if not file_path_obj.exists():
                        missing_files += 1
                        validation_report['errors'].append(f"Missing file: {file_path}")
                        validation_report['is_valid'] = False
                    elif file_path_obj.stat().st_size == 0:
                        empty_files += 1
                        validation_report['warnings'].append(f"Empty file: {file_path}")
                
                # Validate expected values exist
                if not doc_set_data.get('expected_values'):
                    validation_report['warnings'].append(f"No expected values for testing: {app_id}")
            
            validation_report['statistics'] = {
                'total_document_sets': len(dataset_data.get('document_sets', [])),
                'total_files': total_files,
                'missing_files': missing_files,
                'empty_files': empty_files
            }
            
            if missing_files > 0 or empty_files > 0:
                validation_report['warnings'].append(f"Dataset has {missing_files} missing files and {empty_files} empty files")
            
        except Exception as e:
            validation_report['is_valid'] = False
            validation_report['errors'].append(f"Validation error: {e}")
        
        return validation_report