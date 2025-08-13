"""
Tax return document extractor.

This module implements extraction logic specifically for tax return documents,
including business tax returns (Form 1120) and individual tax returns (Form 1040).
"""

import re
import time
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

from .base import (
    BaseExtractor,
    DocumentType,
    ExtractionResult,
    ExtractionStatus,
    ExtractedField
)
from ..utils.patterns import TaxReturnPatterns


class TaxReturnExtractor(BaseExtractor):
    """
    Extractor for tax return documents.
    
    Supports various tax return formats and can extract:
    - Taxpayer information
    - Tax year
    - Income information
    - Deductions
    - Tax calculations
    - Business information (for business returns)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the tax return extractor."""
        super().__init__(config)
        self.patterns = TaxReturnPatterns()
    
    def _setup_extractor(self) -> None:
        """Setup tax return specific configuration."""
        # Configure OCR settings for tax forms
        self.tesseract_config = self.config.get('tesseract_config', '--psm 6')
        
        # Configure extraction thresholds
        self.min_field_confidence = self.config.get('min_field_confidence', 0.7)
        
        # Tax form detection keywords
        self.form_keywords = {
            '1040': ['form 1040', '1040ez', '1040a', 'individual income tax return'],
            '1120': ['form 1120', 'corporation income tax return', 'u.s. corporation'],
            '1120s': ['form 1120s', 's corporation income tax return'],
            '1065': ['form 1065', 'partnership return', 'partnership income']
        }
    
    @property
    def supported_document_types(self) -> List[DocumentType]:
        """Return supported document types."""
        return [DocumentType.TAX_RETURN]
    
    @property
    def required_fields(self) -> List[str]:
        """Return required fields for tax returns."""
        return [
            'tax_year',
            'taxpayer_name',
            'total_income',
            'tax_owed_or_refund'
        ]
    
    def can_process(self, file_path: Path, document_type: Optional[DocumentType] = None) -> bool:
        """
        Check if this extractor can process the given document.
        
        Args:
            file_path: Path to the document file
            document_type: Optional hint about document type
            
        Returns:
            True if this is likely a tax return
        """
        if document_type == DocumentType.TAX_RETURN:
            return True
        
        # Check file extension
        if file_path.suffix.lower() not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']:
            return False
        
        try:
            # Quick text extraction to check for tax return indicators
            text = self._extract_raw_text(file_path)
            text_lower = text.lower()
            
            # Look for tax return keywords
            tax_keywords = [
                'tax return', 'form 1040', 'form 1120', 'irs',
                'internal revenue service', 'adjusted gross income',
                'taxable income', 'tax year', 'ein', 'ssn'
            ]
            
            keyword_matches = sum(1 for keyword in tax_keywords if keyword in text_lower)
            
            # Check for specific form numbers
            form_matches = 0
            for form_type, keywords in self.form_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    form_matches += 1
            
            # If we find multiple tax-related keywords or form matches, likely a tax return
            return keyword_matches >= 3 or form_matches >= 1
            
        except Exception as e:
            self.logger.error(f"Error checking if can process {file_path}: {e}")
            return False
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract data from a tax return document.
        
        Args:
            file_path: Path to the tax return file
            **kwargs: Additional extraction parameters
            
        Returns:
            ExtractionResult containing extracted tax return data
        """
        start_time = time.time()
        extracted_fields = []
        errors = []
        
        try:
            self.logger.info(f"Starting tax return extraction for {file_path}")
            
            # Extract raw text
            raw_text = self._extract_raw_text(file_path)
            if not raw_text.strip():
                errors.append("No text could be extracted from document")
                return ExtractionResult(
                    document_type=DocumentType.TAX_RETURN,
                    status=ExtractionStatus.FAILED,
                    extracted_fields=[],
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    errors=errors,
                    metadata={},
                    raw_text=raw_text
                )
            
            # Detect tax form type
            form_type = self._detect_form_type(raw_text)
            
            # Extract fields based on form type
            if form_type in ['1040', '1040ez', '1040a']:
                extracted_fields.extend(self._extract_individual_tax_fields(raw_text))
            elif form_type in ['1120', '1120s']:
                extracted_fields.extend(self._extract_business_tax_fields(raw_text))
            elif form_type == '1065':
                extracted_fields.extend(self._extract_partnership_tax_fields(raw_text))
            else:
                # Generic extraction
                extracted_fields.extend(self._extract_generic_tax_fields(raw_text))
            
            # Extract common fields for all tax returns
            extracted_fields.extend(self._extract_tax_year(raw_text))
            extracted_fields.extend(self._extract_taxpayer_info(raw_text))
            
            # Calculate overall confidence
            confidence_score = self._calculate_confidence(extracted_fields)
            
            # Determine status
            status = ExtractionStatus.SUCCESS
            if confidence_score < 0.5:
                status = ExtractionStatus.FAILED
            elif confidence_score < 0.8 or errors:
                status = ExtractionStatus.PARTIAL
            
            result = ExtractionResult(
                document_type=DocumentType.TAX_RETURN,
                status=status,
                extracted_fields=extracted_fields,
                confidence_score=confidence_score,
                processing_time=time.time() - start_time,
                errors=errors,
                metadata={
                    'total_fields_extracted': len(extracted_fields),
                    'file_size': file_path.stat().st_size,
                    'extraction_method': 'tax_return_extractor',
                    'detected_form_type': form_type
                },
                raw_text=raw_text
            )
            
            return self.validate_extraction(result)
            
        except Exception as e:
            self.logger.error(f"Error extracting from tax return {file_path}: {e}")
            return ExtractionResult(
                document_type=DocumentType.TAX_RETURN,
                status=ExtractionStatus.FAILED,
                extracted_fields=extracted_fields,
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                errors=[f"Extraction failed: {str(e)}"],
                metadata={}
            )
    
    def _extract_raw_text(self, file_path: Path) -> str:
        """Extract raw text from the document."""
        try:
            if file_path.suffix.lower() == '.pdf':
                return self._extract_text_from_pdf(file_path)
            else:
                return self._extract_text_from_image(file_path)
        except Exception as e:
            self.logger.error(f"Error extracting raw text: {e}")
            return ""
    
    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using pdfplumber."""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            # If PDF text extraction failed, try OCR
            if not text.strip():
                images = convert_from_path(file_path)
                for image in images:
                    text += pytesseract.image_to_string(image, config=self.tesseract_config)
                    
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF: {e}")
            
        return text
    
    def _extract_text_from_image(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image, config=self.tesseract_config)
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {e}")
            return ""
    
    def _detect_form_type(self, text: str) -> Optional[str]:
        """Detect the type of tax form."""
        text_lower = text.lower()
        
        for form_type, keywords in self.form_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return form_type
        
        return None
    
    def _extract_tax_year(self, text: str) -> List[ExtractedField]:
        """Extract tax year from the document."""
        fields = []
        
        # Try pattern matching
        year_match = self.patterns.TAX_YEAR.search(text)
        if year_match:
            year_str = year_match.group(1)
            try:
                year = int(year_str)
                if 2000 <= year <= datetime.now().year:  # Reasonable year range
                    fields.append(ExtractedField(
                        name='tax_year',
                        value=year,
                        confidence=0.9,
                        raw_text=year_match.group(0)
                    ))
            except ValueError:
                pass
        
        # If pattern didn't work, try to find year in common contexts
        if not fields:
            year_patterns = [
                r'(?:tax year|for the year|year ending)\s*:?\s*(\d{4})',
                r'(\d{4})\s*(?:tax return|income tax)',
                r'form\s+\d+\s+\((\d{4})\)'
            ]
            
            for pattern in year_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    try:
                        year = int(match.group(1))
                        if 2000 <= year <= datetime.now().year:
                            fields.append(ExtractedField(
                                name='tax_year',
                                value=year,
                                confidence=0.8,
                                raw_text=match.group(0)
                            ))
                            break
                    except (ValueError, IndexError):
                        continue
                if fields:
                    break
        
        return fields
    
    def _extract_taxpayer_info(self, text: str) -> List[ExtractedField]:
        """Extract taxpayer information."""
        fields = []
        
        # Extract taxpayer name
        name_match = self.patterns.TAXPAYER_NAME.search(text)
        if name_match:
            name = name_match.group(1).strip()
            fields.append(ExtractedField(
                name='taxpayer_name',
                value=name,
                confidence=0.8,
                raw_text=name_match.group(0)
            ))
        
        # Extract last name separately if available
        last_name_match = self.patterns.TAXPAYER_LAST_NAME.search(text)
        if last_name_match:
            last_name = last_name_match.group(1).strip()
            # If we have first name, combine them
            if fields and fields[-1].name == 'taxpayer_name':
                full_name = f"{fields[-1].value} {last_name}"
                fields[-1] = ExtractedField(
                    name='taxpayer_name',
                    value=full_name,
                    confidence=0.85,
                    raw_text=f"{fields[-1].raw_text}, {last_name_match.group(0)}"
                )
            else:
                fields.append(ExtractedField(
                    name='taxpayer_last_name',
                    value=last_name,
                    confidence=0.8,
                    raw_text=last_name_match.group(0)
                ))
        
        # Extract spouse name if available
        spouse_match = self.patterns.SPOUSE_NAME.search(text)
        if spouse_match:
            spouse_name = spouse_match.group(1).strip()
            fields.append(ExtractedField(
                name='spouse_name',
                value=spouse_name,
                confidence=0.8,
                raw_text=spouse_match.group(0)
            ))
        
        return fields
    
    def _extract_individual_tax_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields specific to individual tax returns (Form 1040)."""
        fields = []
        
        # Extract wages
        wages_match = self.patterns.WAGES.search(text)
        if wages_match:
            try:
                wages_str = wages_match.group(1)
                wages = self._parse_currency(wages_str)
                fields.append(ExtractedField(
                    name='wages',
                    value=float(wages),
                    confidence=0.9,
                    raw_text=wages_match.group(0)
                ))
            except ValueError:
                pass
        
        # Extract AGI
        agi_match = self.patterns.AGI.search(text)
        if agi_match:
            try:
                agi_str = agi_match.group(1)
                agi = self._parse_currency(agi_str)
                fields.append(ExtractedField(
                    name='adjusted_gross_income',
                    value=float(agi),
                    confidence=0.9,
                    raw_text=agi_match.group(0)
                ))
                # Also use as total income
                fields.append(ExtractedField(
                    name='total_income',
                    value=float(agi),
                    confidence=0.8,
                    raw_text=agi_match.group(0)
                ))
            except ValueError:
                pass
        
        # Extract tax owed or refund
        total_tax_match = self.patterns.TOTAL_TAX.search(text)
        if total_tax_match:
            try:
                tax_str = total_tax_match.group(1)
                tax = self._parse_currency(tax_str)
                fields.append(ExtractedField(
                    name='total_tax',
                    value=float(tax),
                    confidence=0.9,
                    raw_text=total_tax_match.group(0)
                ))
            except ValueError:
                pass
        
        # Check for refund or amount owed
        refund_match = self.patterns.REFUND_AMOUNT.search(text)
        if refund_match:
            try:
                refund_str = refund_match.group(1)
                refund = self._parse_currency(refund_str)
                fields.append(ExtractedField(
                    name='refund_amount',
                    value=float(refund),
                    confidence=0.9,
                    raw_text=refund_match.group(0)
                ))
                fields.append(ExtractedField(
                    name='tax_owed_or_refund',
                    value=f"Refund: ${refund}",
                    confidence=0.85,
                    raw_text=refund_match.group(0)
                ))
            except ValueError:
                pass
        
        owed_match = self.patterns.AMOUNT_OWED.search(text)
        if owed_match and not refund_match:  # Don't double-count
            try:
                owed_str = owed_match.group(1)
                owed = self._parse_currency(owed_str)
                fields.append(ExtractedField(
                    name='amount_owed',
                    value=float(owed),
                    confidence=0.9,
                    raw_text=owed_match.group(0)
                ))
                fields.append(ExtractedField(
                    name='tax_owed_or_refund',
                    value=f"Owed: ${owed}",
                    confidence=0.85,
                    raw_text=owed_match.group(0)
                ))
            except ValueError:
                pass
        
        return fields
    
    def _extract_business_tax_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields specific to business tax returns (Form 1120/1120S)."""
        fields = []
        
        # Look for business-specific patterns
        business_patterns = [
            (r'(?:gross\s+receipts|total\s+income|total\s+revenue)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'gross_receipts'),
            (r'(?:total\s+deductions|total\s+expenses)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'total_deductions'),
            (r'(?:taxable\s+income|net\s+income)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'taxable_income'),
            (r'(?:income\s+tax|tax\s+liability)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'income_tax')
        ]
        
        for pattern_str, field_name in business_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)
            if match:
                try:
                    amount_str = match.group(1)
                    amount = self._parse_currency(amount_str)
                    fields.append(ExtractedField(
                        name=field_name,
                        value=float(amount),
                        confidence=0.8,
                        raw_text=match.group(0)
                    ))
                    
                    # Map to standard field names
                    if field_name == 'gross_receipts':
                        fields.append(ExtractedField(
                            name='total_income',
                            value=float(amount),
                            confidence=0.75,
                            raw_text=match.group(0)
                        ))
                    elif field_name == 'income_tax':
                        fields.append(ExtractedField(
                            name='tax_owed_or_refund',
                            value=f"Tax: ${amount}",
                            confidence=0.75,
                            raw_text=match.group(0)
                        ))
                        
                except ValueError:
                    continue
        
        return fields
    
    def _extract_partnership_tax_fields(self, text: str) -> List[ExtractedField]:
        """Extract fields specific to partnership tax returns (Form 1065)."""
        # Similar to business tax fields but for partnerships
        return self._extract_business_tax_fields(text)
    
    def _extract_generic_tax_fields(self, text: str) -> List[ExtractedField]:
        """Extract generic tax fields when form type is unknown."""
        fields = []
        
        # Look for common tax amounts
        amount_patterns = [
            (r'(?:total\s+)?income\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'total_income'),
            (r'(?:tax\s+(?:due|owed|liability))\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'tax_owed'),
            (r'refund\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'refund_amount')
        ]
        
        for pattern_str, field_name in amount_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)
            if match:
                try:
                    amount_str = match.group(1)
                    amount = self._parse_currency(amount_str)
                    fields.append(ExtractedField(
                        name=field_name,
                        value=float(amount),
                        confidence=0.7,
                        raw_text=match.group(0)
                    ))
                    
                    # Create summary field
                    if field_name in ['tax_owed', 'refund_amount']:
                        prefix = "Owed" if field_name == 'tax_owed' else "Refund"
                        fields.append(ExtractedField(
                            name='tax_owed_or_refund',
                            value=f"{prefix}: ${amount}",
                            confidence=0.65,
                            raw_text=match.group(0)
                        ))
                        
                except ValueError:
                    continue
        
        return fields
    
    def _parse_currency(self, amount_str: str) -> Decimal:
        """Parse currency string into Decimal."""
        if not amount_str:
            raise ValueError("Empty amount string")
        
        # Remove currency symbols and formatting
        cleaned = re.sub(r'[^\d\.-]', '', amount_str)
        
        # Handle negative amounts in parentheses
        if '(' in amount_str and ')' in amount_str:
            cleaned = '-' + cleaned.replace('-', '')
        
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            raise ValueError(f"Cannot parse currency: {amount_str}")
    
    def _calculate_confidence(self, fields: List[ExtractedField]) -> float:
        """Calculate overall confidence score."""
        if not fields:
            return 0.0
        
        total_confidence = sum(field.confidence for field in fields)
        avg_confidence = total_confidence / len(fields)
        
        # Boost confidence if we found required fields
        required_found = sum(1 for field in fields if field.name in self.required_fields)
        required_ratio = required_found / len(self.required_fields)
        
        return min(1.0, avg_confidence * 0.7 + required_ratio * 0.3)