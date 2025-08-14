"""
Dynamic Form Field Mapper - Generates field mappings on-the-fly from PDF forms.

This module can:
1. Extract field names directly from PDF forms using pdfplumber
2. Generate mappings dynamically without pre-existing JSON files
3. Cache mappings for performance
4. Work with any PDF form
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
import pdfplumber


class DynamicFormMapper:
    """
    Dynamically extracts and maps PDF form fields.
    No need for pre-existing mapping JSON files.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize with optional cache directory."""
        self.cache_dir = cache_dir or Path("outputs/form_mappings")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
    
    def get_form_fields(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract all form fields from a PDF.
        Returns a structure compatible with LLMFormFiller.
        
        Args:
            pdf_path: Path to the PDF form
            
        Returns:
            Dict with form_title, sections, and fields
        """
        pdf_path = Path(pdf_path)
        
        # Check cache first
        cache_key = self._get_cache_key(pdf_path)
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check file cache
        cache_file = self.cache_dir / f"{pdf_path.stem}_dynamic.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    self._cache[cache_key] = cached_data
                    return cached_data
            except:
                pass  # If cache is corrupt, regenerate
        
        # Extract fields from PDF
        fields = self._extract_pdf_fields(pdf_path)
        
        # Organize into sections
        sections = self._organize_sections(fields)
        
        # Create form structure
        form_structure = {
            "form_title": pdf_path.stem.replace('_', ' ').replace('-', ' '),
            "sections": list(sections.keys()),
            "fields": fields,
            "metadata": {
                "total_fields": len(fields),
                "source": str(pdf_path),
                "generated_by": "DynamicFormMapper"
            }
        }
        
        # Cache the result
        self._cache[cache_key] = form_structure
        try:
            with open(cache_file, 'w') as f:
                json.dump(form_structure, f, indent=2)
        except:
            pass  # Cache write failure is not critical
        
        return form_structure
    
    def _extract_pdf_fields(self, pdf_path: Path) -> Dict[str, Dict]:
        """
        Extract all form fields from a PDF using pdfplumber.
        
        Returns:
            Dict mapping field names to field info
        """
        fields = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    if page.annots:
                        for annot in page.annots:
                            if 'data' in annot and annot['data']:
                                field_info = self._parse_annotation(annot['data'], page_num)
                                if field_info and field_info['name']:
                                    fields[field_info['name']] = {
                                        'field_name': field_info['name'],
                                        'field_type': field_info['type'],
                                        'required': field_info.get('required', False),
                                        'page': page_num,
                                        'options': field_info.get('options', None)
                                    }
        except Exception as e:
            print(f"Warning: Could not extract fields from PDF: {e}")
            # Return common fields as fallback
            return self._get_common_fields()
        
        # If no fields found, return common fields
        if not fields:
            print("Warning: No form fields found in PDF, using common fields")
            return self._get_common_fields()
        
        return fields
    
    def _parse_annotation(self, data: Dict, page_num: int) -> Optional[Dict]:
        """Parse a PDF annotation to extract field information."""
        if 'FT' not in data:
            return None
        
        # Extract field name
        field_name = None
        if 'T' in data:
            if isinstance(data['T'], bytes):
                field_name = data['T'].decode('utf-8', errors='ignore')
            else:
                field_name = str(data['T'])
        
        if not field_name:
            return None
        
        # Determine field type
        field_type_code = str(data.get('FT', ''))
        field_type = 'text'  # default
        
        if field_type_code == "/'Btn":
            field_type = 'checkbox'
        elif field_type_code == "/'Ch":
            field_type = 'dropdown'
        elif field_type_code == "/'Sig":
            field_type = 'signature'
        elif 'date' in field_name.lower():
            field_type = 'date'
        
        # Check if required
        required = False
        if 'Ff' in data:
            # Bit 1 indicates required field in PDF spec
            required = bool(data['Ff'] & 2)
        
        result = {
            'name': field_name,
            'type': field_type,
            'required': required,
            'page': page_num
        }
        
        # Extract options for dropdowns
        if field_type == 'dropdown' and 'Opt' in data:
            result['options'] = data['Opt']
        
        return result
    
    def _organize_sections(self, fields: Dict[str, Dict]) -> Dict[str, List[str]]:
        """
        Organize fields into logical sections based on field names.
        
        Returns:
            Dict mapping section names to lists of field names
        """
        sections = {
            "Personal Information": [],
            "Business Information": [],
            "Financial Information": [],
            "Additional Information": []
        }
        
        for field_name in fields.keys():
            field_lower = field_name.lower()
            
            # Categorize based on keywords
            if any(word in field_lower for word in 
                   ['name', 'ssn', 'social', 'birth', 'phone', 'email', 
                    'address', 'city', 'state', 'zip', 'marital', 'citizen']):
                sections["Personal Information"].append(field_name)
            elif any(word in field_lower for word in 
                     ['business', 'company', 'ownership', 'ein', 'entity', 
                      'corporation', 'llc', 'partnership']):
                sections["Business Information"].append(field_name)
            elif any(word in field_lower for word in 
                     ['asset', 'liability', 'income', 'expense', 'worth', 
                      'financial', 'bank', 'loan', 'mortgage', 'debt']):
                sections["Financial Information"].append(field_name)
            else:
                sections["Additional Information"].append(field_name)
        
        # Remove empty sections
        return {k: v for k, v in sections.items() if v}
    
    def _get_common_fields(self) -> Dict[str, Dict]:
        """
        Return common loan application fields as fallback.
        Used when PDF field extraction fails.
        """
        common_fields = [
            # Personal Information
            ("Name", "text", True),
            ("Social Security Number", "text", False),
            ("Date of Birth", "date", False),
            ("Mobile Telephone Number", "text", True),
            ("Email address", "text", True),
            ("Residence Address", "text", True),
            ("City, State, Zip", "text", True),
            ("Marital Status", "text", False),
            ("Spouse Name", "text", False),
            
            # Business Information  
            ("Business Applicant Name", "text", True),
            ("Business Type", "text", False),
            ("Business Address", "text", False),
            ("Business Phone", "text", False),
            ("Years in Business", "text", False),
            ("What percentage of the applicant business do/will you own?", "text", False),
            ("Do you have ownership in other entities aside from the Applicant Business?", "checkbox", False),
            
            # Financial Information
            ("Total Assets", "text", False),
            ("Total Liabilities", "text", False),
            ("Net Worth", "text", False),
            ("Annual Income", "text", False),
            ("Loan Amount Requested", "text", True),
            
            # Citizenship/Legal
            ("Are you a U.S. Citizen?", "checkbox", False),
            ("Are you currently liable for alimony payments, child support or separate maintenance income?", "checkbox", False),
            ("Are you more than 60 days delinquent on any obligation to pay child support?", "checkbox", False),
            ("Are you employed by the U.S. Government?", "checkbox", False),
        ]
        
        fields = {}
        for field_name, field_type, required in common_fields:
            fields[field_name] = {
                'field_name': field_name,
                'field_type': field_type,
                'required': required,
                'page': 1
            }
        
        return fields
    
    def _get_cache_key(self, pdf_path: Path) -> str:
        """Generate a cache key based on file path and modification time."""
        stat = pdf_path.stat()
        key_string = f"{pdf_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(key_string.encode()).hexdigest()


# Convenience function for backward compatibility
def extract_form_fields(pdf_path: Path) -> Dict[str, Any]:
    """
    Extract form fields from a PDF.
    
    Args:
        pdf_path: Path to the PDF form
        
    Returns:
        Form structure dict with fields
    """
    mapper = DynamicFormMapper()
    return mapper.get_form_fields(pdf_path)