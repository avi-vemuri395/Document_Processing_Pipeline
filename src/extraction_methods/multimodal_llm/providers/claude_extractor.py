"""
Claude Sonnet extractor implementation using Anthropic's API.
Leverages Claude's vision capabilities for document understanding.
"""

import os
import base64
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from io import BytesIO

# Load environment variables from .env file
load_dotenv()

# Import PDF conversion if available
try:
    from pdf2image import convert_from_path, convert_from_bytes
    from PIL import Image
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not installed. PDF support limited.")

# Import Excel handling if available
try:
    import pandas as pd
    import openpyxl
    from PIL import Image, ImageDraw, ImageFont
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("Warning: pandas/openpyxl not installed. Excel support limited.")

# Import with error handling for missing dependencies
try:
    from anthropic import Anthropic, AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("Warning: anthropic package not installed. Claude extractor will not be available.")

from ..core.base_llm_extractor import (
    BaseLLMExtractor,
    ExtractionResult,
    FieldExtraction,
    BoundingBox
)
from ..utils.prompt_builder import PromptBuilder, DocumentType
from ..models.extraction_models import (
    PersonalFinancialStatementExtraction,
    ExtractedField
)


class ClaudeExtractor(BaseLLMExtractor):
    """Claude-based document extractor using vision capabilities."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize Claude extractor.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY from .env)
            model: Claude model to use (defaults to CLAUDE_MODEL from .env)
            confidence_threshold: Minimum confidence for automatic processing
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
        
        All parameters can be set via environment variables in .env file.
        """
        # Load from environment with defaults
        confidence_threshold = confidence_threshold or float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
        super().__init__(confidence_threshold)
        
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package is required for Claude extractor. "
                "Install with: pip install anthropic"
            )
        
        # Get API key from parameter or .env file
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key required. Please set ANTHROPIC_API_KEY in your .env file "
                "or pass api_key parameter."
            )
        
        # Get other configurations from .env with defaults
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
        self.model_name = f"Claude {self.model}"
        self.max_retries = max_retries or int(os.getenv("MAX_RETRIES", "3"))
        self.timeout = timeout or int(os.getenv("REQUEST_TIMEOUT", "120"))
        
        # Initialize clients
        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        
        # Initialize prompt builders
        from ..utils.prompt_builder import PromptBuilder
        from ..utils.enhanced_prompt_builder import EnhancedPromptBuilder
        self.prompt_builder = PromptBuilder()
        self.enhanced_prompt_builder = EnhancedPromptBuilder()
    
    def _encode_image(self, file_path: Path) -> str:
        """
        Encode image file to base64.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Base64 encoded string
        """
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    def _prepare_document(self, document: Union[Path, bytes]) -> List[Tuple[str, str]]:
        """
        Prepare document for API call. Converts PDFs to images if needed.
        
        Args:
            document: Document path or bytes
            
        Returns:
            List of tuples (base64_data, media_type) for each page/image
        """
        pages = []
        
        if isinstance(document, bytes):
            # Handle bytes input
            if PDF2IMAGE_AVAILABLE:
                # Convert PDF bytes to images
                images = convert_from_bytes(document)
                for img in images[:5]:  # Limit to first 5 pages for cost
                    pages.append(self._image_to_base64(img))
            else:
                # Fallback: treat as single image
                base64_data = base64.b64encode(document).decode("utf-8")
                pages.append((base64_data, "image/png"))
        else:
            file_path = Path(document)
            if not file_path.exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
            
            suffix = file_path.suffix.lower()
            
            if suffix == ".pdf":
                if not PDF2IMAGE_AVAILABLE:
                    raise ImportError(
                        "PDF support requires pdf2image. Install with: "
                        "pip install pdf2image pillow"
                    )
                # Convert PDF to images
                images = convert_from_path(str(file_path), dpi=150)
                for i, img in enumerate(images[:5]):  # Limit to first 5 pages
                    pages.append(self._image_to_base64(img))
            elif suffix in [".jpg", ".jpeg"]:
                base64_data = self._encode_image(file_path)
                pages.append((base64_data, "image/jpeg"))
            elif suffix == ".png":
                base64_data = self._encode_image(file_path)
                pages.append((base64_data, "image/png"))
            elif suffix in [".xlsx", ".xls"]:
                # Convert Excel to images
                excel_images = self._excel_to_image(file_path)
                for img in excel_images:
                    pages.append(self._image_to_base64(img))
            else:
                raise ValueError(f"Unsupported file type: {suffix}")
        
        if not pages:
            raise ValueError("No pages could be extracted from document")
        
        return pages
    
    def _image_to_base64(self, image: Image.Image) -> Tuple[str, str]:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple of (base64_data, media_type)
        """
        # Convert to PNG for consistency
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return base64_data, "image/png"
    
    def _excel_to_image(self, file_path: Path) -> List[Image.Image]:
        """
        Convert Excel file to images (one per sheet).
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            List of PIL Image objects
        """
        if not EXCEL_AVAILABLE:
            raise ImportError(
                "Excel support requires pandas and openpyxl. Install with: "
                "pip install pandas openpyxl"
            )
        
        images = []
        
        # Read Excel file
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_name in excel_file.sheet_names[:3]:  # Limit to first 3 sheets
            # Read sheet as DataFrame
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # Convert DataFrame to HTML for better formatting
            html = df.to_html(index=True, border=1)
            
            # Create image from DataFrame
            # Calculate image size based on content
            rows, cols = df.shape
            cell_width = 150
            cell_height = 30
            header_height = 40
            
            img_width = max(800, (cols + 1) * cell_width)  # +1 for index column
            img_height = max(600, (rows + 2) * cell_height + header_height)  # +2 for header
            
            # Create white image
            img = Image.new('RGB', (img_width, img_height), 'white')
            draw = ImageDraw.Draw(img)
            
            # Try to use a font, fall back to default if not available
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
                header_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
            except:
                font = ImageFont.load_default()
                header_font = font
            
            # Draw sheet name as title
            draw.text((10, 10), f"Sheet: {sheet_name}", fill='black', font=header_font)
            
            # Draw headers
            y_pos = header_height
            x_pos = 10
            
            # Draw index header
            draw.rectangle([x_pos, y_pos, x_pos + cell_width, y_pos + cell_height], outline='black')
            draw.text((x_pos + 5, y_pos + 5), "Index", fill='black', font=font)
            x_pos += cell_width
            
            # Draw column headers
            for col in df.columns:
                draw.rectangle([x_pos, y_pos, x_pos + cell_width, y_pos + cell_height], outline='black')
                col_text = str(col)[:20]  # Truncate long headers
                draw.text((x_pos + 5, y_pos + 5), col_text, fill='black', font=font)
                x_pos += cell_width
            
            # Draw data rows
            for idx, row in df.iterrows():
                y_pos += cell_height
                x_pos = 10
                
                # Draw index
                draw.rectangle([x_pos, y_pos, x_pos + cell_width, y_pos + cell_height], outline='black')
                draw.text((x_pos + 5, y_pos + 5), str(idx), fill='black', font=font)
                x_pos += cell_width
                
                # Draw row data
                for value in row:
                    draw.rectangle([x_pos, y_pos, x_pos + cell_width, y_pos + cell_height], outline='black')
                    val_text = str(value)[:20] if pd.notna(value) else ""  # Truncate and handle NaN
                    draw.text((x_pos + 5, y_pos + 5), val_text, fill='black', font=font)
                    x_pos += cell_width
            
            images.append(img)
        
        return images
    
    async def extract_with_schema(
        self,
        document: Union[Path, bytes],
        schema: Dict[str, Any],
        document_type: Optional[str] = None
    ) -> ExtractionResult:
        """
        Extract structured data using Claude's vision capabilities.
        
        Args:
            document: Document to process
            schema: JSON Schema for extraction
            document_type: Optional document type hint
            
        Returns:
            Extraction result with confidence scores
        """
        start_time = time.time()
        
        try:
            # Validate schema
            self.validate_schema(schema)
            
            # Prepare document (converts PDF to images)
            pages = self._prepare_document(document)
            
            # Determine document type enum if provided
            doc_type_enum = None
            enhanced_doc_type = None
            if document_type:
                try:
                    # Try original DocumentType first
                    from ..utils.prompt_builder import DocumentType
                    doc_type_enum = DocumentType(document_type.lower())
                except ValueError:
                    # Try enhanced DocumentType
                    try:
                        from ..core.enhanced_document_classifier import DocumentType as EnhancedDocType
                        enhanced_doc_type = EnhancedDocType(document_type.lower())
                    except ValueError:
                        pass
            
            # Build extraction prompt - use enhanced if available
            if enhanced_doc_type:
                prompt = self.enhanced_prompt_builder.build_extraction_prompt(
                    document_type=enhanced_doc_type,
                    schema=schema,
                    include_examples=True
                )
            else:
                prompt = self.prompt_builder.build_extraction_prompt(
                    schema=schema,
                    document_type=doc_type_enum,
                    include_examples=True
                )
            
            # Add specific instructions for confidence scoring
            prompt += """

CRITICAL: For each field you extract, you MUST include a confidence score between 0 and 1.
The confidence should reflect how certain you are about the extraction accuracy.

If the document has multiple pages, look through ALL pages to find the requested information.
"""
            
            # Build content with all page images
            content = [{"type": "text", "text": prompt}]
            
            for page_data, media_type in pages:
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": page_data
                    }
                })
            
            # Make API call with retries
            response = None
            last_error = None
            
            for attempt in range(self.max_retries):
                try:
                    response = await self.async_client.messages.create(
                        model=self.model,
                        max_tokens=4096,
                        temperature=0.1,  # Low temperature for consistency
                        messages=[
                            {
                                "role": "user",
                                "content": content
                            }
                        ]
                    )
                    break
                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            
            if not response:
                raise last_error or Exception("Failed to get response from Claude")
            
            # Parse response
            extracted_data = self._parse_response(response.content[0].text)
            
            # Convert to field extractions
            fields = self._convert_to_field_extractions(extracted_data)
            
            # Calculate overall confidence
            field_confidences = [f.confidence for f in fields]
            overall_confidence = self.aggregate_confidence(field_confidences)
            
            # Create result
            result = ExtractionResult(
                document_type=document_type or "unknown",
                fields=fields,
                overall_confidence=overall_confidence,
                processing_time=time.time() - start_time,
                model_used=self.model_name,
                needs_review=overall_confidence < self.confidence_threshold,
                metadata={
                    "api_calls": 1,
                    "tokens_used": getattr(response.usage, 'total_tokens', None) if hasattr(response, 'usage') else None
                }
            )
            
            return result
            
        except Exception as e:
            # Return error result
            return ExtractionResult(
                document_type=document_type or "unknown",
                fields=[],
                overall_confidence=0.0,
                processing_time=time.time() - start_time,
                model_used=self.model_name,
                needs_review=True,
                error=str(e)
            )
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's response to extract JSON data.
        
        Args:
            response_text: Raw response text from Claude
            
        Returns:
            Parsed JSON data
        """
        # Try to extract JSON from response
        # Claude sometimes wraps JSON in markdown code blocks
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        elif response_text.startswith("```"):
            response_text = response_text[3:]
        
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to find JSON object in the text
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            
            raise ValueError(f"Could not parse JSON from response: {response_text[:500]}")
    
    def _convert_to_field_extractions(
        self,
        extracted_data: Dict[str, Any]
    ) -> List[FieldExtraction]:
        """
        Convert extracted data to FieldExtraction objects.
        
        Args:
            extracted_data: Raw extracted data
            
        Returns:
            List of FieldExtraction objects
        """
        fields = []
        
        for field_name, field_data in extracted_data.items():
            if field_data is None:
                continue
            
            # Handle different formats
            if isinstance(field_data, dict):
                # Expected format with value and confidence
                value = field_data.get("value")
                confidence = field_data.get("confidence", 0.5)
                raw_text = field_data.get("raw_text")
                page_number = field_data.get("page_number")
                
                if value is not None:
                    fields.append(FieldExtraction(
                        field_name=field_name,
                        value=value,
                        confidence=confidence,
                        raw_text=raw_text,
                        bounding_box=None  # Claude doesn't provide bounding boxes
                    ))
            else:
                # Direct value without confidence
                fields.append(FieldExtraction(
                    field_name=field_name,
                    value=field_data,
                    confidence=0.5,  # Default confidence
                    raw_text=None
                ))
        
        return fields
    
    async def classify_document(
        self,
        document: Union[Path, bytes]
    ) -> Tuple[str, float]:
        """
        Classify document type using Claude's vision.
        
        Args:
            document: Document to classify
            
        Returns:
            Tuple of (document_type, confidence)
        """
        try:
            # Prepare document (only use first page for classification)
            pages = self._prepare_document(document)
            first_page_data, media_type = pages[0]
            
            # Get classification prompt
            prompt = self.prompt_builder.build_classification_prompt()
            
            # Make API call (only with first page for speed)
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": first_page_data
                                }
                            }
                        ]
                    }
                ]
            )
            
            # Parse response
            result = self._parse_response(response.content[0].text)
            
            return result.get("document_type", "unknown"), result.get("confidence", 0.0)
            
        except Exception as e:
            print(f"Classification error: {e}")
            return "unknown", 0.0
    
    def get_api_cost(self, document_pages: int) -> float:
        """
        Estimate API cost for processing document.
        
        Args:
            document_pages: Number of pages
            
        Returns:
            Estimated cost in USD
        """
        # Claude 3.5 Sonnet pricing (as of late 2024)
        # Input: $3 per million tokens
        # Output: $15 per million tokens
        # Images: ~1000 tokens per image
        
        estimated_input_tokens = document_pages * 1500  # Image + prompt
        estimated_output_tokens = 500  # Structured extraction
        
        input_cost = (estimated_input_tokens / 1_000_000) * 3.00
        output_cost = (estimated_output_tokens / 1_000_000) * 15.00
        
        return input_cost + output_cost
    
    # Synchronous wrapper for testing
    def extract_sync(
        self,
        document: Union[Path, bytes],
        schema: Dict[str, Any],
        document_type: Optional[str] = None
    ) -> ExtractionResult:
        """
        Synchronous wrapper for extract_with_schema.
        
        Args:
            document: Document to process
            schema: JSON Schema for extraction
            document_type: Optional document type hint
            
        Returns:
            Extraction result
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.extract_with_schema(document, schema, document_type)
            )
        finally:
            loop.close()