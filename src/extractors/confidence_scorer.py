"""
Confidence scoring system for document extraction.

This module provides comprehensive confidence scoring at the field level,
tracks extraction confidence, flags low-confidence extractions for manual review,
and provides detailed reasoning for confidence scores.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal
import statistics
import re
from collections import Counter

from .base import ExtractedField, ExtractionResult, DocumentType

logger = logging.getLogger(__name__)


class ConfidenceFactorType(Enum):
    """Types of factors that affect confidence scoring."""
    PATTERN_MATCH = "pattern_match"
    CONTEXT_VALIDATION = "context_validation"
    FORMAT_VALIDATION = "format_validation"
    CROSS_FIELD_VALIDATION = "cross_field_validation"
    DOCUMENT_QUALITY = "document_quality"
    EXTRACTION_METHOD = "extraction_method"
    FIELD_COMPLETENESS = "field_completeness"
    CONSISTENCY_CHECK = "consistency_check"


@dataclass
class ConfidenceFactor:
    """Individual factor contributing to confidence score."""
    factor_type: ConfidenceFactorType
    impact: float  # -1.0 to 1.0
    weight: float  # 0.0 to 1.0
    description: str
    evidence: Optional[str] = None


@dataclass
class FieldConfidenceAnalysis:
    """Detailed confidence analysis for a single field."""
    field_name: str
    base_confidence: float
    factors: List[ConfidenceFactor]
    final_confidence: float
    reasoning: str
    requires_manual_review: bool
    validation_notes: List[str] = field(default_factory=list)


@dataclass
class DocumentConfidenceReport:
    """Comprehensive confidence report for entire document extraction."""
    document_type: DocumentType
    overall_confidence: float
    field_analyses: Dict[str, FieldConfidenceAnalysis]
    extraction_quality_score: float
    manual_review_fields: List[str]
    confidence_distribution: Dict[str, int]  # low, medium, high counts
    recommendations: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConfidenceScorer:
    """
    Advanced confidence scoring system for document extraction.
    
    Provides field-level confidence analysis, cross-field validation,
    and detailed reasoning for confidence scores.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the confidence scorer."""
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Confidence thresholds
        self.high_confidence_threshold = self.config.get('high_confidence_threshold', 0.8)
        self.medium_confidence_threshold = self.config.get('medium_confidence_threshold', 0.5)
        self.manual_review_threshold = self.config.get('manual_review_threshold', 0.6)
        
        # Field importance weights for different document types
        self._setup_field_weights()
        
        # Validation patterns and rules
        self._setup_validation_rules()
    
    def _setup_field_weights(self):
        """Setup importance weights for different fields by document type."""
        self.field_weights = {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: {
                'name': 1.0,
                'social_security_number': 0.9,
                'total_assets': 1.0,
                'total_liabilities': 1.0,
                'net_worth': 1.0,
                'date_of_birth': 0.7,
                'residence_address': 0.6,
                'statement_date': 0.5,
                'cash_on_hand': 0.8,
                'savings_accounts': 0.7,
                'real_estate_owned': 0.8,
                'mortgages_on_real_estate': 0.8,
                'salary': 0.9,
            },
            DocumentType.SBA_FORM_413: {
                'name': 1.0,
                'social_security_number': 0.95,
                'total_assets': 1.0,
                'total_liabilities': 1.0,
                'net_worth': 1.0,
                'is_sba_form_413': 0.9,
                'statement_date': 0.7,
            },
            DocumentType.BANK_STATEMENT: {
                'account_holder_name': 1.0,
                'account_number': 0.9,
                'beginning_balance': 0.8,
                'ending_balance': 0.9,
                'statement_period': 0.8,
                'bank_name': 0.6,
            }
        }
        
        # Default weights for any document type
        self.default_field_weights = {
            'name': 0.9,
            'date': 0.7,
            'amount': 0.8,
            'total': 0.9,
            'address': 0.6,
            'phone': 0.5,
            'email': 0.6,
        }
    
    def _setup_validation_rules(self):
        """Setup validation rules for different field types."""
        self.validation_rules = {
            'currency_fields': {
                'pattern': re.compile(r'^\$?[\d,]+\.?\d*$'),
                'min_confidence_boost': 0.1,
                'max_confidence_boost': 0.2,
            },
            'date_fields': {
                'pattern': re.compile(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}'),
                'min_confidence_boost': 0.05,
                'max_confidence_boost': 0.15,
            },
            'name_fields': {
                'pattern': re.compile(r'^[A-Z][a-z]+\s+[A-Z][a-z]+'),
                'min_confidence_boost': 0.1,
                'max_confidence_boost': 0.2,
            },
            'ssn_fields': {
                'pattern': re.compile(r'^\d{3}-\d{2}-\d{4}$'),
                'min_confidence_boost': 0.15,
                'max_confidence_boost': 0.25,
            },
        }
    
    def analyze_field_confidence(
        self, 
        field: ExtractedField, 
        document_type: DocumentType,
        all_fields: List[ExtractedField],
        document_text: str = ""
    ) -> FieldConfidenceAnalysis:
        """
        Analyze confidence for a single extracted field.
        
        Args:
            field: The extracted field to analyze
            document_type: Type of document being processed
            all_fields: All extracted fields for cross-validation
            document_text: Original document text for context analysis
            
        Returns:
            FieldConfidenceAnalysis with detailed confidence breakdown
        """
        factors = []
        base_confidence = field.confidence or 0.5
        
        # Factor 1: Pattern matching quality
        pattern_factor = self._analyze_pattern_matching(field, document_type)
        factors.append(pattern_factor)
        
        # Factor 2: Format validation
        format_factor = self._analyze_format_validation(field)
        factors.append(format_factor)
        
        # Factor 3: Context validation
        if document_text:
            context_factor = self._analyze_context_validation(field, document_text)
            factors.append(context_factor)
        
        # Factor 4: Cross-field validation
        cross_field_factor = self._analyze_cross_field_validation(field, all_fields, document_type)
        factors.append(cross_field_factor)
        
        # Factor 5: Field completeness
        completeness_factor = self._analyze_field_completeness(field)
        factors.append(completeness_factor)
        
        # Calculate final confidence
        final_confidence = self._calculate_final_confidence(base_confidence, factors)
        
        # Generate reasoning
        reasoning = self._generate_confidence_reasoning(field, factors, final_confidence)
        
        # Determine if manual review is needed
        requires_review = self._requires_manual_review(field, final_confidence, factors)
        
        # Generate validation notes
        validation_notes = self._generate_validation_notes(field, factors)
        
        return FieldConfidenceAnalysis(
            field_name=field.name,
            base_confidence=base_confidence,
            factors=factors,
            final_confidence=final_confidence,
            reasoning=reasoning,
            requires_manual_review=requires_review,
            validation_notes=validation_notes
        )
    
    def _analyze_pattern_matching(self, field: ExtractedField, document_type: DocumentType) -> ConfidenceFactor:
        """Analyze pattern matching quality for the field."""
        impact = 0.0
        weight = 0.3
        description = "Pattern matching analysis"
        evidence = []
        
        # Check if field has source patterns information
        if hasattr(field, 'source_patterns') and field.source_patterns:
            impact += 0.2
            evidence.append(f"Matched patterns: {', '.join(field.source_patterns)}")
        
        # Check raw text quality
        if field.raw_text:
            # Clean, well-structured raw text boosts confidence
            if len(field.raw_text) > 5 and ':' in field.raw_text:
                impact += 0.1
                evidence.append("Well-structured field label")
            
            # Check for OCR artifacts
            ocr_artifacts = re.findall(r'[^\w\s$.,()/-]', field.raw_text)
            if len(ocr_artifacts) > 2:
                impact -= 0.2
                evidence.append("Potential OCR artifacts detected")
        
        # Field-specific pattern analysis
        if field.name in ['total_assets', 'total_liabilities', 'net_worth']:
            if field.value and isinstance(field.value, (Decimal, float, int)) and field.value > 0:
                impact += 0.15
                evidence.append("Valid total amount detected")
        
        evidence_str = "; ".join(evidence) if evidence else "Standard pattern matching"
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.PATTERN_MATCH,
            impact=max(-1.0, min(1.0, impact)),
            weight=weight,
            description=description,
            evidence=evidence_str
        )
    
    def _analyze_format_validation(self, field: ExtractedField) -> ConfidenceFactor:
        """Analyze format validation for the field."""
        impact = 0.0
        weight = 0.25
        description = "Format validation"
        evidence = []
        
        if field.value is None:
            return ConfidenceFactor(
                factor_type=ConfidenceFactorType.FORMAT_VALIDATION,
                impact=-0.5,
                weight=weight,
                description=description,
                evidence="Field value is None"
            )
        
        # Currency field validation
        if field.name in ['total_assets', 'total_liabilities', 'net_worth', 'salary'] or 'amount' in field.name.lower():
            if isinstance(field.value, (Decimal, float, int)):
                if field.value >= 0:
                    impact += 0.2
                    evidence.append("Valid currency format and positive value")
                else:
                    impact -= 0.1
                    evidence.append("Negative currency value (may be intentional)")
            else:
                impact -= 0.3
                evidence.append("Invalid currency format")
        
        # Date field validation
        elif field.name in ['date_of_birth', 'statement_date'] or 'date' in field.name.lower():
            from datetime import date
            if isinstance(field.value, date):
                # Check if date is reasonable (not too far in past/future)
                current_year = date.today().year
                if 1900 <= field.value.year <= current_year + 1:
                    impact += 0.2
                    evidence.append("Valid date format and reasonable year")
                else:
                    impact -= 0.2
                    evidence.append("Date year seems unreasonable")
            else:
                impact -= 0.3
                evidence.append("Invalid date format")
        
        # Name field validation
        elif field.name in ['name'] or 'name' in field.name.lower():
            if isinstance(field.value, str):
                name_parts = field.value.split()
                if len(name_parts) >= 2:
                    impact += 0.2
                    evidence.append("Name has multiple parts (first/last)")
                
                if all(part.isalpha() for part in name_parts):
                    impact += 0.1
                    evidence.append("Name contains only alphabetic characters")
                else:
                    impact -= 0.1
                    evidence.append("Name contains non-alphabetic characters")
            else:
                impact -= 0.3
                evidence.append("Invalid name format")
        
        # SSN validation
        elif field.name in ['social_security_number', 'ssn']:
            if isinstance(field.value, str) and re.match(r'\d{3}-\d{2}-\d{4}', field.value):
                impact += 0.3
                evidence.append("Valid SSN format")
            else:
                impact -= 0.4
                evidence.append("Invalid SSN format")
        
        evidence_str = "; ".join(evidence) if evidence else "Standard format validation"
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.FORMAT_VALIDATION,
            impact=max(-1.0, min(1.0, impact)),
            weight=weight,
            description=description,
            evidence=evidence_str
        )
    
    def _analyze_context_validation(self, field: ExtractedField, document_text: str) -> ConfidenceFactor:
        """Analyze context validation for the field."""
        impact = 0.0
        weight = 0.2
        description = "Context validation"
        evidence = []
        
        if not field.raw_text or not document_text:
            return ConfidenceFactor(
                factor_type=ConfidenceFactorType.CONTEXT_VALIDATION,
                impact=0.0,
                weight=weight,
                description=description,
                evidence="No context available for validation"
            )
        
        # Check if field appears in expected context
        field_context = self._find_field_context(field.raw_text, document_text)
        
        # Look for field labels and structure
        expected_labels = self._get_expected_labels(field.name)
        label_found = False
        
        for label in expected_labels:
            if re.search(label, field_context, re.IGNORECASE):
                impact += 0.15
                label_found = True
                evidence.append(f"Found expected label: {label}")
                break
        
        if not label_found:
            impact -= 0.1
            evidence.append("Expected field label not found in context")
        
        # Check for tabular structure (indicates form-like document)
        if self._has_tabular_structure(field_context):
            impact += 0.1
            evidence.append("Field appears in tabular structure")
        
        evidence_str = "; ".join(evidence) if evidence else "Standard context validation"
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.CONTEXT_VALIDATION,
            impact=max(-1.0, min(1.0, impact)),
            weight=weight,
            description=description,
            evidence=evidence_str
        )
    
    def _analyze_cross_field_validation(
        self, 
        field: ExtractedField, 
        all_fields: List[ExtractedField],
        document_type: DocumentType
    ) -> ConfidenceFactor:
        """Analyze cross-field validation."""
        impact = 0.0
        weight = 0.15
        description = "Cross-field validation"
        evidence = []
        
        # Financial calculation validation for PFS
        if document_type in [DocumentType.PERSONAL_FINANCIAL_STATEMENT, DocumentType.SBA_FORM_413]:
            if field.name == 'net_worth':
                assets_field = next((f for f in all_fields if f.name == 'total_assets'), None)
                liabilities_field = next((f for f in all_fields if f.name == 'total_liabilities'), None)
                
                if assets_field and liabilities_field and field.value is not None:
                    if assets_field.value is not None and liabilities_field.value is not None:
                        calculated_net_worth = assets_field.value - liabilities_field.value
                        difference = abs(calculated_net_worth - field.value)
                        
                        if difference <= Decimal('1.00'):  # Allow small rounding errors
                            impact += 0.3
                            evidence.append("Net worth calculation is consistent")
                        elif difference <= Decimal('100.00'):
                            impact += 0.1
                            evidence.append("Net worth calculation has minor discrepancy")
                        else:
                            impact -= 0.2
                            evidence.append(f"Net worth calculation discrepancy: {difference}")
        
        # Name consistency validation
        if field.name == 'name':
            # Check if name appears consistently throughout document
            name_fields = [f for f in all_fields if 'name' in f.name.lower() and f.value]
            if len(name_fields) > 1:
                names = [str(f.value) for f in name_fields]
                if len(set(names)) == 1:
                    impact += 0.2
                    evidence.append("Name is consistent across fields")
                else:
                    impact -= 0.1
                    evidence.append("Name inconsistency detected")
        
        # Date consistency validation
        if 'date' in field.name.lower():
            date_fields = [f for f in all_fields if 'date' in f.name.lower() and f.value]
            if len(date_fields) > 1:
                # Check for reasonable date relationships
                dates = [(f.name, f.value) for f in date_fields if hasattr(f.value, 'year')]
                if len(dates) >= 2:
                    # Basic consistency check - dates should be in reasonable range
                    years = [d[1].year for d in dates]
                    if max(years) - min(years) <= 5:  # Reasonable span
                        impact += 0.1
                        evidence.append("Dates are within reasonable range")
        
        evidence_str = "; ".join(evidence) if evidence else "No cross-field validation available"
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.CROSS_FIELD_VALIDATION,
            impact=max(-1.0, min(1.0, impact)),
            weight=weight,
            description=description,
            evidence=evidence_str
        )
    
    def _analyze_field_completeness(self, field: ExtractedField) -> ConfidenceFactor:
        """Analyze field completeness and quality."""
        impact = 0.0
        weight = 0.1
        description = "Field completeness"
        evidence = []
        
        # Check if field has value
        if field.value is not None:
            impact += 0.2
            evidence.append("Field has extracted value")
        else:
            impact -= 0.3
            evidence.append("Field value is missing")
            
        # Check if field has raw text
        if field.raw_text:
            impact += 0.1
            evidence.append("Raw text available")
        
        # Check validation status
        if hasattr(field, 'validation_status'):
            if field.validation_status == 'valid':
                impact += 0.2
                evidence.append("Field passes validation")
            elif field.validation_status == 'invalid':
                impact -= 0.3
                evidence.append("Field fails validation")
            elif field.validation_status == 'questionable':
                impact -= 0.1
                evidence.append("Field validation is questionable")
        
        evidence_str = "; ".join(evidence) if evidence else "Standard completeness check"
        
        return ConfidenceFactor(
            factor_type=ConfidenceFactorType.FIELD_COMPLETENESS,
            impact=max(-1.0, min(1.0, impact)),
            weight=weight,
            description=description,
            evidence=evidence_str
        )
    
    def _calculate_final_confidence(
        self, 
        base_confidence: float, 
        factors: List[ConfidenceFactor]
    ) -> float:
        """Calculate final confidence score based on factors."""
        weighted_impact = 0.0
        total_weight = 0.0
        
        for factor in factors:
            weighted_impact += factor.impact * factor.weight
            total_weight += factor.weight
        
        if total_weight > 0:
            adjustment = weighted_impact / total_weight
        else:
            adjustment = 0.0
        
        # Apply adjustment to base confidence
        final_confidence = base_confidence + (adjustment * 0.3)  # Limit factor impact
        
        # Ensure confidence is within valid range
        return max(0.0, min(1.0, final_confidence))
    
    def _generate_confidence_reasoning(
        self, 
        field: ExtractedField, 
        factors: List[ConfidenceFactor], 
        final_confidence: float
    ) -> str:
        """Generate human-readable reasoning for confidence score."""
        reasoning_parts = []
        
        # Base confidence
        reasoning_parts.append(f"Base confidence: {field.confidence:.2f}")
        
        # Significant positive factors
        positive_factors = [f for f in factors if f.impact > 0.1]
        if positive_factors:
            positive_desc = [f.description for f in positive_factors]
            reasoning_parts.append(f"Positive factors: {', '.join(positive_desc)}")
        
        # Significant negative factors
        negative_factors = [f for f in factors if f.impact < -0.1]
        if negative_factors:
            negative_desc = [f.description for f in negative_factors]
            reasoning_parts.append(f"Negative factors: {', '.join(negative_desc)}")
        
        # Final assessment
        if final_confidence >= self.high_confidence_threshold:
            reasoning_parts.append("High confidence extraction")
        elif final_confidence >= self.medium_confidence_threshold:
            reasoning_parts.append("Medium confidence extraction")
        else:
            reasoning_parts.append("Low confidence extraction")
        
        return "; ".join(reasoning_parts)
    
    def _requires_manual_review(
        self, 
        field: ExtractedField, 
        final_confidence: float, 
        factors: List[ConfidenceFactor]
    ) -> bool:
        """Determine if field requires manual review."""
        # Low confidence threshold
        if final_confidence < self.manual_review_threshold:
            return True
        
        # Check for critical validation failures
        critical_failures = [
            f for f in factors 
            if f.factor_type == ConfidenceFactorType.FORMAT_VALIDATION and f.impact < -0.2
        ]
        if critical_failures:
            return True
        
        # Important fields with medium confidence
        important_fields = ['name', 'total_assets', 'total_liabilities', 'net_worth', 'social_security_number']
        if field.name in important_fields and final_confidence < 0.75:
            return True
        
        return False
    
    def _generate_validation_notes(
        self, 
        field: ExtractedField, 
        factors: List[ConfidenceFactor]
    ) -> List[str]:
        """Generate validation notes for the field."""
        notes = []
        
        for factor in factors:
            if factor.impact < -0.1:  # Significant negative impact
                notes.append(f"{factor.description}: {factor.evidence}")
        
        # Add field-specific notes
        if field.name == 'net_worth' and field.value and field.value < 0:
            notes.append("Negative net worth detected - verify calculation")
        
        if field.name in ['total_assets', 'total_liabilities'] and field.value and field.value == 0:
            notes.append("Zero total detected - verify if accurate")
        
        return notes
    
    def _find_field_context(self, field_text: str, document_text: str, context_window: int = 200) -> str:
        """Find the context around a field in the document."""
        if not field_text or not document_text:
            return ""
        
        # Find the position of the field text in the document
        pos = document_text.find(field_text)
        if pos == -1:
            return ""
        
        # Extract context window around the field
        start = max(0, pos - context_window)
        end = min(len(document_text), pos + len(field_text) + context_window)
        
        return document_text[start:end]
    
    def _get_expected_labels(self, field_name: str) -> List[str]:
        """Get expected labels for a field name."""
        label_mapping = {
            'name': [r'name', r'individual', r'borrower'],
            'social_security_number': [r'social\s+security', r'ssn', r'ss\s+number'],
            'date_of_birth': [r'date\s+of\s+birth', r'dob', r'birth\s+date'],
            'total_assets': [r'total\s+assets', r'assets\s+total'],
            'total_liabilities': [r'total\s+liabilities', r'liabilities\s+total'],
            'net_worth': [r'net\s+worth', r'net\s+value'],
            'cash_on_hand': [r'cash', r'checking'],
            'savings_accounts': [r'savings', r'time\s+deposits'],
            'real_estate_owned': [r'real\s+estate', r'property'],
            'mortgages_on_real_estate': [r'mortgage', r'real\s+estate\s+loan'],
        }
        
        return label_mapping.get(field_name, [field_name.replace('_', r'\s+')])
    
    def _has_tabular_structure(self, text: str) -> bool:
        """Check if text has tabular structure."""
        # Look for patterns indicating tabular data
        tabular_patterns = [
            r'^\s*[A-Za-z\s]+:\s*\$?[\d,]+\.?\d*\s*$',  # Label: Amount
            r'^\s*[A-Za-z\s]+\s+\$?[\d,]+\.?\d*\s*$',   # Label Amount
            r'(_){3,}',  # Underlines indicating form fields
            r'\.{3,}',   # Dots indicating form fields
        ]
        
        for pattern in tabular_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        return False
    
    def generate_document_confidence_report(
        self, 
        extraction_result: ExtractionResult,
        document_text: str = ""
    ) -> DocumentConfidenceReport:
        """
        Generate comprehensive confidence report for entire document extraction.
        
        Args:
            extraction_result: The extraction result to analyze
            document_text: Original document text for additional analysis
            
        Returns:
            DocumentConfidenceReport with detailed analysis
        """
        field_analyses = {}
        manual_review_fields = []
        confidence_scores = []
        
        # Analyze each extracted field
        for field in extraction_result.extracted_fields:
            analysis = self.analyze_field_confidence(
                field, 
                extraction_result.document_type,
                extraction_result.extracted_fields,
                document_text
            )
            
            field_analyses[field.name] = analysis
            confidence_scores.append(analysis.final_confidence)
            
            if analysis.requires_manual_review:
                manual_review_fields.append(field.name)
        
        # Calculate overall statistics
        overall_confidence = statistics.mean(confidence_scores) if confidence_scores else 0.0
        
        # Confidence distribution
        confidence_distribution = {'low': 0, 'medium': 0, 'high': 0}
        for score in confidence_scores:
            if score >= self.high_confidence_threshold:
                confidence_distribution['high'] += 1
            elif score >= self.medium_confidence_threshold:
                confidence_distribution['medium'] += 1
            else:
                confidence_distribution['low'] += 1
        
        # Calculate extraction quality score
        extraction_quality_score = self._calculate_extraction_quality_score(
            extraction_result, field_analyses
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            extraction_result, field_analyses, confidence_distribution
        )
        
        return DocumentConfidenceReport(
            document_type=extraction_result.document_type,
            overall_confidence=overall_confidence,
            field_analyses=field_analyses,
            extraction_quality_score=extraction_quality_score,
            manual_review_fields=manual_review_fields,
            confidence_distribution=confidence_distribution,
            recommendations=recommendations,
            metadata={
                'total_fields': len(extraction_result.extracted_fields),
                'processing_time': extraction_result.processing_time,
                'extraction_status': extraction_result.status.value,
                'document_errors': extraction_result.errors
            }
        )
    
    def _calculate_extraction_quality_score(
        self, 
        extraction_result: ExtractionResult,
        field_analyses: Dict[str, FieldConfidenceAnalysis]
    ) -> float:
        """Calculate overall extraction quality score."""
        quality_factors = []
        
        # Factor 1: Required fields completion
        doc_type = extraction_result.document_type
        if doc_type in self.field_weights:
            important_fields = [
                name for name, weight in self.field_weights[doc_type].items() 
                if weight >= 0.8
            ]
            
            found_important = sum(
                1 for field in extraction_result.extracted_fields
                if field.name in important_fields and field.value is not None
            )
            
            if important_fields:
                completion_score = found_important / len(important_fields)
                quality_factors.append(completion_score * 0.4)  # 40% weight
        
        # Factor 2: Average confidence
        confidences = [analysis.final_confidence for analysis in field_analyses.values()]
        if confidences:
            avg_confidence = statistics.mean(confidences)
            quality_factors.append(avg_confidence * 0.3)  # 30% weight
        
        # Factor 3: Error rate
        error_penalty = 0.0
        if extraction_result.errors:
            error_penalty = min(0.3, len(extraction_result.errors) * 0.1)
        quality_factors.append((1.0 - error_penalty) * 0.2)  # 20% weight
        
        # Factor 4: Processing efficiency
        processing_score = 1.0
        if extraction_result.processing_time > 30:  # More than 30 seconds
            processing_score = max(0.5, 1.0 - (extraction_result.processing_time - 30) / 60)
        quality_factors.append(processing_score * 0.1)  # 10% weight
        
        return sum(quality_factors)
    
    def _generate_recommendations(
        self,
        extraction_result: ExtractionResult,
        field_analyses: Dict[str, FieldConfidenceAnalysis],
        confidence_distribution: Dict[str, int]
    ) -> List[str]:
        """Generate recommendations based on confidence analysis."""
        recommendations = []
        
        # Low confidence fields
        if confidence_distribution['low'] > 0:
            recommendations.append(
                f"{confidence_distribution['low']} fields have low confidence and require manual review"
            )
        
        # Missing critical fields
        critical_fields = ['name', 'total_assets', 'total_liabilities', 'net_worth']
        missing_critical = [
            field for field in critical_fields
            if field not in [f.name for f in extraction_result.extracted_fields if f.value is not None]
        ]
        
        if missing_critical:
            recommendations.append(
                f"Critical fields missing: {', '.join(missing_critical)}"
            )
        
        # Document quality issues
        if extraction_result.errors:
            recommendations.append(
                "Document contains extraction errors - consider alternative extraction methods"
            )
        
        # Overall confidence assessment
        low_confidence_ratio = confidence_distribution['low'] / sum(confidence_distribution.values())
        if low_confidence_ratio > 0.3:
            recommendations.append(
                "High proportion of low-confidence fields suggests document quality issues"
            )
        
        # Processing efficiency
        if extraction_result.processing_time > 60:
            recommendations.append(
                "Long processing time - consider document optimization or preprocessing"
            )
        
        return recommendations