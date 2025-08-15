"""
Universal document extractor that works with ANY format.
No assumptions about layout, structure, or content.
Schema-driven extraction with multi-document aggregation.
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from ..core.universal_preprocessor import UniversalPreprocessor, SchemaHintBuilder
from ..core.base_llm_extractor import ExtractionResult, FieldExtraction

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class UniversalExtractionResult:
    """Result from universal extraction with confidence and source tracking."""
    extracted_data: Dict[str, Any]
    confidence_by_field: Dict[str, float]
    sources_by_field: Dict[str, List[str]]  # Which documents provided each field
    overall_confidence: float
    processing_time: float
    documents_processed: int
    api_calls: int
    cost_estimate: float
    warnings: List[str]


class UniversalExtractor:
    """
    Universal document extractor that works with ANY financial document format.
    Uses schema-driven extraction with multi-document aggregation.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize universal extractor."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required")
        
        self.client = AsyncAnthropic(api_key=api_key)
        self.preprocessor = UniversalPreprocessor()
        self.hint_builder = SchemaHintBuilder()
        
        # Universal settings
        self.model = "claude-3-5-sonnet-20241022"
        self.max_images_per_call = 5  # Claude handles 5 images well
        self.cost_per_1k_tokens = {"input": 0.003, "output": 0.015}
    
    async def extract_from_any_documents(
        self,
        file_paths: List[Union[str, Path]],
        target_schema: Dict[str, Any],
        application_id: Optional[str] = None
    ) -> UniversalExtractionResult:
        """
        Extract schema from ANY combination of documents.
        
        Args:
            file_paths: List of document paths (any format)
            target_schema: Schema to extract
            application_id: Optional ID for tracking
            
        Returns:
            UniversalExtractionResult with aggregated data
        """
        start_time = time.time()
        api_calls = 0
        warnings = []
        
        print(f"🌍 Universal extraction from {len(file_paths)} documents")
        
        # Step 1: Process all documents to images
        all_images = []
        document_sources = []  # Track which images came from which documents
        
        for file_path in file_paths:
            try:
                processed = self.preprocessor.preprocess_any_document(file_path)
                
                for img in processed.images:
                    all_images.append(img)
                    document_sources.append(str(file_path))
                
                print(f"  ✅ {Path(file_path).name}: {len(processed.images)} images")
                
            except Exception as e:
                warnings.append(f"Failed to process {file_path}: {e}")
                print(f"  ❌ {Path(file_path).name}: {e}")
        
        if not all_images:
            raise ValueError("No documents could be processed")
        
        # Step 2: Build schema hints for better extraction
        schema_hints = self.hint_builder.build_hints_for_schema(target_schema)
        
        # Step 3: Extract using optimal strategy
        if len(all_images) <= self.max_images_per_call:
            # Send all images in one request
            extraction_result = await self._extract_from_multiple_images(
                all_images, target_schema, schema_hints, document_sources
            )
            api_calls = 1
        else:
            # Extract from batches and aggregate
            extraction_result = await self._extract_and_aggregate(
                all_images, target_schema, schema_hints, document_sources
            )
            api_calls = len(all_images) // self.max_images_per_call + 1
        
        total_time = time.time() - start_time
        
        return UniversalExtractionResult(
            extracted_data=extraction_result['data'],
            confidence_by_field=extraction_result['confidence'],
            sources_by_field=extraction_result['sources'],
            overall_confidence=extraction_result['overall_confidence'],
            processing_time=total_time,
            documents_processed=len(file_paths),
            api_calls=api_calls,
            cost_estimate=self._estimate_cost(api_calls, len(all_images)),
            warnings=warnings
        )
    
    async def _extract_from_multiple_images(
        self,
        images: List,
        schema: Dict[str, Any],
        hints: Dict[str, List[str]],
        sources: List[str]
    ) -> Dict[str, Any]:
        """Extract from multiple images in single API call."""
        
        # Convert images to base64
        image_data = self.preprocessor.images_to_base64(images)
        
        # Build universal prompt
        prompt = self._build_universal_prompt(schema, hints)
        
        # Build message content
        content = [{"type": "text", "text": prompt}]
        
        for img_data in image_data:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img_data['media_type'],
                    "data": img_data['data']
                }
            })
        
        # Call Claude
        response = await self._call_claude(content)
        
        # Parse response
        return self._parse_extraction_response(response, sources)
    
    async def _extract_and_aggregate(
        self,
        images: List,
        schema: Dict[str, Any],
        hints: Dict[str, List[str]],
        sources: List[str]
    ) -> Dict[str, Any]:
        """Extract from image batches and aggregate results."""
        
        batch_results = []
        
        # Process in batches
        for i in range(0, len(images), self.max_images_per_call):
            batch_images = images[i:i + self.max_images_per_call]
            batch_sources = sources[i:i + self.max_images_per_call]
            
            batch_result = await self._extract_from_multiple_images(
                batch_images, schema, hints, batch_sources
            )
            batch_results.append(batch_result)
        
        # Aggregate all results
        return await self._aggregate_extractions(batch_results, schema)
    
    def _build_universal_prompt(
        self,
        schema: Dict[str, Any],
        hints: Dict[str, List[str]]
    ) -> str:
        """Build universal extraction prompt that works with any document."""
        
        schema_fields = list(schema.get('properties', {}).keys())
        
        prompt = f"""You are a universal financial document extractor. Extract data from ALL the provided images to fill this schema:

TARGET SCHEMA:
{json.dumps(schema, indent=2)}

FIELD VARIATIONS TO LOOK FOR:
{json.dumps(hints, indent=2)}

DOCUMENTS: The images could be ANYTHING - PDFs, Excel sheets, handwritten notes, screenshots, photos, forms in any layout.

EXTRACTION RULES:
1. Look through ALL images for each field
2. Use ANY variation of field names (see hints above)
3. Calculate/sum values if multiple entries exist
4. Extract even if format is unexpected
5. For currency: remove $, commas, convert to numbers
6. For dates: use YYYY-MM-DD format when possible
7. If a field appears in multiple documents, use the most complete/recent value
8. Return null only if truly not found anywhere

RESPONSE FORMAT - Return ONLY this JSON structure:
{{
  "extracted_data": {{
    "field_name": extracted_value,
    ...
  }},
  "confidence_scores": {{
    "field_name": 0.95,
    ...
  }},
  "source_info": {{
    "field_name": "Found in image X, section Y",
    ...
  }}
}}

CRITICAL: Look through ALL images before deciding a field is missing. Different document types contain different information."""
        
        return prompt
    
    async def _aggregate_extractions(
        self,
        batch_results: List[Dict[str, Any]],
        schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate multiple extraction results using Claude."""
        
        # Build aggregation prompt
        aggregation_prompt = f"""You have multiple extraction results from different document batches. Merge them into a single accurate dataset:

EXTRACTION RESULTS:
{json.dumps(batch_results, indent=2)}

TARGET SCHEMA:
{json.dumps(schema, indent=2)}

AGGREGATION RULES:
1. If a field appears in multiple results, choose the most complete/detailed value
2. If values conflict, use the one with higher confidence
3. Combine complementary information (e.g., different address parts)
4. Sum financial values if they represent parts of a total
5. Flag any major discrepancies in the source_info
6. Calculate overall confidence based on consistency across results

Return the same JSON format as individual extractions."""
        
        response = await self._call_claude([{"type": "text", "text": aggregation_prompt}])
        
        # Parse aggregated result
        return self._parse_extraction_response(response, ["aggregated"])
    
    async def _call_claude(self, content: List[Dict]) -> Any:
        """Call Claude API with retry logic."""
        
        for attempt in range(3):
            try:
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.1,  # Low for consistency
                    messages=[{
                        "role": "user",
                        "content": content
                    }]
                )
                return response
                
            except Exception as e:
                if attempt < 2:
                    wait_time = (2 ** attempt)
                    print(f"  API call failed (attempt {attempt + 1}): {e}")
                    print(f"  Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
    
    def _parse_extraction_response(
        self,
        response: Any,
        sources: List[str]
    ) -> Dict[str, Any]:
        """Parse Claude's extraction response."""
        
        try:
            raw_text = response.content[0].text.strip()
            
            # Clean response
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3]
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3]
            
            parsed = json.loads(raw_text)
            
            # Extract components
            extracted_data = parsed.get('extracted_data', {})
            confidence_scores = parsed.get('confidence_scores', {})
            source_info = parsed.get('source_info', {})
            
            # Calculate overall confidence
            confidences = list(confidence_scores.values())
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Build sources mapping
            sources_by_field = {}
            for field, info in source_info.items():
                sources_by_field[field] = [info] if isinstance(info, str) else info
            
            return {
                'data': extracted_data,
                'confidence': confidence_scores,
                'sources': sources_by_field,
                'overall_confidence': overall_confidence
            }
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse extraction response: {e}")
            print(f"Raw response: {raw_text[:500]}")
            
            # Return empty result
            return {
                'data': {},
                'confidence': {},
                'sources': {},
                'overall_confidence': 0.0
            }
    
    def _estimate_cost(self, api_calls: int, total_images: int) -> float:
        """Estimate API costs."""
        
        # Rough estimates based on image size and text
        estimated_input_tokens = api_calls * (1000 + total_images * 500)  # Base + images
        estimated_output_tokens = api_calls * 800  # Response tokens
        
        input_cost = (estimated_input_tokens / 1000) * self.cost_per_1k_tokens['input']
        output_cost = (estimated_output_tokens / 1000) * self.cost_per_1k_tokens['output']
        
        return input_cost + output_cost
    
    def convert_to_extraction_result(
        self,
        universal_result: UniversalExtractionResult
    ) -> ExtractionResult:
        """Convert to standard ExtractionResult format for compatibility."""
        
        fields = []
        for field_name, value in universal_result.extracted_data.items():
            if value is not None:
                confidence = universal_result.confidence_by_field.get(field_name, 0.8)
                sources = universal_result.sources_by_field.get(field_name, [])
                
                fields.append(FieldExtraction(
                    field_name=field_name,
                    value=value,
                    confidence=confidence,
                    source=", ".join(sources) if sources else "universal_extraction",
                    metadata={
                        "extraction_method": "universal",
                        "documents_processed": universal_result.documents_processed,
                        "api_calls": universal_result.api_calls
                    }
                ))
        
        return ExtractionResult(
            document_type="universal",
            fields=fields,
            overall_confidence=universal_result.overall_confidence,
            processing_time=universal_result.processing_time,
            model_used=self.model,
            needs_review=universal_result.overall_confidence < 0.8,
            metadata={
                "documents_processed": universal_result.documents_processed,
                "api_calls": universal_result.api_calls,
                "cost_estimate": universal_result.cost_estimate,
                "warnings": universal_result.warnings
            }
        )


class SimpleUniversalExtractor:
    """
    Dead simple universal extractor - the MVP approach.
    Works with literally anything.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.extractor = UniversalExtractor(api_key)
    
    async def process_loan_application(
        self,
        uploaded_files: List[Union[str, Path]],
        target_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process complete loan application from any uploaded files.
        
        Args:
            uploaded_files: Any combination of PDFs, Excel, images, etc.
            target_schema: What you want to extract
            
        Returns:
            Filled schema with confidence scores
        """
        
        print(f"🚀 Processing loan application with {len(uploaded_files)} files")
        
        # Extract from all documents
        result = await self.extractor.extract_from_any_documents(
            uploaded_files,
            target_schema
        )
        
        # Return simple format
        return {
            'data': result.extracted_data,
            'confidence': result.overall_confidence,
            'field_confidence': result.confidence_by_field,
            'sources': result.sources_by_field,
            'processing_time': result.processing_time,
            'cost': result.cost_estimate,
            'needs_review': result.overall_confidence < 0.8,
            'warnings': result.warnings
        }