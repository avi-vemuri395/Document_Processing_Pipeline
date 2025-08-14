"""
Base abstract class for synthetic data generators.

This module defines the abstract interface that all synthetic data generators
must implement for creating realistic test documents.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GenerationStatus(Enum):
    """Status of document generation."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class DocumentSet:
    """Represents a set of related generated documents."""
    application_id: str
    document_type: str
    files: Dict[str, Path]  # document_name -> file_path
    metadata: Dict[str, Any]
    expected_values: Dict[str, Any]  # For testing - expected extraction results
    generation_timestamp: datetime
    
    def get_file(self, document_name: str) -> Optional[Path]:
        """Get file path for a specific document."""
        return self.files.get(document_name)
    
    def add_file(self, document_name: str, file_path: Path) -> None:
        """Add a file to the document set."""
        self.files[document_name] = file_path


@dataclass
class GenerationResult:
    """Result of document generation process."""
    status: GenerationStatus
    document_sets: List[DocumentSet]
    generation_time: float
    errors: List[str]
    metadata: Dict[str, Any]


class BaseGenerator(ABC):
    """
    Abstract base class for all synthetic data generators.
    
    This class defines the interface that all specific generators must implement.
    It provides common functionality for document generation and validation.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the generator.
        
        Args:
            config: Configuration dictionary for the generator
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_generator()
    
    def _setup_generator(self) -> None:
        """Setup generator-specific configuration and resources."""
        pass
    
    @property
    @abstractmethod
    def supported_document_types(self) -> List[str]:
        """Return list of document types this generator can create."""
        pass
    
    @property
    @abstractmethod
    def required_config_keys(self) -> List[str]:
        """Return list of required configuration keys."""
        pass
    
    @abstractmethod
    def generate(
        self, 
        output_dir: Path, 
        num_applications: int = 1,
        **kwargs
    ) -> GenerationResult:
        """
        Generate synthetic documents.
        
        Args:
            output_dir: Directory to save generated documents
            num_applications: Number of applications to generate
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResult containing generated documents and metadata
        """
        pass
    
    def validate_config(self) -> List[str]:
        """
        Validate generator configuration.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check required config keys
        for key in self.required_config_keys:
            if key not in self.config:
                errors.append(f"Missing required config key: {key}")
        
        return errors
    
    def create_metadata_file(
        self, 
        document_set: DocumentSet, 
        output_dir: Path
    ) -> Path:
        """
        Create metadata file for a document set.
        
        Args:
            document_set: Document set to create metadata for
            output_dir: Output directory
            
        Returns:
            Path to created metadata file
        """
        metadata_file = output_dir / document_set.application_id / "metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        import json
        
        metadata = {
            "application_id": document_set.application_id,
            "document_type": document_set.document_type,
            "files": {name: str(path) for name, path in document_set.files.items()},
            "metadata": document_set.metadata,
            "expected_values": document_set.expected_values,
            "generation_timestamp": document_set.generation_timestamp.isoformat(),
            "generator": self.__class__.__name__
        }
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        return metadata_file
    
    def load_templates(self, template_dir: Path) -> Dict[str, Any]:
        """
        Load templates from directory.
        
        Args:
            template_dir: Directory containing templates
            
        Returns:
            Dictionary of loaded templates
        """
        templates = {}
        
        if not template_dir.exists():
            self.logger.warning(f"Template directory does not exist: {template_dir}")
            return templates
        
        # Load JSON templates
        for json_file in template_dir.glob("*.json"):
            try:
                import json
                with open(json_file, 'r', encoding='utf-8') as f:
                    templates[json_file.stem] = json.load(f)
            except Exception as e:
                self.logger.error(f"Error loading template {json_file}: {e}")
        
        return templates
    
    def generate_realistic_data(self, data_type: str, **kwargs) -> Any:
        """
        Generate realistic data of specified type.
        
        Args:
            data_type: Type of data to generate (e.g., 'name', 'address', 'amount')
            **kwargs: Additional parameters for data generation
            
        Returns:
            Generated data
        """
        # This is a basic implementation - subclasses can override for more sophisticated generation
        from faker import Faker
        fake = Faker()
        
        generators = {
            'name': lambda: fake.name(),
            'business_name': lambda: fake.company(),
            'address': lambda: fake.address(),
            'phone': lambda: fake.phone_number(),
            'email': lambda: fake.email(),
            'ssn': lambda: fake.ssn(),
            'ein': lambda: fake.ein(),
            'amount': lambda: round(fake.random.uniform(1000, 500000), 2),
            'date': lambda: fake.date_this_year(),
            'account_number': lambda: fake.random_int(min=100000000, max=999999999),
            'routing_number': lambda: fake.random_int(min=100000000, max=999999999),
        }
        
        generator = generators.get(data_type)
        if generator:
            return generator()
        else:
            self.logger.warning(f"Unknown data type: {data_type}")
            return None
    
    def create_directory_structure(self, base_dir: Path, application_id: str) -> Path:
        """
        Create directory structure for generated documents.
        
        Args:
            base_dir: Base output directory
            application_id: Unique application identifier
            
        Returns:
            Path to created application directory
        """
        app_dir = base_dir / application_id
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for different document types
        (app_dir / "financial").mkdir(exist_ok=True)
        (app_dir / "tax_returns").mkdir(exist_ok=True)
        (app_dir / "bank_statements").mkdir(exist_ok=True)
        (app_dir / "reports").mkdir(exist_ok=True)
        
        return app_dir
    
    def validate_generated_documents(self, document_set: DocumentSet) -> List[str]:
        """
        Validate generated documents.
        
        Args:
            document_set: Document set to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check that all files exist
        for doc_name, file_path in document_set.files.items():
            if not file_path.exists():
                errors.append(f"Generated file does not exist: {file_path}")
            elif file_path.stat().st_size == 0:
                errors.append(f"Generated file is empty: {file_path}")
        
        # Check required metadata
        if not document_set.application_id:
            errors.append("Missing application_id in document set")
        
        if not document_set.expected_values:
            errors.append("Missing expected_values for testing")
        
        return errors
    
    def __str__(self) -> str:
        """String representation of the generator."""
        return f"{self.__class__.__name__}(types={self.supported_document_types})"
    
    def __repr__(self) -> str:
        """Detailed string representation of the generator."""
        return (f"{self.__class__.__name__}("
                f"supported_types={self.supported_document_types}, "
                f"config_keys={self.required_config_keys})")