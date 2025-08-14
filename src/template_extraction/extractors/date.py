"""
Date extraction module for handling various date formats.
Part of Phase 2 implementation.
"""

import re
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path

from pypdf import PdfReader
from pdfplumber import PDF

from .base import BaseExtractor, ExtractionResult
from ..models import FormSpec, FieldSpec, FieldExtractionResult, ExtractionCandidate


class DateExtractor(BaseExtractor):
    """
    Specialized extractor for date fields.
    Handles various date formats and normalizes them.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "date"
        
        # Common date patterns
        self.date_patterns = [
            # MM/DD/YYYY or MM-DD-YYYY
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', 'MDY'),
            # YYYY/MM/DD or YYYY-MM-DD
            (r'\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b', 'YMD'),
            # MM/DD/YY or MM-DD-YY
            (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2})\b', 'MDY_SHORT'),
            # Month DD, YYYY (e.g., January 15, 2025)
            (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})\b', 'MONTH_NAME'),
            # DD Month YYYY (e.g., 15 January 2025)
            (r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', 'DAY_MONTH_NAME'),
            # Short month names (e.g., Jan 15, 2025)
            (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2}),?\s+(\d{4})\b', 'SHORT_MONTH'),
        ]
        
        # Month name to number mapping
        self.month_map = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def supports_field(self, field_spec: FieldSpec) -> bool:
        """Check if this extractor can handle the given field."""
        return field_spec.type == 'date'
    
    def extract(self, 
                pdf_path: Path,
                form_spec: FormSpec,
                field_ids: Optional[List[str]] = None) -> ExtractionResult:
        """
        Extract date fields from the PDF.
        
        Args:
            pdf_path: Path to PDF file
            form_spec: Form specification
            field_ids: Optional list of field IDs to extract
            
        Returns:
            Extraction results
        """
        print(f"\n📅 Date Extraction: {pdf_path.name}")
        print("-" * 50)
        
        # Create result
        result = ExtractionResult(
            doc_id=str(pdf_path.stem),
            doc_path=str(pdf_path),
            form_id=form_spec.form_id
        )
        
        # Get fields to extract
        fields_to_extract = form_spec.fields
        if field_ids:
            fields_to_extract = [f for f in form_spec.fields if f.id in field_ids]
        date_fields = [f for f in fields_to_extract if f.type == 'date']
        
        if not date_fields:
            print("  ⚠️  No date fields to extract")
            return result
        
        print(f"  📋 Extracting {len(date_fields)} date fields")
        
        # Extract text from PDF
        try:
            with PDF.open(pdf_path) as pdf:
                # Try both AcroForm and text extraction
                dates_found = {}
                
                # First try AcroForm fields
                dates_from_forms = self._extract_from_acroform(pdf_path, date_fields)
                dates_found.update(dates_from_forms)
                
                # Then search text for dates near anchors
                dates_from_text = self._extract_from_text(pdf, date_fields)
                
                # Merge results (prefer form fields over text)
                for field_id, value in dates_from_text.items():
                    if field_id not in dates_found:
                        dates_found[field_id] = value
                
                # Create field results
                for field in date_fields:
                    if field.id in dates_found:
                        value = dates_found[field.id]
                        normalized = self._normalize_date(value, field)
                        
                        field_result = FieldExtractionResult(
                            field_id=field.id,
                            field_name=field.field_name
                        )
                        
                        candidate = ExtractionCandidate(
                            value=normalized,
                            confidence=0.9,
                            source={'method': 'date_extraction'}
                        )
                        field_result.add_candidate(candidate)
                        field_result.select_best_candidate()
                        
                        result.add_field_result(field_result)
                        print(f"  📝 {field.field_name}: '{normalized}'")
                    
                    self.stats['fields_attempted'] += 1
                    if field.id in dates_found:
                        self.stats['fields_extracted'] += 1
        
        except Exception as e:
            result.errors.append(f"Date extraction failed: {str(e)}")
            print(f"  ❌ Error: {e}")
        
        print(f"\n  ✅ Extracted {len([f for f in result.fields.values() if f.selected_value])}/{len(date_fields)} date fields")
        
        return result
    
    def _extract_from_acroform(self, pdf_path: Path, fields: List[FieldSpec]) -> Dict[str, str]:
        """Extract dates from AcroForm fields."""
        dates = {}
        
        try:
            reader = PdfReader(pdf_path)
            form_fields = reader.get_form_text_fields() or {}
            
            for field in fields:
                if field.extraction and field.extraction.acroform:
                    for form_name in field.extraction.acroform:
                        if form_name in form_fields:
                            value = form_fields[form_name]
                            if value and self._is_date(value):
                                dates[field.id] = value
                                break
        except:
            pass
        
        return dates
    
    def _extract_from_text(self, pdf: PDF, fields: List[FieldSpec]) -> Dict[str, str]:
        """Extract dates from text near anchors."""
        dates = {}
        
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            
            # Find all dates on the page
            page_dates = self._find_dates_in_text(text)
            
            # Match dates to fields based on anchors
            for field in fields:
                if field.extraction and field.extraction.anchors:
                    for anchor_spec in field.extraction.anchors:
                        anchor_text = anchor_spec.get('text', '')
                        
                        # Find anchor position
                        if anchor_text in text:
                            anchor_pos = text.index(anchor_text)
                            
                            # Find nearest date after anchor
                            best_date = None
                            best_distance = float('inf')
                            
                            for date_text, date_pos in page_dates:
                                if date_pos > anchor_pos:
                                    distance = date_pos - anchor_pos
                                    if distance < best_distance and distance < 200:  # Within 200 chars
                                        best_date = date_text
                                        best_distance = distance
                            
                            if best_date:
                                dates[field.id] = best_date
                                break
        
        return dates
    
    def _find_dates_in_text(self, text: str) -> List[tuple]:
        """Find all dates in text with their positions."""
        dates = []
        
        for pattern, format_type in self.date_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                date_text = match.group(0)
                position = match.start()
                dates.append((date_text, position))
        
        return dates
    
    def _is_date(self, value: str) -> bool:
        """Check if a string looks like a date."""
        if not value:
            return False
        
        # Check against patterns
        for pattern, _ in self.date_patterns:
            if re.match(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _normalize_date(self, date_str: str, field: FieldSpec) -> str:
        """
        Normalize date to specified format.
        
        Args:
            date_str: Raw date string
            field: Field specification
            
        Returns:
            Normalized date string
        """
        if not date_str:
            return date_str
        
        # Determine target format
        target_format = "MM/DD/YYYY"  # Default
        if field.normalize and field.normalize.format:
            target_format = field.normalize.format
        
        # Try to parse the date
        parsed_date = self._parse_date(date_str)
        
        if parsed_date:
            # Format according to target
            if target_format == "MM/DD/YYYY":
                return f"{parsed_date.month:02d}/{parsed_date.day:02d}/{parsed_date.year}"
            elif target_format == "YYYY-MM-DD":
                return f"{parsed_date.year}-{parsed_date.month:02d}-{parsed_date.day:02d}"
            elif target_format == "DD/MM/YYYY":
                return f"{parsed_date.day:02d}/{parsed_date.month:02d}/{parsed_date.year}"
            else:
                # Try to format with strftime
                try:
                    return parsed_date.strftime(target_format.replace('YYYY', '%Y').replace('MM', '%m').replace('DD', '%d'))
                except:
                    return date_str
        
        return date_str
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse a date string into a date object."""
        if not date_str:
            return None
        
        # Try each pattern
        for pattern, format_type in self.date_patterns:
            match = re.match(pattern, date_str, re.IGNORECASE)
            if match:
                try:
                    if format_type == 'MDY':
                        month, day, year = match.groups()
                        return date(int(year), int(month), int(day))
                    
                    elif format_type == 'YMD':
                        year, month, day = match.groups()
                        return date(int(year), int(month), int(day))
                    
                    elif format_type == 'MDY_SHORT':
                        month, day, year = match.groups()
                        # Convert 2-digit year to 4-digit
                        year = int(year)
                        if year < 100:
                            year = 2000 + year if year < 50 else 1900 + year
                        return date(year, int(month), int(day))
                    
                    elif format_type in ['MONTH_NAME', 'SHORT_MONTH']:
                        month_name, day, year = match.groups()
                        month_num = self.month_map.get(month_name.lower())
                        if month_num:
                            return date(int(year), month_num, int(day))
                    
                    elif format_type == 'DAY_MONTH_NAME':
                        day, month_name, year = match.groups()
                        month_num = self.month_map.get(month_name.lower())
                        if month_num:
                            return date(int(year), month_num, int(day))
                except:
                    continue
        
        # Try parsing with dateutil if available
        try:
            from dateutil import parser
            parsed = parser.parse(date_str, fuzzy=True)
            return parsed.date()
        except:
            pass
        
        return None