"""
Anchor-based extractor for extracting values relative to text labels.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time
import re
import pdfplumber

from .base import BaseExtractor, ExtractionResult
from ..models import FormSpec, FieldSpec, FieldExtractionResult, AnchorSpec


class AnchorExtractor(BaseExtractor):
    """Extract values based on text anchors (labels) in the PDF."""
    
    def __init__(self):
        """Initialize the anchor extractor."""
        super().__init__(name="anchor")
        self.tolerance = 10  # Pixel tolerance for alignment
    
    def extract(self, 
                pdf_path: Path, 
                spec: FormSpec,
                target_fields: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract data using anchor-based extraction.
        
        Args:
            pdf_path: Path to the PDF document
            spec: Form specification
            target_fields: Optional list of specific field IDs to extract
            
        Returns:
            ExtractionResult with extracted data
        """
        start_time = time.time()
        result = self.create_extraction_result(pdf_path, spec)
        
        print(f"\n🎯 Anchor-Based Extraction: {pdf_path.name}")
        print("-" * 50)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"  📄 Processing {len(pdf.pages)} pages")
                
                # Build text index for all pages
                page_texts = self._build_page_index(pdf)
                
                # Extract fields based on spec
                fields_to_extract = spec.fields
                if target_fields:
                    fields_to_extract = [f for f in spec.fields if f.id in target_fields]
                
                extracted_count = 0
                for field_spec in fields_to_extract:
                    if not self._should_extract_field(field_spec):
                        continue
                    
                    field_result = self._extract_field(field_spec, pdf, page_texts)
                    if field_result and field_result.selected_value is not None:
                        result.add_field_result(field_result)
                        self.log_extraction(field_spec.id, field_result.selected_value, "anchor")
                        extracted_count += 1
                
                print(f"\n  ✅ Extracted {extracted_count}/{len(fields_to_extract)} fields")
                
        except Exception as e:
            error_msg = f"Anchor extraction failed: {e}"
            print(f"  ❌ {error_msg}")
            result.errors.append(error_msg)
        
        # Update stats
        elapsed = time.time() - start_time
        result.metadata['extraction_time'] = elapsed
        self.stats['documents_processed'] += 1
        self.stats['extraction_time'] += elapsed
        
        return result
    
    def _build_page_index(self, pdf: pdfplumber.PDF) -> Dict[int, Dict[str, Any]]:
        """
        Build an index of text and positions for all pages.
        
        Args:
            pdf: pdfplumber PDF object
            
        Returns:
            Dictionary mapping page numbers to text data
        """
        page_index = {}
        
        for i, page in enumerate(pdf.pages, 1):
            try:
                # Extract words with positions
                words = page.extract_words() or []
                
                # Extract full text for context
                text = page.extract_text() or ""
                
                # Group words into lines
                lines = self._group_words_into_lines(words)
                
                page_index[i] = {
                    'words': words,
                    'lines': lines,
                    'text': text,
                    'page': page
                }
            except Exception as e:
                print(f"  ⚠️ Error indexing page {i}: {e}")
                page_index[i] = {'words': [], 'lines': [], 'text': '', 'page': page}
        
        return page_index
    
    def _group_words_into_lines(self, words: List[Dict]) -> List[Dict]:
        """
        Group words into lines based on y-coordinate.
        
        Args:
            words: List of word dictionaries from pdfplumber
            
        Returns:
            List of line dictionaries
        """
        if not words:
            return []
        
        # Sort by y-coordinate (top) then x-coordinate (left)
        sorted_words = sorted(words, key=lambda w: (w['top'], w['x0']))
        
        lines = []
        current_line = []
        current_top = None
        
        for word in sorted_words:
            if current_top is None or abs(word['top'] - current_top) <= self.tolerance:
                current_line.append(word)
                if current_top is None:
                    current_top = word['top']
            else:
                # New line
                if current_line:
                    lines.append(self._create_line_dict(current_line))
                current_line = [word]
                current_top = word['top']
        
        # Add last line
        if current_line:
            lines.append(self._create_line_dict(current_line))
        
        return lines
    
    def _create_line_dict(self, words: List[Dict]) -> Dict:
        """Create a line dictionary from words."""
        text = ' '.join(w['text'] for w in words)
        return {
            'text': text,
            'words': words,
            'x0': min(w['x0'] for w in words),
            'x1': max(w['x1'] for w in words),
            'top': words[0]['top'],
            'bottom': words[0]['bottom']
        }
    
    def _should_extract_field(self, field_spec: FieldSpec) -> bool:
        """Check if this extractor should handle this field."""
        if not field_spec.extraction:
            return False
        
        # Check if field has anchors defined
        return bool(field_spec.extraction.anchors)
    
    def _extract_field(self,
                      field_spec: FieldSpec,
                      pdf: pdfplumber.PDF,
                      page_texts: Dict[int, Dict]) -> Optional[FieldExtractionResult]:
        """
        Extract a single field based on anchors.
        
        Args:
            field_spec: Field specification
            pdf: pdfplumber PDF object
            page_texts: Page text index
            
        Returns:
            FieldExtractionResult or None
        """
        result = FieldExtractionResult(
            field_id=field_spec.id,
            field_name=field_spec.field_name
        )
        
        # Try each anchor in the spec
        for anchor_dict in field_spec.extraction.anchors:
            anchor = AnchorSpec(**anchor_dict) if isinstance(anchor_dict, dict) else anchor_dict
            
            # Determine which pages to search
            pages_to_search = [anchor.page_hint] if anchor.page_hint else range(1, len(pdf.pages) + 1)
            
            for page_num in pages_to_search:
                if page_num not in page_texts:
                    continue
                
                page_data = page_texts[page_num]
                value = self._extract_by_anchor(anchor, page_data)
                
                if value:
                    candidate = self.create_candidate(
                        value=value,
                        page=page_num,
                        method=f"anchor_{anchor.strategy}",
                        confidence=0.85
                    )
                    result.candidates.append(candidate)
                    
                    # Use first successful extraction
                    if not result.selected_value:
                        result.selected_value = value
        
        # Return result if we found any candidates
        if result.candidates:
            return result
        
        return None
    
    def _extract_by_anchor(self, anchor: AnchorSpec, page_data: Dict) -> Optional[str]:
        """
        Extract value based on an anchor specification.
        
        Args:
            anchor: Anchor specification
            page_data: Page text data
            
        Returns:
            Extracted value or None
        """
        # Find anchor text in page
        anchor_positions = self._find_anchor_text(anchor.text, page_data)
        
        if not anchor_positions:
            return None
        
        # Use the specified occurrence (default to first)
        if anchor.occurrence <= len(anchor_positions):
            anchor_pos = anchor_positions[anchor.occurrence - 1]
        else:
            return None
        
        # Extract value based on strategy
        if anchor.strategy == "right":
            return self._extract_right_of(anchor_pos, page_data, anchor.offset)
        elif anchor.strategy == "below":
            return self._extract_below(anchor_pos, page_data, anchor.offset)
        elif anchor.strategy == "above":
            return self._extract_above(anchor_pos, page_data, anchor.offset)
        elif anchor.strategy == "left":
            return self._extract_left_of(anchor_pos, page_data, anchor.offset)
        
        return None
    
    def _find_anchor_text(self, anchor_text: str, page_data: Dict) -> List[Dict]:
        """
        Find all occurrences of anchor text in the page.
        
        Args:
            anchor_text: Text to search for
            page_data: Page text data
            
        Returns:
            List of anchor positions
        """
        positions = []
        
        # Search in words for more precise positioning
        for i, line in enumerate(page_data['lines']):
            line_text = line['text'].lower()
            anchor_lower = anchor_text.lower()
            
            if anchor_lower in line_text:
                # Find the words that make up this anchor
                words = line['words']
                
                # Try to find the exact position of the anchor text
                anchor_end_x = line['x0']  # Default to line start
                
                # Build text from words to find where anchor ends
                accumulated_text = ""
                for word in words:
                    accumulated_text += word['text'].lower() + " "
                    if anchor_lower in accumulated_text.strip():
                        # Found the end of the anchor text
                        anchor_end_x = word['x1']
                        break
                
                # For better accuracy, try to find the actual end position
                # by looking at individual words
                anchor_words = anchor_text.split()
                if anchor_words:
                    last_anchor_word = anchor_words[-1].lower()
                    for word in words:
                        if last_anchor_word in word['text'].lower():
                            anchor_end_x = word['x1'] + 5  # Small buffer after anchor
                            break
                
                positions.append({
                    'x0': line['x0'],
                    'x1': anchor_end_x,  # More precise end position
                    'top': line['top'],
                    'bottom': line['bottom'],
                    'text': anchor_text,
                    'line_text': line['text']  # Keep full line for context
                })
        
        return positions
    
    def _extract_right_of(self, anchor_pos: Dict, page_data: Dict, offset: int) -> Optional[str]:
        """Extract text to the right of an anchor."""
        # Find words to the right of the anchor
        anchor_right = anchor_pos['x1']
        anchor_top = anchor_pos['top']
        
        # First, check if there's text on the same line after the anchor
        line_text = anchor_pos.get('line_text', '')
        anchor_text = anchor_pos['text']
        
        # Try to extract value from the same line first
        if line_text and anchor_text in line_text:
            # Find what comes after the anchor in the same line
            anchor_idx = line_text.lower().find(anchor_text.lower())
            if anchor_idx >= 0:
                after_anchor = line_text[anchor_idx + len(anchor_text):].strip()
                # Remove common separators
                after_anchor = after_anchor.lstrip(':').lstrip('-').strip()
                
                # Check if this looks like a value (not another label)
                if after_anchor and not self._is_label_text(after_anchor):
                    # Take the first meaningful part (before any other label)
                    value_parts = []
                    for part in after_anchor.split():
                        if self._is_label_text(part):
                            break
                        value_parts.append(part)
                    
                    if value_parts:
                        return ' '.join(value_parts)
        
        # If no value on same line, look for words to the right
        words_right = []
        for word in page_data['words']:
            # Check if word is to the right and on the same line
            if (word['x0'] > anchor_right and  # Changed >= to > to avoid overlap
                word['x0'] <= anchor_right + offset and
                abs(word['top'] - anchor_top) <= self.tolerance):
                # Skip if this looks like a label
                if not self._is_label_text(word['text']):
                    words_right.append(word)
        
        if words_right:
            # Sort by x-coordinate and join
            words_right.sort(key=lambda w: w['x0'])
            
            # Take words until we hit another label
            value_words = []
            for word in words_right:
                if self._is_label_text(word['text']):
                    break
                value_words.append(word['text'])
            
            if value_words:
                return ' '.join(value_words)
        
        return None
    
    def _is_label_text(self, text: str) -> bool:
        """Check if text looks like a label rather than a value."""
        if not text:
            return False
        
        # Common label indicators
        label_indicators = [
            text.endswith(':'),
            text.endswith('?'),
            text.startswith('('),
            text.endswith(')'),
            len(text) > 30,  # Very long text is likely a label/question
            'please' in text.lower(),
            'enter' in text.lower(),
            'provide' in text.lower(),
            'specify' in text.lower(),
            text.isupper() and len(text) > 5,  # All caps labels
        ]
        
        return any(label_indicators)
    
    def _extract_below(self, anchor_pos: Dict, page_data: Dict, offset: int) -> Optional[str]:
        """Extract text below an anchor."""
        anchor_bottom = anchor_pos['bottom']
        anchor_x0 = anchor_pos['x0']
        anchor_x1 = anchor_pos.get('x1', anchor_x0 + 100)
        
        # Find the next line below
        for line in page_data['lines']:
            if (line['top'] >= anchor_bottom and
                line['top'] <= anchor_bottom + offset):
                # Check horizontal alignment (allow some flexibility)
                if (line['x0'] >= anchor_x0 - 50 and
                    line['x0'] <= anchor_x1 + 100):
                    text = line['text'].strip()
                    # Skip if this is another label
                    if not self._is_label_text(text):
                        return text
                    # If it's a label with a value after it, extract the value
                    if ':' in text:
                        parts = text.split(':', 1)
                        if len(parts) == 2 and parts[1].strip():
                            return parts[1].strip()
        
        return None
    
    def _extract_above(self, anchor_pos: Dict, page_data: Dict, offset: int) -> Optional[str]:
        """Extract text above an anchor."""
        anchor_top = anchor_pos['top']
        anchor_x0 = anchor_pos['x0']
        anchor_x1 = anchor_pos['x1']
        
        # Find the line above
        for line in reversed(page_data['lines']):
            if (line['bottom'] <= anchor_top and
                line['bottom'] >= anchor_top - offset):
                # Check horizontal alignment
                if (line['x0'] >= anchor_x0 - 50 and
                    line['x0'] <= anchor_x1 + 50):
                    return line['text'].strip()
        
        return None
    
    def _extract_left_of(self, anchor_pos: Dict, page_data: Dict, offset: int) -> Optional[str]:
        """Extract text to the left of an anchor."""
        anchor_left = anchor_pos['x0']
        anchor_top = anchor_pos['top']
        
        words_left = []
        for word in page_data['words']:
            # Check if word is to the left and on the same line
            if (word['x1'] <= anchor_left and
                word['x1'] >= anchor_left - offset and
                abs(word['top'] - anchor_top) <= self.tolerance):
                words_left.append(word)
        
        if words_left:
            # Sort by x-coordinate and join
            words_left.sort(key=lambda w: w['x0'])
            return ' '.join(w['text'] for w in words_left)
        
        return None
    
    def supports_field(self, field: FieldSpec) -> bool:
        """Check if this extractor can handle a specific field."""
        if not field.extraction:
            return False
        
        # We support fields with anchors
        return bool(field.extraction.anchors)