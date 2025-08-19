#!/usr/bin/env python3
"""
Document classifier for intelligent routing between DocAI and Claude Vision.
Uses heuristics and DocAI metadata to classify documents without additional API calls.
"""

from typing import Tuple, Dict, Any, Optional
from enum import Enum
import re


class DocumentCategory(Enum):
    """Document categories for routing decisions"""
    STRUCTURED_FORM = "structured_form"      # Route to DocAI
    TAX_DOCUMENT = "tax_document"           # Route to DocAI
    BANK_STATEMENT = "bank_statement"       # Route to DocAI
    FINANCIAL_TABLE = "financial_table"     # Route to DocAI
    NARRATIVE_TEXT = "narrative_text"       # Route to Claude Vision
    VISUAL_DIAGRAM = "visual_diagram"       # Route to Claude Vision
    GENERAL_DOCUMENT = "general_document"   # Default to DocAI
    UNKNOWN = "unknown"                     # Needs further classification


class DocumentClassifier:
    """
    Classifies documents using multiple strategies:
    1. Heuristic text patterns (zero cost)
    2. DocAI metadata inference (no additional cost)
    3. Minimal Claude classification (last resort)
    """
    
    def __init__(self):
        self.classification_cache = {}
        
        # Define patterns for heuristic classification
        self.tax_patterns = [
            r'form\s+1040', r'form\s+w-?2', r'schedule\s+[a-z]',
            r'adjusted\s+gross\s+income', r'taxable\s+income',
            r'form\s+1099', r'form\s+1120', r'form\s+1065',
            r'tax\s+return', r'internal\s+revenue\s+service'
        ]
        
        self.bank_statement_patterns = [
            r'statement\s+period', r'account\s+summary', r'beginning\s+balance',
            r'ending\s+balance', r'deposits?\s+and\s+credits?',
            r'withdrawals?\s+and\s+debits?', r'daily\s+balance',
            r'account\s+number', r'routing\s+number'
        ]
        
        self.structured_form_patterns = [
            r'personal\s+financial\s+statement', r'loan\s+application',
            r'business\s+financial\s+statement', r'credit\s+application',
            r'sba\s+form', r'uniform\s+residential\s+loan'
        ]
        
        self.narrative_patterns = [
            r'management\s+bio', r'executive\s+bio', r'business\s+plan',
            r'letter\s+of\s+intent', r'operating\s+agreement',
            r'franchise\s+agreement', r'org\s+chart', r'organizational\s+chart',
            r'company\s+overview', r'executive\s+summary'
        ]
        
        self.financial_table_patterns = [
            r'balance\s+sheet', r'income\s+statement', r'cash\s+flow',
            r'profit\s+and\s+loss', r'p\s*&\s*l\s+statement',
            r'financial\s+statements?', r'statement\s+of\s+operations'
        ]
    
    def classify_from_text_heuristics(self, text: str) -> Tuple[DocumentCategory, float]:
        """
        Zero-cost heuristic classification based on text patterns.
        
        Args:
            text: First page text or full document text
            
        Returns:
            Tuple of (DocumentCategory, confidence_score)
        """
        if not text:
            return DocumentCategory.UNKNOWN, 0.0
        
        text_lower = text.lower()
        
        # Check each pattern category
        checks = [
            (self.tax_patterns, DocumentCategory.TAX_DOCUMENT, 0.9),
            (self.bank_statement_patterns, DocumentCategory.BANK_STATEMENT, 0.85),
            (self.structured_form_patterns, DocumentCategory.STRUCTURED_FORM, 0.95),
            (self.financial_table_patterns, DocumentCategory.FINANCIAL_TABLE, 0.85),
            (self.narrative_patterns, DocumentCategory.NARRATIVE_TEXT, 0.8)
        ]
        
        for patterns, category, base_confidence in checks:
            matches = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            if matches >= 2:  # At least 2 pattern matches for confidence
                # Adjust confidence based on number of matches
                confidence = min(base_confidence + (matches - 2) * 0.05, 1.0)
                return category, confidence
            elif matches == 1:
                # Single match = lower confidence
                return category, base_confidence * 0.7
        
        # No strong patterns found
        return DocumentCategory.UNKNOWN, 0.3
    
    def classify_from_docai_result(self, docai_result: Dict[str, Any]) -> Tuple[DocumentCategory, float]:
        """
        Infer document type from DocAI extraction results.
        No additional API cost since we already have the data.
        
        Args:
            docai_result: Result from DocAI Form Parser or General Processor
            
        Returns:
            Tuple of (DocumentCategory, confidence_score)
        """
        if not docai_result or not docai_result.get('success'):
            return DocumentCategory.UNKNOWN, 0.0
        
        # Extract metadata
        form_fields = docai_result.get('form_fields', {})
        tables = docai_result.get('tables', [])
        entities = docai_result.get('entities', [])
        text = docai_result.get('text', '').lower()
        
        # Convert to strings for pattern matching
        fields_str = ' '.join(form_fields.keys()).lower() if form_fields else ''
        entities_str = ' '.join(str(e) for e in entities).lower()
        tables_str = ' '.join(str(t) for t in tables).lower()
        
        # Tax document indicators
        tax_indicators = [
            'adjusted_gross_income', 'taxable_income', 'form_1040',
            'w2', '1099', 'schedule_c', 'tax_return', 'irs'
        ]
        tax_matches = sum(1 for ind in tax_indicators if ind in fields_str or ind in text)
        if tax_matches >= 2:
            return DocumentCategory.TAX_DOCUMENT, min(0.8 + tax_matches * 0.05, 0.95)
        
        # Bank statement indicators
        bank_indicators = [
            'balance', 'transaction', 'deposit', 'withdrawal',
            'account_number', 'statement_period', 'routing'
        ]
        has_transaction_table = len(tables) > 0 and 'balance' in tables_str
        bank_matches = sum(1 for ind in bank_indicators if ind in fields_str or ind in text)
        if has_transaction_table or bank_matches >= 3:
            return DocumentCategory.BANK_STATEMENT, 0.85
        
        # Financial statement with tables
        if len(tables) > 2 and ('assets' in tables_str or 'liabilities' in tables_str):
            return DocumentCategory.FINANCIAL_TABLE, 0.8
        
        # Structured form - many fields
        if len(form_fields) > 20:
            return DocumentCategory.STRUCTURED_FORM, 0.8
        elif len(form_fields) > 10:
            return DocumentCategory.STRUCTURED_FORM, 0.7
        
        # Narrative document - few fields, lots of text
        text_length = len(text)
        if len(form_fields) < 5 and text_length > 2000:
            return DocumentCategory.NARRATIVE_TEXT, 0.7
        
        # General document
        if len(form_fields) > 0 or len(tables) > 0:
            return DocumentCategory.GENERAL_DOCUMENT, 0.5
        
        return DocumentCategory.UNKNOWN, 0.3
    
    def map_loan_application_type(self, loan_type: str) -> Tuple[DocumentCategory, float]:
        """
        Map LoanApplicationItemType to document category.
        
        Args:
            loan_type: The LoanApplicationItemType string
            
        Returns:
            Tuple of (DocumentCategory, confidence_score)
        """
        if not loan_type:
            return DocumentCategory.UNKNOWN, 0.0
        
        loan_type_upper = loan_type.upper()
        
        # Direct mappings with high confidence
        mappings = {
            # Tax documents
            'TAX_RETURN': (DocumentCategory.TAX_DOCUMENT, 1.0),
            'BUSINESS_TAX_RETURN': (DocumentCategory.TAX_DOCUMENT, 1.0),
            'PERSONAL_TAX_RETURN': (DocumentCategory.TAX_DOCUMENT, 1.0),
            'W2': (DocumentCategory.TAX_DOCUMENT, 1.0),
            '1099': (DocumentCategory.TAX_DOCUMENT, 1.0),
            
            # Bank statements
            'BANK_STATEMENT': (DocumentCategory.BANK_STATEMENT, 1.0),
            'BUSINESS_BANK_STATEMENT': (DocumentCategory.BANK_STATEMENT, 1.0),
            'PERSONAL_BANK_STATEMENT': (DocumentCategory.BANK_STATEMENT, 1.0),
            
            # Structured forms
            'PERSONAL_FINANCIAL_STATEMENT': (DocumentCategory.STRUCTURED_FORM, 1.0),
            'BUSINESS_FINANCIAL_STATEMENT': (DocumentCategory.STRUCTURED_FORM, 1.0),
            'LOAN_APPLICATION': (DocumentCategory.STRUCTURED_FORM, 1.0),
            'CREDIT_APPLICATION': (DocumentCategory.STRUCTURED_FORM, 1.0),
            
            # Financial tables
            'BALANCE_SHEET': (DocumentCategory.FINANCIAL_TABLE, 1.0),
            'PROFIT_LOSS_STATEMENT': (DocumentCategory.FINANCIAL_TABLE, 1.0),
            'INCOME_STATEMENT': (DocumentCategory.FINANCIAL_TABLE, 1.0),
            'CASH_FLOW_STATEMENT': (DocumentCategory.FINANCIAL_TABLE, 1.0),
            
            # Narrative documents
            'BUSINESS_PLAN': (DocumentCategory.NARRATIVE_TEXT, 1.0),
            'MANAGEMENT_BIOS': (DocumentCategory.NARRATIVE_TEXT, 1.0),
            'ORG_CHART': (DocumentCategory.VISUAL_DIAGRAM, 1.0),
            'LETTER_OF_INTENT': (DocumentCategory.NARRATIVE_TEXT, 1.0),
            'OPERATING_AGREEMENT': (DocumentCategory.NARRATIVE_TEXT, 1.0),
            'FRANCHISE_AGREEMENT': (DocumentCategory.NARRATIVE_TEXT, 1.0),
        }
        
        return mappings.get(loan_type_upper, (DocumentCategory.GENERAL_DOCUMENT, 0.7))
    
    def should_use_docai(self, category: DocumentCategory, confidence: float) -> bool:
        """
        Determine if document should be processed with DocAI based on classification.
        
        Args:
            category: Document category
            confidence: Classification confidence
            
        Returns:
            True if should use DocAI, False if should use Claude Vision
        """
        # High confidence narrative/visual = skip DocAI
        if category in [DocumentCategory.NARRATIVE_TEXT, DocumentCategory.VISUAL_DIAGRAM] and confidence > 0.7:
            return False
        
        # Low confidence = try DocAI first (can extract more metadata)
        if confidence < 0.5:
            return True
        
        # Structured documents = use DocAI
        if category in [DocumentCategory.STRUCTURED_FORM, DocumentCategory.TAX_DOCUMENT, 
                        DocumentCategory.BANK_STATEMENT, DocumentCategory.FINANCIAL_TABLE]:
            return True
        
        # Default to DocAI for general documents
        return category == DocumentCategory.GENERAL_DOCUMENT