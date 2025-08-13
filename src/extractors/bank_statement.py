"""
Bank statement document extractor.

This module implements extraction logic specifically for bank statements,
including account information, transactions, and balances.
"""

import re
import time
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
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
from ..utils.patterns import BankStatementPatterns


class BankStatementExtractor(BaseExtractor):
    """
    Extractor for bank statement documents.
    
    Supports various bank statement formats and can extract:
    - Account holder information
    - Account numbers
    - Statement period
    - Beginning and ending balances
    - Transaction details
    - Bank information
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the bank statement extractor."""
        super().__init__(config)
        self.patterns = BankStatementPatterns()
        
    def _setup_extractor(self) -> None:
        """Setup bank statement specific configuration."""
        # Configure OCR settings
        self.tesseract_config = self.config.get('tesseract_config', '--psm 6')
        
        # Configure preprocessing
        self.preprocess_images = self.config.get('preprocess_images', True)
        self.image_enhancement = self.config.get('image_enhancement', True)
        
        # Configure extraction thresholds
        self.min_transaction_confidence = self.config.get('min_transaction_confidence', 0.7)
        self.balance_confidence_threshold = self.config.get('balance_confidence_threshold', 0.9)
    
    @property
    def supported_document_types(self) -> List[DocumentType]:
        """Return supported document types."""
        return [DocumentType.BANK_STATEMENT]
    
    @property
    def required_fields(self) -> List[str]:
        """Return required fields for bank statements."""
        return [
            'account_number',
            'account_holder_name',
            'statement_start_date',
            'statement_end_date',
            'beginning_balance',
            'ending_balance'
        ]
    
    def can_process(self, file_path: Path, document_type: Optional[DocumentType] = None) -> bool:
        """
        Check if this extractor can process the given document.
        
        Args:
            file_path: Path to the document file
            document_type: Optional hint about document type
            
        Returns:
            True if this is likely a bank statement
        """
        if document_type == DocumentType.BANK_STATEMENT:
            return True
            
        # Check file extension
        if file_path.suffix.lower() not in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.xlsx', '.xls']:
            return False
        
        try:
            # Quick text extraction to check for bank statement indicators
            text = self._extract_raw_text(file_path)
            
            # Look for bank statement keywords
            bank_keywords = [
                'statement', 'account summary', 'beginning balance', 
                'ending balance', 'transaction', 'deposit', 'withdrawal',
                'checking account', 'savings account', 'account number'
            ]
            
            text_lower = text.lower()
            keyword_matches = sum(1 for keyword in bank_keywords if keyword in text_lower)
            
            # If we find multiple bank-related keywords, likely a bank statement
            return keyword_matches >= 3
            
        except Exception as e:
            self.logger.error(f"Error checking if can process {file_path}: {e}")
            return False
    
    def extract(self, file_path: Path, **kwargs) -> ExtractionResult:
        """
        Extract data from a bank statement.
        
        Args:
            file_path: Path to the bank statement file
            **kwargs: Additional extraction parameters
            
        Returns:
            ExtractionResult containing extracted bank statement data
        """
        start_time = time.time()
        extracted_fields = []
        errors = []
        
        try:
            self.logger.info(f"Starting bank statement extraction for {file_path}")
            
            # Preprocess the document
            processed_path = self.preprocess_document(file_path)
            if not processed_path:
                return ExtractionResult(
                    document_type=DocumentType.BANK_STATEMENT,
                    status=ExtractionStatus.FAILED,
                    extracted_fields=[],
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    errors=["Failed to preprocess document"],
                    metadata={}
                )
            
            # Extract raw text
            raw_text = self._extract_raw_text(processed_path)
            if not raw_text.strip():
                errors.append("No text could be extracted from document")
                return ExtractionResult(
                    document_type=DocumentType.BANK_STATEMENT,
                    status=ExtractionStatus.FAILED,
                    extracted_fields=[],
                    confidence_score=0.0,
                    processing_time=time.time() - start_time,
                    errors=errors,
                    metadata={},
                    raw_text=raw_text
                )
            
            # Extract specific fields
            if processed_path.suffix.lower() in ['.xlsx', '.xls']:
                # Use structured Excel extraction
                extracted_fields.extend(self._extract_from_excel_structured(processed_path))
            else:
                # Use text-based extraction for PDFs and images
                extracted_fields.extend(self._extract_account_info(raw_text))
                extracted_fields.extend(self._extract_statement_period(raw_text))
                extracted_fields.extend(self._extract_balances(raw_text))
                extracted_fields.extend(self._extract_bank_info(raw_text))
            
            # Extract transactions (optional, can be resource intensive)
            if kwargs.get('extract_transactions', True):
                transactions = self._extract_transactions(raw_text)
                if transactions:
                    extracted_fields.append(ExtractedField(
                        name='transactions',
                        value=transactions,
                        confidence=0.8,
                        raw_text=None
                    ))
            
            # Calculate overall confidence
            confidence_score = self._calculate_confidence(extracted_fields)
            
            # Determine status
            status = ExtractionStatus.SUCCESS
            if confidence_score < 0.5:
                status = ExtractionStatus.FAILED
            elif confidence_score < 0.8 or errors:
                status = ExtractionStatus.PARTIAL
            
            result = ExtractionResult(
                document_type=DocumentType.BANK_STATEMENT,
                status=status,
                extracted_fields=extracted_fields,
                confidence_score=confidence_score,
                processing_time=time.time() - start_time,
                errors=errors,
                metadata={
                    'total_fields_extracted': len(extracted_fields),
                    'file_size': file_path.stat().st_size,
                    'extraction_method': 'bank_statement_extractor'
                },
                raw_text=raw_text
            )
            
            return self.validate_extraction(result)
            
        except Exception as e:
            self.logger.error(f"Error extracting from bank statement {file_path}: {e}")
            return ExtractionResult(
                document_type=DocumentType.BANK_STATEMENT,
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
                # Include column names
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
            
            # Preprocess image if enabled
            if self.preprocess_images:
                image = self._preprocess_image(image)
            
            return pytesseract.image_to_string(image, config=self.tesseract_config)
            
        except Exception as e:
            self.logger.error(f"Error extracting text from image: {e}")
            return ""
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        try:
            # Convert PIL image to OpenCV format
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Convert to grayscale
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply gaussian blur to remove noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply threshold to get binary image
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL Image
            return Image.fromarray(thresh)
            
        except Exception as e:
            self.logger.error(f"Error preprocessing image: {e}")
            return image
    
    def _extract_account_info(self, text: str) -> List[ExtractedField]:
        """Extract account information from text."""
        fields = []
        
        # Extract account number
        account_match = self.patterns.ACCOUNT_NUMBER.search(text)
        if account_match:
            account_number = account_match.group(1).strip()
            fields.append(ExtractedField(
                name='account_number',
                value=account_number,
                confidence=0.9,
                raw_text=account_match.group(0)
            ))
        
        # Extract account holder name
        name_match = self.patterns.ACCOUNT_HOLDER_NAME.search(text)
        if name_match:
            name = name_match.group(1).strip()
            fields.append(ExtractedField(
                name='account_holder_name',
                value=name,
                confidence=0.8,
                raw_text=name_match.group(0)
            ))
        
        return fields
    
    def _extract_statement_period(self, text: str) -> List[ExtractedField]:
        """Extract statement period dates."""
        fields = []
        
        # Extract statement period
        period_match = self.patterns.STATEMENT_PERIOD.search(text)
        if period_match:
            try:
                start_date_str = period_match.group(1)
                end_date_str = period_match.group(2)
                
                start_date = self._parse_date(start_date_str)
                end_date = self._parse_date(end_date_str)
                
                if start_date:
                    fields.append(ExtractedField(
                        name='statement_start_date',
                        value=start_date.isoformat(),
                        confidence=0.9,
                        raw_text=start_date_str
                    ))
                
                if end_date:
                    fields.append(ExtractedField(
                        name='statement_end_date',
                        value=end_date.isoformat(),
                        confidence=0.9,
                        raw_text=end_date_str
                    ))
                    
            except Exception as e:
                self.logger.error(f"Error parsing statement period: {e}")
        
        return fields
    
    def _extract_balances(self, text: str) -> List[ExtractedField]:
        """Extract beginning and ending balances."""
        fields = []
        
        # Extract beginning balance
        beginning_match = self.patterns.BEGINNING_BALANCE.search(text)
        if beginning_match:
            try:
                balance_str = beginning_match.group(1)
                balance = self._parse_currency(balance_str)
                fields.append(ExtractedField(
                    name='beginning_balance',
                    value=float(balance),
                    confidence=0.9,
                    raw_text=beginning_match.group(0)
                ))
            except Exception as e:
                self.logger.error(f"Error parsing beginning balance: {e}")
        
        # Extract ending balance
        ending_match = self.patterns.ENDING_BALANCE.search(text)
        if ending_match:
            try:
                balance_str = ending_match.group(1)
                balance = self._parse_currency(balance_str)
                fields.append(ExtractedField(
                    name='ending_balance',
                    value=float(balance),
                    confidence=0.9,
                    raw_text=ending_match.group(0)
                ))
            except Exception as e:
                self.logger.error(f"Error parsing ending balance: {e}")
        
        return fields
    
    def _extract_bank_info(self, text: str) -> List[ExtractedField]:
        """Extract bank information."""
        fields = []
        
        # Extract bank name
        bank_match = self.patterns.BANK_NAME.search(text)
        if bank_match:
            bank_name = bank_match.group(1).strip()
            fields.append(ExtractedField(
                name='bank_name',
                value=bank_name,
                confidence=0.8,
                raw_text=bank_match.group(0)
            ))
        
        return fields
    
    def _extract_transactions(self, text: str) -> List[Dict[str, Any]]:
        """Extract transaction details from text."""
        transactions = []
        
        # Find all transaction lines
        for match in self.patterns.TRANSACTION_LINE.finditer(text):
            try:
                transaction = {
                    'date': self._parse_date(match.group(1)),
                    'description': match.group(2).strip(),
                    'amount': float(self._parse_currency(match.group(3))),
                    'type': 'debit' if '-' in match.group(3) else 'credit'
                }
                
                if transaction['date']:
                    transaction['date'] = transaction['date'].isoformat()
                    transactions.append(transaction)
                    
            except Exception as e:
                self.logger.error(f"Error parsing transaction: {e}")
                continue
        
        return transactions
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string into date object."""
        if not date_str:
            return None
            
        # Clean the date string
        date_str = date_str.strip()
        
        # Common date formats
        date_formats = [
            '%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y',
            '%B %d, %Y', '%b %d, %Y', '%d %B %Y', '%d %b %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
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
    
    def _extract_from_excel_structured(self, file_path: Path) -> List[ExtractedField]:
        """Extract data from Excel file using structured approach."""
        fields = []
        
        try:
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None)
            
            for sheet_name, df in excel_data.items():
                if df.empty:
                    continue
                
                # Look for account info in header sheets
                if 'account_info' in sheet_name.lower() or 'header' in sheet_name.lower():
                    fields.extend(self._extract_excel_account_info(df))
                
                # Look for summary information
                elif 'summary' in sheet_name.lower():
                    fields.extend(self._extract_excel_summary(df))
                
                # Look for transaction data
                elif 'transaction' in sheet_name.lower():
                    transactions = self._extract_excel_transactions(df)
                    if transactions:
                        fields.append(ExtractedField(
                            name='transactions',
                            value=transactions,
                            confidence=0.9,
                            raw_text=None
                        ))
            
        except Exception as e:
            self.logger.error(f"Error in structured Excel extraction: {e}")
        
        return fields
    
    def _extract_excel_account_info(self, df: pd.DataFrame) -> List[ExtractedField]:
        """Extract account information from Excel DataFrame."""
        fields = []
        
        try:
            # Look for field-value pairs in the first two columns
            for _, row in df.iterrows():
                if len(row) >= 2:
                    field_name = str(row.iloc[0]).strip().lower()
                    field_value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    
                    if not field_value or field_value == 'nan':
                        continue
                    
                    # Map field names to our standard names
                    field_mapping = {
                        'bank name': 'bank_name',
                        'account holder': 'account_holder_name',
                        'account number': 'account_number',
                        'routing number': 'routing_number',
                        'statement date': 'statement_date'
                    }
                    
                    for pattern, standard_name in field_mapping.items():
                        if pattern in field_name:
                            fields.append(ExtractedField(
                                name=standard_name,
                                value=field_value,
                                confidence=0.95,
                                raw_text=f"{row.iloc[0]}: {field_value}"
                            ))
                            break
                    
                    # Extract statement period
                    if 'statement period' in field_name and ' - ' in field_value:
                        dates = field_value.split(' - ')
                        if len(dates) == 2:
                            fields.append(ExtractedField(
                                name='statement_start_date',
                                value=dates[0].strip(),
                                confidence=0.9,
                                raw_text=field_value
                            ))
                            fields.append(ExtractedField(
                                name='statement_end_date',
                                value=dates[1].strip(),
                                confidence=0.9,
                                raw_text=field_value
                            ))
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel account info: {e}")
        
        return fields
    
    def _extract_excel_summary(self, df: pd.DataFrame) -> List[ExtractedField]:
        """Extract summary information from Excel DataFrame."""
        fields = []
        
        try:
            for _, row in df.iterrows():
                if len(row) >= 2:
                    desc = str(row.iloc[0]).strip().lower()
                    value = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    
                    if not value or value == 'nan':
                        continue
                    
                    # Remove currency formatting and extract numeric value
                    cleaned_value = value.replace('$', '').replace(',', '')
                    
                    # Map descriptions to field names
                    if 'beginning balance' in desc:
                        try:
                            numeric_value = float(cleaned_value)
                            fields.append(ExtractedField(
                                name='beginning_balance',
                                value=numeric_value,
                                confidence=0.95,
                                raw_text=value
                            ))
                        except ValueError:
                            pass
                    
                    elif 'ending balance' in desc:
                        try:
                            numeric_value = float(cleaned_value)
                            fields.append(ExtractedField(
                                name='ending_balance',
                                value=numeric_value,
                                confidence=0.95,
                                raw_text=value
                            ))
                        except ValueError:
                            pass
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel summary: {e}")
        
        return fields
    
    def _extract_excel_transactions(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Extract transactions from Excel DataFrame."""
        transactions = []
        
        try:
            # Expected columns: Date, Description, Amount, Balance
            for _, row in df.iterrows():
                if len(row) >= 3:  # Minimum: date, description, amount
                    try:
                        transaction = {}
                        
                        # Parse date
                        date_val = row.iloc[0]
                        if pd.notna(date_val):
                            if isinstance(date_val, str):
                                parsed_date = self._parse_date(date_val)
                                if parsed_date:
                                    transaction['date'] = parsed_date.isoformat()
                            else:
                                # Might be a datetime object
                                transaction['date'] = str(date_val)
                        
                        # Description
                        desc_val = row.iloc[1]
                        if pd.notna(desc_val):
                            transaction['description'] = str(desc_val).strip()
                        
                        # Amount
                        amount_val = row.iloc[2]
                        if pd.notna(amount_val):
                            amount_str = str(amount_val)
                            try:
                                amount = self._parse_currency(amount_str)
                                transaction['amount'] = float(amount)
                                transaction['type'] = 'debit' if amount < 0 else 'credit'
                            except ValueError:
                                continue
                        
                        # Balance (if available)
                        if len(row) >= 4 and pd.notna(row.iloc[3]):
                            balance_str = str(row.iloc[3])
                            try:
                                balance = self._parse_currency(balance_str)
                                transaction['balance'] = float(balance)
                            except ValueError:
                                pass
                        
                        # Only add if we have essential fields
                        if 'date' in transaction and 'amount' in transaction:
                            transactions.append(transaction)
                    
                    except Exception as e:
                        self.logger.debug(f"Error parsing transaction row: {e}")
                        continue
        
        except Exception as e:
            self.logger.error(f"Error extracting Excel transactions: {e}")
        
        return transactions