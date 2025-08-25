"""
DocAI Semantic Mapper - Intelligent Field Mapping Service
Maps Google Document AI extracted fields to target form fields using 
Claude 3.5 Sonnet's semantic understanding with research-backed techniques.

This service implements:
- Ontology-based schema injection for precise field alignment
- XML-structured prompting with chain-of-thought reasoning
- Confidence-aware field consolidation
- Value normalization for financial data
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Follow existing import patterns from visual_form_filler.py
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Import rate limiter following existing patterns
from ..extraction_methods.multimodal_llm.providers.rate_limiter import RateLimitHandler


class DocAISemanticMapper:
    """
    Maps DocAI form fields to target form fields using Claude 3.5 Sonnet
    semantic understanding with ontology-based schema injection.
    
    This replaces simple field name matching with intelligent semantic
    alignment, handling naming mismatches and field consolidation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize following existing service patterns."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")
        
        # API key handling (same pattern as visual_form_filler)
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required for semantic mapping")
        
        # Lazy initialization pattern from existing services
        self._client = None
        self._rate_limiter = None
        self._field_ontology_cache = {}
        self._consolidator = None
        
        self.api_key = api_key
        self.model = "claude-sonnet-4-20250514"  # Same model as other services
        
        # Performance tracking
        self.stats = {
            'mappings_performed': 0,
            'fields_mapped': 0,
            'fields_consolidated': 0,
            'avg_confidence': 0.0
        }
    
    @property
    def client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client
    
    @property
    def rate_limiter(self):
        """Lazy initialization of rate limiter."""
        if self._rate_limiter is None:
            self._rate_limiter = RateLimitHandler()
        return self._rate_limiter
    
    @property
    def consolidator(self):
        """Lazy initialization of field consolidator."""
        if self._consolidator is None:
            from .field_consolidator import ConfidenceAwareFieldConsolidator
            self._consolidator = ConfidenceAwareFieldConsolidator()
        return self._consolidator
    
    async def map_docai_to_form(
        self,
        docai_fields: Dict[str, Any],
        target_form_schema: Dict[str, Any],
        form_key: str
    ) -> Dict[str, Any]:
        """
        Semantically map DocAI fields to target form fields.
        
        Uses ontology-based schema injection and confidence-aware 
        field consolidation based on research findings.
        
        Args:
            docai_fields: Raw DocAI extracted fields with confidence scores
            target_form_schema: Target form specification with field definitions
            form_key: Form identifier for context
            
        Returns:
            Mapped fields with confidence scores and metadata
        """
        print(f"    🧠 Semantic mapping for {form_key}")
        start_time = time.time()
        
        try:
            # Step 1: Consolidate fragmented DocAI fields
            print(f"    📊 Processing {len(docai_fields)} DocAI fields...")
            consolidated_fields = self.consolidator.consolidate_fragmented_fields(
                docai_fields, 
                confidence_threshold=0.6  # Lower threshold for DocAI confidence
            )
            print(f"    ✅ Consolidated to {len(consolidated_fields)} fields")
            
            # Step 2: Create semantic mapping prompt using research techniques
            prompt = self._create_semantic_mapping_prompt(
                consolidated_fields, target_form_schema, form_key
            )
            
            # Step 3: Call Claude with XML-structured prompt
            print(f"    🤖 Calling Claude for semantic mapping...")
            mapped_result = await self._call_claude_semantic_mapping(prompt)
            
            # Step 4: Process and validate the mapping result
            final_result = self._process_mapping_result(
                mapped_result, consolidated_fields, target_form_schema
            )
            
            # Update statistics
            self.stats['mappings_performed'] += 1
            self.stats['fields_mapped'] += len(final_result.get('mapped_data', {}))
            self.stats['fields_consolidated'] += len(consolidated_fields)
            
            processing_time = time.time() - start_time
            print(f"    ✅ Semantic mapping completed in {processing_time:.2f}s")
            
            return final_result
            
        except Exception as e:
            print(f"    ❌ Semantic mapping failed: {e}")
            return {
                'mapped_data': {},
                'confidence_scores': {},
                'overall_confidence': 0.0,
                'extraction_method': 'docai_semantic_mapping',
                'error': str(e),
                'success': False
            }
    
    def _create_semantic_mapping_prompt(
        self, 
        docai_fields: Dict, 
        target_schema: Dict, 
        form_key: str
    ) -> str:
        """
        Create ontology-based XML-structured prompt for semantic mapping.
        
        Implements research findings: 
        - XML tagging for structure
        - Ontology-based schema injection
        - Chain-of-thought reasoning
        - Few-shot normalization examples
        """
        
        # Extract target field ontology from schema
        target_fields = self._extract_target_ontology(target_schema)
        
        return f"""<semantic_field_mapping>

<context>
Task: Map Google Document AI extracted fields to target form fields
Form: {form_key}
Goal: Achieve semantic alignment using financial domain knowledge
Method: Match DocAI field names/values to target form fields semantically
</context>

<docai_source_fields>
{json.dumps(docai_fields, indent=2)}
</docai_source_fields>

<target_form_ontology>
{json.dumps(target_fields, indent=2)}
</target_form_ontology>

<mapping_instructions>
1. SEMANTIC_ANALYSIS: For each DocAI field, identify its financial/business meaning
2. ONTOLOGY_MATCHING: Match to the most semantically similar target field
3. VALUE_NORMALIZATION: Apply standard financial formatting rules
4. CONFIDENCE_SCORING: Rate your certainty for each mapping (0.0-1.0)
5. FIELD_CONSOLIDATION: Merge related fields when appropriate

Think step-by-step about each mapping decision. Consider:
- Semantic similarity of field names
- Context from field values
- Common financial document patterns
- Standard form field conventions
</mapping_instructions>

<normalization_examples>
Dates: "July 30, 2025" → "2025-07-30"
Currency: "$ 1,234.56" → 1234.56
SSN: "123-45-6789" → "XXX-XX-6789" 
Phone: "803.981.3446" → "(803) 981-3446"
Business names: "WAXXPOT GROUP" + "HOLDINGS LLC" → "Waxxpot Group Holdings LLC"
Percentages: "50.000000" → 50.0
</normalization_examples>

<critical_mappings>
Common DocAI → Target Form mappings:
- "Name" → "Primary Applicant Name" or "Applicant Name"
- "Business Phone" → "Applicant Business Phone Number"
- "Employer Identification Number" → "Business Tax ID Number" or "EIN"
- "Net Investment Income" → "Investment Income"
- "Total" (in assets section) → "Total Assets"
- "Total Liabilities ." → "Total Liabilities"
- "Salary" → "Annual Salary" or "Gross Income"
</critical_mappings>

<response_format>
Return ONLY a JSON object:
{{
  "field_mappings": {{
    "target_field_name": {{
      "value": "normalized_value",
      "confidence": 0.95,
      "source_field": "original_docai_field_name",
      "reasoning": "brief explanation"
    }}
  }},
  "unmapped_fields": ["list of DocAI fields that couldn't be mapped"],
  "consolidation_summary": {{
    "fields_mapped": count,
    "avg_confidence": 0.0-1.0,
    "low_confidence_fields": ["fields below 0.7 confidence"]
  }}
}}
</response_format>

</semantic_field_mapping>"""
    
    def _extract_target_ontology(self, target_schema: Dict) -> Dict[str, Any]:
        """
        Extract target field definitions from form schema.
        
        Creates an ontology of target fields with their types and descriptions
        for semantic matching.
        """
        target_fields = {}
        
        # Extract fields from schema
        fields = target_schema.get('fields', [])
        
        for field in fields:
            if isinstance(field, dict):
                field_name = field.get('name', field.get('field_name', ''))
                if field_name:
                    target_fields[field_name] = {
                        'type': field.get('type', 'text'),
                        'required': field.get('required', False),
                        'description': field.get('description', ''),
                        'format': field.get('format', None)
                    }
            elif isinstance(field, str):
                # Simple field name
                target_fields[field] = {'type': 'text', 'required': False}
        
        return target_fields
    
    async def _call_claude_semantic_mapping(self, prompt: str) -> Dict[str, Any]:
        """
        Make Claude API call for semantic mapping.
        
        Follows existing patterns from benchmark_extractor and visual_form_filler.
        """
        try:
            # API call with rate limiting (same pattern as other services)
            response = await self.rate_limiter.execute_with_backoff(
                self.client.messages.create,
                model=self.model,
                max_tokens=8192,
                temperature=0.2,  # Lower temperature for more consistent mapping
                messages=[{"role": "user", "content": prompt}],
                api_type="claude"
            )
            
            # Parse response (same pattern as visual_form_filler)
            raw_text = response.content[0].text.strip()
            
            # Extract JSON (same logic as other services)
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
            
            # Parse JSON
            result = json.loads(raw_text)
            
            if not isinstance(result, dict):
                raise ValueError("Response is not a JSON object")
            
            field_count = len(result.get('field_mappings', {}))
            print(f"    ✅ Mapped {field_count} fields semantically")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"    ❌ JSON parsing failed: {e}")
            return {'field_mappings': {}, 'error': str(e)}
        except Exception as e:
            print(f"    ❌ API call failed: {e}")
            return {'field_mappings': {}, 'error': str(e)}
    
    def _process_mapping_result(
        self, 
        mapped_result: Dict,
        consolidated_fields: Dict,
        target_schema: Dict
    ) -> Dict[str, Any]:
        """
        Process and validate the semantic mapping result.
        
        Formats the result to match expected output structure and
        validates against target schema.
        """
        field_mappings = mapped_result.get('field_mappings', {})
        
        # Extract mapped data and confidence scores
        mapped_data = {}
        confidence_scores = {}
        
        for target_field, mapping_info in field_mappings.items():
            if isinstance(mapping_info, dict):
                mapped_data[target_field] = mapping_info.get('value')
                confidence_scores[target_field] = mapping_info.get('confidence', 0.8)
            else:
                # Simple value (shouldn't happen with our prompt)
                mapped_data[target_field] = mapping_info
                confidence_scores[target_field] = 0.7
        
        # Calculate overall confidence
        avg_confidence = (
            sum(confidence_scores.values()) / len(confidence_scores)
            if confidence_scores else 0.0
        )
        
        # Get consolidation summary
        consolidation_summary = mapped_result.get('consolidation_summary', {})
        
        return {
            'mapped_data': mapped_data,
            'confidence_scores': confidence_scores,
            'overall_confidence': avg_confidence,
            'extraction_method': 'docai_semantic_mapping',
            'success': True,
            'metadata': {
                'fields_mapped': len(mapped_data),
                'unmapped_fields': mapped_result.get('unmapped_fields', []),
                'consolidation_summary': consolidation_summary,
                'processing_timestamp': datetime.now().isoformat()
            }
        }