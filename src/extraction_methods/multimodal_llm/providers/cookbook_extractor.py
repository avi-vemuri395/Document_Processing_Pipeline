"""
Two-pass extraction based on Anthropic Transcription Cookbook.
First pass: Pure transcription for accuracy
Second pass: Structure mapping for schema compliance
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from ..core.optimized_pdf_processor import ClaudeOptimizedProcessor, ProcessedPage
from ..core.base_llm_extractor import ExtractionResult, FieldExtraction

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class TranscriptionResult:
    """Result from first-pass transcription."""
    text: str
    confidence: float
    processing_time: float
    pages_processed: int
    metadata: Dict[str, Any]


@dataclass
class CookbookExtractionResult:
    """Enhanced result with transcription and structured data."""
    transcription: TranscriptionResult
    structured_data: ExtractionResult
    total_processing_time: float
    cost_estimate: float
    api_calls: int


class CookbookExtractor:
    """
    Implementation of Anthropic Cookbook two-pass approach.
    Significantly improves accuracy over single-pass extraction.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optimized settings."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required")
        
        self.client = AsyncAnthropic(api_key=api_key)
        self.processor = ClaudeOptimizedProcessor()
        
        # Claude model optimized for different tasks
        self.transcription_model = "claude-3-5-sonnet-20241022"
        self.structuring_model = "claude-3-5-sonnet-20241022"
        
        # Cost tracking (approximate)
        self.cost_per_1k_tokens = {
            "input": 0.003,   # $3 per 1M input tokens
            "output": 0.015   # $15 per 1M output tokens
        }
    
    async def extract_with_cookbook_approach(
        self,
        document_path: Path,
        schema: Dict[str, Any],
        document_type: Optional[str] = None
    ) -> CookbookExtractionResult:
        """
        Main extraction using Anthropic cookbook two-pass approach.
        
        Args:
            document_path: Path to document
            schema: Target schema for extraction
            document_type: Optional document type for optimization
            
        Returns:
            CookbookExtractionResult with transcription and structured data
        """
        start_time = time.time()
        api_calls = 0
        
        print(f"🔍 Starting cookbook extraction: {document_path.name}")
        
        # Step 1: Optimize document for Claude
        print("  📄 Processing document for Claude...")
        processed_pages = self.processor.process_pdf_for_claude(document_path, document_type)
        
        # Step 2: First pass - Pure transcription
        print("  📝 First pass: Transcribing document...")
        transcription_result = await self._transcribe_document(processed_pages)
        api_calls += 1
        
        # Step 3: Second pass - Structure mapping
        print("  🏗️  Second pass: Mapping to schema...")
        structured_result = await self._structure_transcription(
            transcription_result.text, 
            schema,
            document_type
        )
        api_calls += 1
        
        # Step 4: Calculate costs and metrics
        total_time = time.time() - start_time
        cost_estimate = self._estimate_cost(transcription_result, structured_result)
        
        print(f"  ✅ Extraction complete: {total_time:.2f}s, ~${cost_estimate:.4f}")
        
        return CookbookExtractionResult(
            transcription=transcription_result,
            structured_data=structured_result,
            total_processing_time=total_time,
            cost_estimate=cost_estimate,
            api_calls=api_calls
        )
    
    async def _transcribe_document(self, pages: List[ProcessedPage]) -> TranscriptionResult:
        """
        First pass: Pure transcription optimized for accuracy.
        Based on Anthropic cookbook recommendations.
        """
        start_time = time.time()
        
        # Build optimized transcription prompt
        transcription_prompt = """You are a document transcription specialist. Your task is to transcribe ALL text from this document with perfect accuracy.

CRITICAL REQUIREMENTS:
1. Transcribe EVERY piece of text exactly as it appears
2. Maintain original structure and formatting
3. For tables, preserve column/row relationships using clear separators
4. Include ALL numbers, especially financial figures with their exact formatting
5. Preserve spacing and alignment where it adds meaning
6. Include labels, headers, field names, and values
7. Note any handwritten text or unclear sections

FORMATTING GUIDELINES:
- Use | to separate table columns
- Use --- to separate table rows
- Preserve line breaks for forms
- Keep currency symbols and commas in numbers
- Maintain date formats exactly as shown

Begin transcription:"""
        
        # Process pages (combine if multiple, or use segments)
        content = [{"type": "text", "text": transcription_prompt}]
        
        pages_processed = 0
        for page in pages[:3]:  # Limit to 3 pages for cost control
            # Use main image
            base64_data, media_type = self.processor.to_base64(page.image)
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64_data
                }
            })
            pages_processed += 1
            
            # Add high-quality table images if available
            for i, table in enumerate(page.tables[:2]):  # Max 2 tables per page
                table_base64, table_media = self.processor.to_base64(table)
                content.append({
                    "type": "text", 
                    "text": f"\\n--- Enhanced Table {i+1} from Page {page.page_number} ---"
                })
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": table_media,
                        "data": table_base64
                    }
                })
        
        # Make API call with retry logic
        response = await self._call_claude_with_retry(
            model=self.transcription_model,
            content=content,
            max_tokens=4096,
            temperature=0.0  # Deterministic for transcription
        )
        
        transcribed_text = response.content[0].text
        
        # Calculate confidence based on response quality
        confidence = self._assess_transcription_quality(transcribed_text, pages_processed)
        
        return TranscriptionResult(
            text=transcribed_text,
            confidence=confidence,
            processing_time=time.time() - start_time,
            pages_processed=pages_processed,
            metadata={
                "input_tokens": getattr(response.usage, 'input_tokens', 0),
                "output_tokens": getattr(response.usage, 'output_tokens', 0),
                "model_used": self.transcription_model
            }
        )
    
    async def _structure_transcription(
        self,
        transcription: str,
        schema: Dict[str, Any],
        document_type: Optional[str]
    ) -> ExtractionResult:
        """
        Second pass: Map transcription to structured schema.
        More reliable than direct extraction.
        """
        start_time = time.time()
        
        # Build schema-focused prompt
        structure_prompt = f"""You are a financial document data extraction specialist. You have been provided with a complete transcription of a {document_type or 'financial'} document.

TRANSCRIPTION:
{transcription}

EXTRACTION SCHEMA:
{json.dumps(schema, indent=2)}

TASK: Extract and structure the data according to the schema above.

CRITICAL RULES:
1. Map each schema field to the corresponding value in the transcription
2. Convert currency strings to numbers (remove $, commas)
3. Extract dates in ISO format (YYYY-MM-DD) when possible
4. For missing fields, use null
5. Ensure all numeric fields are proper numbers (not strings)
6. Sum multiple entries when schema expects totals
7. Provide confidence score (0.0-1.0) for each field

RESPONSE FORMAT: Return ONLY valid JSON in this format:
{{
  "field_name": {{
    "value": extracted_value,
    "confidence": 0.95,
    "source": "exact text from transcription where found"
  }}
}}

JSON Response:"""
        
        # Call Claude for structuring
        response = await self._call_claude_with_retry(
            model=self.structuring_model,
            content=[{"type": "text", "text": structure_prompt}],
            max_tokens=2048,
            temperature=0.1  # Low but not 0 for flexibility
        )
        
        # Parse response
        try:
            raw_response = response.content[0].text.strip()
            
            # Clean up response (remove markdown blocks if present)
            if raw_response.startswith("```json"):
                raw_response = raw_response[7:-3]
            elif raw_response.startswith("```"):
                raw_response = raw_response[3:-3]
            
            structured_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            print(f"Failed to parse structured response: {e}")
            print(f"Raw response: {raw_response[:500]}")
            structured_data = {}
        
        # Convert to FieldExtraction objects
        fields = []
        for field_name, field_data in structured_data.items():
            if field_data is None:
                continue
            
            if isinstance(field_data, dict) and 'value' in field_data:
                fields.append(FieldExtraction(
                    field_name=field_name,
                    value=field_data['value'],
                    confidence=field_data.get('confidence', 0.8),
                    source=field_data.get('source', 'transcription_mapping'),
                    metadata={
                        "extraction_method": "cookbook_two_pass",
                        "transcription_based": True
                    }
                ))
            else:
                # Simple value format
                fields.append(FieldExtraction(
                    field_name=field_name,
                    value=field_data,
                    confidence=0.7,  # Lower confidence for simple format
                    source="transcription_mapping",
                    metadata={"extraction_method": "cookbook_two_pass"}
                ))
        
        # Calculate overall confidence
        confidences = [f.confidence for f in fields if f.confidence is not None]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return ExtractionResult(
            document_type=document_type or "unknown",
            fields=fields,
            overall_confidence=overall_confidence,
            processing_time=time.time() - start_time,
            model_used=f"{self.transcription_model} + {self.structuring_model}",
            needs_review=overall_confidence < 0.8,
            metadata={
                "transcription_length": len(transcription),
                "fields_extracted": len(fields),
                "input_tokens": getattr(response.usage, 'input_tokens', 0),
                "output_tokens": getattr(response.usage, 'output_tokens', 0),
                "two_pass_approach": True
            }
        )
    
    async def _call_claude_with_retry(
        self,
        model: str,
        content: List[Dict],
        max_tokens: int,
        temperature: float,
        max_retries: int = 3
    ):
        """Call Claude API with retry logic and error handling."""
        
        for attempt in range(max_retries):
            try:
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{
                        "role": "user",
                        "content": content
                    }]
                )
                return response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff
                    print(f"API call failed (attempt {attempt + 1}): {e}")
                    print(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
    
    def _assess_transcription_quality(self, transcription: str, pages_processed: int) -> float:
        """Assess quality of transcription for confidence scoring."""
        
        confidence = 0.8  # Base confidence
        
        # Length check
        expected_length = pages_processed * 1000  # ~1000 chars per page
        actual_length = len(transcription)
        
        if actual_length > expected_length * 0.5:
            confidence += 0.1
        if actual_length > expected_length:
            confidence += 0.05
        
        # Content quality indicators
        financial_indicators = [
            '$', 'total', 'assets', 'liabilities', 'income',
            'name', 'address', 'phone', 'date'
        ]
        
        found_indicators = sum(1 for indicator in financial_indicators 
                             if indicator.lower() in transcription.lower())
        
        confidence += (found_indicators / len(financial_indicators)) * 0.1
        
        # Structure indicators
        if '|' in transcription:  # Table formatting
            confidence += 0.05
        if transcription.count('\\n') > pages_processed * 10:  # Good structure
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _estimate_cost(
        self,
        transcription: TranscriptionResult,
        structured: ExtractionResult
    ) -> float:
        """Estimate API costs for the extraction."""
        
        total_cost = 0.0
        
        # Transcription costs
        if transcription.metadata:
            input_tokens = transcription.metadata.get('input_tokens', 0)
            output_tokens = transcription.metadata.get('output_tokens', 0)
            
            total_cost += (input_tokens / 1000) * self.cost_per_1k_tokens['input']
            total_cost += (output_tokens / 1000) * self.cost_per_1k_tokens['output']
        
        # Structuring costs
        if structured.metadata:
            input_tokens = structured.metadata.get('input_tokens', 0)
            output_tokens = structured.metadata.get('output_tokens', 0)
            
            total_cost += (input_tokens / 1000) * self.cost_per_1k_tokens['input']
            total_cost += (output_tokens / 1000) * self.cost_per_1k_tokens['output']
        
        return total_cost
    
    def create_extraction_report(self, result: CookbookExtractionResult) -> str:
        """Create detailed extraction report."""
        
        report = f"""
# Cookbook Extraction Report

## Document Processing
- **Processing Time**: {result.total_processing_time:.2f}s
- **API Calls**: {result.api_calls}
- **Estimated Cost**: ${result.cost_estimate:.4f}

## Transcription (Pass 1)
- **Length**: {len(result.transcription.text):,} characters
- **Confidence**: {result.transcription.confidence:.1%}
- **Pages Processed**: {result.transcription.pages_processed}
- **Processing Time**: {result.transcription.processing_time:.2f}s

## Structured Extraction (Pass 2)
- **Fields Extracted**: {len(result.structured_data.fields)}
- **Overall Confidence**: {result.structured_data.overall_confidence:.1%}
- **Needs Review**: {'Yes' if result.structured_data.needs_review else 'No'}
- **Processing Time**: {result.structured_data.processing_time:.2f}s

## Extracted Fields
"""
        
        for field in result.structured_data.fields:
            report += f"- **{field.field_name}**: {field.value} (confidence: {field.confidence:.1%})\\n"
        
        if result.transcription.confidence > 0.9 and result.structured_data.overall_confidence > 0.85:
            report += "\\n✅ **High Quality Extraction** - Ready for production use"
        elif result.structured_data.overall_confidence > 0.7:
            report += "\\n⚠️ **Medium Quality Extraction** - Review recommended"
        else:
            report += "\\n❌ **Low Quality Extraction** - Manual review required"
        
        return report