"""
Template registry for managing form specifications.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Any
from .models import FormSpec, FieldSpec


class TemplateRegistry:
    """Registry for loading and managing form template specifications."""
    
    def __init__(self, specs_dir: Optional[Path] = None):
        """
        Initialize the registry.
        
        Args:
            specs_dir: Directory containing form spec JSON files
        """
        self.specs_dir = specs_dir or Path("templates/form_specs")
        self.specs: Dict[str, FormSpec] = {}
        self._load_all_specs()
    
    def _load_all_specs(self) -> None:
        """Load all form specs from the specs directory."""
        if not self.specs_dir.exists():
            print(f"⚠️ Specs directory not found: {self.specs_dir}")
            return
        
        for spec_file in self.specs_dir.glob("*.json"):
            try:
                spec = self.load_spec_from_file(spec_file)
                if spec:
                    self.specs[spec.form_id] = spec
                    print(f"✅ Loaded spec: {spec.form_id} v{spec.version}")
            except Exception as e:
                print(f"❌ Failed to load spec {spec_file.name}: {e}")
    
    def load_spec_from_file(self, spec_path: Path) -> Optional[FormSpec]:
        """
        Load a form spec from a JSON file.
        
        Args:
            spec_path: Path to the spec JSON file
            
        Returns:
            FormSpec object or None if loading failed
        """
        try:
            with open(spec_path, 'r') as f:
                spec_data = json.load(f)
            
            # Validate required fields
            required = ['form_id', 'version', 'fields']
            for field in required:
                if field not in spec_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create FormSpec object
            return FormSpec(**spec_data)
            
        except Exception as e:
            print(f"Error loading spec from {spec_path}: {e}")
            return None
    
    def get_spec(self, form_id: str) -> Optional[FormSpec]:
        """
        Get a form spec by ID.
        
        Args:
            form_id: The form identifier
            
        Returns:
            FormSpec object or None if not found
        """
        return self.specs.get(form_id)
    
    def match_form(self, pdf_path: Path) -> Optional[FormSpec]:
        """
        Match a PDF to a form spec based on fingerprint.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Matched FormSpec or None
        """
        # For now, simple matching based on filename
        # TODO: Implement proper fingerprint matching with page count, text hash, etc.
        
        pdf_name = pdf_path.stem.lower()
        
        # Check for exact matches first
        for form_id, spec in self.specs.items():
            if form_id.lower() in pdf_name:
                return spec
            
            # Check form title
            if spec.form_title and spec.form_title.lower() in pdf_name:
                return spec
        
        # Check for partial matches
        if 'live oak' in pdf_name:
            return self.get_spec('live_oak_application')
        elif 'huntington' in pdf_name:
            return self.get_spec('huntington_pfs')
        
        # Default to first available spec for testing
        if self.specs:
            first_spec = list(self.specs.values())[0]
            print(f"⚠️ No exact match found for {pdf_path.name}, using {first_spec.form_id}")
            return first_spec
        
        return None
    
    def list_specs(self) -> List[str]:
        """List all available form spec IDs."""
        return list(self.specs.keys())
    
    def reload(self) -> None:
        """Reload all specs from disk."""
        self.specs.clear()
        self._load_all_specs()
    
    def validate_spec(self, spec: FormSpec) -> List[str]:
        """
        Validate a form spec for completeness and correctness.
        
        Args:
            spec: FormSpec to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not spec.form_id:
            errors.append("Missing form_id")
        if not spec.version:
            errors.append("Missing version")
        if not spec.fields:
            errors.append("No fields defined")
        
        # Check field definitions
        field_ids = set()
        for field in spec.fields:
            if not field.id:
                errors.append(f"Field missing id: {field.field_name}")
            elif field.id in field_ids:
                errors.append(f"Duplicate field id: {field.id}")
            else:
                field_ids.add(field.id)
            
            if not field.field_name:
                errors.append(f"Field {field.id} missing field_name")
            
            # Check extraction config
            if field.extraction:
                if not any([
                    field.extraction.acroform,
                    field.extraction.anchors,
                    field.extraction.zones,
                    field.extraction.checkboxes
                ]):
                    errors.append(f"Field {field.id} has no extraction methods defined")
        
        return errors
    
    def get_required_fields(self, form_id: str) -> List[FieldSpec]:
        """Get all required fields for a form."""
        spec = self.get_spec(form_id)
        if not spec:
            return []
        return [f for f in spec.fields if f.required]
    
    def get_fields_by_type(self, form_id: str, field_type: str) -> List[FieldSpec]:
        """Get all fields of a specific type."""
        spec = self.get_spec(form_id)
        if not spec:
            return []
        return [f for f in spec.fields if f.type == field_type]