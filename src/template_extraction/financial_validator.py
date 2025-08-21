"""
Financial Business Rules Validator.
Implements deterministic validation rules for financial document data.
"""

import re
import datetime
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal, InvalidOperation


class FinancialBusinessRulesValidator:
    """
    Validates extracted financial data using business rules.
    
    Implements deterministic validation patterns including:
    - SSN and EIN format validation
    - Financial calculation verification
    - Mandatory field checks
    - Cross-reference validation
    """
    
    def __init__(self):
        """Initialize validator with business rules configuration."""
        # SSN patterns - various formats
        self.ssn_patterns = [
            r'^\d{3}-\d{2}-\d{4}$',  # XXX-XX-XXXX
            r'^\d{9}$',              # XXXXXXXXX
            r'^\d{3} \d{2} \d{4}$'   # XXX XX XXXX
        ]
        
        # EIN patterns - various formats
        self.ein_patterns = [
            r'^\d{2}-\d{7}$',        # XX-XXXXXXX
            r'^\d{9}$'               # XXXXXXXXX
        ]
        
        # Critical fields that must be present for complete processing
        self.critical_fields = [
            'ssn', 'social_security_number',
            'ein', 'employer_id', 'federal_tax_id',
            'total_assets', 'total_liabilities', 'net_worth',
            'business_name', 'legal_name', 'company_name'
        ]
        
        # Financial calculation tolerance (for rounding differences)
        self.calculation_tolerance = 0.01
        
    def validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all validation rules on extracted data.
        
        Args:
            data: Extracted data dictionary (nested structure)
            
        Returns:
            Dict containing:
            - passed_rules: List of rules that passed
            - failed_rules: List of rules that failed with details
            - warnings: List of non-critical issues
            - overall_score: Validation score (0.0-1.0)
            - confidence_adjustments: Suggested confidence modifications
        """
        validation_results = {
            'passed_rules': [],
            'failed_rules': [],
            'warnings': [],
            'overall_score': 1.0,
            'confidence_adjustments': {},
            'rule_details': {}
        }
        
        # Flatten data for easier searching
        flat_data = self._flatten_dict(data)
        
        # Run validation rules
        self._validate_ssn_format(flat_data, validation_results)
        self._validate_ein_format(flat_data, validation_results)
        self._validate_financial_calculations(flat_data, validation_results)
        self._validate_mandatory_fields(flat_data, validation_results)
        self._validate_date_consistency(flat_data, validation_results)
        self._validate_percentage_ownership(flat_data, validation_results)
        self._validate_currency_formats(flat_data, validation_results)
        
        # Calculate overall score
        total_rules = len(validation_results['passed_rules']) + len(validation_results['failed_rules'])
        if total_rules > 0:
            validation_results['overall_score'] = len(validation_results['passed_rules']) / total_rules
        
        return validation_results
    
    def _validate_ssn_format(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Validate Social Security Number format."""
        ssn_fields = self._find_fields_by_name(flat_data, ['ssn', 'social_security_number', 'social_security'])
        
        for field_path, value in ssn_fields.items():
            if value and str(value).strip():
                ssn_value = str(value).strip()
                
                # Check if it's properly redacted or formatted
                if 'XXX' in ssn_value.upper() or '*' in ssn_value:
                    results['passed_rules'].append(f"SSN properly redacted: {field_path}")
                    results['rule_details'][f"ssn_redacted_{field_path}"] = {
                        'status': 'passed',
                        'value': ssn_value,
                        'message': 'SSN is properly redacted for privacy'
                    }
                else:
                    # Check format patterns
                    is_valid_format = any(re.match(pattern, ssn_value) for pattern in self.ssn_patterns)
                    
                    if is_valid_format:
                        results['passed_rules'].append(f"SSN format valid: {field_path}")
                        results['confidence_adjustments'][field_path] = 1.0
                        results['rule_details'][f"ssn_format_{field_path}"] = {
                            'status': 'passed',
                            'value': 'XXX-XX-' + ssn_value[-4:],  # Show only last 4
                            'message': 'SSN format is valid'
                        }
                    else:
                        results['failed_rules'].append(f"SSN format invalid: {field_path} = {ssn_value}")
                        results['confidence_adjustments'][field_path] = 0.3
                        results['rule_details'][f"ssn_format_{field_path}"] = {
                            'status': 'failed',
                            'value': ssn_value,
                            'message': f'SSN format invalid. Expected formats: XXX-XX-XXXX, XXXXXXXXX, or XXX XX XXXX'
                        }
    
    def _validate_ein_format(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Validate Employer Identification Number format."""
        ein_fields = self._find_fields_by_name(flat_data, ['ein', 'employer_id', 'federal_tax_id', 'tax_id'])
        
        for field_path, value in ein_fields.items():
            if value and str(value).strip():
                ein_value = str(value).strip()
                
                # Check format patterns
                is_valid_format = any(re.match(pattern, ein_value) for pattern in self.ein_patterns)
                
                if is_valid_format:
                    results['passed_rules'].append(f"EIN format valid: {field_path}")
                    results['confidence_adjustments'][field_path] = 1.0
                    results['rule_details'][f"ein_format_{field_path}"] = {
                        'status': 'passed',
                        'value': ein_value,
                        'message': 'EIN format is valid'
                    }
                else:
                    results['failed_rules'].append(f"EIN format invalid: {field_path} = {ein_value}")
                    results['confidence_adjustments'][field_path] = 0.3
                    results['rule_details'][f"ein_format_{field_path}"] = {
                        'status': 'failed',
                        'value': ein_value,
                        'message': f'EIN format invalid. Expected formats: XX-XXXXXXX or XXXXXXXXX'
                    }
    
    def _validate_financial_calculations(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Validate financial calculations (Assets - Liabilities = Net Worth)."""
        # Find financial fields
        assets_fields = self._find_fields_by_name(flat_data, ['total_assets', 'assets', 'total_asset_value'])
        liabilities_fields = self._find_fields_by_name(flat_data, ['total_liabilities', 'liabilities', 'total_liability_value'])
        net_worth_fields = self._find_fields_by_name(flat_data, ['net_worth', 'total_net_worth', 'networth'])
        
        # Try to find a complete set of values for calculation
        for assets_path, assets_value in assets_fields.items():
            for liabilities_path, liabilities_value in liabilities_fields.items():
                for net_worth_path, net_worth_value in net_worth_fields.items():
                    
                    try:
                        assets_num = self._parse_currency(assets_value)
                        liabilities_num = self._parse_currency(liabilities_value)
                        net_worth_num = self._parse_currency(net_worth_value)
                        
                        if assets_num is not None and liabilities_num is not None and net_worth_num is not None:
                            calculated_net_worth = assets_num - liabilities_num
                            difference = abs(calculated_net_worth - net_worth_num)
                            
                            if difference <= self.calculation_tolerance:
                                results['passed_rules'].append(f"Financial calculation valid: Assets({assets_num}) - Liabilities({liabilities_num}) = Net Worth({net_worth_num})")
                                results['confidence_adjustments'][assets_path] = 1.0
                                results['confidence_adjustments'][liabilities_path] = 1.0
                                results['confidence_adjustments'][net_worth_path] = 1.0
                                results['rule_details']['financial_calculation'] = {
                                    'status': 'passed',
                                    'assets': assets_num,
                                    'liabilities': liabilities_num,
                                    'net_worth': net_worth_num,
                                    'calculated_net_worth': calculated_net_worth,
                                    'difference': difference,
                                    'message': 'Financial calculation is correct'
                                }
                            else:
                                results['failed_rules'].append(f"Financial calculation mismatch: Assets({assets_num}) - Liabilities({liabilities_num}) ≠ Net Worth({net_worth_num}), difference: {difference}")
                                results['confidence_adjustments'][net_worth_path] = 0.5
                                results['rule_details']['financial_calculation'] = {
                                    'status': 'failed',
                                    'assets': assets_num,
                                    'liabilities': liabilities_num,
                                    'net_worth': net_worth_num,
                                    'calculated_net_worth': calculated_net_worth,
                                    'difference': difference,
                                    'message': f'Calculation error: expected {calculated_net_worth}, got {net_worth_num}'
                                }
                            return  # Exit after first complete calculation found
                            
                    except (ValueError, TypeError, InvalidOperation):
                        # Skip invalid numeric values
                        continue
        
        # If we get here, no complete calculation was possible
        results['warnings'].append("Could not verify financial calculations - missing or invalid Assets/Liabilities/Net Worth values")
    
    def _validate_mandatory_fields(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Check for presence of mandatory fields."""
        found_critical = []
        missing_critical = []
        
        for critical_field in self.critical_fields:
            field_found = False
            for field_path, value in flat_data.items():
                if critical_field.lower() in field_path.lower() and value and str(value).strip():
                    found_critical.append((critical_field, field_path, value))
                    field_found = True
                    break
            
            if not field_found:
                missing_critical.append(critical_field)
        
        # Report results
        for field_name, field_path, value in found_critical:
            results['passed_rules'].append(f"Mandatory field present: {field_name} ({field_path})")
            results['confidence_adjustments'][field_path] = 1.0
            
        for field_name in missing_critical:
            results['warnings'].append(f"Missing recommended field: {field_name}")
    
    def _validate_date_consistency(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Validate date consistency (e.g., tax year should be recent, dates should be logical)."""
        date_fields = self._find_fields_by_name(flat_data, ['date', 'year', 'tax_year', 'dob', 'birth_date'])
        current_year = datetime.datetime.now().year
        
        for field_path, value in date_fields.items():
            if value:
                try:
                    # Try to extract year from various formats
                    year_value = None
                    if isinstance(value, int) and 1900 <= value <= current_year + 1:
                        year_value = value
                    elif isinstance(value, str):
                        # Try to find 4-digit year in string
                        year_match = re.search(r'\b(19|20)\d{2}\b', str(value))
                        if year_match:
                            year_value = int(year_match.group())
                    
                    if year_value:
                        if 1900 <= year_value <= current_year + 1:
                            results['passed_rules'].append(f"Date reasonable: {field_path} = {year_value}")
                            results['confidence_adjustments'][field_path] = 1.0
                        else:
                            results['failed_rules'].append(f"Date unreasonable: {field_path} = {year_value}")
                            results['confidence_adjustments'][field_path] = 0.5
                            
                except (ValueError, TypeError):
                    # Skip invalid date values
                    pass
    
    def _validate_percentage_ownership(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Validate ownership percentages add up to reasonable totals."""
        ownership_fields = self._find_fields_by_name(flat_data, ['ownership', 'percentage', 'percent', 'share'])
        
        ownership_values = []
        for field_path, value in ownership_fields.items():
            try:
                num_value = float(str(value).replace('%', '').replace(',', ''))
                
                # Handle both decimal (0.5) and percentage (50) formats
                if num_value > 1:
                    num_value = num_value / 100
                
                if 0 <= num_value <= 1:
                    ownership_values.append((field_path, num_value))
                    
            except (ValueError, TypeError):
                continue
        
        if ownership_values:
            total_ownership = sum(value for _, value in ownership_values)
            
            if 0.99 <= total_ownership <= 1.01:  # Allow for rounding
                results['passed_rules'].append(f"Ownership percentages valid: total = {total_ownership:.1%}")
                for field_path, _ in ownership_values:
                    results['confidence_adjustments'][field_path] = 1.0
            elif total_ownership > 1.01:
                results['failed_rules'].append(f"Ownership percentages exceed 100%: total = {total_ownership:.1%}")
                for field_path, _ in ownership_values:
                    results['confidence_adjustments'][field_path] = 0.7
    
    def _validate_currency_formats(self, flat_data: Dict[str, Any], results: Dict[str, Any]) -> None:
        """Validate currency values are reasonable and properly formatted."""
        currency_fields = self._find_fields_by_name(flat_data, ['amount', 'value', 'assets', 'liabilities', 'income', 'revenue', 'balance'])
        
        for field_path, value in currency_fields.items():
            if value:
                parsed_value = self._parse_currency(value)
                if parsed_value is not None:
                    # Check for reasonable ranges
                    if 0 <= parsed_value <= 1_000_000_000:  # $1B max
                        results['passed_rules'].append(f"Currency value reasonable: {field_path}")
                        results['confidence_adjustments'][field_path] = 1.0
                    else:
                        results['warnings'].append(f"Currency value unusually large: {field_path} = {parsed_value}")
                        results['confidence_adjustments'][field_path] = 0.8
    
    def _find_fields_by_name(self, flat_data: Dict[str, Any], field_names: List[str]) -> Dict[str, Any]:
        """Find fields whose keys contain any of the specified names."""
        matches = {}
        for field_path, value in flat_data.items():
            field_path_lower = field_path.lower()
            for field_name in field_names:
                if field_name.lower() in field_path_lower:
                    matches[field_path] = value
                    break
        return matches
    
    def _parse_currency(self, value: Any) -> Optional[float]:
        """Parse currency value from various formats."""
        if value is None:
            return None
            
        try:
            # Convert to string and clean up
            str_value = str(value).strip()
            
            # Remove currency symbols and commas
            cleaned = str_value.replace('$', '').replace(',', '').replace(' ', '')
            
            # Handle parentheses as negative
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    def _flatten_dict(self, obj: Any, parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for field searching."""
        items = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                # Skip metadata and error fields
                if key in ["metadata", "_metadata", "_extraction_failed", "raw_text", "error", "_confidence"]:
                    continue
                
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                
                if isinstance(value, dict):
                    items.update(self._flatten_dict(value, new_key, separator))
                elif isinstance(value, list):
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            items.update(self._flatten_dict(item, f"{new_key}[{i}]", separator))
                        elif item is not None and item != "":
                            items[f"{new_key}[{i}]"] = item
                elif value is not None and value != "" and value != []:
                    items[new_key] = value
        
        return items