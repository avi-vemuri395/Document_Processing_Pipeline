"""
Ultra-simple LLM-based form filler for benchmark testing.
Extracts documents, reads forms, and uses Claude to fill them.
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Union, Optional

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # dotenv not required

from .benchmark_extractor import BenchmarkExtractor
from .pdf_form_generator import PDFFormGenerator, AcroFormFiller


class LLMFormFiller:
    """
    Simple form filler that uses Claude to map extracted data to form fields.
    No PDF manipulation - outputs filled forms as structured JSON.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with minimal setup."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")
        
        # Use provided key, then env var, then .env file
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        self.extractor = BenchmarkExtractor(api_key)
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = "claude-3-5-sonnet-20241022"
    
    async def fill_forms_from_documents(
        self,
        documents_folder: Union[str, Path],
        form_template_path: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Complete workflow: Extract documents → Read form → Fill with Claude.
        
        Args:
            documents_folder: Folder containing source documents
            form_template_path: Path to form template (PDF)
            
        Returns:
            Filled form data as structured JSON
        """
        start_time = time.time()
        
        print(f"📂 Processing documents from: {documents_folder}")
        print(f"📋 Using form template: {Path(form_template_path).name}")
        print("-" * 60)
        
        # Step 1: Extract all documents in folder
        documents = self._find_documents(documents_folder)
        if not documents:
            return {"error": "No documents found in folder"}
        
        print(f"\n📄 Found {len(documents)} documents to process")
        extracted_data = await self.extractor.extract_all(documents)
        
        # Step 2: Read form template
        print(f"\n📋 Reading form template...")
        form_content = await self._read_form_template(form_template_path)
        
        # Step 3: Use Claude to fill form with extracted data
        print(f"\n🤖 Filling form with extracted data...")
        filled_form = await self._fill_form_with_llm(form_content, extracted_data)
        
        # Add metadata
        filled_form['_metadata'] = {
            'processing_time': time.time() - start_time,
            'documents_processed': len(documents),
            'form_template': str(form_template_path),
            'extraction_time': extracted_data.get('_metadata', {}).get('processing_time', 0)
        }
        
        print(f"\n✅ Form filling complete in {filled_form['_metadata']['processing_time']:.2f}s")
        
        return filled_form
    
    def _find_documents(self, folder: Union[str, Path]) -> List[Path]:
        """Find all processable documents in folder."""
        folder = Path(folder)
        if not folder.exists():
            return []
        
        # Supported extensions
        extensions = ['.pdf', '.xlsx', '.xls', '.png', '.jpg', '.jpeg']
        
        documents = []
        for ext in extensions:
            documents.extend(folder.glob(f'*{ext}'))
        
        return sorted(documents)
    
    async def _read_form_template(self, form_path: Union[str, Path]) -> Dict[str, Any]:
        """Read form template and extract its structure."""
        form_path = Path(form_path)
        
        # First try to load existing static mapping
        mapping_path = Path("outputs/form_mappings") / f"{form_path.stem}_mapping.json"
        
        if mapping_path.exists():
            # Load the field mappings we already have
            with open(mapping_path, 'r') as f:
                mapping_data = json.load(f)
            
            # Convert mapping to form structure format
            fields = {}
            for field_name, field_info in mapping_data.get('mappings', {}).items():
                fields[field_name] = {
                    'field_name': field_name,
                    'field_type': 'checkbox' if 'checkbox' in field_info.get('type', '').lower() else 'text',
                    'required': field_info.get('required', False)
                }
            
            print(f"✅ Loaded {len(fields)} fields from static mapping")
            
            return {
                "form_title": form_path.stem.replace('_', ' '),
                "sections": ["Personal Information", "Business Information", "Financial Information"],
                "fields": fields
            }
        
        # NEW: Try dynamic field extraction for any PDF
        try:
            from .dynamic_form_mapper import DynamicFormMapper
            print(f"📋 Dynamically extracting fields from {form_path.name}...")
            
            mapper = DynamicFormMapper()
            form_structure = mapper.get_form_fields(form_path)
            
            field_count = len(form_structure.get('fields', {}))
            if field_count > 0:
                print(f"✅ Dynamically extracted {field_count} fields")
                return form_structure
            else:
                print("⚠️  No fields found via dynamic extraction")
        except ImportError:
            print("⚠️  pdfplumber not available for dynamic extraction")
        except Exception as e:
            print(f"⚠️  Dynamic extraction failed: {e}")
        
        # Final fallback: Common fields
        print(f"⚠️  Using fallback common fields for {form_path.stem}")
        
        return {
            "form_title": form_path.stem.replace('_', ' '),
            "sections": ["Personal Information", "Business Information"],
            "fields": {
                "Name": {"field_name": "Name", "field_type": "text", "required": True},
                "Social Security Number": {"field_name": "Social Security Number", "field_type": "text", "required": False},
                "Date of Birth": {"field_name": "Date of Birth", "field_type": "date", "required": False},
                "Mobile Telephone Number": {"field_name": "Mobile Telephone Number", "field_type": "text", "required": True},
                "Email address": {"field_name": "Email address", "field_type": "text", "required": True},
                "Residence Address": {"field_name": "Residence Address", "field_type": "text", "required": True},
                "City, State, Zip": {"field_name": "City, State, Zip", "field_type": "text", "required": True},
                "Business Applicant Name": {"field_name": "Business Applicant Name", "field_type": "text", "required": True},
                "What percentage of the applicant business do/will you own?": {"field_name": "What percentage of the applicant business do/will you own?", "field_type": "text", "required": False}
            }
        }
    
    async def _fill_form_with_llm(
        self,
        form_structure: Dict[str, Any],
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use Claude to intelligently map extracted data to form fields."""
        
        # First try deterministic mapping for common fields
        filled_fields = self._deterministic_field_mapping(form_structure, extracted_data)
        
        # Remove metadata from extracted data for cleaner prompt
        clean_data = {k: v for k, v in extracted_data.items() if not k.startswith('_')}
        
        # Count pre-filled fields
        pre_filled_count = len([v for v in filled_fields.values() if v])
        if pre_filled_count > 0:
            print(f"  ✅ Pre-filled {pre_filled_count} fields via deterministic mapping")
        
        prompt = f"""You have extracted data from loan application documents and need to fill out a form.

FORM STRUCTURE:
{json.dumps(form_structure, indent=2)}

EXTRACTED DATA:
{json.dumps(clean_data, indent=2)}

INSTRUCTIONS:
1. Map the extracted data to the appropriate form fields
2. Use the exact field names from the form structure
3. For checkboxes/radio buttons, use true/false or the specific option value
4. If data is missing, use null
5. Convert currency values to numbers (remove $ and commas)
6. Format dates as MM/DD/YYYY
7. Include a confidence score (0-1) for each field
8. Add source information showing which document provided the data

PRE-FILLED FIELDS (already mapped deterministically):
{json.dumps(filled_fields, indent=2) if filled_fields else "None"}

FOCUS ON:
1. Fields that weren't already filled
2. Complex fields requiring interpretation
3. Business entity relationships
4. Calculated fields

Return a JSON object with:
- form_title: The form being filled
- filled_fields: Object with ALL field_name: value pairs (include pre-filled and new)
- field_confidence: Object with field_name: confidence pairs
- field_sources: Object with field_name: source document
- completion_percentage: What percentage of required fields were filled
- missing_fields: List of required fields that couldn't be filled
- mapping_notes: Brief notes on any complex mappings made

Return ONLY the JSON object."""
        
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )
            
            raw_text = response.content[0].text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            
            result = json.loads(raw_text)
            
            # Merge with pre-filled fields, preferring LLM mappings for conflicts
            if filled_fields:
                for field, value in filled_fields.items():
                    if field not in result.get('filled_fields', {}) or not result['filled_fields'][field]:
                        result.setdefault('filled_fields', {})[field] = value
            
            return result
            
        except Exception as e:
            print(f"  ⚠️ LLM mapping failed: {e}")
            print(f"  ✅ Using {len(filled_fields)} deterministically mapped fields")
            
            # Return deterministic mappings if LLM fails
            total_fields = len(form_structure.get('fields', {}))
            filled_count = len([v for v in filled_fields.values() if v])
            
            return {
                "error": f"LLM mapping failed, using deterministic mapping: {str(e)}",
                "form_title": form_structure.get("form_title", "Unknown"),
                "filled_fields": filled_fields,
                "completion_percentage": (filled_count / total_fields * 100) if total_fields > 0 else 0,
                "field_confidence": {field: 0.8 for field in filled_fields if filled_fields[field]},
                "mapping_method": "deterministic_fallback"
            }
    
    def _deterministic_field_mapping(
        self,
        form_structure: Dict[str, Any],
        extracted_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """Deterministically map common fields from structured extraction to form."""
        
        filled_fields = {}
        form_fields = form_structure.get('fields', {})
        
        # Define mapping rules from structured extraction to common form fields
        mapping_rules = {
            # Personal Information
            "Name": lambda d: self._get_full_name(d),
            "First Name": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'name', 'first'),
            "Last Name": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'name', 'last'),
            "Social Security Number": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'ssn'),
            "SSN": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'ssn'),
            "Date of Birth": lambda d: self._format_date(self._get_nested(d, 'personal', 'primary_applicant', 'dob')),
            "DOB": lambda d: self._format_date(self._get_nested(d, 'personal', 'primary_applicant', 'dob')),
            
            # Contact Information
            "Mobile Telephone Number": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'phones', 'mobile'),
            "Mobile Phone": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'phones', 'mobile'),
            "Business Phone": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'phones', 'business'),
            "Email address": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'email'),
            "Email": lambda d: self._get_nested(d, 'personal', 'primary_applicant', 'email'),
            
            # Address Information
            "Residence Address": lambda d: self._get_address_street(d, 'current_residence'),
            "Home Address": lambda d: self._get_address_street(d, 'current_residence'),
            "City, State, Zip": lambda d: self._get_address_csz(d, 'current_residence'),
            "City": lambda d: self._get_nested(d, 'addresses', 'current_residence', 'city'),
            "State": lambda d: self._get_nested(d, 'addresses', 'current_residence', 'state'),
            "Zip": lambda d: self._get_nested(d, 'addresses', 'current_residence', 'zip'),
            
            # Business Information
            "Business Applicant Name": lambda d: self._get_nested(d, 'business', 'primary_business', 'legal_name'),
            "Business Name": lambda d: self._get_nested(d, 'business', 'primary_business', 'legal_name'),
            "What percentage of the applicant business do/will you own?": lambda d: self._get_ownership_percentage(d),
            "Ownership Percentage": lambda d: self._get_ownership_percentage(d),
            "EIN": lambda d: self._get_nested(d, 'business', 'primary_business', 'ein'),
            
            # Citizenship Questions
            "Are you a U.S. Citizen?": lambda d: self._get_yes_no(self._get_nested(d, 'personal', 'primary_applicant', 'citizenship', 'is_us_citizen')),
            "US Citizen": lambda d: self._get_yes_no(self._get_nested(d, 'personal', 'primary_applicant', 'citizenship', 'is_us_citizen')),
            
            # Other Yes/No Questions
            "Do you have ownership in other entities aside from the Applicant Business?": lambda d: self._check_other_businesses(d),
            "Have you ever declared bankruptcy?": lambda d: self._get_yes_no(self._get_nested(d, 'checkboxes_and_questions', 'has_declared_bankruptcy')),
            "Are you a defendant in any lawsuits or legal actions?": lambda d: self._get_yes_no(self._get_nested(d, 'checkboxes_and_questions', 'pending_lawsuits')),
            "Are you delinquent on any taxes?": lambda d: self._get_yes_no(self._get_nested(d, 'checkboxes_and_questions', 'delinquent_on_taxes')),
        }
        
        # Apply mapping rules
        for field_name in form_fields:
            # Try exact match
            if field_name in mapping_rules:
                try:
                    value = mapping_rules[field_name](extracted_data)
                    if value:
                        filled_fields[field_name] = value
                except Exception:
                    pass  # Skip if mapping fails
            
            # Try case-insensitive match
            else:
                for rule_name, rule_func in mapping_rules.items():
                    if field_name.lower() == rule_name.lower():
                        try:
                            value = rule_func(extracted_data)
                            if value:
                                filled_fields[field_name] = value
                                break
                        except Exception:
                            pass
        
        return filled_fields
    
    def _get_nested(self, data: Dict, *keys) -> Any:
        """Safely get nested dictionary values."""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current
    
    def _get_full_name(self, data: Dict) -> str:
        """Construct full name from structured data."""
        name_parts = self._get_nested(data, 'personal', 'primary_applicant', 'name')
        if not name_parts:
            return None
        
        parts = []
        for key in ['first', 'middle', 'last', 'suffix']:
            if key in name_parts and name_parts[key]:
                parts.append(name_parts[key])
        
        return ' '.join(parts) if parts else None
    
    def _get_address_street(self, data: Dict, address_type: str = 'current_residence') -> str:
        """Get street address."""
        address = self._get_nested(data, 'addresses', address_type)
        if address and 'street' in address:
            return address['street']
        return None
    
    def _get_address_csz(self, data: Dict, address_type: str = 'current_residence') -> str:
        """Get city, state, zip as single string."""
        address = self._get_nested(data, 'addresses', address_type)
        if not address:
            return None
        
        parts = []
        if 'city' in address:
            parts.append(address['city'])
        if 'state' in address:
            parts.append(address['state'])
        if 'zip' in address:
            parts.append(str(address['zip']))
        
        if len(parts) == 3:
            return f"{parts[0]}, {parts[1]} {parts[2]}"
        elif parts:
            return ', '.join(parts)
        return None
    
    def _get_ownership_percentage(self, data: Dict) -> str:
        """Get ownership percentage, trying multiple sources."""
        # Try primary applicant ownership
        pct = self._get_nested(data, 'personal', 'primary_applicant', 'ownership_percentage')
        if pct:
            return f"{pct}%" if not str(pct).endswith('%') else str(pct)
        
        # Try business ownership array
        ownership = self._get_nested(data, 'business', 'primary_business', 'ownership')
        if ownership and isinstance(ownership, list):
            # Look for primary applicant in ownership list
            applicant_name = self._get_full_name(data)
            if applicant_name:
                for owner in ownership:
                    if owner.get('name') and applicant_name.lower() in owner['name'].lower():
                        if 'percentage' in owner:
                            return f"{owner['percentage']}%"
        
        return None
    
    def _get_yes_no(self, value: Any) -> str:
        """Convert boolean or various inputs to Yes/No."""
        if value is None:
            return None
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, str):
            lower = value.lower()
            if lower in ['yes', 'y', 'true', '1']:
                return "Yes"
            elif lower in ['no', 'n', 'false', '0']:
                return "No"
        return None
    
    def _check_other_businesses(self, data: Dict) -> str:
        """Check if there are other businesses besides primary."""
        affiliated = self._get_nested(data, 'business', 'affiliated_businesses')
        if affiliated and isinstance(affiliated, list) and len(affiliated) > 0:
            return "Yes"
        return "No"
    
    def _format_date(self, date_str: Any) -> str:
        """Format date to MM/DD/YYYY."""
        if not date_str:
            return None
        
        date_str = str(date_str)
        
        # If already in MM/DD/YYYY format
        if '/' in date_str:
            parts = date_str.split('/')
            if len(parts) == 3:
                return date_str
        
        # If in YYYY-MM-DD format
        if '-' in date_str:
            parts = date_str.split('-')
            if len(parts) == 3 and len(parts[0]) == 4:
                return f"{parts[1]}/{parts[2]}/{parts[0]}"
        
        return date_str  # Return as-is if format unknown


class LLMFormFillerWithPDF(LLMFormFiller):
    """
    Extended form filler that generates actual PDF files.
    Combines LLM extraction with deterministic PDF filling.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with PDF generation capability."""
        super().__init__(api_key)
        self.pdf_generator = PDFFormGenerator()
    
    async def extract_and_fill_pdf(
        self,
        documents_folder: Union[str, Path],
        template_name: str = "Live Oak",
        output_dir: Union[str, Path] = "outputs/filled_pdfs"
    ) -> Dict[str, Any]:
        """
        Complete workflow: Extract → Fill → Generate PDF.
        
        Args:
            documents_folder: Folder with source documents
            template_name: Which template to use
            output_dir: Where to save filled PDF
            
        Returns:
            Dict with filled data and PDF path
        """
        # Determine template path
        if "Live Oak" in template_name:
            template_path = Path("templates/Live Oak Express - Application Forms.pdf")
        else:
            template_path = Path("templates/Huntington Bank Personal Financial Statement.pdf")
        
        # Extract and fill form data (existing functionality)
        filled_data = await self.fill_forms_from_documents(
            documents_folder,
            template_path
        )
        
        # Generate actual PDF
        if 'filled_fields' in filled_data and filled_data['filled_fields']:
            pdf_path = self.pdf_generator.generate_filled_pdf(
                template_name,
                filled_data['filled_fields'],
                output_dir
            )
            
            if pdf_path:
                filled_data['pdf_path'] = str(pdf_path)
                print(f"📄 Generated PDF: {pdf_path}")
            else:
                print("❌ Failed to generate PDF")
        
        return filled_data


class SimpleLoanApplicationProcessor:
    """
    Simplified interface for processing complete loan applications.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.filler = LLMFormFiller(api_key)
    
    async def process_application(
        self,
        applicant_name: str,
        documents_folder: Union[str, Path],
        output_folder: Union[str, Path] = "outputs/filled_forms"
    ) -> Dict[str, Any]:
        """
        Process a complete loan application for an applicant.
        
        Args:
            applicant_name: Name of the applicant (for organization)
            documents_folder: Folder with applicant's documents
            output_folder: Where to save filled forms
            
        Returns:
            Summary of all filled forms
        """
        documents_folder = Path(documents_folder)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        
        print(f"🏦 Processing loan application for: {applicant_name}")
        print("=" * 60)
        
        # Find all form templates
        templates_folder = Path("templates")
        form_templates = [
            templates_folder / "Live Oak Express - Application Forms.pdf",
            templates_folder / "Huntington Bank Personal Financial Statement.pdf"
        ]
        
        results = {}
        
        for template in form_templates:
            if template.exists():
                print(f"\n📝 Filling: {template.name}")
                
                # Fill the form
                filled_form = await self.filler.fill_forms_from_documents(
                    documents_folder,
                    template
                )
                
                # Save result
                output_file = output_folder / f"{applicant_name}_{template.stem}_filled.json"
                with open(output_file, 'w') as f:
                    json.dump(filled_form, f, indent=2)
                
                print(f"💾 Saved to: {output_file}")
                
                # Store result
                results[template.name] = {
                    'completion': filled_form.get('completion_percentage', 0),
                    'filled_fields': len(filled_form.get('filled_fields', {})),
                    'output_file': str(output_file)
                }
        
        # Create summary
        summary = {
            'applicant': applicant_name,
            'forms_processed': len(results),
            'forms': results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save summary
        summary_file = output_folder / f"{applicant_name}_application_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📊 Application Summary saved to: {summary_file}")
        
        return summary