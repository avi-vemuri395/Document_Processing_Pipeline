"""
Form Mapping Service - Part 2 of Two-Part Pipeline
Maps master data from Part 1 to 9 different bank forms
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..extraction_methods.multimodal_llm.providers import (
    LLMFormFiller,
    PDFFormGenerator,
    DynamicFormMapper
)


class FormMappingService:
    """
    Correctly implements Part 2: Map master data to 9 different forms.
    
    This service takes the comprehensive extraction from Part 1 and
    distributes it to multiple bank forms. Each bank has different
    requirements and field names for the same information.
    """
    
    # Define which forms each bank requires
    BANK_FORMS = {
        "live_oak": {
            "application": "live_oak_application_v1.json",
            "pfs": "live_oak_pfs_v1.json", 
            "4506t": "live_oak_4506t_v1.json"
        },
        "huntington": {
            "business_app": "huntington_business_app_v1.json",
            "pfs": "huntington_pfs_v1.json",
            "tax_transcript": "huntington_tax_transcript_v1.json",
            "debt_schedule": "huntington_debt_schedule_v1.json"
        },
        "wells_fargo": {
            "loan_app": "wells_fargo_loan_app_v1.json",
            "financial": "wells_fargo_financial_v1.json"
        }
    }
    
    # PDF templates available (we only have 2 actual PDF templates)
    PDF_TEMPLATES = {
        "live_oak": "templates/Live Oak Express - Application Forms.pdf",
        "huntington": "templates/Huntington Bank Personal Financial Statement.pdf",
        "wells_fargo": None  # No Wells Fargo PDF template available
    }
    
    def __init__(self):
        """Initialize form mapping components"""
        self.form_specs = self._load_all_form_specifications()
        self.pdf_generator = PDFFormGenerator()
        self.output_base = Path("outputs/applications")
    
    def map_all_forms(self, application_id: str) -> Dict[str, Any]:
        """
        Map master data to all 9 forms across 3 banks.
        
        Args:
            application_id: Unique application identifier
            
        Returns:
            Results dictionary with all form mappings and PDFs
        """
        print(f"\n{'='*70}")
        print(f"  PART 2: FORM MAPPING (Distribute to Many)")
        print(f"  Application ID: {application_id}")
        print(f"  Target: 9 forms across 3 banks")
        print(f"{'='*70}")
        
        # Load master data from Part 1
        master_data = self._load_master_data(application_id)
        
        if not master_data:
            print("  ❌ No master data found. Run Part 1 first.")
            return {}
        
        print(f"\n  📊 Master data contains:")
        for category, fields in master_data.items():
            if isinstance(fields, dict) and category != "metadata":
                count = len(fields)
                if count > 0:
                    print(f"    • {category}: {count} fields")
        
        results = {}
        total_forms = 0
        
        # Process each bank's forms
        for bank_name, forms in self.BANK_FORMS.items():
            print(f"\n  🏦 Processing {bank_name.upper()} forms...")
            bank_results = self._map_bank_forms(
                master_data,
                bank_name,
                forms,
                application_id
            )
            results[bank_name] = bank_results
            total_forms += len(bank_results)
        
        print(f"\n✅ Part 2 Complete: Generated {total_forms} forms")
        
        # Save summary
        self._save_mapping_summary(application_id, results)
        
        return results
    
    def map_bank_forms(
        self, 
        application_id: str,
        bank_name: str
    ) -> Dict[str, Any]:
        """
        Map master data to a specific bank's forms.
        
        Args:
            application_id: Unique application identifier
            bank_name: Name of bank (live_oak, huntington, wells_fargo)
            
        Returns:
            Mapping results for the specified bank
        """
        if bank_name not in self.BANK_FORMS:
            raise ValueError(f"Unknown bank: {bank_name}")
        
        master_data = self._load_master_data(application_id)
        
        if not master_data:
            print(f"  ❌ No master data found for {application_id}")
            return {}
        
        return self._map_bank_forms(
            master_data,
            bank_name,
            self.BANK_FORMS[bank_name],
            application_id
        )
    
    def _map_bank_forms(
        self,
        master_data: Dict[str, Any],
        bank_name: str,
        form_configs: Dict[str, str],
        application_id: str
    ) -> Dict[str, Any]:
        """
        Map master data to a specific bank's forms.
        
        Args:
            master_data: Combined data from Part 1
            bank_name: Name of the bank
            form_configs: Dictionary of form_type -> spec_file
            application_id: Application identifier
            
        Returns:
            Results for this bank's forms
        """
        bank_results = {}
        
        for form_type, spec_file in form_configs.items():
            print(f"    📝 Mapping to {form_type}...")
            
            # Get form specification
            form_spec = self.form_specs.get(spec_file.replace('.json', ''))
            
            if not form_spec:
                print(f"      ⚠️  Form spec not found: {spec_file}")
                continue
            
            # Map master data to form fields
            mapped_data = self._intelligent_field_mapping(
                master_data,
                form_spec
            )
            
            # Calculate coverage
            total_fields = len(form_spec.get('fields', []))
            filled_fields = len([v for v in mapped_data.values() if v])
            coverage = (filled_fields / total_fields * 100) if total_fields > 0 else 0
            
            # Save mapped data
            output_dir = self.output_base / application_id / "part2_form_mapping" / "banks" / bank_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            mapped_path = output_dir / f"{form_type}_mapped.json"
            with open(mapped_path, 'w') as f:
                json.dump({
                    "form_type": form_type,
                    "bank": bank_name,
                    "mapped_data": mapped_data,
                    "coverage": coverage,
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
            
            # Generate PDF if template exists
            pdf_path = None
            if self.PDF_TEMPLATES.get(bank_name) and Path(self.PDF_TEMPLATES[bank_name]).exists():
                try:
                    pdf_path = self._generate_pdf(
                        mapped_data,
                        self.PDF_TEMPLATES[bank_name],
                        output_dir / f"{form_type}_filled.pdf"
                    )
                    print(f"      ✅ Generated PDF: {pdf_path.name}")
                except Exception as e:
                    print(f"      ⚠️  PDF generation failed: {e}")
            
            bank_results[form_type] = {
                "mapped_fields": filled_fields,
                "total_fields": total_fields,
                "coverage": round(coverage, 1),
                "mapped_data_path": str(mapped_path),
                "pdf_path": str(pdf_path) if pdf_path else None
            }
            
            print(f"      ✅ Mapped {filled_fields}/{total_fields} fields ({coverage:.1f}% coverage)")
        
        return bank_results
    
    def _intelligent_field_mapping(
        self,
        master_data: Dict[str, Any],
        form_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Map fields from master data to form specification.
        
        This uses intelligent matching to handle field name variations
        between the master data and different bank forms.
        
        Args:
            master_data: Comprehensive extraction from Part 1
            form_spec: Form specification with field requirements
            
        Returns:
            Dictionary of form_field_name -> value
        """
        mapped_data = {}
        
        # Deep flatten master data to extract only leaf values
        flat_master = self._deep_flatten(master_data)
        
        # Map each form field
        for field in form_spec.get('fields', []):
            # Fix: Use 'field_name' from spec, not 'name'
            field_name = field.get('field_name', '')
            field_id = field.get('id', field_name)
            
            # Skip if no field name
            if not field_name:
                continue
            
            # Try direct match first
            value = None
            if field_id in flat_master:
                value = flat_master[field_id]
            elif field_id.lower() in flat_master:
                value = flat_master[field_id.lower()]
            elif field_name in flat_master:
                value = flat_master[field_name]
            elif field_name.lower() in flat_master:
                value = flat_master[field_name.lower()]
            else:
                # Try intelligent matching based on common variations
                value = self._find_field_match(field_id, flat_master)
                if not value:
                    value = self._find_field_match(field_name, flat_master)
            
            # Only add if value is not a dict or list (must be a leaf value)
            if value and not isinstance(value, (dict, list)):
                mapped_data[field_id] = value
        
        return mapped_data
    
    def _deep_flatten(self, obj: Any, parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
        """
        Recursively flatten nested dictionaries to extract only leaf values.
        
        Args:
            obj: Object to flatten (dict, list, or primitive)
            parent_key: Parent key path
            separator: Separator for nested keys
            
        Returns:
            Flattened dictionary with only leaf values
        """
        items = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip metadata and error fields
                if key in ["metadata", "_metadata", "_extraction_failed", "raw_text", "error"]:
                    continue
                
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                
                if isinstance(value, dict):
                    # Recursively flatten nested dicts
                    items.update(self._deep_flatten(value, new_key, separator))
                elif isinstance(value, list):
                    # Handle lists - extract first non-empty item if it's a primitive
                    for i, item in enumerate(value):
                        if item and not isinstance(item, (dict, list)):
                            # Store first item without index for simple access
                            if i == 0:
                                items[new_key] = item
                            # Also store with index for specific access
                            items[f"{new_key}[{i}]"] = item
                        elif isinstance(item, dict):
                            # Flatten dict items in lists
                            items.update(self._deep_flatten(item, f"{new_key}[{i}]", separator))
                elif value is not None and value != "" and value != []:
                    # This is a leaf value - add it with full path
                    items[new_key] = value
                    
                    # For common fields, also add short version
                    # This helps with field matching while avoiding too many duplicates
                    common_fields = ['name', 'first', 'last', 'ssn', 'email', 'phone', 
                                   'address', 'city', 'state', 'zip', 'ein', 'legal_name']
                    if key.lower() in common_fields:
                        items[key] = value
        elif not isinstance(obj, list):
            # It's a primitive value
            if obj is not None and obj != "":
                return {parent_key: obj} if parent_key else {}
        
        return items
    
    def _find_field_match(
        self, 
        form_field: str, 
        master_data: Dict[str, Any]
    ) -> Any:
        """
        Find matching field in master data using common variations.
        
        Args:
            form_field: Field name from form specification
            master_data: Flattened master data
            
        Returns:
            Matched value or None
        """
        # Common field name variations
        variations = {
            'ssn': ['social_security_number', 'social_security', 'ss_number', 'taxpayer_id'],
            'ein': ['employer_id', 'tax_id', 'business_tax_id', 'federal_tax_id'],
            'business_name': ['company_name', 'company', 'business', 'dba'],
            'phone': ['phone_number', 'telephone', 'contact_number', 'primary_phone'],
            'email': ['email_address', 'contact_email', 'primary_email'],
            'address': ['street_address', 'mailing_address', 'physical_address'],
            'city': ['city_name', 'municipality'],
            'state': ['state_code', 'province'],
            'zip': ['zip_code', 'postal_code', 'zipcode'],
            'dob': ['date_of_birth', 'birth_date', 'birthdate'],
            'net_worth': ['total_net_worth', 'networth', 'net_value'],
            'total_assets': ['assets', 'total_asset_value', 'asset_total'],
            'total_liabilities': ['liabilities', 'total_liability_value', 'liability_total']
        }
        
        form_field_lower = form_field.lower()
        
        # Check if form field matches any variation key
        for key, variations_list in variations.items():
            if key in form_field_lower:
                # Try each variation
                for variation in variations_list:
                    if variation in master_data:
                        return master_data[variation]
                    if variation.lower() in master_data:
                        return master_data[variation.lower()]
        
        # Check if any master data key contains the form field
        for master_key, value in master_data.items():
            if isinstance(master_key, str):
                if form_field_lower in master_key.lower() or master_key.lower() in form_field_lower:
                    return value
        
        return None
    
    def _generate_pdf(
        self,
        mapped_data: Dict[str, Any],
        template_path: str,
        output_path: Path
    ) -> Path:
        """
        Generate filled PDF from mapped data.
        
        Args:
            mapped_data: Field name -> value mapping
            template_path: Path to PDF template
            output_path: Where to save filled PDF
            
        Returns:
            Path to generated PDF
        """
        # Use the existing PDF generator
        generator = PDFFormGenerator()
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Use the correct method name
        result_path = generator.generate_filled_pdf(
            template_name=Path(template_path).stem,
            extracted_data=mapped_data,
            output_dir=output_path.parent
        )
        
        if result_path:
            # Rename to our desired name if needed
            if result_path != output_path:
                result_path.rename(output_path)
            return output_path
        else:
            raise Exception("PDF generation failed")
    
    def _load_master_data(self, application_id: str) -> Dict[str, Any]:
        """Load master data from Part 1"""
        master_path = self.output_base / application_id / "part1_document_processing" / "master_data.json"
        
        if not master_path.exists():
            return {}
        
        with open(master_path, 'r') as f:
            return json.load(f)
    
    def _load_all_form_specifications(self) -> Dict[str, Any]:
        """Load all 9 form specifications"""
        specs = {}
        spec_dir = Path("templates/form_specs")
        
        for bank_forms in self.BANK_FORMS.values():
            for form_type, spec_file in bank_forms.items():
                spec_path = spec_dir / spec_file
                if spec_path.exists():
                    with open(spec_path, 'r') as f:
                        spec_key = spec_file.replace('.json', '')
                        specs[spec_key] = json.load(f)
        
        return specs
    
    def _save_mapping_summary(
        self,
        application_id: str,
        results: Dict[str, Any]
    ):
        """Save summary of all form mappings"""
        summary = {
            "application_id": application_id,
            "timestamp": datetime.now().isoformat(),
            "banks_processed": list(results.keys()),
            "total_forms": sum(len(bank_results) for bank_results in results.values()),
            "results": results,
            "overall_stats": {
                "total_fields_mapped": sum(
                    form_result.get('mapped_fields', 0)
                    for bank_results in results.values()
                    for form_result in bank_results.values()
                ),
                "average_coverage": sum(
                    form_result.get('coverage', 0)
                    for bank_results in results.values()
                    for form_result in bank_results.values()
                ) / max(1, sum(len(bank_results) for bank_results in results.values()))
            }
        }
        
        summary_path = self.output_base / application_id / "part2_form_mapping" / "mapping_summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)