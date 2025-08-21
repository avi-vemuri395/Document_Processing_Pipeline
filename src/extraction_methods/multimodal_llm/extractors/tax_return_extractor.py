"""
Tax return extraction module supporting 1040, 1065, 1120S forms.
Handles both regex patterns and LLM-based extraction.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path
import re
from decimal import Decimal

@dataclass
class TaxReturnData:
    """Structured tax return data."""
    # Form Information
    form_type: str  # 1040, 1065, 1120S
    tax_year: int
    filing_status: Optional[str] = None
    
    # Entity Information
    taxpayer_name: Optional[str] = None
    taxpayer_ssn: Optional[str] = None
    spouse_name: Optional[str] = None
    spouse_ssn: Optional[str] = None
    business_name: Optional[str] = None
    business_ein: Optional[str] = None
    
    # Income Fields - 1040
    wages_salaries: Optional[Decimal] = None
    interest_income: Optional[Decimal] = None
    dividend_income: Optional[Decimal] = None
    business_income: Optional[Decimal] = None  # Schedule C
    capital_gains: Optional[Decimal] = None
    rental_income: Optional[Decimal] = None
    other_income: Optional[Decimal] = None
    total_income: Optional[Decimal] = None
    
    # Adjustments & Deductions - 1040
    adjustments_to_income: Optional[Decimal] = None
    adjusted_gross_income: Optional[Decimal] = None
    standard_or_itemized_deduction: Optional[Decimal] = None
    qualified_business_income_deduction: Optional[Decimal] = None
    taxable_income: Optional[Decimal] = None
    
    # Tax Calculations - 1040
    total_tax: Optional[Decimal] = None
    total_payments: Optional[Decimal] = None
    refund_or_amount_owed: Optional[Decimal] = None
    
    # Business Fields - 1065/1120S
    gross_receipts: Optional[Decimal] = None
    cost_of_goods_sold: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    total_deductions: Optional[Decimal] = None
    ordinary_business_income: Optional[Decimal] = None
    
    # Partner/Shareholder Info
    number_of_partners: Optional[int] = None
    number_of_shareholders: Optional[int] = None
    total_distributions: Optional[Decimal] = None
    
    # Schedule K-1 Summary
    k1_ordinary_income: Optional[Decimal] = None
    k1_rental_income: Optional[Decimal] = None
    k1_interest_income: Optional[Decimal] = None
    k1_dividend_income: Optional[Decimal] = None
    k1_capital_gains: Optional[Decimal] = None
    
    # Confidence Scores
    confidence_scores: Dict[str, float] = None
    
    def __post_init__(self):
        if self.confidence_scores is None:
            self.confidence_scores = {}


class TaxReturnPatterns:
    """Regex patterns for tax return extraction."""
    
    # Form Type Patterns
    FORM_PATTERNS = {
        '1040': [
            r'Form\s+1040(?:\s|$)',
            r'U\.?S\.?\s+Individual\s+Income\s+Tax\s+Return',
        ],
        '1065': [
            r'Form\s+1065',
            r'U\.?S\.?\s+Return\s+of\s+Partnership\s+Income',
        ],
        '1120S': [
            r'Form\s+1120-?S',
            r'U\.?S\.?\s+Income\s+Tax\s+Return.*S\s+Corporation',
        ],
    }
    
    # Income Field Patterns - 1040
    INCOME_PATTERNS_1040 = {
        'wages_salaries': [
            r'Wages[,\s]+salaries[,\s]+tips.*?\$?\s*([\d,]+)',
            r'Line\s+1[a-z]?.*?Wages.*?\$?\s*([\d,]+)',
        ],
        'interest_income': [
            r'Taxable\s+interest.*?\$?\s*([\d,]+)',
            r'Line\s+2b.*?\$?\s*([\d,]+)',
        ],
        'dividend_income': [
            r'(?:Qualified\s+)?[Dd]ividends.*?\$?\s*([\d,]+)',
            r'Line\s+3b.*?\$?\s*([\d,]+)',
        ],
        'business_income': [
            r'Business\s+income.*?Schedule\s+C.*?\$?\s*([\d,]+)',
            r'Line\s+3.*?Schedule\s+C.*?\$?\s*([\d,]+)',
        ],
        'capital_gains': [
            r'Capital\s+gain.*?\$?\s*([\d,]+)',
            r'Line\s+7.*?\$?\s*([\d,]+)',
        ],
        'total_income': [
            r'Total\s+income.*?\$?\s*([\d,]+)',
            r'Line\s+9.*?\$?\s*([\d,]+)',
        ],
        'adjusted_gross_income': [
            r'Adjusted\s+gross\s+income.*?\$?\s*([\d,]+)',
            r'AGI.*?\$?\s*([\d,]+)',
            r'Line\s+11.*?\$?\s*([\d,]+)',
        ],
        'taxable_income': [
            r'Taxable\s+income.*?\$?\s*([\d,]+)',
            r'Line\s+15.*?\$?\s*([\d,]+)',
        ],
        'total_tax': [
            r'Total\s+tax.*?\$?\s*([\d,]+)',
            r'Line\s+24.*?\$?\s*([\d,]+)',
        ],
    }
    
    # Business Income Patterns - 1065/1120S
    INCOME_PATTERNS_BUSINESS = {
        'gross_receipts': [
            r'Gross\s+receipts\s+or\s+sales.*?\$?\s*([\d,]+)',
            r'Line\s+1[a-c]?.*?Gross\s+receipts.*?\$?\s*([\d,]+)',
        ],
        'cost_of_goods_sold': [
            r'Cost\s+of\s+goods\s+sold.*?\$?\s*([\d,]+)',
            r'Line\s+2.*?COGS.*?\$?\s*([\d,]+)',
        ],
        'gross_profit': [
            r'Gross\s+profit.*?\$?\s*([\d,]+)',
            r'Line\s+3.*?\$?\s*([\d,]+)',
        ],
        'ordinary_business_income': [
            r'Ordinary\s+(?:business\s+)?income.*?\$?\s*([\d,]+)',
            r'Line\s+22.*?\$?\s*([\d,]+)',
        ],
        'total_deductions': [
            r'Total\s+deductions.*?\$?\s*([\d,]+)',
            r'Line\s+21.*?\$?\s*([\d,]+)',
        ],
    }
    
    @classmethod
    def compile_patterns(cls) -> Dict[str, List[re.Pattern]]:
        """Compile all patterns for efficiency."""
        compiled = {}
        
        # Compile form patterns
        for form_type, patterns in cls.FORM_PATTERNS.items():
            compiled[f'form_{form_type}'] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]
        
        # Compile income patterns
        for field, patterns in cls.INCOME_PATTERNS_1040.items():
            compiled[f'1040_{field}'] = [
                re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns
            ]
        
        for field, patterns in cls.INCOME_PATTERNS_BUSINESS.items():
            compiled[f'business_{field}'] = [
                re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns
            ]
        
        return compiled


class TaxReturnExtractor:
    """Extract data from tax return documents."""
    
    def __init__(self):
        """Initialize with compiled patterns."""
        self.patterns = TaxReturnPatterns.compile_patterns()
    
    def extract(self, text: str, form_type: Optional[str] = None) -> TaxReturnData:
        """
        Extract tax return data from text.
        
        Args:
            text: Document text content
            form_type: Optional form type hint (1040, 1065, 1120S)
            
        Returns:
            TaxReturnData with extracted fields
        """
        # Detect form type if not provided
        if not form_type:
            form_type = self._detect_form_type(text)
        
        # Extract tax year
        tax_year = self._extract_tax_year(text)
        
        # Initialize result
        result = TaxReturnData(
            form_type=form_type,
            tax_year=tax_year or 0
        )
        
        # Extract based on form type
        if form_type == '1040':
            self._extract_1040_data(text, result)
        elif form_type == '1065':
            self._extract_1065_data(text, result)
        elif form_type == '1120S':
            self._extract_1120s_data(text, result)
        
        # Extract entity information
        self._extract_entity_info(text, result)
        
        return result
    
    def _detect_form_type(self, text: str) -> str:
        """Detect tax form type from text."""
        for form_type in ['1040', '1065', '1120S']:
            patterns = self.patterns[f'form_{form_type}']
            for pattern in patterns:
                if pattern.search(text[:2000]):
                    return form_type
        return 'unknown'
    
    def _extract_tax_year(self, text: str) -> Optional[int]:
        """Extract tax year from document."""
        # Look for year patterns
        year_patterns = [
            r'(?:Tax\s+Year|Form\s+Year|For\s+Calendar\s+Year)\s+(\d{4})',
            r'(\d{4})\s+(?:Tax\s+Return|Form)',
            r'(?:January|December)\s+\d+[,\s]+(\d{4})',
        ]
        
        for pattern_str in year_patterns:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            match = pattern.search(text[:2000])
            if match:
                year = int(match.group(1))
                if 2000 <= year <= 2030:  # Sanity check
                    return year
        
        return None
    
    def _extract_1040_data(self, text: str, result: TaxReturnData):
        """Extract 1040 specific fields."""
        # Extract income fields
        for field in ['wages_salaries', 'interest_income', 'dividend_income',
                      'business_income', 'capital_gains', 'total_income',
                      'adjusted_gross_income', 'taxable_income', 'total_tax']:
            
            patterns = self.patterns[f'1040_{field}']
            value, confidence = self._extract_monetary_field(text, patterns)
            
            if value is not None:
                setattr(result, field, value)
                result.confidence_scores[field] = confidence
    
    def _extract_1065_data(self, text: str, result: TaxReturnData):
        """Extract 1065 partnership return data."""
        self._extract_business_income_fields(text, result)
        
        # Extract partner count
        partner_pattern = re.compile(
            r'Number\s+of\s+(?:Schedules\s+K-?1|partners).*?(\d+)',
            re.IGNORECASE
        )
        match = partner_pattern.search(text)
        if match:
            result.number_of_partners = int(match.group(1))
            result.confidence_scores['number_of_partners'] = 0.9
    
    def _extract_1120s_data(self, text: str, result: TaxReturnData):
        """Extract 1120S S-corporation return data."""
        self._extract_business_income_fields(text, result)
        
        # Extract shareholder count
        shareholder_pattern = re.compile(
            r'Number\s+of\s+(?:shareholders|Schedules\s+K-?1).*?(\d+)',
            re.IGNORECASE
        )
        match = shareholder_pattern.search(text)
        if match:
            result.number_of_shareholders = int(match.group(1))
            result.confidence_scores['number_of_shareholders'] = 0.9
    
    def _extract_business_income_fields(self, text: str, result: TaxReturnData):
        """Extract business income fields common to 1065/1120S."""
        for field in ['gross_receipts', 'cost_of_goods_sold', 'gross_profit',
                      'ordinary_business_income', 'total_deductions']:
            
            patterns = self.patterns[f'business_{field}']
            value, confidence = self._extract_monetary_field(text, patterns)
            
            if value is not None:
                setattr(result, field, value)
                result.confidence_scores[field] = confidence
    
    def _extract_entity_info(self, text: str, result: TaxReturnData):
        """Extract taxpayer/business entity information."""
        if result.form_type == '1040':
            # Extract taxpayer name and SSN
            name_pattern = re.compile(
                r'(?:Your\s+)?(?:first\s+)?name.*?(?:and\s+initial)?[:\s]+([^\n]+)',
                re.IGNORECASE
            )
            match = name_pattern.search(text[:1000])
            if match:
                result.taxpayer_name = match.group(1).strip()
            
            # SSN pattern
            ssn_pattern = re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b')
            match = ssn_pattern.search(text[:2000])
            if match:
                result.taxpayer_ssn = match.group()
        
        elif result.form_type in ['1065', '1120S']:
            # Extract business name and EIN
            name_patterns = [
                r'(?:Name\s+of\s+)?(?:partnership|corporation)[:\s]+([^\n]+)',
                r'Business\s+name[:\s]+([^\n]+)',
            ]
            
            for pattern_str in name_patterns:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                match = pattern.search(text[:2000])
                if match:
                    result.business_name = match.group(1).strip()
                    break
            
            # EIN pattern
            ein_pattern = re.compile(r'\b\d{2}-?\d{7}\b')
            match = ein_pattern.search(text[:2000])
            if match:
                result.business_ein = match.group()
    
    def _extract_monetary_field(
        self, 
        text: str, 
        patterns: List[re.Pattern]
    ) -> tuple[Optional[Decimal], float]:
        """
        Extract monetary value using patterns.
        
        Returns:
            Tuple of (value, confidence)
        """
        for i, pattern in enumerate(patterns):
            match = pattern.search(text)
            if match:
                try:
                    # Extract number and clean it
                    value_str = match.group(1)
                    value_str = value_str.replace(',', '').replace('$', '')
                    
                    # Handle negative values
                    if '(' in value_str and ')' in value_str:
                        value_str = '-' + value_str.replace('(', '').replace(')', '')
                    
                    value = Decimal(value_str)
                    
                    # Higher confidence for earlier patterns
                    confidence = 0.9 - (i * 0.1)
                    confidence = max(0.5, confidence)
                    
                    return value, confidence
                    
                except (ValueError, ArithmeticError):
                    continue
        
        return None, 0.0
    
    def generate_llm_prompt(self, form_type: str) -> str:
        """Generate extraction prompt for LLM based on form type."""
        base_prompt = """Extract the following tax return information:
        
        1. Form type and tax year
        2. Taxpayer/Entity identification (name, SSN/EIN)
        3. Key income fields
        4. Deductions and adjustments
        5. Tax calculations
        
        Return as structured JSON with field names and values.
        Include confidence scores for each field.
        """
        
        if form_type == '1040':
            return base_prompt + """
            
            Focus on:
            - Wages and salaries (Line 1)
            - Interest and dividends (Lines 2-3)
            - Business income from Schedule C
            - Adjusted Gross Income (AGI)
            - Taxable income
            - Total tax and refund/amount owed
            """
        
        elif form_type in ['1065', '1120S']:
            return base_prompt + f"""
            
            For {form_type}, focus on:
            - Gross receipts or sales
            - Cost of goods sold
            - Gross profit
            - Total deductions
            - Ordinary business income
            - Number of partners/shareholders
            - Distributions to partners/shareholders
            """
        
        return base_prompt