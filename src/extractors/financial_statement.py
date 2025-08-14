"""
Financial statement document extractor.

This module implements extraction logic specifically for financial statements,
including balance sheets, income statements, and cash flow statements.
"""

import re
import time
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
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
from ..utils.patterns import CommonPatterns


class FinancialStatementExtractor(BaseExtractor):
    """
    Extractor for financial statement documents.
    
    Supports various financial statement formats and can extract:
    - Balance sheet items (assets, liabilities, equity)
    - Income statement items (revenue, expenses, net income)
    - Cash flow statement items
    - Financial ratios
    - Company information
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the financial statement extractor."""
        super().__init__(config)
        self.patterns = CommonPatterns()
        
        # Financial statement types
        self.statement_types = {
            'balance_sheet': ['balance sheet', 'statement of financial position', 'assets and liabilities'],
            'income_statement': ['income statement', 'profit and loss', 'p&l', 'statement of operations'],
            'cash_flow': ['cash flow', 'statement of cash flows', 'cash flows statement'],
            'retained_earnings': ['retained earnings', 'statement of retained earnings']
        }
    
    def _setup_extractor(self) -> None:
        """Setup financial statement specific configuration."""
        # Configure OCR settings
        self.tesseract_config = self.config.get('tesseract_config', '--psm 6')
        
        # Configure extraction thresholds
        self.min_field_confidence = self.config.get('min_field_confidence', 0.7)
    
    @property
    def supported_document_types(self) -> List[DocumentType]:
        """Return supported document types."""
        return [DocumentType.UNKNOWN]  # Financial statements are often classified as unknown initially
    
    @property
    def required_fields(self) -> List[str]:
        """Return required fields for financial statements."""
        return [
            'company_name',
            'statement_date',
            'total_revenue',
            'net_income'
        ]
    
    def can_process(self, file_path: Path, document_type: Optional[DocumentType] = None) -> bool:
        """
        Check if this extractor can process the given document.
        
        Args:
            file_path: Path to the document file
            document_type: Optional hint about document type
            
        Returns:
            True if this is likely a financial statement
        """
        # Check file extension
        supported_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.xlsx', '.xls']
        if file_path.suffix.lower() not in supported_extensions:
            return False
        
        try:
            # Quick text extraction to check for financial statement indicators
            text = self._extract_raw_text(file_path)
            text_lower = text.lower()
            
            # Look for financial statement keywords
            financial_keywords = [
                'balance sheet', 'income statement', 'cash flow', 'profit and loss',
                'assets', 'liabilities', 'equity', 'revenue', 'expenses',
                'net income', 'total assets', 'shareholders equity'
            ]
            
            keyword_matches = sum(1 for keyword in financial_keywords if keyword in text_lower)
            
            # Check for specific statement type indicators
            statement_type_matches = 0
            for stmt_type, keywords in self.statement_types.items():
                if any(keyword in text_lower for keyword in keywords):
                    statement_type_matches += 1
            
            # If we find multiple financial keywords or statement type matches
            return keyword_matches >= 4 or statement_type_matches >= 1
            
        except Exception as e:
            self.logger.error(f"Error checking if can process {file_path}: {e}")
            return False
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract data from a financial statement document.
        
        Args:
            file_path: Path to the financial statement file
            **kwargs: Additional extraction parameters
            
        Returns:
            ExtractionResult containing extracted financial statement data
        """
        start_time = time.time()
        extracted_fields = []
        errors = []
        
        try:
            self.logger.info(f"Starting financial statement extraction for {file_path}")
            
            # Extract raw text
            raw_text = self._extract_raw_text(file_path)
            if not raw_text.strip():
                errors.append("No text could be extracted from document")
                return ExtractionResult(
                    document_type=DocumentType.UNKNOWN,
                    status=ExtractionStatus.FAILED,
                    extracted_fields=[],
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    errors=errors,
                    metadata={},
                    raw_text=raw_text
                )
            
            # Detect statement type
            statement_type = self._detect_statement_type(raw_text)
            
            # Extract fields based on file type and statement type
            if file_path.suffix.lower() in ['.xlsx', '.xls']:
                extracted_fields.extend(self._extract_from_excel(file_path, statement_type))
            else:
                extracted_fields.extend(self._extract_from_text(raw_text, statement_type))
            
            # Extract common fields for all financial statements
            extracted_fields.extend(self._extract_company_info(raw_text))
            extracted_fields.extend(self._extract_statement_date(raw_text))
            
            # Calculate overall confidence
            confidence_score = self._calculate_confidence(extracted_fields)
            
            # Determine status
            status = ExtractionStatus.SUCCESS
            if confidence_score < 0.5:
                status = ExtractionStatus.FAILED
            elif confidence_score < 0.8 or errors:
                status = ExtractionStatus.PARTIAL
            
            result = ExtractionResult(
                document_type=DocumentType.UNKNOWN,
                status=status,
                extracted_fields=extracted_fields,
                confidence_score=confidence_score,
                processing_time=time.time() - start_time,
                errors=errors,
                metadata={
                    'total_fields_extracted': len(extracted_fields),
                    'file_size': file_path.stat().st_size,
                    'extraction_method': 'financial_statement_extractor',
                    'detected_statement_type': statement_type
                },
                raw_text=raw_text
            )
            
            return self.validate_extraction(result)
            
        except Exception as e:
            self.logger.error(f"Error extracting from financial statement {file_path}: {e}")
            return ExtractionResult(
                document_type=DocumentType.UNKNOWN,
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
            elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                return self._extract_text_from_excel(file_path)
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
    
    def _extract_text_from_excel(self, file_path: Path) -> str:
        """Extract text from Excel file."""
        try:
            # Read all sheets from the Excel file
            excel_data = pd.read_excel(file_path, sheet_name=None)
            text = ""
            
            for sheet_name, df in excel_data.items():
                # Add sheet name as header
                text += f"\n=== {sheet_name} ===\n"
                
                # Convert DataFrame to text
                if not df.empty:
                    # Add column headers
                    text += " | ".join(str(col) for col in df.columns) + "\n"
                    
                    # Add data rows
                    for _, row in df.iterrows():
                        row_text = " | ".join(str(value) if pd.notna(value) else "" for value in row.values)
                        text += row_text + "\n"
                
                text += "\n"
            
            return text
            
        except Exception as e:
            self.logger.error(f"Error extracting text from Excel: {e}")
            return ""
    
    def _extract_text_from_image(self, file_path: Path) -> str:
        """Extract text from image using OCR."""
        try:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image, config=self.tesseract_config)
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {e}")
            return ""
    
    def _detect_statement_type(self, text: str) -> Optional[str]:
        """Detect the type of financial statement."""
        text_lower = text.lower()
        
        # Check for statement type keywords
        for stmt_type, keywords in self.statement_types.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return stmt_type
        
        return None
    
    def _extract_from_excel(self, file_path: Path, statement_type: Optional[str]) -> List[ExtractedField]:
        """Extract data from Excel financial statement."""
        fields = []
        
        try:
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            for sheet_name, df in excel_data.items():
                if df.empty:
                    continue
                
                # Extract based on statement type or sheet content
                if statement_type == 'balance_sheet' or 'balance' in sheet_name.lower():
                    fields.extend(self._extract_excel_balance_sheet(df))
                elif statement_type == 'income_statement' or any(word in sheet_name.lower() for word in ['income', 'profit', 'p&l']):
                    fields.extend(self._extract_excel_income_statement(df))
                elif statement_type == 'cash_flow' or 'cash' in sheet_name.lower():
                    fields.extend(self._extract_excel_cash_flow(df))
                else:
                    # Generic extraction
                    fields.extend(self._extract_excel_generic(df))
        
        except Exception as e:
            self.logger.error(f"Error extracting from Excel: {e}")
        
        return fields
    
    def _extract_excel_balance_sheet(self, df: pd.DataFrame) -> List[ExtractedField]:
        """Extract balance sheet data from Excel DataFrame."""
        fields = []
        
        try:
            # Look for balance sheet line items
            balance_sheet_items = {
                'total assets': 'total_assets',
                'current assets': 'current_assets',
                'total liabilities': 'total_liabilities',
                'current liabilities': 'current_liabilities',
                'shareholders equity': 'shareholders_equity',
                'total equity': 'total_equity',
                'retained earnings': 'retained_earnings'
            }
            
            for _, row in df.iterrows():
                if len(row) >= 2:
                    desc = str(row.iloc[0]).strip().lower()
                    value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    
                    if not value or value == 'nan':
                        continue
                    
                    for item_name, field_name in balance_sheet_items.items():
                        if item_name in desc:
                            try:
                                cleaned_value = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                                numeric_value = float(cleaned_value)
                                fields.append(ExtractedField(
                                    name=field_name,
                                    value=numeric_value,
                                    confidence=0.9,
                                    raw_text=f"{row.iloc[0]}: {value}"
                                ))
                            except ValueError:
                                pass
                            break
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel balance sheet: {e}")
        
        return fields
    
    def _extract_excel_income_statement(self, df: pd.DataFrame) -> List[ExtractedField]:
        """Extract income statement data from Excel DataFrame."""
        fields = []
        
        try:
            income_statement_items = {
                'revenue': 'total_revenue',
                'gross revenue': 'total_revenue',
                'total revenue': 'total_revenue',
                'sales': 'total_revenue',
                'gross profit': 'gross_profit',
                'operating income': 'operating_income',
                'net income': 'net_income',
                'total expenses': 'total_expenses',
                'operating expenses': 'operating_expenses',
                'cost of goods sold': 'cost_of_goods_sold',
                'cogs': 'cost_of_goods_sold'
            }
            
            for _, row in df.iterrows():
                if len(row) >= 2:
                    desc = str(row.iloc[0]).strip().lower()
                    value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    
                    if not value or value == 'nan':
                        continue
                    
                    for item_name, field_name in income_statement_items.items():
                        if item_name in desc:
                            try:
                                cleaned_value = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                                numeric_value = float(cleaned_value)
                                fields.append(ExtractedField(
                                    name=field_name,
                                    value=numeric_value,
                                    confidence=0.9,
                                    raw_text=f"{row.iloc[0]}: {value}"
                                ))
                            except ValueError:
                                pass
                            break
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel income statement: {e}")
        
        return fields
    
    def _extract_excel_cash_flow(self, df: pd.DataFrame) -> List[ExtractedField]:
        """Extract cash flow statement data from Excel DataFrame."""
        fields = []
        
        try:
            cash_flow_items = {
                'operating activities': 'cash_from_operations',
                'investing activities': 'cash_from_investing',
                'financing activities': 'cash_from_financing',
                'net change in cash': 'net_change_in_cash',
                'beginning cash': 'beginning_cash',
                'ending cash': 'ending_cash'
            }
            
            for _, row in df.iterrows():
                if len(row) >= 2:
                    desc = str(row.iloc[0]).strip().lower()
                    value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    
                    if not value or value == 'nan':
                        continue
                    
                    for item_name, field_name in cash_flow_items.items():
                        if item_name in desc:
                            try:
                                cleaned_value = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                                numeric_value = float(cleaned_value)
                                fields.append(ExtractedField(
                                    name=field_name,
                                    value=numeric_value,
                                    confidence=0.9,
                                    raw_text=f"{row.iloc[0]}: {value}"
                                ))
                            except ValueError:
                                pass
                            break
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel cash flow: {e}")
        
        return fields
    
    def _extract_excel_generic(self, df: pd.DataFrame) -> List[ExtractedField]:
        """Extract generic financial data from Excel DataFrame."""
        fields = []
        
        try:
            # Look for any financial amounts
            financial_patterns = {
                r'(?:revenue|sales|income)': 'total_revenue',
                r'(?:profit|earnings)': 'net_income',
                r'(?:assets)': 'total_assets',
                r'(?:liabilities)': 'total_liabilities'
            }
            
            for _, row in df.iterrows():
                if len(row) >= 2:
                    desc = str(row.iloc[0]).strip().lower()
                    value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    
                    if not value or value == 'nan':
                        continue
                    
                    for pattern, field_name in financial_patterns.items():
                        if re.search(pattern, desc):
                            try:
                                cleaned_value = value.replace('$', '').replace(',', '').replace('(', '-').replace(')', '')
                                numeric_value = float(cleaned_value)
                                fields.append(ExtractedField(
                                    name=field_name,
                                    value=numeric_value,
                                    confidence=0.7,
                                    raw_text=f"{row.iloc[0]}: {value}"
                                ))
                            except ValueError:
                                pass
                            break
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel generic financial data: {e}")
        
        return fields
    
    def _extract_from_text(self, text: str, statement_type: Optional[str]) -> List[ExtractedField]:
        """Extract data from text-based financial statement."""
        fields = []
        
        # Common financial statement patterns
        financial_patterns = [
            (r'(?:total\s+)?(?:revenue|sales)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'total_revenue'),
            (r'(?:net\s+income|net\s+profit|earnings)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'net_income'),
            (r'(?:total\s+assets)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'total_assets'),
            (r'(?:total\s+liabilities)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'total_liabilities'),
            (r'(?:shareholders?\s+equity|total\s+equity)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'shareholders_equity'),
            (r'(?:gross\s+profit)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'gross_profit'),
            (r'(?:operating\s+income)\s*:?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', 'operating_income')
        ]
        
        for pattern_str, field_name in financial_patterns:
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
                except ValueError:
                    continue
        
        return fields
    
    def _extract_company_info(self, text: str) -> List[ExtractedField]:
        """Extract company information from financial statement."""
        fields = []
        
        # Look for company name at the beginning of the document
        lines = text.split('\n')[:10]  # Check first 10 lines
        for line in lines:
            line = line.strip()
            if len(line) > 10 and not any(char.isdigit() for char in line):
                # Skip lines with common headers
                skip_patterns = [
                    'balance sheet', 'income statement', 'cash flow',
                    'financial statement', 'for the year', 'as of'
                ]
                if not any(pattern in line.lower() for pattern in skip_patterns):
                    # Might be company name
                    fields.append(ExtractedField(
                        name='company_name',
                        value=line,
                        confidence=0.7,
                        raw_text=line
                    ))
                    break
        
        return fields
    
    def _extract_statement_date(self, text: str) -> List[ExtractedField]:
        """Extract statement date from financial statement."""
        fields = []
        
        # Look for date patterns
        date_patterns = [
            r'(?:as of|for the year ending?|statement date)\s*:?\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})',
            r'(?:december|march|june|september)\s+\d{1,2},?\s+(\d{4})',
            r'(\d{4})\s*(?:financial|annual)'
        ]
        
        for pattern_str in date_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text)
            if match:
                date_str = match.group(1)
                fields.append(ExtractedField(
                    name='statement_date',
                    value=date_str,
                    confidence=0.8,
                    raw_text=match.group(0)
                ))
                break
        
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