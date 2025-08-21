"""
Self-Consistency Confidence Scorer for BenchmarkExtractor.
Implements research-based confidence scoring without logprobs using ensemble sampling.
"""

import asyncio
import json
import statistics
from typing import Dict, Any, List, Optional
from collections import Counter

class SelfConsistencyScorer:
    """
    Implements self-consistency confidence scoring based on model agreement.
    
    Uses multiple temperature-based samples and calculates confidence based on
    agreement across responses. Based on CISC (Confidence-Informed Self-Consistency)
    research showing 40% reduction in required samples.
    """
    
    def __init__(self, client, model: str, rate_limiter):
        """
        Initialize scorer with Claude client and rate limiter.
        
        Args:
            client: AsyncAnthropic client instance
            model: Model name (e.g., "claude-sonnet-4-20250514")
            rate_limiter: RateLimitHandler instance
        """
        self.client = client
        self.model = model
        self.rate_limiter = rate_limiter
        
    async def extract_with_confidence(
        self, 
        content, 
        num_samples: int = 3,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Extract data with confidence scores using self-consistency.
        
        Args:
            content: Prompt content for extraction (can be string or messages format)
            num_samples: Number of samples for self-consistency (default: 3)
            temperature: Sampling temperature (default: 0.7)
            
        Returns:
            Dict containing:
            - extraction: Best extraction result
            - confidence_scores: Field-level confidence scores
            - agreement_data: Raw agreement statistics
        """
        print(f"  🎯 Self-consistency scoring with {num_samples} samples (temp={temperature})")
        
        # Generate multiple samples
        samples = []
        for i in range(num_samples):
            print(f"    • Sample {i+1}/{num_samples}...")
            try:
                response = await self.rate_limiter.execute_with_backoff(
                    self.client.messages.create,
                    model=self.model,
                    max_tokens=8192,
                    temperature=temperature,
                    messages=[{"role": "user", "content": content}],
                    api_type="claude"
                )
                
                # Parse response
                raw_text = response.content[0].text.strip()
                parsed_result = self._parse_json_response(raw_text)
                samples.append(parsed_result)
                
            except Exception as e:
                print(f"    ⚠️ Sample {i+1} failed: {e}")
                # Continue with remaining samples
                continue
        
        if not samples:
            raise Exception("All self-consistency samples failed")
            
        print(f"  ✅ Generated {len(samples)} valid samples")
        
        # Calculate agreement and confidence
        return self._calculate_agreement_confidence(samples)
    
    def _parse_json_response(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from Claude response, handling various formats."""
        # Try to extract JSON from the response
        if "```json" in raw_text:
            start = raw_text.find("```json") + 7
            end = raw_text.find("```", start)
            if end > start:
                raw_text = raw_text[start:end].strip()
        elif "```" in raw_text:
            parts = raw_text.split("```")
            if len(parts) >= 2:
                raw_text = parts[1].strip()
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
        
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            print(f"    ⚠️ Failed to parse JSON from response")
            return None
    
    def _calculate_agreement_confidence(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate confidence scores based on agreement across samples.
        
        Args:
            samples: List of parsed extraction results
            
        Returns:
            Dict with extraction, confidence scores, and agreement data
        """
        if not samples:
            raise ValueError("No valid samples provided")
            
        # Flatten all samples to get field-level data
        field_agreements = {}
        all_field_values = {}
        
        for sample in samples:
            flat_sample = self._flatten_dict(sample)
            for field_path, value in flat_sample.items():
                if field_path not in field_agreements:
                    field_agreements[field_path] = []
                    all_field_values[field_path] = []
                
                # Store normalized value for agreement calculation
                normalized_value = self._normalize_value(value)
                field_agreements[field_path].append(normalized_value)
                all_field_values[field_path].append(value)
        
        # Calculate field-level confidence scores
        confidence_scores = {}
        for field_path, values in field_agreements.items():
            confidence = self._calculate_field_confidence(values)
            confidence_scores[field_path] = confidence
        
        # Select best extraction (most confident overall)
        best_sample_index = self._select_best_sample(samples, confidence_scores)
        best_extraction = samples[best_sample_index] if best_sample_index is not None else samples[0]
        
        # Calculate overall confidence
        field_confidences = list(confidence_scores.values())
        overall_confidence = statistics.mean(field_confidences) if field_confidences else 0.0
        
        return {
            'extraction': best_extraction,
            'confidence_scores': confidence_scores,
            'overall_confidence': overall_confidence,
            'agreement_data': {
                'num_samples': len(samples),
                'field_count': len(confidence_scores),
                'high_confidence_fields': len([c for c in field_confidences if c >= 0.8]),
                'low_confidence_fields': len([c for c in field_confidences if c < 0.6])
            },
            'method': 'self_consistency'
        }
    
    def _flatten_dict(self, obj: Any, parent_key: str = '', separator: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for field-level comparison."""
        items = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                
                if isinstance(value, dict):
                    items.update(self._flatten_dict(value, new_key, separator))
                elif value is not None and value != "" and value != []:
                    items[new_key] = value
        
        return items
    
    def _normalize_value(self, value: Any) -> str:
        """Normalize values for agreement comparison."""
        if value is None:
            return ""
        
        # Convert to string and normalize
        str_value = str(value).strip().lower()
        
        # Handle common variations
        str_value = str_value.replace(',', '')  # Remove commas from numbers
        str_value = str_value.replace('$', '')  # Remove currency symbols
        str_value = str_value.replace('%', '')  # Remove percent symbols
        
        return str_value
    
    def _calculate_field_confidence(self, values: List[str]) -> float:
        """Calculate confidence for a single field based on agreement."""
        if not values:
            return 0.0
            
        # Count occurrences of each value
        value_counts = Counter(values)
        total_samples = len(values)
        
        # Most common value
        most_common_value, most_common_count = value_counts.most_common(1)[0]
        
        # Agreement ratio
        agreement_ratio = most_common_count / total_samples
        
        # Confidence score based on agreement
        # Perfect agreement (1.0) -> 0.95 confidence
        # Majority agreement (2/3) -> 0.75 confidence  
        # No agreement (1/3) -> 0.33 confidence
        confidence = min(0.95, agreement_ratio * 0.95)
        
        return round(confidence, 3)
    
    def _select_best_sample(self, samples: List[Dict[str, Any]], confidence_scores: Dict[str, float]) -> Optional[int]:
        """Select the sample with highest overall field confidence."""
        if not samples:
            return None
            
        sample_scores = []
        
        for i, sample in enumerate(samples):
            flat_sample = self._flatten_dict(sample)
            sample_confidence = []
            
            for field_path in flat_sample.keys():
                if field_path in confidence_scores:
                    sample_confidence.append(confidence_scores[field_path])
            
            # Average confidence for this sample
            avg_confidence = statistics.mean(sample_confidence) if sample_confidence else 0.0
            sample_scores.append(avg_confidence)
        
        # Return index of highest confidence sample
        return sample_scores.index(max(sample_scores)) if sample_scores else 0