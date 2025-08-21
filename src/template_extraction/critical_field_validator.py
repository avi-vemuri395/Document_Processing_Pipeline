"""
Critical Field Validator for Form Mapping Quality.
Validates critical field coverage and form-specific requirements for bank forms.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from decimal import Decimal, InvalidOperation


class CriticalFieldValidator:
    """
    Validates critical field coverage for specific bank forms.
    
    Implements form-level validation including:
    - Critical field coverage thresholds (80%+ for key forms)
    - Bank-specific mandatory fields
    - Form completion quality gates
    - Missing field impact assessment
    """
    
    def __init__(self):
        """Initialize validator with form specifications and critical field mappings."""
        self.form_specs_path = Path("templates/form_specs")
        self.coverage_thresholds = {
            "live_oak": {
                "application": 0.80,     # 80% coverage required
                "pfs": 0.85,            # 85% coverage required  
                "4506t": 0.95           # 95% coverage required (simple form)
            },
            "huntington": {
                "business_app": 0.75,   # 75% coverage required
                "tax_transcript": 0.90, # 90% coverage required
                "debt_schedule": 0.80,  # 80% coverage required
                "financial_statement": 0.85  # 85% coverage required
            },
            "wells_fargo": {
                "financial_questionnaire": 0.70,  # 70% coverage (complex form)
                "business_info": 0.85   # 85% coverage required
            }
        }
        
        # Critical fields that must be present for each bank
        self.critical_fields = {
            "live_oak": {
                "application": [
                    "Business Legal Name", "DBA Name", "Business Address", 
                    "Business Phone", "Name", "Title", "Email Address"
                ],
                "pfs": [
                    "Business Name", "Total Assets", "Total Liabilities", 
                    "Net Worth", "Name", "Date"
                ],
                "4506t": [
                    "Name", "SSN", "Address", "Signature", "Date"
                ]
            },
            "huntington": {
                "business_app": [
                    "Legal Business Name", "Business Address", "Business Phone",
                    "Federal Tax ID", "Type of Entity", "Principal Name"
                ],
                "debt_schedule": [
                    "Creditor Name", "Original Amount", "Current Balance",
                    "Monthly Payment", "Maturity Date"
                ],
                "financial_statement": [
                    "Business Name", "Total Assets", "Total Liabilities",
                    "Net Worth", "Period Ending"
                ]
            },
            "wells_fargo": {
                "financial_questionnaire": [
                    "Business Name", "Business Type", "Annual Revenue",
                    "Years in Business", "Number of Employees"
                ],
                "business_info": [
                    "Legal Name", "DBA", "Address", "Phone", "EIN", "Industry"
                ]
            }
        }
        
        # Impact weights for missing fields
        self.field_impact_weights = {
            "high": 1.0,    # Critical business impact
            "medium": 0.6,  # Moderate impact
            "low": 0.3      # Low impact
        }
        
    def validate_form_mapping(
        self, 
        bank: str, 
        form_type: str, 
        mapped_data: Dict[str, Any],
        form_spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate form mapping quality and critical field coverage.
        
        Args:
            bank: Bank name (live_oak, huntington, wells_fargo)
            form_type: Form type (application, pfs, etc.)
            mapped_data: Dictionary of mapped form data
            form_spec: Optional form specification (will load if not provided)
            
        Returns:
            Dict containing:
            - coverage_score: Field coverage percentage (0.0-1.0)
            - critical_fields_status: Status of critical fields
            - missing_fields: List of missing critical fields
            - quality_gate_passed: Whether form meets quality threshold
            - recommendations: List of improvement recommendations
        """
        print(f"  🎯 Validating {bank} {form_type} form mapping...")
        
        # Load form specification if not provided
        if form_spec is None:
            form_spec = self._load_form_spec(bank, form_type)
        
        if not form_spec:
            return self._create_error_result(f"Form specification not found for {bank} {form_type}")
        
        # Calculate field coverage
        total_fields = len(form_spec.get('fields', []))
        filled_fields = len([v for v in mapped_data.values() if v and str(v).strip()])
        coverage_score = filled_fields / total_fields if total_fields > 0 else 0.0
        
        # Validate critical fields
        critical_fields_result = self._validate_critical_fields(bank, form_type, mapped_data)
        
        # Check quality gate
        threshold = self.coverage_thresholds.get(bank, {}).get(form_type, 0.70)
        quality_gate_passed = coverage_score >= threshold and critical_fields_result['all_critical_present']
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            bank, form_type, coverage_score, critical_fields_result, threshold
        )
        
        result = {
            'bank': bank,
            'form_type': form_type,
            'coverage_score': round(coverage_score, 3),
            'coverage_percentage': round(coverage_score * 100, 1),
            'total_fields': total_fields,
            'filled_fields': filled_fields,
            'missing_fields_count': total_fields - filled_fields,
            'critical_fields_status': critical_fields_result,
            'quality_threshold': threshold,
            'quality_gate_passed': quality_gate_passed,
            'recommendations': recommendations,
            'validation_timestamp': str(Path.cwd() / "temp")  # Placeholder
        }
        
        print(f"    • Coverage: {coverage_score:.1%} (threshold: {threshold:.1%})")
        print(f"    • Critical fields: {critical_fields_result['critical_present']}/{critical_fields_result['critical_total']}")
        print(f"    • Quality gate: {'✅ PASSED' if quality_gate_passed else '❌ FAILED'}")
        
        return result
    
    def _validate_critical_fields(self, bank: str, form_type: str, mapped_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate presence of critical fields for specific bank/form combination."""
        critical_field_names = self.critical_fields.get(bank, {}).get(form_type, [])
        
        if not critical_field_names:
            return {
                'critical_total': 0,
                'critical_present': 0,
                'all_critical_present': True,
                'missing_critical': [],
                'present_critical': []
            }
        
        missing_critical = []
        present_critical = []
        
        for critical_field in critical_field_names:
            # Check for exact match or partial match in mapped data
            field_found = False
            field_value = None
            
            # Exact match
            if critical_field in mapped_data:
                field_value = mapped_data[critical_field]
                if field_value and str(field_value).strip():
                    present_critical.append(critical_field)
                    field_found = True
            
            # Partial match (case-insensitive)
            if not field_found:
                for mapped_field, value in mapped_data.items():
                    if self._fields_match(critical_field, mapped_field):
                        if value and str(value).strip():
                            present_critical.append(f"{critical_field} (as {mapped_field})")
                            field_found = True
                            break
            
            if not field_found:
                missing_critical.append(critical_field)
        
        return {
            'critical_total': len(critical_field_names),
            'critical_present': len(present_critical),
            'all_critical_present': len(missing_critical) == 0,
            'missing_critical': missing_critical,
            'present_critical': present_critical
        }
    
    def _fields_match(self, critical_field: str, mapped_field: str) -> bool:
        """Check if field names match (handles variations in field naming)."""
        # Normalize field names for comparison
        def normalize(field_name):
            return field_name.lower().replace(' ', '').replace('_', '').replace('-', '')
        
        critical_normalized = normalize(critical_field)
        mapped_normalized = normalize(mapped_field)
        
        # Direct match
        if critical_normalized == mapped_normalized:
            return True
        
        # Partial matches for common variations
        variations = {
            'businesslegalname': ['businessname', 'legalname', 'companyname'],
            'dbaname': ['dba', 'doingbusinessas', 'tradename'],
            'businessaddress': ['address', 'businessaddr', 'companyaddress'],
            'businessphone': ['phone', 'businessph', 'companyhone'],
            'emailaddress': ['email', 'emailaddr'],
            'socialsecuritynumber': ['ssn', 'socialsecurity'],
            'federaltaxid': ['ein', 'employerid', 'taxid'],
            'totalassets': ['assets', 'totalasset'],
            'totalliabilities': ['liabilities', 'totalliability'],
            'networth': ['equity', 'netequity', 'ownersquity']
        }
        
        # Check if critical field has known variations
        for base_field, field_variations in variations.items():
            if critical_normalized == base_field:
                return mapped_normalized in field_variations
            elif mapped_normalized == base_field:
                return critical_normalized in field_variations
        
        # Check if one field name is contained in the other
        return critical_normalized in mapped_normalized or mapped_normalized in critical_normalized
    
    def _load_form_spec(self, bank: str, form_type: str) -> Optional[Dict[str, Any]]:
        """Load form specification from templates directory."""
        try:
            # Try multiple possible paths
            possible_paths = [
                self.form_specs_path / f"{bank}_{form_type}.json",
                self.form_specs_path / bank / f"{form_type}.json",
                Path("templates") / f"{bank}_{form_type}_fields.json"
            ]
            
            for spec_path in possible_paths:
                if spec_path.exists():
                    with open(spec_path, 'r') as f:
                        return json.load(f)
            
            print(f"    ⚠️ Form spec not found for {bank} {form_type}")
            return None
            
        except Exception as e:
            print(f"    ⚠️ Error loading form spec: {e}")
            return None
    
    def _generate_recommendations(
        self, 
        bank: str, 
        form_type: str, 
        coverage_score: float,
        critical_fields_result: Dict[str, Any],
        threshold: float
    ) -> List[str]:
        """Generate improvement recommendations based on validation results."""
        recommendations = []
        
        # Coverage recommendations
        if coverage_score < threshold:
            gap = (threshold - coverage_score) * 100
            recommendations.append(f"Increase field coverage by {gap:.1f}% to meet quality threshold")
        
        # Critical field recommendations
        if critical_fields_result['missing_critical']:
            missing_count = len(critical_fields_result['missing_critical'])
            recommendations.append(f"Fill {missing_count} missing critical fields: {', '.join(critical_fields_result['missing_critical'][:3])}{'...' if missing_count > 3 else ''}")
        
        # Bank-specific recommendations
        if bank == "live_oak" and form_type == "application":
            if coverage_score < 0.80:
                recommendations.append("Live Oak Application requires minimum 80% completion for processing")
        elif bank == "huntington" and form_type == "debt_schedule":
            if critical_fields_result['missing_critical']:
                recommendations.append("Huntington Debt Schedule requires complete liability details for underwriting")
        elif bank == "wells_fargo":
            if coverage_score < 0.70:
                recommendations.append("Wells Fargo forms have complex requirements - ensure all available data is mapped")
        
        # Quality improvement suggestions
        if coverage_score > 0.90:
            recommendations.append("Excellent coverage! Consider this form ready for submission")
        elif coverage_score > 0.75:
            recommendations.append("Good coverage. Review missing fields for additional data extraction opportunities")
        else:
            recommendations.append("Low coverage detected. Consider additional data sources or improved extraction methods")
        
        return recommendations
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """Create error result structure."""
        return {
            'error': error_message,
            'coverage_score': 0.0,
            'coverage_percentage': 0.0,
            'quality_gate_passed': False,
            'critical_fields_status': {
                'all_critical_present': False,
                'missing_critical': [],
                'critical_total': 0,
                'critical_present': 0
            },
            'recommendations': [f"Error: {error_message}"]
        }
    
    def validate_application_forms(
        self, 
        application_id: str,
        form_mappings: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate all forms for an application and provide overall quality assessment.
        
        Args:
            application_id: Unique application identifier
            form_mappings: Dict of {form_key: mapped_data} for all forms
            
        Returns:
            Dict containing:
            - overall_quality_score: Average quality across all forms
            - forms_passed: Number of forms passing quality gates
            - forms_failed: Number of forms failing quality gates
            - form_results: Individual form validation results
            - application_ready: Whether application meets submission criteria
        """
        print(f"\n📋 Validating all forms for application: {application_id}")
        
        form_results = {}
        quality_scores = []
        forms_passed = 0
        forms_failed = 0
        
        for form_key, mapped_data in form_mappings.items():
            # Parse form key (format: {bank}_{form_type})
            try:
                bank, form_type = form_key.split('_', 1)
            except ValueError:
                print(f"  ⚠️ Invalid form key format: {form_key}")
                continue
            
            # Validate individual form
            form_result = self.validate_form_mapping(bank, form_type, mapped_data)
            form_results[form_key] = form_result
            
            # Track quality metrics
            quality_scores.append(form_result['coverage_score'])
            if form_result['quality_gate_passed']:
                forms_passed += 1
            else:
                forms_failed += 1
        
        # Calculate overall metrics
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        total_forms = len(form_results)
        
        # Determine application readiness (at least 70% of forms must pass)
        application_ready = (forms_passed / total_forms) >= 0.70 if total_forms > 0 else False
        
        result = {
            'application_id': application_id,
            'overall_quality_score': round(overall_quality, 3),
            'overall_quality_percentage': round(overall_quality * 100, 1),
            'total_forms': total_forms,
            'forms_passed': forms_passed,
            'forms_failed': forms_failed,
            'pass_rate': round((forms_passed / total_forms) * 100, 1) if total_forms > 0 else 0.0,
            'application_ready': application_ready,
            'form_results': form_results,
            'summary_recommendations': self._generate_application_recommendations(
                overall_quality, forms_passed, forms_failed, application_ready
            )
        }
        
        print(f"  📊 Overall quality: {overall_quality:.1%}")
        print(f"  ✅ Forms passed: {forms_passed}/{total_forms}")
        print(f"  🚀 Application ready: {'Yes' if application_ready else 'No'}")
        
        return result
    
    def _generate_application_recommendations(
        self, 
        overall_quality: float,
        forms_passed: int,
        forms_failed: int,
        application_ready: bool
    ) -> List[str]:
        """Generate application-level recommendations."""
        recommendations = []
        
        if application_ready:
            recommendations.append("✅ Application meets submission criteria")
            if overall_quality > 0.90:
                recommendations.append("🌟 Excellent form completion quality")
        else:
            recommendations.append("❌ Application needs improvement before submission")
            if forms_failed > 0:
                recommendations.append(f"Focus on improving {forms_failed} failed forms")
        
        if overall_quality < 0.70:
            recommendations.append("Consider additional data sources to improve coverage")
        elif overall_quality < 0.85:
            recommendations.append("Good progress - review individual form recommendations")
        
        return recommendations