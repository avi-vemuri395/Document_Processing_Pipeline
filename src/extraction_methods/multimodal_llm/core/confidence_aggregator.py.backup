"""
Multi-stage confidence scoring and aggregation system.
Combines confidence from classification, extraction, and validation stages.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics


class ConfidenceSource(Enum):
    """Sources of confidence scores."""
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    CONSISTENCY = "consistency"


@dataclass
class ConfidenceScore:
    """Individual confidence score with source and weight."""
    source: ConfidenceSource
    value: float
    weight: float = 1.0
    description: Optional[str] = None
    
    @property
    def weighted_value(self) -> float:
        """Get weighted confidence value."""
        return self.value * self.weight


class ConfidenceAggregator:
    """Aggregates confidence scores from multiple sources."""
    
    def __init__(self):
        """Initialize aggregator with default weights."""
        self.weights = {
            ConfidenceSource.CLASSIFICATION: 0.2,
            ConfidenceSource.EXTRACTION: 0.5,
            ConfidenceSource.VALIDATION: 0.2,
            ConfidenceSource.CONSISTENCY: 0.1
        }
        
        self.critical_fields = [
            "firstName", "lastName", "totalAssets", "totalLiabilities",
            "businessName", "ein", "creditorName", "currentBalance"
        ]
    
    def aggregate_scores(
        self,
        scores: List[ConfidenceScore],
        method: str = "weighted_average"
    ) -> float:
        """
        Aggregate multiple confidence scores.
        
        Args:
            scores: List of confidence scores
            method: Aggregation method (weighted_average, min, harmonic_mean)
            
        Returns:
            Aggregated confidence score
        """
        if not scores:
            return 0.0
        
        if method == "weighted_average":
            total_weight = sum(s.weight for s in scores)
            if total_weight == 0:
                return 0.0
            weighted_sum = sum(s.weighted_value for s in scores)
            return weighted_sum / total_weight
        
        elif method == "min":
            return min(s.value for s in scores)
        
        elif method == "harmonic_mean":
            values = [s.value for s in scores if s.value > 0]
            if not values:
                return 0.0
            return statistics.harmonic_mean(values)
        
        else:
            raise ValueError(f"Unknown aggregation method: {method}")
    
    def calculate_field_confidence(
        self,
        field_name: str,
        extracted_confidence: float,
        context_scores: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate confidence for a single field.
        
        Args:
            field_name: Name of the field
            extracted_confidence: Base extraction confidence
            context_scores: Additional context-based scores
            
        Returns:
            Field confidence score
        """
        scores = [
            ConfidenceScore(
                source=ConfidenceSource.EXTRACTION,
                value=extracted_confidence,
                weight=1.0
            )
        ]
        
        # Add context scores if available
        if context_scores:
            for context_name, score in context_scores.items():
                scores.append(
                    ConfidenceScore(
                        source=ConfidenceSource.CONSISTENCY,
                        value=score,
                        weight=0.3,
                        description=context_name
                    )
                )
        
        # Boost weight for critical fields
        if field_name in self.critical_fields:
            for score in scores:
                score.weight *= 1.5
        
        return self.aggregate_scores(scores)
    
    def calculate_document_confidence(
        self,
        classification_confidence: float,
        field_confidences: List[float],
        validation_scores: Optional[Dict[str, float]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate overall document extraction confidence.
        
        Args:
            classification_confidence: Document classification confidence
            field_confidences: Individual field extraction confidences
            validation_scores: Validation check scores
            
        Returns:
            Tuple of (overall_confidence, confidence_breakdown)
        """
        scores = []
        
        # Classification confidence
        scores.append(
            ConfidenceScore(
                source=ConfidenceSource.CLASSIFICATION,
                value=classification_confidence,
                weight=self.weights[ConfidenceSource.CLASSIFICATION]
            )
        )
        
        # Extraction confidence (average of fields)
        if field_confidences:
            avg_extraction = statistics.mean(field_confidences)
            scores.append(
                ConfidenceScore(
                    source=ConfidenceSource.EXTRACTION,
                    value=avg_extraction,
                    weight=self.weights[ConfidenceSource.EXTRACTION]
                )
            )
        
        # Validation scores
        if validation_scores:
            avg_validation = statistics.mean(validation_scores.values())
            scores.append(
                ConfidenceScore(
                    source=ConfidenceSource.VALIDATION,
                    value=avg_validation,
                    weight=self.weights[ConfidenceSource.VALIDATION]
                )
            )
        
        # Calculate overall
        overall = self.aggregate_scores(scores)
        
        # Create breakdown
        breakdown = {
            "overall": overall,
            "classification": classification_confidence,
            "extraction": {
                "average": statistics.mean(field_confidences) if field_confidences else 0,
                "min": min(field_confidences) if field_confidences else 0,
                "max": max(field_confidences) if field_confidences else 0,
                "count": len(field_confidences)
            },
            "validation": validation_scores or {},
            "sources": [
                {
                    "source": s.source.value,
                    "value": s.value,
                    "weight": s.weight,
                    "weighted": s.weighted_value
                }
                for s in scores
            ]
        }
        
        return overall, breakdown
    
    def validate_consistency(
        self,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Validate internal consistency of extracted data.
        
        Args:
            extracted_data: Extracted field data
            
        Returns:
            Dictionary of consistency check scores
        """
        consistency_scores = {}
        
        # Check if total assets equals sum of individual assets
        if "totalAssets" in extracted_data:
            asset_fields = [
                "cashOnHand", "savingsAccount", "retirementAccount",
                "accountAndNotesReceivable", "lifeInsuranceCashValue",
                "stockAndBonds", "realEstate", "automobileValue",
                "otherPersonalProperty", "otherAssets"
            ]
            
            asset_sum = sum(
                extracted_data.get(field, {}).get("value", 0)
                for field in asset_fields
                if field in extracted_data
            )
            
            total_assets = extracted_data["totalAssets"].get("value", 0)
            
            if total_assets > 0:
                diff_percent = abs(asset_sum - total_assets) / total_assets
                consistency_scores["asset_sum_check"] = max(0, 1 - diff_percent)
        
        # Check if total liabilities equals sum
        if "totalLiabilities" in extracted_data:
            liability_fields = [
                "accountsPayable", "notesPayableToBanks",
                "installmentAccountAutoLoan", "installmentAccountOtherLoan",
                "loanOnLifeInsurance", "mortgageOnRealEstate",
                "unpaidTaxes", "otherLiabilities"
            ]
            
            liability_sum = sum(
                extracted_data.get(field, {}).get("value", 0)
                for field in liability_fields
                if field in extracted_data
            )
            
            total_liabilities = extracted_data["totalLiabilities"].get("value", 0)
            
            if total_liabilities > 0:
                diff_percent = abs(liability_sum - total_liabilities) / total_liabilities
                consistency_scores["liability_sum_check"] = max(0, 1 - diff_percent)
        
        # Check net worth calculation
        if all(k in extracted_data for k in ["totalAssets", "totalLiabilities", "netWorth"]):
            assets = extracted_data["totalAssets"].get("value", 0)
            liabilities = extracted_data["totalLiabilities"].get("value", 0)
            stated_net_worth = extracted_data["netWorth"].get("value", 0)
            calculated_net_worth = assets - liabilities
            
            if stated_net_worth > 0:
                diff_percent = abs(calculated_net_worth - stated_net_worth) / stated_net_worth
                consistency_scores["net_worth_check"] = max(0, 1 - diff_percent)
        
        # Check email format
        if "email" in extracted_data:
            email = extracted_data["email"].get("value", "")
            if "@" in email and "." in email.split("@")[-1]:
                consistency_scores["email_format"] = 1.0
            else:
                consistency_scores["email_format"] = 0.0
        
        # Check SSN format
        if "ssn" in extracted_data:
            ssn = extracted_data["ssn"].get("value", "")
            if len(ssn.replace("-", "")) == 9:
                consistency_scores["ssn_format"] = 1.0
            else:
                consistency_scores["ssn_format"] = 0.0
        
        return consistency_scores
    
    def get_review_recommendation(
        self,
        overall_confidence: float,
        field_confidences: Dict[str, float],
        consistency_scores: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Generate review recommendation based on confidence scores.
        
        Args:
            overall_confidence: Overall document confidence
            field_confidences: Individual field confidences
            consistency_scores: Consistency check scores
            
        Returns:
            Review recommendation with details
        """
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
        
        # Check consistency
        failed_checks = [
            check for check, score in consistency_scores.items()
            if score < 0.8
        ]
        
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
            "consistency_scores": consistency_scores
        }