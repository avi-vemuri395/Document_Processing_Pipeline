"""
Accuracy reporting utilities for synthetic data testing.

This module provides functions to compare extracted data against expected values
and generate detailed accuracy reports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import pandas as pd

from ..extractors.base import ExtractionResult, ExtractedField

logger = logging.getLogger(__name__)


class AccuracyLevel(Enum):
    """Levels of accuracy assessment."""
    EXACT = "exact"           # Values match exactly
    APPROXIMATE = "approximate"  # Values are close (within tolerance)
    INCORRECT = "incorrect"   # Values don't match
    MISSING = "missing"       # Expected value not extracted


class FieldType(Enum):
    """Types of fields for accuracy assessment."""
    TEXT = "text"
    NUMERIC = "numeric" 
    DATE = "date"
    CURRENCY = "currency"
    PHONE = "phone"
    EMAIL = "email"
    ADDRESS = "address"


@dataclass
class FieldComparison:
    """Comparison result for a single field."""
    field_name: str
    expected_value: Any
    extracted_value: Any
    accuracy_level: AccuracyLevel
    field_type: FieldType
    confidence_score: Optional[float]
    similarity_score: float
    notes: str = ""


@dataclass
class AccuracyReport:
    """Complete accuracy report for a document set."""
    document_id: str
    document_type: str
    overall_accuracy: float
    field_comparisons: List[FieldComparison]
    extraction_time: float
    total_fields: int
    exact_matches: int
    approximate_matches: int
    incorrect_matches: int
    missing_fields: int
    report_timestamp: datetime
    
    @property
    def accuracy_by_type(self) -> Dict[str, float]:
        """Get accuracy breakdown by field type."""
        type_stats = {}
        
        for field_type in FieldType:
            type_fields = [fc for fc in self.field_comparisons if fc.field_type == field_type]
            if type_fields:
                exact_count = sum(1 for fc in type_fields if fc.accuracy_level == AccuracyLevel.EXACT)
                approx_count = sum(1 for fc in type_fields if fc.accuracy_level == AccuracyLevel.APPROXIMATE)
                accuracy = (exact_count + approx_count) / len(type_fields)
                type_stats[field_type.value] = accuracy
        
        return type_stats


class AccuracyReporter:
    """Main class for generating accuracy reports."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize accuracy reporter.
        
        Args:
            config: Configuration for accuracy assessment
        """
        self.config = config or {}
        
        # Tolerance settings
        self.numeric_tolerance = self.config.get('numeric_tolerance', 0.01)  # 1% tolerance
        self.currency_tolerance = self.config.get('currency_tolerance', 0.01)  # 1% tolerance
        self.text_similarity_threshold = self.config.get('text_similarity_threshold', 0.8)
    
    def compare_extraction_results(
        self,
        extraction_result: ExtractionResult,
        expected_values: Dict[str, Any],
        document_id: str
    ) -> AccuracyReport:
        """
        Compare extraction results against expected values.
        
        Args:
            extraction_result: Results from document extraction
            expected_values: Expected values for comparison
            document_id: Unique identifier for the document
            
        Returns:
            Complete accuracy report
        """
        field_comparisons = []
        
        # Create lookup of extracted fields
        extracted_fields = {field.name: field for field in extraction_result.extracted_fields}
        
        # Compare each expected field
        for field_name, expected_value in expected_values.items():
            extracted_field = extracted_fields.get(field_name)
            
            if extracted_field is None:
                # Field was not extracted
                field_comparison = FieldComparison(
                    field_name=field_name,
                    expected_value=expected_value,
                    extracted_value=None,
                    accuracy_level=AccuracyLevel.MISSING,
                    field_type=self._determine_field_type(field_name, expected_value),
                    confidence_score=None,
                    similarity_score=0.0,
                    notes="Field not extracted"
                )
            else:
                # Field was extracted - compare values
                field_comparison = self._compare_field_values(
                    field_name, 
                    expected_value, 
                    extracted_field
                )
            
            field_comparisons.append(field_comparison)
        
        # Calculate overall statistics
        total_fields = len(expected_values)
        exact_matches = sum(1 for fc in field_comparisons if fc.accuracy_level == AccuracyLevel.EXACT)
        approximate_matches = sum(1 for fc in field_comparisons if fc.accuracy_level == AccuracyLevel.APPROXIMATE)
        incorrect_matches = sum(1 for fc in field_comparisons if fc.accuracy_level == AccuracyLevel.INCORRECT)
        missing_fields = sum(1 for fc in field_comparisons if fc.accuracy_level == AccuracyLevel.MISSING)
        
        # Calculate overall accuracy (exact + approximate matches)
        overall_accuracy = (exact_matches + approximate_matches) / total_fields if total_fields > 0 else 0.0
        
        return AccuracyReport(
            document_id=document_id,
            document_type=extraction_result.document_type.value,
            overall_accuracy=overall_accuracy,
            field_comparisons=field_comparisons,
            extraction_time=extraction_result.processing_time,
            total_fields=total_fields,
            exact_matches=exact_matches,
            approximate_matches=approximate_matches,
            incorrect_matches=incorrect_matches,
            missing_fields=missing_fields,
            report_timestamp=datetime.now()
        )
    
    def _compare_field_values(
        self,
        field_name: str,
        expected_value: Any,
        extracted_field: ExtractedField
    ) -> FieldComparison:
        """Compare individual field values."""
        field_type = self._determine_field_type(field_name, expected_value)
        extracted_value = extracted_field.value
        
        # Type-specific comparison
        if field_type == FieldType.NUMERIC:
            accuracy_level, similarity_score, notes = self._compare_numeric_values(
                expected_value, extracted_value
            )
        elif field_type == FieldType.CURRENCY:
            accuracy_level, similarity_score, notes = self._compare_currency_values(
                expected_value, extracted_value
            )
        elif field_type == FieldType.DATE:
            accuracy_level, similarity_score, notes = self._compare_date_values(
                expected_value, extracted_value
            )
        elif field_type in [FieldType.PHONE, FieldType.EMAIL]:
            accuracy_level, similarity_score, notes = self._compare_formatted_values(
                expected_value, extracted_value, field_type
            )
        else:  # TEXT, ADDRESS, or other
            accuracy_level, similarity_score, notes = self._compare_text_values(
                expected_value, extracted_value
            )
        
        return FieldComparison(
            field_name=field_name,
            expected_value=expected_value,
            extracted_value=extracted_value,
            accuracy_level=accuracy_level,
            field_type=field_type,
            confidence_score=extracted_field.confidence,
            similarity_score=similarity_score,
            notes=notes
        )
    
    def _determine_field_type(self, field_name: str, value: Any) -> FieldType:
        """Determine the type of field for appropriate comparison."""
        field_name_lower = field_name.lower()
        
        # Check by field name patterns
        if any(keyword in field_name_lower for keyword in ['amount', 'balance', 'revenue', 'income', 'loan']):
            return FieldType.CURRENCY
        elif any(keyword in field_name_lower for keyword in ['date', 'period']):
            return FieldType.DATE
        elif 'phone' in field_name_lower:
            return FieldType.PHONE
        elif 'email' in field_name_lower:
            return FieldType.EMAIL
        elif 'address' in field_name_lower:
            return FieldType.ADDRESS
        elif any(keyword in field_name_lower for keyword in ['number', 'count', 'employees', 'years']):
            return FieldType.NUMERIC
        else:
            return FieldType.TEXT
    
    def _compare_numeric_values(
        self, 
        expected: Union[int, float], 
        extracted: Any
    ) -> Tuple[AccuracyLevel, float, str]:
        """Compare numeric values with tolerance."""
        try:
            extracted_num = float(extracted) if extracted is not None else None
            expected_num = float(expected)
            
            if extracted_num is None:
                return AccuracyLevel.MISSING, 0.0, "No value extracted"
            
            if abs(extracted_num - expected_num) < 0.001:  # Essentially equal
                return AccuracyLevel.EXACT, 1.0, "Exact match"
            
            # Check percentage difference
            if expected_num != 0:
                percent_diff = abs(extracted_num - expected_num) / abs(expected_num)
                if percent_diff <= self.numeric_tolerance:
                    similarity = 1 - percent_diff
                    return AccuracyLevel.APPROXIMATE, similarity, f"Within {self.numeric_tolerance:.1%} tolerance"
            
            # Calculate similarity based on magnitude difference
            max_val = max(abs(expected_num), abs(extracted_num))
            if max_val > 0:
                similarity = 1 - (abs(extracted_num - expected_num) / max_val)
                similarity = max(0, similarity)
            else:
                similarity = 0
            
            return AccuracyLevel.INCORRECT, similarity, f"Expected: {expected_num}, Got: {extracted_num}"
            
        except (ValueError, TypeError):
            return AccuracyLevel.INCORRECT, 0.0, f"Cannot convert to numeric: {extracted}"
    
    def _compare_currency_values(
        self, 
        expected: Union[int, float], 
        extracted: Any
    ) -> Tuple[AccuracyLevel, float, str]:
        """Compare currency values with tolerance."""
        # Use same logic as numeric but with currency-specific formatting
        return self._compare_numeric_values(expected, extracted)
    
    def _compare_date_values(
        self, 
        expected: Any, 
        extracted: Any
    ) -> Tuple[AccuracyLevel, float, str]:
        """Compare date values."""
        from datetime import datetime
        
        try:
            # Normalize both dates to strings for comparison
            expected_str = str(expected).strip()
            extracted_str = str(extracted).strip() if extracted else ""
            
            if not extracted_str:
                return AccuracyLevel.MISSING, 0.0, "No date extracted"
            
            if expected_str == extracted_str:
                return AccuracyLevel.EXACT, 1.0, "Exact date match"
            
            # Try to parse both as dates for more flexible comparison
            try:
                expected_date = datetime.fromisoformat(expected_str.replace('/', '-'))
                extracted_date = datetime.fromisoformat(extracted_str.replace('/', '-'))
                
                if expected_date.date() == extracted_date.date():
                    return AccuracyLevel.APPROXIMATE, 0.9, "Date matches (different format)"
                
            except ValueError:
                pass
            
            # Check if main components match (year, month)
            similarity = self._calculate_text_similarity(expected_str, extracted_str)
            if similarity > 0.7:
                return AccuracyLevel.APPROXIMATE, similarity, "Partial date match"
            
            return AccuracyLevel.INCORRECT, similarity, f"Expected: {expected_str}, Got: {extracted_str}"
            
        except Exception as e:
            return AccuracyLevel.INCORRECT, 0.0, f"Date comparison error: {e}"
    
    def _compare_formatted_values(
        self, 
        expected: str, 
        extracted: Any,
        field_type: FieldType
    ) -> Tuple[AccuracyLevel, float, str]:
        """Compare formatted values like phone numbers and emails."""
        expected_str = str(expected).strip()
        extracted_str = str(extracted).strip() if extracted else ""
        
        if not extracted_str:
            return AccuracyLevel.MISSING, 0.0, f"No {field_type.value} extracted"
        
        if expected_str == extracted_str:
            return AccuracyLevel.EXACT, 1.0, "Exact match"
        
        # For phone numbers, normalize by removing formatting
        if field_type == FieldType.PHONE:
            expected_digits = ''.join(c for c in expected_str if c.isdigit())
            extracted_digits = ''.join(c for c in extracted_str if c.isdigit())
            
            if expected_digits == extracted_digits:
                return AccuracyLevel.APPROXIMATE, 0.9, "Phone digits match (different format)"
        
        # For emails, check domain and username separately
        if field_type == FieldType.EMAIL:
            if '@' in expected_str and '@' in extracted_str:
                expected_parts = expected_str.split('@')
                extracted_parts = extracted_str.split('@')
                
                if len(expected_parts) == 2 and len(extracted_parts) == 2:
                    if expected_parts[1] == extracted_parts[1]:  # Same domain
                        username_similarity = self._calculate_text_similarity(
                            expected_parts[0], extracted_parts[0]
                        )
                        if username_similarity > 0.7:
                            return AccuracyLevel.APPROXIMATE, 0.8, "Similar email (same domain)"
        
        similarity = self._calculate_text_similarity(expected_str, extracted_str)
        if similarity > self.text_similarity_threshold:
            return AccuracyLevel.APPROXIMATE, similarity, "Similar format"
        
        return AccuracyLevel.INCORRECT, similarity, f"Expected: {expected_str}, Got: {extracted_str}"
    
    def _compare_text_values(
        self, 
        expected: str, 
        extracted: Any
    ) -> Tuple[AccuracyLevel, float, str]:
        """Compare text values."""
        expected_str = str(expected).strip().lower()
        extracted_str = str(extracted).strip().lower() if extracted else ""
        
        if not extracted_str:
            return AccuracyLevel.MISSING, 0.0, "No text extracted"
        
        if expected_str == extracted_str:
            return AccuracyLevel.EXACT, 1.0, "Exact match"
        
        similarity = self._calculate_text_similarity(expected_str, extracted_str)
        
        if similarity >= self.text_similarity_threshold:
            return AccuracyLevel.APPROXIMATE, similarity, "High text similarity"
        elif similarity >= 0.5:
            return AccuracyLevel.INCORRECT, similarity, "Partial text similarity"
        else:
            return AccuracyLevel.INCORRECT, similarity, f"Expected: {expected}, Got: {extracted}"
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, text1, text2).ratio()
    
    def generate_summary_report(self, reports: List[AccuracyReport]) -> Dict[str, Any]:
        """
        Generate summary report across multiple document accuracy reports.
        
        Args:
            reports: List of individual accuracy reports
            
        Returns:
            Summary statistics and insights
        """
        if not reports:
            return {}
        
        # Overall statistics
        total_documents = len(reports)
        total_fields = sum(report.total_fields for report in reports)
        total_exact = sum(report.exact_matches for report in reports)
        total_approximate = sum(report.approximate_matches for report in reports)
        total_incorrect = sum(report.incorrect_matches for report in reports)
        total_missing = sum(report.missing_fields for report in reports)
        
        overall_accuracy = sum(report.overall_accuracy for report in reports) / total_documents
        
        # Accuracy by document type
        type_accuracy = {}
        for doc_type in set(report.document_type for report in reports):
            type_reports = [r for r in reports if r.document_type == doc_type]
            type_accuracy[doc_type] = {
                'count': len(type_reports),
                'accuracy': sum(r.overall_accuracy for r in type_reports) / len(type_reports),
                'avg_extraction_time': sum(r.extraction_time for r in type_reports) / len(type_reports)
            }
        
        # Accuracy by field type
        field_type_stats = {}
        all_comparisons = [fc for report in reports for fc in report.field_comparisons]
        
        for field_type in FieldType:
            type_comparisons = [fc for fc in all_comparisons if fc.field_type == field_type]
            if type_comparisons:
                exact_count = sum(1 for fc in type_comparisons if fc.accuracy_level == AccuracyLevel.EXACT)
                approx_count = sum(1 for fc in type_comparisons if fc.accuracy_level == AccuracyLevel.APPROXIMATE)
                accuracy = (exact_count + approx_count) / len(type_comparisons)
                
                field_type_stats[field_type.value] = {
                    'count': len(type_comparisons),
                    'accuracy': accuracy,
                    'avg_confidence': sum(fc.confidence_score or 0 for fc in type_comparisons) / len(type_comparisons),
                    'avg_similarity': sum(fc.similarity_score for fc in type_comparisons) / len(type_comparisons)
                }
        
        # Most problematic fields
        field_stats = {}
        for comparison in all_comparisons:
            field_name = comparison.field_name
            if field_name not in field_stats:
                field_stats[field_name] = {'total': 0, 'correct': 0, 'similarities': []}
            
            field_stats[field_name]['total'] += 1
            if comparison.accuracy_level in [AccuracyLevel.EXACT, AccuracyLevel.APPROXIMATE]:
                field_stats[field_name]['correct'] += 1
            field_stats[field_name]['similarities'].append(comparison.similarity_score)
        
        # Calculate field accuracies
        field_accuracies = {}
        for field_name, stats in field_stats.items():
            accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
            avg_similarity = sum(stats['similarities']) / len(stats['similarities'])
            field_accuracies[field_name] = {
                'accuracy': accuracy,
                'avg_similarity': avg_similarity,
                'count': stats['total']
            }
        
        # Sort fields by accuracy (worst first)
        problematic_fields = sorted(
            field_accuracies.items(),
            key=lambda x: (x[1]['accuracy'], x[1]['avg_similarity'])
        )[:10]
        
        return {
            'summary': {
                'total_documents': total_documents,
                'total_fields': total_fields,
                'overall_accuracy': overall_accuracy,
                'exact_matches': total_exact,
                'approximate_matches': total_approximate,
                'incorrect_matches': total_incorrect,
                'missing_fields': total_missing
            },
            'accuracy_by_document_type': type_accuracy,
            'accuracy_by_field_type': field_type_stats,
            'most_problematic_fields': dict(problematic_fields),
            'generation_timestamp': datetime.now().isoformat()
        }
    
    def export_report_to_excel(self, reports: List[AccuracyReport], output_path: Path) -> None:
        """
        Export accuracy reports to Excel file.
        
        Args:
            reports: List of accuracy reports
            output_path: Path to save Excel file
        """
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = self.generate_summary_report(reports)
            if summary_data:
                summary_df = pd.DataFrame([summary_data['summary']])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed results sheet
            detailed_data = []
            for report in reports:
                for comparison in report.field_comparisons:
                    detailed_data.append({
                        'Document ID': report.document_id,
                        'Document Type': report.document_type,
                        'Field Name': comparison.field_name,
                        'Field Type': comparison.field_type.value,
                        'Expected Value': comparison.expected_value,
                        'Extracted Value': comparison.extracted_value,
                        'Accuracy Level': comparison.accuracy_level.value,
                        'Similarity Score': comparison.similarity_score,
                        'Confidence Score': comparison.confidence_score,
                        'Notes': comparison.notes
                    })
            
            if detailed_data:
                detailed_df = pd.DataFrame(detailed_data)
                detailed_df.to_excel(writer, sheet_name='Detailed Results', index=False)
    
    def export_report_to_json(self, reports: List[AccuracyReport], output_path: Path) -> None:
        """
        Export accuracy reports to JSON file.
        
        Args:
            reports: List of accuracy reports
            output_path: Path to save JSON file
        """
        # Convert reports to serializable format
        serializable_reports = []
        for report in reports:
            serializable_report = {
                'document_id': report.document_id,
                'document_type': report.document_type,
                'overall_accuracy': report.overall_accuracy,
                'extraction_time': report.extraction_time,
                'total_fields': report.total_fields,
                'exact_matches': report.exact_matches,
                'approximate_matches': report.approximate_matches,
                'incorrect_matches': report.incorrect_matches,
                'missing_fields': report.missing_fields,
                'report_timestamp': report.report_timestamp.isoformat(),
                'field_comparisons': [
                    {
                        'field_name': fc.field_name,
                        'expected_value': fc.expected_value,
                        'extracted_value': fc.extracted_value,
                        'accuracy_level': fc.accuracy_level.value,
                        'field_type': fc.field_type.value,
                        'confidence_score': fc.confidence_score,
                        'similarity_score': fc.similarity_score,
                        'notes': fc.notes
                    }
                    for fc in report.field_comparisons
                ]
            }
            serializable_reports.append(serializable_report)
        
        # Add summary
        export_data = {
            'reports': serializable_reports,
            'summary': self.generate_summary_report(reports)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)