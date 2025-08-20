"""
Form Schema Extractor - Convert existing form specs to OpenAI JSON Schema format
"""
import json
from pathlib import Path
from typing import Dict, Any


class FormSchemaExtractor:
    """Extract OpenAI JSON schemas from existing form specifications"""
    
    def __init__(self, form_specs_dir: Path = None):
        self.form_specs_dir = form_specs_dir or Path("templates/form_specs")
        self.form_specs = self._load_all_form_specs()
    
    def extract_all_openai_schemas(self) -> Dict[str, Dict]:
        """Convert all 9 form specs to OpenAI JSON Schema format"""
        schemas = {}
        
        print(f"Converting {len(self.form_specs)} form specs to OpenAI schemas...")
        
        for form_key, form_spec in self.form_specs.items():
            print(f"  Converting {form_key}...")
            schemas[form_key] = self._convert_to_openai_schema(form_spec, form_key)
        
        return schemas
    
    def _convert_to_openai_schema(self, form_spec: Dict, form_key: str) -> Dict:
        """Convert single form spec to OpenAI JSON Schema with semantic descriptions"""
        properties = {}
        required = []
        
        fields = form_spec.get('fields', [])
        print(f"    Processing {len(fields)} fields...")
        
        for field in fields:
            # Handle both formats: {'name': 'X'} and {'field_name': 'X', 'name': 'Y'}
            field_name = field.get('field_name') or field.get('name', '')
            if not field_name:
                continue
                
            # Create semantic property definition
            properties[field_name] = self._create_property_definition(field, form_key)
            
            if field.get('required', False):
                required.append(field_name)
        
        # OpenAI structured outputs with strict mode requires ALL properties in required array
        # Otherwise it throws validation errors
        all_fields_required = list(properties.keys())
        
        return {
            "type": "object",
            "properties": properties,
            "required": all_fields_required,  # Use all fields as required for OpenAI strict mode
            "additionalProperties": False,
            "description": f"Form schema for {form_spec.get('form_name', form_key)} - {form_spec.get('bank', 'Unknown Bank')}"
        }
    
    def _create_property_definition(self, field: Dict, form_key: str) -> Dict:
        """Create detailed property definition with semantic context"""
        field_type = field.get('type', 'text')
        field_name = field.get('field_name') or field.get('name', '')
        
        # Base property
        prop = {"type": "string"}  # Default to string, OpenAI handles validation
        
        # Add semantic description based on field name and type
        prop["description"] = self._generate_semantic_description(field_name, field_type, form_key)
        
        # Add format constraints for common field types
        if field_type == "email" or "email" in field_name.lower():
            prop["format"] = "email"
        elif field_type == "date" or "date" in field_name.lower():
            prop["pattern"] = r"^\d{2}/\d{2}/\d{4}$"
            prop["description"] += " Format: MM/DD/YYYY"
        elif field_type in ["money", "currency"] or any(word in field_name.lower() 
                                                       for word in ["amount", "revenue", "income"]):
            prop["pattern"] = r"^\$?[\d,]+\.?\d{0,2}$"
            prop["description"] += " Format: Dollar amount (e.g., $150,000.00)"
        elif "ssn" in field_name.lower() or "social security" in field_name.lower():
            prop["pattern"] = r"^\d{3}-\d{2}-\d{4}$|^XXX-XX-\d{4}$"
            prop["description"] += " Format: XXX-XX-1234 (masked) or 123-45-6789"
        elif "phone" in field_name.lower():
            prop["description"] += " Format: (555) 123-4567"
        elif "ein" in field_name.lower() or "tax id" in field_name.lower():
            prop["pattern"] = r"^\d{2}-\d{7}$"
            prop["description"] += " Format: 12-3456789"
        
        # Add enum values if available
        if field.get('options'):
            prop["enum"] = field['options']
        
        return prop
    
    def _generate_semantic_description(self, field_name: str, field_type: str, form_key: str) -> str:
        """Generate semantic description to help AI understand field context"""
        base_desc = f"{field_name} field"
        
        # Add context based on field name patterns
        lower_name = field_name.lower()
        
        # Business vs Personal context
        if any(word in lower_name for word in ["business", "company", "corporation", "entity"]):
            base_desc += " - Business/company information only, never personal names"
        elif any(word in lower_name for word in ["applicant", "borrower"]) or \
             ("name" in lower_name and "business" not in lower_name):
            base_desc += " - Individual person information, not business names"
        
        # Field type context
        elif "email" in lower_name:
            base_desc += " - Valid email address only, never physical addresses"
        elif "address" in lower_name and "email" not in lower_name:
            base_desc += " - Physical mailing address, never email addresses"
        elif "ssn" in lower_name or "social security" in lower_name:
            base_desc += " - Individual's Social Security Number, never business EIN"
        elif "ein" in lower_name or ("tax id" in lower_name and "social" not in lower_name):
            base_desc += " - Business Employer Identification Number, never personal SSN"
        elif any(word in lower_name for word in ["revenue", "income", "amount"]):
            base_desc += " - Financial amount in dollars"
        elif "date" in lower_name or field_type == "date":
            base_desc += " - Date value"
        
        # Add bank-specific context
        if "live_oak" in form_key:
            base_desc += " (Live Oak Bank application)"
        elif "huntington" in form_key:
            base_desc += " (Huntington Bank application)"
        elif "wells_fargo" in form_key:
            base_desc += " (Wells Fargo application)"
        
        return base_desc
    
    def _load_all_form_specs(self) -> Dict[str, Any]:
        """Load all form specifications from templates directory"""
        specs = {}
        
        if not self.form_specs_dir.exists():
            print(f"⚠️ Form specs directory not found: {self.form_specs_dir}")
            return specs
        
        print(f"Loading form specifications from {self.form_specs_dir}...")
        
        for spec_file in self.form_specs_dir.glob("*.json"):
            spec_key = spec_file.stem  # Filename without extension
            
            try:
                with open(spec_file, 'r') as f:
                    specs[spec_key] = json.load(f)
                print(f"  ✅ Loaded {spec_key}")
            except Exception as e:
                print(f"  ❌ Failed to load {spec_file}: {e}")
        
        print(f"Successfully loaded {len(specs)} form specifications")
        return specs
    
    def save_schemas(self, output_path: Path = None) -> Path:
        """Extract and save all OpenAI schemas to file"""
        output_path = output_path or Path("schemas/openai_form_schemas.json")
        output_path.parent.mkdir(exist_ok=True)
        
        schemas = self.extract_all_openai_schemas()
        
        with open(output_path, 'w') as f:
            json.dump(schemas, f, indent=2)
        
        print(f"✅ Saved {len(schemas)} OpenAI schemas to {output_path}")
        return output_path


# CLI for schema extraction
if __name__ == "__main__":
    extractor = FormSchemaExtractor()
    extractor.save_schemas()