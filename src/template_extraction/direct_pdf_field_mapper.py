"""
Direct PDF Field Mapper - Alternative to DocAI Form Parser
Extracts field metadata directly from blank PDF templates and maps master JSON data.

This bypasses the Google Document AI Form Parser limitation that it
"doesn't reliably parse a KVP with an unfilled value, such as a blank form"
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pypdf import PdfReader
from difflib import SequenceMatcher

class DirectPDFFieldMapper:
    """
    Maps master JSON data to PDF form fields by:
    1. Extracting field names directly from blank PDF templates
    2. Using intelligent fuzzy matching to map data fields to PDF fields
    3. Handling field type conversions (text, checkbox, dropdown)
    """
    
    def __init__(self):
        """Initialize the mapper with common field name variations."""
        self.field_cache = {}
        
        # Common field name transformations
        self.field_synonyms = {
            # Personal Information
            "full_name": ["Name", "Full Legal Name", "Applicant Full Legal Name", "Primary Applicant Name"],
            "first_name": ["First Name", "Given Name", "First"],
            "last_name": ["Last Name", "Surname", "Family Name", "Last"],
            "ssn": ["Social Security Number", "SSN", "Tax ID", "Social Security"],
            "date_of_birth": ["Date of Birth", "DOB", "Birth Date", "Birthdate"],
            "phone": ["Phone", "Telephone Number", "Mobile Telephone Number", "Phone Number", "Business Phone"],
            "email": ["Email", "Email address", "EMAIL", "Email Address"],
            "address": ["Address", "Residence Address", "Street Address", "Home Address"],
            "city": ["City", "City State Zip", "City, State, & Zip Code"],
            
            # Business Information
            "business_name": ["Business Name", "Business Applicant Name", "Company Name", "Legal Name"],
            "ein": ["EIN", "Tax ID", "Federal Tax ID", "Employer Identification Number"],
            "business_address": ["Business Address", "Company Address", "Office Address"],
            "ownership_percentage": ["Ownership %", "What percentage of the applicant business dowill you own", "Ownership Row1"],
            
            # Financial Information
            "total_assets": ["Total Assets", "Total", "Assets Total"],
            "total_liabilities": ["Total Liabilities", "Total Liabilities .", "Liabilities Total"],
            "net_worth": ["Net Worth", "Net Worth (Total Assets minus Total Liabilities)"],
            "annual_income": ["Annual Income", "Salary", "Total Income"],
            "real_estate_value": ["Real Estate", "Real Estate (Describe in Section 4)", "Real Estate Value"],
            "stocks_bonds": ["Stocks and Bonds", "Stocks and Bonds (Describe in Section 3)", "Securities"],
            "cash": ["Cash", "Cash on Hand", "Savings Accounts", "Checking Accounts"],
            
            # Checkboxes
            "married": ["Married", "Marital Status - Married"],
            "unmarried": ["Unmarried", "Single", "Marital Status - Single"],
            "us_citizen": ["US Citizen", "Are you a US Citizen", "Citizenship - US"],
            "yes": ["Yes", "check 15", "check 16", "check 10"],
            "no": ["No", "check 17", "check 18", "check 13"]
        }
        
        # Reverse mapping for quick lookups
        self.synonym_to_standard = {}
        for standard, synonyms in self.field_synonyms.items():
            for synonym in synonyms:
                self.synonym_to_standard[synonym.lower()] = standard
    
    def extract_pdf_fields(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract all form fields from a blank PDF template.
        
        Args:
            pdf_path: Path to the PDF template
            
        Returns:
            Dictionary of field names to field metadata
        """
        pdf_path = Path(pdf_path)
        
        # Check cache
        cache_key = str(pdf_path)
        if cache_key in self.field_cache:
            return self.field_cache[cache_key]
        
        fields = {}
        
        try:
            reader = PdfReader(pdf_path)
            
            # Get all form fields
            if hasattr(reader, 'get_fields'):
                all_fields = reader.get_fields() or {}
            else:
                all_fields = {}
            
            for field_name, field_obj in all_fields.items():
                # Clean field name
                clean_name = field_name.replace('\x00', '').strip()
                
                # Determine field type
                field_type = self._get_field_type(field_obj)
                
                # Get field options for dropdowns
                options = self._get_field_options(field_obj) if field_type == "choice" else None
                
                fields[clean_name] = {
                    "type": field_type,
                    "original_name": field_name,
                    "options": options,
                    "standard_field": self._get_standard_field_name(clean_name)
                }
            
            # Cache the result
            self.field_cache[cache_key] = fields
            
        except Exception as e:
            print(f"Error extracting fields from {pdf_path}: {e}")
        
        return fields
    
    def map_data_to_pdf_fields(self, master_data: Dict[str, Any], 
                               pdf_fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map master JSON data to PDF form fields using intelligent matching.
        
        Args:
            master_data: Extracted data from documents (master JSON)
            pdf_fields: Field structure from PDF template
            
        Returns:
            Mapped data ready for PDF filling
        """
        mapped_data = {}
        unmapped_fields = []
        
        # Flatten master data for easier access
        flat_data = self._flatten_dict(master_data)
        
        for pdf_field, field_info in pdf_fields.items():
            field_type = field_info.get("type", "text")
            standard_name = field_info.get("standard_field")
            
            # Try multiple matching strategies
            value = None
            confidence = 0.0
            
            # Strategy 1: Direct standard field match
            if standard_name and standard_name in flat_data:
                value = flat_data[standard_name]
                confidence = 0.95
            
            # Strategy 2: Fuzzy match on field names
            if value is None:
                value, match_key, confidence = self._fuzzy_match_field(pdf_field, flat_data)
            
            # Strategy 3: Look for similar field patterns
            if value is None and confidence < 0.7:
                value, confidence = self._pattern_match_field(pdf_field, flat_data)
            
            # Apply value if confident enough
            if value is not None and confidence >= 0.6:
                # Convert value based on field type
                converted_value = self._convert_value_for_field_type(value, field_type, field_info)
                if converted_value is not None:
                    mapped_data[pdf_field] = converted_value
                    print(f"  ✓ Mapped '{pdf_field}' = '{converted_value}' (confidence: {confidence:.2f})")
            else:
                unmapped_fields.append(pdf_field)
        
        if unmapped_fields and len(unmapped_fields) < 20:  # Only show first 20
            print(f"\n  ⚠️ {len(unmapped_fields)} fields could not be mapped:")
            for field in unmapped_fields[:10]:
                print(f"    - {field}")
        
        return mapped_data
    
    def _get_field_type(self, field_obj: Any) -> str:
        """Determine the type of a PDF form field."""
        if hasattr(field_obj, 'get') and '/FT' in field_obj:
            ft = str(field_obj['/FT'])
            if 'Btn' in ft:
                return "checkbox"
            elif 'Tx' in ft:
                return "text"
            elif 'Ch' in ft:
                return "choice"
            elif 'Sig' in ft:
                return "signature"
        return "text"
    
    def _get_field_options(self, field_obj: Any) -> Optional[List[str]]:
        """Extract options from a dropdown/choice field."""
        if hasattr(field_obj, 'get') and '/Opt' in field_obj:
            options = field_obj['/Opt']
            if isinstance(options, list):
                return [str(opt) for opt in options]
        return None
    
    def _get_standard_field_name(self, field_name: str) -> Optional[str]:
        """Get the standard field name for a PDF field."""
        field_lower = field_name.lower()
        return self.synonym_to_standard.get(field_lower)
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for easier field matching."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                # Handle confidence objects
                if 'value' in v and 'confidence' in v:
                    items.append((new_key, v['value']))
                else:
                    items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def _fuzzy_match_field(self, pdf_field: str, flat_data: Dict[str, Any]) -> Tuple[Any, str, float]:
        """Find the best fuzzy match for a PDF field in the data."""
        best_match = None
        best_key = None
        best_score = 0.0
        
        pdf_field_clean = self._clean_field_name(pdf_field)
        
        for data_key, data_value in flat_data.items():
            if data_value is None:
                continue
            
            data_key_clean = self._clean_field_name(data_key)
            
            # Calculate similarity
            score = SequenceMatcher(None, pdf_field_clean, data_key_clean).ratio()
            
            # Boost score for partial matches
            if pdf_field_clean in data_key_clean or data_key_clean in pdf_field_clean:
                score = min(score * 1.2, 1.0)
            
            # Check for common keywords
            common_keywords = set(pdf_field_clean.split()) & set(data_key_clean.split())
            if common_keywords:
                score = min(score + 0.1 * len(common_keywords), 1.0)
            
            if score > best_score:
                best_score = score
                best_match = data_value
                best_key = data_key
        
        return best_match, best_key, best_score
    
    def _pattern_match_field(self, pdf_field: str, flat_data: Dict[str, Any]) -> Tuple[Any, float]:
        """Use pattern matching to find field values."""
        pdf_field_lower = pdf_field.lower()
        
        # SSN pattern
        if 'social security' in pdf_field_lower or 'ssn' in pdf_field_lower:
            for key, value in flat_data.items():
                if value and re.match(r'^\d{3}-?\d{2}-?\d{4}$', str(value)):
                    return value, 0.8
        
        # EIN pattern
        if 'ein' in pdf_field_lower or 'tax id' in pdf_field_lower:
            for key, value in flat_data.items():
                if value and re.match(r'^\d{2}-?\d{7}$', str(value)):
                    return value, 0.8
        
        # Email pattern
        if 'email' in pdf_field_lower:
            for key, value in flat_data.items():
                if value and '@' in str(value):
                    return value, 0.8
        
        # Phone pattern
        if 'phone' in pdf_field_lower or 'telephone' in pdf_field_lower:
            for key, value in flat_data.items():
                if value and re.match(r'^[\d\.\-\(\)\s]+$', str(value)) and len(str(value)) >= 10:
                    return value, 0.7
        
        # Dollar amount pattern
        if any(keyword in pdf_field_lower for keyword in ['total', 'amount', 'value', 'income', 'asset', 'liabilit']):
            for key, value in flat_data.items():
                if key.lower() in pdf_field_lower or pdf_field_lower in key.lower():
                    if value and ('$' in str(value) or re.match(r'^[\d,\.]+$', str(value))):
                        return value, 0.7
        
        return None, 0.0
    
    def _clean_field_name(self, field_name: str) -> str:
        """Clean and normalize field names for comparison."""
        # Remove special characters and normalize spaces
        cleaned = re.sub(r'[^\w\s]', ' ', field_name)
        cleaned = ' '.join(cleaned.split()).lower()
        return cleaned
    
    def _convert_value_for_field_type(self, value: Any, field_type: str, 
                                      field_info: Dict[str, Any]) -> Any:
        """Convert value to appropriate type for PDF field."""
        if value is None:
            return None
        
        if field_type == "text":
            # Clean dollar amounts
            if isinstance(value, str) and '$' in value:
                value = value.replace('\n', ' ').strip()
            return str(value)
        
        elif field_type == "checkbox":
            # Convert to boolean
            if isinstance(value, bool):
                return value
            value_str = str(value).lower()
            if value_str in ['yes', 'true', '1', 'x', 'checked']:
                return True
            elif value_str in ['no', 'false', '0', '', 'unchecked']:
                return False
            return None
        
        elif field_type == "choice":
            # Match to available options
            options = field_info.get("options", [])
            if options and value:
                value_str = str(value)
                # Direct match
                if value_str in options:
                    return value_str
                # Case-insensitive match
                for opt in options:
                    if opt.lower() == value_str.lower():
                        return opt
            return str(value) if value else None
        
        return str(value)