"""
Form Mapping Service - Part 2 of Two-Part Pipeline
Maps master data from Part 1 to 9 different bank forms
"""

import json
import statistics
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from ..extraction_methods.multimodal_llm.providers import (
    LLMFormFiller,
    PDFFormGenerator,
    DynamicFormMapper
)

# Safe import of schema-driven components
try:
    from ..schema_driven.openai_form_mapper import OpenAIFormMapper
    SCHEMA_DRIVEN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Schema-driven mapping not available: {e}")
    SCHEMA_DRIVEN_AVAILABLE = False


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
        self._confidence_aggregator = None  # Lazy initialization for confidence aggregator
    
    @property
    def confidence_aggregator(self):
        """Load confidence aggregator with embedded implementation (bypassing import issue)."""
        if self._confidence_aggregator is None:
            # Embedded confidence aggregator to avoid problematic import
            class EmbeddedConfidenceAggregator:
                def __init__(self):
                    self.critical_fields = [
                        "firstName", "lastName", "totalAssets", "totalLiabilities",
                        "businessName", "ein", "creditorName", "currentBalance"
                    ]
                
                def get_review_recommendation(self, overall_confidence, field_confidences, validation_scores):
                    needs_review = False
                    review_reasons = []
                    fields_to_review = []
                    
                    # Check overall confidence
                    if overall_confidence < 0.85:
                        needs_review = True
                        review_reasons.append(f"Overall confidence ({overall_confidence:.2f}) below threshold")
                    
                    # Check critical fields
                    for field in self.critical_fields:
                        if field in field_confidences:
                            if field_confidences[field] < 0.7:
                                needs_review = True
                                fields_to_review.append(field)
                    
                    if fields_to_review:
                        review_reasons.append(f"Critical fields with low confidence: {', '.join(fields_to_review)}")
                    
                    # Check validation scores
                    failed_checks = [
                        check for check, score in validation_scores.items()
                        if score < 0.8
                    ] if validation_scores else []
                    
                    if failed_checks:
                        needs_review = True
                        review_reasons.append(f"Failed consistency checks: {', '.join(failed_checks)}")
                    
                    # Determine priority
                    if overall_confidence < 0.5:
                        priority = "high"
                    elif overall_confidence < 0.7 or len(fields_to_review) > 3:
                        priority = "medium"
                    else:
                        priority = "low"
                    
                    return {
                        "needs_review": needs_review,
                        "priority": priority,
                        "reasons": review_reasons,
                        "fields_to_review": fields_to_review,
                        "overall_confidence": overall_confidence,
                        "consistency_scores": validation_scores or {},
                        "status": "embedded_implementation"
                    }
            
            self._confidence_aggregator = EmbeddedConfidenceAggregator()
        return self._confidence_aggregator
    
    async def map_all_forms(self, application_id: str) -> Dict[str, Any]:
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
            bank_results = await self._map_bank_forms(
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
    
    async def map_bank_forms(
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
        
        return await self._map_bank_forms(
            master_data,
            bank_name,
            self.BANK_FORMS[bank_name],
            application_id
        )
    
    async def _map_bank_forms(
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
            
            # Get form specification (dynamic extraction with manual fallback)
            spec_key = spec_file.replace('.json', '')
            form_spec = self._get_form_specification(bank_name, spec_file, spec_key)
            
            print(f"      🔍 Looking for spec key: '{spec_key}'")
            print(f"      📋 Available spec keys: {list(self.form_specs.keys())}")
            print(f"      ✅ Found spec: {form_spec is not None}")
            
            if not form_spec:
                print(f"      ⚠️  Form spec not found: {spec_file}")
                print(f"      🔧 DEBUG: Tried key '{spec_key}' in {list(self.form_specs.keys())}")
                continue
            else:
                field_count = len(form_spec.get('fields', []))
                print(f"      ✅ Using spec with {field_count} fields")
            
            # Map master data to form fields with confidence scoring
            # NEW: Schema-driven mapping with automatic fallback protection
            mapping_result = await self._schema_driven_mapping_with_fallback(
                master_data,
                form_spec,
                spec_key  # e.g., "live_oak_application_v1"
            )
            
            mapped_data = mapping_result['mapped_data']
            confidence_scores = mapping_result['confidence_scores']
            overall_confidence = mapping_result['overall_confidence']
            
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
                    "confidence": {
                        "overall": overall_confidence,
                        "field_scores": confidence_scores,
                        "needs_review": overall_confidence < 0.85
                    },
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
                "confidence": round(overall_confidence, 3),
                "needs_review": overall_confidence < 0.85,
                "mapped_data_path": str(mapped_path),
                "pdf_path": str(pdf_path) if pdf_path else None
            }
            
            confidence_indicator = "🟢" if overall_confidence >= 0.85 else "🟡" if overall_confidence >= 0.7 else "🔴"
            print(f"      ✅ Mapped {filled_fields}/{total_fields} fields ({coverage:.1f}% coverage) {confidence_indicator} Confidence: {overall_confidence:.1%}")
        
        return bank_results
    
    def _intelligent_field_mapping_with_confidence(
        self,
        master_data: Dict[str, Any],
        form_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Map fields with confidence scoring (Phase 1 enhancement)."""
        mapped_data = {}
        confidence_scores = {}
        
        flat_master = self._deep_flatten(master_data)
        
        print(f"        🗂️  DEBUG: Flattened master data contains {len(flat_master)} keys")
        if len(flat_master) > 0:
            sample_keys = list(flat_master.keys())[:10]
            print(f"        📋 Sample flattened keys: {sample_keys}")
            if len(flat_master) > 10:
                print(f"        📋 ... and {len(flat_master) - 10} more keys")
        
        form_fields = form_spec.get('fields', [])
        print(f"        🎯 Form expects {len(form_fields)} fields")
        
        matched_count = 0
        total_fields = len(form_fields)
        
        for field in form_spec.get('fields', []):
            # Handle both 'name' and 'field_name' properties for compatibility with all form specs
            field_name = field.get('name') or field.get('field_name', '')
            field_id = field.get('id', field_name)
            
            if not field_name:
                continue
            
            # Find value with confidence scoring
            value, confidence = self._find_field_with_confidence(field_name, field_id, flat_master)
            
            if value and not isinstance(value, (dict, list)):
                mapped_data[field_id] = value
                confidence_scores[field_id] = confidence
                matched_count += 1
                print(f"          ✅ MATCHED '{field_name}' → '{value}' (confidence: {confidence:.2f})")
            else:
                print(f"          ❌ NO MATCH for '{field_name}' (id: '{field_id}')")
        
        print(f"        📊 Field mapping summary: {matched_count}/{total_fields} fields matched")
        
        # Calculate overall confidence
        overall_confidence = statistics.mean(confidence_scores.values()) if confidence_scores else 0.0
        
        # Get review recommendation using embedded confidence aggregator
        review_rec = self.confidence_aggregator.get_review_recommendation(
            overall_confidence,
            confidence_scores,
            {}
        )
        
        return {
            'mapped_data': mapped_data,
            'confidence_scores': confidence_scores,
            'overall_confidence': overall_confidence,
            'review_recommendation': review_rec
        }
    
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
            # Handle both 'name' and 'field_name' properties for compatibility with all form specs
            field_name = field.get('name') or field.get('field_name', '')
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
    
    def _find_field_with_confidence(
        self,
        field_name: str,
        field_id: str,
        flat_master: Dict[str, Any]
    ) -> Tuple[Any, float]:
        """Find field value with confidence score."""
        print(f"            🔍 Searching for field: '{field_name}' (id: '{field_id}')")
        
        # Direct exact match - highest confidence
        if field_id in flat_master:
            print(f"            ✅ Direct match on field_id: {field_id}")
            return flat_master[field_id], 1.0
        if field_id.lower() in flat_master:
            print(f"            ✅ Case-insensitive match on field_id: {field_id.lower()}")
            return flat_master[field_id.lower()], 0.95
        if field_name in flat_master:
            print(f"            ✅ Direct match on field_name: {field_name}")
            return flat_master[field_name], 0.95
        if field_name.lower() in flat_master:
            print(f"            ✅ Case-insensitive match on field_name: {field_name.lower()}")
            return flat_master[field_name.lower()], 0.9
        
        # Try intelligent matching with lower confidence
        print(f"            🧠 Trying intelligent matching for field_id...")
        value = self._find_field_match(field_id, flat_master)
        if value:
            print(f"            ✅ Intelligent match on field_id found: {value}")
            return value, 0.8
        
        print(f"            🧠 Trying intelligent matching for field_name...")
        value = self._find_field_match(field_name, flat_master)
        if value:
            print(f"            ✅ Intelligent match on field_name found: {value}")
            return value, 0.75
        
        print(f"            ❌ No match found for '{field_name}'")
        # No match found
        return None, 0.0
    
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
    
    async def _schema_driven_mapping_with_fallback(
        self,
        master_data: Dict[str, Any],
        form_spec: Dict[str, Any],
        form_key: str
    ) -> Dict[str, Any]:
        """
        Schema-driven mapping using OpenAI structured outputs with automatic fallback.
        
        This method attempts to use AI semantic understanding to map master data
        to form fields. If it fails for any reason, it automatically falls back
        to the existing string-matching approach.
        
        Args:
            master_data: Comprehensive extraction from Part 1
            form_spec: Form specification with field requirements  
            form_key: Key for OpenAI schema (e.g., 'live_oak_application_v1')
            
        Returns:
            Same format as _intelligent_field_mapping_with_confidence()
        """
        # Check if schema-driven mapping is enabled and available
        if not SCHEMA_DRIVEN_AVAILABLE:
            print(f"        📝 Schema-driven not available, using existing method")
            return self._intelligent_field_mapping_with_confidence(master_data, form_spec)
        
        enable_schema = os.getenv('ENABLE_SCHEMA_DRIVEN', 'false').lower() == 'true'
        if not enable_schema:
            print(f"        📝 Schema-driven disabled, using existing method")
            return self._intelligent_field_mapping_with_confidence(master_data, form_spec)
        
        print(f"        🤖 Attempting schema-driven mapping for {form_key}...")
        
        try:
            # Initialize schema mapper if not exists (lazy loading)
            if not hasattr(self, 'schema_mapper'):
                print(f"        🔧 Initializing OpenAI schema mapper...")
                self.schema_mapper = OpenAIFormMapper()
            
            # Attempt semantic mapping via OpenAI
            mapped_data = await self.schema_mapper.map_to_form_schema(
                master_data, 
                form_key
            )
            
            # Validate minimum coverage threshold  
            if len(mapped_data) < 2:  # Require at least 2 fields for success
                raise Exception(f"Insufficient field coverage: {len(mapped_data)} fields")
            
            # Calculate metrics in same format as existing method
            total_fields = len(form_spec.get('fields', []))
            filled_fields = len([v for k, v in mapped_data.items() if v is not None and str(v).strip()])
            coverage = (filled_fields / total_fields * 100) if total_fields > 0 else 0
            
            # High confidence for schema-driven approach (AI understands semantics)
            field_confidences = {k: 0.95 for k, v in mapped_data.items() if v is not None}
            overall_confidence = 0.95 if coverage > 80 else (0.90 if coverage > 60 else 0.85)
            
            print(f"        ✅ Schema-driven success: {filled_fields}/{total_fields} fields ({coverage:.1f}%)")
            
            return {
                'mapped_data': mapped_data,
                'confidence_scores': field_confidences,
                'overall_confidence': overall_confidence,
                'extraction_method': 'openai_structured_outputs'
            }
            
        except Exception as e:
            print(f"        ⚠️ Schema-driven mapping failed: {e}")
            print(f"        🔄 Falling back to existing string matching...")
            # Complete fallback to existing method
            return self._intelligent_field_mapping_with_confidence(master_data, form_spec)
    
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
    
    def _get_form_specification(self, bank_name: str, spec_file: str, spec_key: str) -> Dict[str, Any]:
        """
        Get form specification from dynamic extraction or manual fallback.
        
        This method implements the core migration strategy:
        1. Check if dynamic extraction is enabled for this bank
        2. If enabled, try to extract fields from PDF template
        3. Convert dynamic format to manual format for compatibility
        4. Fall back to manual specifications if dynamic extraction fails
        
        Args:
            bank_name: Name of the bank (live_oak, huntington, wells_fargo)
            spec_file: Original spec file name (e.g., "live_oak_application_v1.json")
            spec_key: Spec key without extension (e.g., "live_oak_application_v1")
            
        Returns:
            Form specification dict compatible with existing field mapping logic
        """
        # Check if dynamic extraction is enabled for this bank
        enabled_banks = os.getenv('DYNAMIC_FORMS_ENABLED_FOR', '').lower().split(',')
        use_dynamic = (
            os.getenv('USE_DYNAMIC_FORM_EXTRACTION', 'false').lower() == 'true' and
            bank_name.lower().strip() in [b.strip() for b in enabled_banks if b.strip()]
        )
        
        if use_dynamic:
            print(f"      🚀 Dynamic extraction enabled for {bank_name}")
            try:
                # Check if PDF template exists for this bank
                pdf_path_str = self.PDF_TEMPLATES.get(bank_name)
                if pdf_path_str:
                    pdf_path = Path(pdf_path_str)
                    if pdf_path.exists():
                        print(f"      📄 Using PDF template: {pdf_path.name}")
                        
                        # Initialize dynamic form mapper
                        if not hasattr(self, '_dynamic_mapper'):
                            self._dynamic_mapper = DynamicFormMapper()
                        
                        # Extract fields from PDF
                        dynamic_spec = self._dynamic_mapper.get_form_fields(pdf_path)
                        
                        # Convert dynamic format to manual format for compatibility
                        manual_format_spec = self._convert_dynamic_to_manual_format(dynamic_spec, spec_key)
                        
                        field_count = len(manual_format_spec.get('fields', []))
                        print(f"      ✅ Dynamic extraction successful: {field_count} fields")
                        return manual_format_spec
                        
                    else:
                        print(f"      ❌ PDF template not found: {pdf_path_str}")
                else:
                    print(f"      ❌ No PDF template configured for {bank_name}")
                    
            except Exception as e:
                print(f"      ⚠️ Dynamic extraction failed for {bank_name}: {e}")
                print(f"      🔄 Falling back to manual specifications...")
        
        # Fallback to manual specifications
        print(f"      📚 Using manual specification for {spec_key}")
        return self.form_specs.get(spec_key)
    
    def _convert_dynamic_to_manual_format(self, dynamic_spec: Dict[str, Any], spec_key: str) -> Dict[str, Any]:
        """
        Convert dynamic format to manual format for compatibility.
        
        Dynamic format (from DynamicFormMapper):
        {
            "form_title": "Form Name",
            "sections": ["Section1", "Section2"],
            "fields": {
                "Field Name": {
                    "field_name": "Field Name",
                    "field_type": "text",
                    "required": false,
                    "page": 1
                }
            }
        }
        
        Manual format (expected by existing logic):
        {
            "form_id": "spec_key",
            "form_name": "Form Name", 
            "bank": "Bank Name",
            "version": "1.0",
            "total_fields": 203,
            "fields": [
                {
                    "name": "Field Name",
                    "type": "text", 
                    "required": false
                }
            ]
        }
        
        Args:
            dynamic_spec: Dynamic specification from DynamicFormMapper
            spec_key: Specification key (e.g., "live_oak_application_v1")
            
        Returns:
            Manual format specification dict
        """
        dynamic_fields = dynamic_spec.get('fields', {})
        
        # Convert fields from dict format to list format with form-specific filtering
        manual_fields = []
        filtered_fields = self._apply_form_specific_filtering(dynamic_fields, spec_key)
        
        for field_name, field_info in filtered_fields.items():
            manual_field = {
                "name": field_info.get('field_name', field_name),
                "type": field_info.get('field_type', 'text'),
                "required": field_info.get('required', False)
            }
            
            # Add optional properties if they exist
            if 'options' in field_info:
                manual_field['options'] = field_info['options']
            if 'page' in field_info:
                manual_field['page'] = field_info['page']
                
            manual_fields.append(manual_field)
        
        # Extract bank name from spec_key (e.g., "live_oak_application_v1" -> "Live Oak")
        bank_name = "Unknown Bank"
        if spec_key.startswith('live_oak'):
            bank_name = "Live Oak"
        elif spec_key.startswith('huntington'):
            bank_name = "Huntington"
        elif spec_key.startswith('wells_fargo'):
            bank_name = "Wells Fargo"
        
        # Build manual format specification
        manual_spec = {
            "form_id": spec_key,
            "form_name": dynamic_spec.get('form_title', f"{bank_name} Form"),
            "bank": bank_name,
            "version": "dynamic_v1.0",  # Mark as dynamic version
            "total_fields": len(manual_fields),
            "fields": manual_fields,
            "_dynamic_extraction": True,  # Flag to indicate dynamic source
            "_source_pdf": dynamic_spec.get('metadata', {}).get('source', 'unknown')
        }
        
        print(f"      🔄 Converted {len(filtered_fields)} filtered fields to manual format (from {len(dynamic_fields)} total)")
        return manual_spec
    
    def _apply_form_specific_filtering(self, dynamic_fields: Dict[str, Any], spec_key: str) -> Dict[str, Any]:
        """
        Apply form-specific filtering to dynamic fields.
        
        This method addresses the Huntington complexity where 1 PDF (461 fields)
        needs to be distributed across 4 different form types.
        
        Args:
            dynamic_fields: All fields extracted from PDF
            spec_key: Form specification key (e.g., "huntington_business_app_v1")
            
        Returns:
            Filtered dict of fields relevant to the specific form
        """
        # If not Huntington, return all fields (no filtering needed)
        if not spec_key.startswith('huntington_'):
            return dynamic_fields
        
        # Determine form type from spec_key
        form_type = None
        if 'business_app' in spec_key:
            form_type = 'business_app'
        elif 'pfs' in spec_key:
            form_type = 'pfs'
        elif 'tax_transcript' in spec_key:
            form_type = 'tax_transcript'  
        elif 'debt_schedule' in spec_key:
            form_type = 'debt_schedule'
        else:
            # Unknown Huntington form, return all fields
            return dynamic_fields
        
        print(f"        🎯 Applying {form_type} filtering to {len(dynamic_fields)} fields")
        
        # Define form-specific keywords for filtering
        form_keywords = {
            'business_app': [
                'business', 'company', 'corporation', 'llc', 'entity', 'ownership',
                'operation', 'industry', 'employee', 'revenue', 'gross', 'applicant',
                'legal', 'name', 'address', 'phone', 'email', 'contact',  # Basic info
                'ein', 'tax', 'id', 'entity', 'type', 'structure'  # Business identifiers
            ],
            'pfs': [
                'asset', 'liability', 'net', 'worth', 'financial', 'income', 'expense',
                'property', 'investment', 'savings', 'checking', 'personal', 'statement',
                'cash', 'deposit', 'securities', 'real', 'estate', 'automobile',
                'insurance', 'retirement', 'pension', 'ira', '401k', 'value',
                'mortgage', 'note', 'payable', 'credit', 'card', 'balance'
            ],
            'tax_transcript': [
                'tax', 'return', 'transcript', 'irs', 'schedule', 'form', 'year',
                'filing', 'refund', 'agi', 'adjusted', 'gross', 'income',
                'federal', 'state', 'withholding', '1040', 'w2', '1099'
            ],
            'debt_schedule': [
                'debt', 'loan', 'mortgage', 'liability', 'payment', 'monthly',
                'balance', 'creditor', 'installment', 'line', 'credit',
                'payable', 'note', 'original', 'amount', 'current', 'due',
                'maturity', 'rate', 'interest', 'secured', 'unsecured'
            ]
        }
        
        # Get keywords for this form type
        keywords = form_keywords.get(form_type, [])
        
        # Always include common personal identification fields
        common_keywords = [
            'name', 'address', 'phone', 'email', 'ssn', 'social', 'date', 'birth',
            'city', 'state', 'zip', 'county', 'signature', 'applicant'
        ]
        
        all_keywords = keywords + common_keywords
        
        # Filter fields based on keywords
        filtered_fields = {}
        
        for field_name, field_info in dynamic_fields.items():
            field_lower = field_name.lower()
            
            # Check if field matches any keyword
            is_relevant = any(keyword in field_lower for keyword in all_keywords)
            
            if is_relevant:
                filtered_fields[field_name] = field_info
        
        # Ensure we have at least some fields (fallback)
        if len(filtered_fields) < 10:
            print(f"        ⚠️ Too few filtered fields ({len(filtered_fields)}), including top general fields")
            
            # Add first 50 fields as fallback to ensure form has adequate coverage
            fallback_count = 0
            for field_name, field_info in dynamic_fields.items():
                if field_name not in filtered_fields:
                    filtered_fields[field_name] = field_info
                    fallback_count += 1
                    if fallback_count >= 40:  # Add up to 40 more fields
                        break
        
        efficiency_gain = (1 - len(filtered_fields) / len(dynamic_fields)) * 100
        print(f"        ✅ Filtered to {len(filtered_fields)} fields ({efficiency_gain:.1f}% reduction)")
        
        return filtered_fields
    
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
        
        print(f"\n  🔧 DEBUG: Loading form specifications from {spec_dir}")
        print(f"  📂 Directory exists: {spec_dir.exists()}")
        
        if spec_dir.exists():
            available_files = list(spec_dir.glob("*.json"))
            print(f"  📄 Available spec files: {[f.name for f in available_files]}")
        
        for bank_name, bank_forms in self.BANK_FORMS.items():
            print(f"\n  🏦 Processing {bank_name} forms:")
            for form_type, spec_file in bank_forms.items():
                spec_path = spec_dir / spec_file
                spec_key = spec_file.replace('.json', '')
                
                print(f"    📝 {form_type}: looking for '{spec_file}' → key '{spec_key}'")
                print(f"      Path: {spec_path}")
                print(f"      Exists: {spec_path.exists()}")
                
                if spec_path.exists():
                    with open(spec_path, 'r') as f:
                        spec_data = json.load(f)
                        specs[spec_key] = spec_data
                        field_count = len(spec_data.get('fields', []))
                        print(f"      ✅ Loaded {field_count} fields")
                else:
                    print(f"      ❌ File not found!")
        
        print(f"\n  📋 Final loaded specs: {list(specs.keys())}")
        total_specs = len(specs)
        expected_specs = sum(len(forms) for forms in self.BANK_FORMS.values())
        print(f"  📊 Loaded {total_specs}/{expected_specs} specifications")
        
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