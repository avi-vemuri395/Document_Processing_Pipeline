"""
Enhanced document classifier supporting comprehensive loan package documents.
Handles tax returns, business financials, organizational documents, and more.
"""

from enum import Enum
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from pathlib import Path
import re

class DocumentType(Enum):
    """Comprehensive document type enumeration."""
    # Financial Statements
    PERSONAL_FINANCIAL_STATEMENT = "personal_financial_statement"
    PFS_STANDARD = "pfs_standard"
    PFS_CUSTOM = "pfs_custom"
    SBA_FORM_413 = "sba_form_413"
    
    # Tax Returns
    TAX_RETURN_1040 = "tax_return_1040"  # Personal
    TAX_RETURN_1065 = "tax_return_1065"  # Partnership
    TAX_RETURN_1120S = "tax_return_1120s"  # S-Corp
    TAX_RETURN_SCHEDULE_C = "schedule_c"  # Business income
    TAX_RETURN_K1 = "schedule_k1"  # Partner share
    
    # Business Financials
    BALANCE_SHEET = "balance_sheet"
    PROFIT_LOSS = "profit_loss"
    CASH_FLOW = "cash_flow"
    AR_AGING = "ar_aging"
    AP_AGING = "ap_aging"
    
    # Debt Documentation
    DEBT_SCHEDULE = "debt_schedule"
    LOAN_AGREEMENT = "loan_agreement"
    PAYMENT_HISTORY = "payment_history"
    
    # Projections
    REVENUE_PROJECTION = "revenue_projection"
    COST_PROJECTION = "cost_projection"
    BREAK_EVEN_ANALYSIS = "break_even_analysis"
    
    # Organizational
    ORG_CHART = "org_chart"
    MANAGEMENT_BIOS = "management_bios"
    BUSINESS_PLAN = "business_plan"
    
    # Other
    BANK_STATEMENT = "bank_statement"
    EQUIPMENT_QUOTE = "equipment_quote"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Document classification result with confidence and metadata."""
    primary_type: DocumentType
    sub_type: Optional[DocumentType] = None
    confidence: float = 0.0
    tax_year: Optional[int] = None
    entity_name: Optional[str] = None
    statement_period: Optional[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class EnhancedDocumentClassifier:
    """Enhanced classifier for comprehensive document type detection."""
    
    def __init__(self):
        """Initialize with classification patterns."""
        self.classification_patterns = self._build_classification_patterns()
        self.filename_patterns = self._build_filename_patterns()
    
    def _build_classification_patterns(self) -> Dict[DocumentType, List[re.Pattern]]:
        """Build regex patterns for document content classification."""
        return {
            # Personal Financial Statements
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: [
                re.compile(r'personal\s+financial\s+statement', re.I),
                re.compile(r'statement\s+of\s+financial\s+condition', re.I),
                re.compile(r'assets.*liabilities.*net\s+worth', re.I | re.S),
            ],
            DocumentType.SBA_FORM_413: [
                re.compile(r'sba\s+form\s+413', re.I),
                re.compile(r'personal\s+financial\s+statement.*sba', re.I),
            ],
            
            # Tax Returns - Personal
            DocumentType.TAX_RETURN_1040: [
                re.compile(r'form\s+1040(?:\s|$)', re.I),
                re.compile(r'u\.?s\.?\s+individual\s+income\s+tax\s+return', re.I),
                re.compile(r'schedule\s+1.*additional\s+income', re.I),
            ],
            
            # Tax Returns - Business
            DocumentType.TAX_RETURN_1065: [
                re.compile(r'form\s+1065', re.I),
                re.compile(r'u\.?s\.?\s+return.*partnership\s+income', re.I),
                re.compile(r'partnership\s+return', re.I),
            ],
            DocumentType.TAX_RETURN_1120S: [
                re.compile(r'form\s+1120s', re.I),
                re.compile(r's\s+corporation\s+income\s+tax', re.I),
                re.compile(r'u\.?s\.?\s+income\s+tax.*s\s+corporation', re.I),
            ],
            DocumentType.TAX_RETURN_SCHEDULE_C: [
                re.compile(r'schedule\s+c\s', re.I),
                re.compile(r'profit\s+or\s+loss\s+from\s+business', re.I),
                re.compile(r'sole\s+proprietorship', re.I),
            ],
            DocumentType.TAX_RETURN_K1: [
                re.compile(r'schedule\s+k-?1', re.I),
                re.compile(r'partner\'s\s+share', re.I),
                re.compile(r'shareholder\'s\s+share', re.I),
            ],
            
            # Business Financial Statements
            DocumentType.BALANCE_SHEET: [
                re.compile(r'balance\s+sheet', re.I),
                re.compile(r'statement\s+of\s+financial\s+position', re.I),
                re.compile(r'assets.*equity.*liabilities', re.I | re.S),
            ],
            DocumentType.PROFIT_LOSS: [
                re.compile(r'profit\s+(?:and|&)\s+loss', re.I),
                re.compile(r'income\s+statement', re.I),
                re.compile(r'statement\s+of\s+operations', re.I),
                re.compile(r'p\s*&\s*l\s+statement', re.I),
            ],
            DocumentType.CASH_FLOW: [
                re.compile(r'cash\s+flow\s+statement', re.I),
                re.compile(r'statement\s+of\s+cash\s+flows', re.I),
                re.compile(r'operating.*investing.*financing', re.I | re.S),
            ],
            DocumentType.AR_AGING: [
                re.compile(r'accounts?\s+receivable\s+aging', re.I),
                re.compile(r'a/?r\s+aging', re.I),
                re.compile(r'customer\s+aging', re.I),
            ],
            DocumentType.AP_AGING: [
                re.compile(r'accounts?\s+payable\s+aging', re.I),
                re.compile(r'a/?p\s+aging', re.I),
                re.compile(r'vendor\s+aging', re.I),
            ],
            
            # Debt Documentation
            DocumentType.DEBT_SCHEDULE: [
                re.compile(r'debt\s+schedule', re.I),
                re.compile(r'loan\s+schedule', re.I),
                re.compile(r'liabilities\s+schedule', re.I),
                re.compile(r'creditor.*balance.*payment', re.I | re.S),
            ],
            
            # Projections
            DocumentType.REVENUE_PROJECTION: [
                re.compile(r'revenue\s+projection', re.I),
                re.compile(r'sales\s+forecast', re.I),
                re.compile(r'projected\s+revenue', re.I),
            ],
            
            # Organizational
            DocumentType.ORG_CHART: [
                re.compile(r'org(?:anizational)?\s+chart', re.I),
                re.compile(r'organization\s+structure', re.I),
                re.compile(r'management\s+structure', re.I),
            ],
            DocumentType.MANAGEMENT_BIOS: [
                re.compile(r'management\s+bio', re.I),
                re.compile(r'executive\s+bio', re.I),
                re.compile(r'management\s+team', re.I),
                re.compile(r'key\s+personnel', re.I),
            ],
        }
    
    def _build_filename_patterns(self) -> Dict[DocumentType, List[re.Pattern]]:
        """Build patterns for filename-based classification."""
        return {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: [
                re.compile(r'pfs', re.I),
                re.compile(r'personal.*financial', re.I),
            ],
            DocumentType.TAX_RETURN_1040: [
                re.compile(r'1040', re.I),
                re.compile(r'personal.*tax', re.I),
                re.compile(r'individual.*return', re.I),
            ],
            DocumentType.TAX_RETURN_1065: [
                re.compile(r'1065', re.I),
                re.compile(r'partnership.*return', re.I),
            ],
            DocumentType.TAX_RETURN_1120S: [
                re.compile(r'1120s?', re.I),
                re.compile(r's.?corp.*return', re.I),
            ],
            DocumentType.BALANCE_SHEET: [
                re.compile(r'balance.*sheet', re.I),
                re.compile(r'bs(?:_|\s|$)', re.I),
            ],
            DocumentType.PROFIT_LOSS: [
                re.compile(r'p\s*&?\s*l', re.I),
                re.compile(r'profit.*loss', re.I),
                re.compile(r'income.*statement', re.I),
            ],
            DocumentType.AR_AGING: [
                re.compile(r'ar.*aging', re.I),
                re.compile(r'receivable', re.I),
            ],
            DocumentType.AP_AGING: [
                re.compile(r'ap.*aging', re.I),
                re.compile(r'payable', re.I),
            ],
            DocumentType.DEBT_SCHEDULE: [
                re.compile(r'debt.*schedule', re.I),
                re.compile(r'loan.*schedule', re.I),
            ],
            DocumentType.ORG_CHART: [
                re.compile(r'org.*chart', re.I),
            ],
            DocumentType.MANAGEMENT_BIOS: [
                re.compile(r'bio', re.I),
                re.compile(r'management', re.I),
            ],
        }
    
    def classify_document(
        self, 
        document_path: Optional[Path] = None,
        content: Optional[str] = None,
        filename: Optional[str] = None
    ) -> ClassificationResult:
        """
        Classify document using multiple signals.
        
        Args:
            document_path: Path to document file
            content: Document text content (if already extracted)
            filename: Filename to use for classification
            
        Returns:
            ClassificationResult with document type and metadata
        """
        if document_path:
            filename = filename or document_path.name
            
        # Start with filename classification
        if filename:
            filename_result = self._classify_by_filename(filename)
            if filename_result.confidence > 0.7:
                # High confidence from filename
                if content:
                    # Validate with content if available
                    content_result = self._classify_by_content(content)
                    if content_result.primary_type == filename_result.primary_type:
                        filename_result.confidence = min(0.95, filename_result.confidence + 0.1)
                return filename_result
        
        # Fall back to content classification
        if content:
            return self._classify_by_content(content)
        
        # Default to unknown
        return ClassificationResult(
            primary_type=DocumentType.UNKNOWN,
            confidence=0.0
        )
    
    def _classify_by_filename(self, filename: str) -> ClassificationResult:
        """Classify based on filename patterns."""
        filename_lower = filename.lower()
        
        # Check for tax year in filename
        tax_year = None
        year_match = re.search(r'20\d{2}', filename)
        if year_match:
            tax_year = int(year_match.group())
        
        # Extract potential entity name
        entity_name = None
        if 'llc' in filename_lower or 'inc' in filename_lower or 'corp' in filename_lower:
            # Try to extract business name
            parts = filename.replace('_', ' ').replace('-', ' ').split()
            entity_parts = []
            for part in parts:
                if part.lower() in ['llc', 'inc', 'corp', 'corporation', 'limited']:
                    entity_parts.append(part)
                    break
                entity_parts.append(part)
            if entity_parts:
                entity_name = ' '.join(entity_parts)
        
        # Check patterns
        for doc_type, patterns in self.filename_patterns.items():
            for pattern in patterns:
                if pattern.search(filename):
                    return ClassificationResult(
                        primary_type=doc_type,
                        confidence=0.75,
                        tax_year=tax_year,
                        entity_name=entity_name
                    )
        
        return ClassificationResult(
            primary_type=DocumentType.UNKNOWN,
            confidence=0.0
        )
    
    def _classify_by_content(self, content: str) -> ClassificationResult:
        """Classify based on document content."""
        # Track matches for each type
        matches = {}
        
        for doc_type, patterns in self.classification_patterns.items():
            match_count = 0
            for pattern in patterns:
                if pattern.search(content[:5000]):  # Check first 5000 chars
                    match_count += 1
            
            if match_count > 0:
                matches[doc_type] = match_count
        
        if not matches:
            return ClassificationResult(
                primary_type=DocumentType.UNKNOWN,
                confidence=0.0
            )
        
        # Get best match
        best_type = max(matches, key=matches.get)
        match_count = matches[best_type]
        pattern_count = len(self.classification_patterns[best_type])
        
        # Calculate confidence
        confidence = min(0.95, 0.5 + (match_count / pattern_count) * 0.45)
        
        # Extract metadata based on type
        metadata = self._extract_metadata(content, best_type)
        
        return ClassificationResult(
            primary_type=best_type,
            confidence=confidence,
            **metadata
        )
    
    def _extract_metadata(self, content: str, doc_type: DocumentType) -> Dict:
        """Extract type-specific metadata from content."""
        metadata = {}
        
        # Extract tax year for tax documents
        if 'TAX_RETURN' in doc_type.name:
            year_match = re.search(r'(?:tax\s+year|form\s+year|20\d{2})', content[:1000], re.I)
            if year_match:
                year_text = year_match.group()
                year_num = re.search(r'20\d{2}', year_text)
                if year_num:
                    metadata['tax_year'] = int(year_num.group())
        
        # Extract statement period for financials
        if doc_type in [DocumentType.BALANCE_SHEET, DocumentType.PROFIT_LOSS]:
            period_match = re.search(r'(?:as\s+of|for\s+the\s+period|ended?)\s+([^,\n]+)', content[:1000], re.I)
            if period_match:
                metadata['statement_period'] = period_match.group(1).strip()
        
        # Extract entity name
        if doc_type in [DocumentType.TAX_RETURN_1065, DocumentType.TAX_RETURN_1120S]:
            entity_match = re.search(r'(?:name\s+of\s+(?:partnership|corporation)|business\s+name)[:\s]+([^\n]+)', content[:2000], re.I)
            if entity_match:
                metadata['entity_name'] = entity_match.group(1).strip()
        
        return metadata
    
    def classify_batch(self, documents: List[Path]) -> Dict[Path, ClassificationResult]:
        """Classify multiple documents efficiently."""
        results = {}
        
        for doc_path in documents:
            # Read first 5000 chars for classification
            try:
                if doc_path.suffix.lower() == '.pdf':
                    # For PDFs, would need to extract text first
                    # For now, use filename classification
                    results[doc_path] = self.classify_document(document_path=doc_path)
                elif doc_path.suffix.lower() in ['.xlsx', '.xls']:
                    # Excel files - use filename
                    results[doc_path] = self.classify_document(document_path=doc_path)
                else:
                    # Text files
                    with open(doc_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(5000)
                    results[doc_path] = self.classify_document(
                        document_path=doc_path,
                        content=content
                    )
            except Exception as e:
                results[doc_path] = ClassificationResult(
                    primary_type=DocumentType.UNKNOWN,
                    confidence=0.0,
                    metadata={'error': str(e)}
                )
        
        return results