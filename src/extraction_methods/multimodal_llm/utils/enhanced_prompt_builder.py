"""
Enhanced prompt builder with document-specific extraction prompts.
Optimizes extraction accuracy for each document type.
"""

import json
from typing import Dict, Any, List, Optional
from ..core.enhanced_document_classifier import DocumentType


class EnhancedPromptBuilder:
    """Build optimized prompts for specific document types."""
    
    def __init__(self):
        """Initialize with document-specific prompts and examples."""
        self.document_prompts = self._build_document_prompts()
        self.extraction_guidelines = self._build_extraction_guidelines()
        self.validation_rules = self._build_validation_rules()
    
    def _build_document_prompts(self) -> Dict[DocumentType, str]:
        """Build specialized prompts for each document type."""
        return {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: """
You are extracting data from a Personal Financial Statement (PFS).

CRITICAL EXTRACTION RULES:
1. Extract ALL monetary values in DOLLARS (not cents)
2. Verify calculations: Assets - Liabilities = Net Worth
3. Look for contingent liabilities in footnotes
4. Distinguish between personal and business phone numbers
5. Extract both current date and statement date

Focus on these sections:
- Personal Information (name, address, phone, email)
- Assets (cash, investments, real estate, personal property)
- Liabilities (loans, mortgages, credit cards)
- Income sources (salary, business, investments)
- Contingent liabilities (guarantees, co-signed loans)

Special attention:
- Some PFS forms have business loans listed as contingent liabilities
- Real estate may be listed with both value and mortgage
- Income may include K-1 distributions from businesses
""",
            
            DocumentType.TAX_RETURN_1040: """
You are extracting data from IRS Form 1040 (Individual Income Tax Return).

CRITICAL EXTRACTION RULES:
1. Identify the tax year prominently displayed
2. Extract line numbers with their values for accuracy
3. Look for attached schedules (Schedule C, D, E)
4. Verify AGI calculation if possible

Key fields to extract:
- Filing status and exemptions
- Income sources:
  * Line 1: Wages, salaries, tips
  * Line 2b: Taxable interest
  * Line 3b: Ordinary dividends
  * Line 5: Pension and annuities
  * Schedule C: Business income
  * Schedule E: Rental income
- Adjusted Gross Income (AGI)
- Taxable income
- Total tax
- Refund or amount owed

Cross-reference with:
- W-2 totals should match Line 1
- 1099 forms should reconcile with interest/dividends
- Schedule C net profit flows to main form
""",
            
            DocumentType.TAX_RETURN_1065: """
You are extracting data from IRS Form 1065 (Partnership Return).

CRITICAL EXTRACTION RULES:
1. Partnership name and EIN are critical identifiers
2. Number of partners affects K-1 distributions
3. Ordinary business income flows to partners

Key fields to extract:
- Partnership identification (name, EIN, address)
- Gross receipts or sales
- Cost of goods sold
- Gross profit
- Ordinary business income (loss)
- Total deductions
- Number of Schedules K-1 attached
- Partner capital accounts

Important relationships:
- Ordinary income × ownership % = Partner's K-1 income
- Total distributions should not exceed cash available
""",
            
            DocumentType.TAX_RETURN_1120S: """
You are extracting data from IRS Form 1120S (S Corporation Return).

CRITICAL EXTRACTION RULES:
1. S Corp income passes through to shareholders
2. Shareholder basis affects loss deductibility
3. Distributions vs wages distinction is critical

Key fields to extract:
- Corporation name and EIN
- Gross receipts or sales
- Cost of goods sold
- Officer compensation (impacts personal income)
- Ordinary business income
- Number of shareholders
- Distributions to shareholders

Tax planning indicators:
- High officer compensation vs distributions
- Accumulated adjustments account (AAA)
- Built-in gains tax if applicable
""",
            
            DocumentType.BALANCE_SHEET: """
You are extracting data from a Balance Sheet (Statement of Financial Position).

CRITICAL EXTRACTION RULES:
1. Assets = Liabilities + Equity (must balance)
2. Distinguish current vs non-current items
3. Look for period date (as of date)
4. May be comparative (multiple periods)

Key sections to extract:
ASSETS:
- Current Assets (cash, AR, inventory)
- Fixed Assets (property, equipment)
- Intangible Assets
- Total Assets

LIABILITIES:
- Current Liabilities (AP, current debt)
- Long-term Debt
- Total Liabilities

EQUITY:
- Paid-in Capital
- Retained Earnings
- Total Equity

Key ratios to note:
- Current Ratio = Current Assets / Current Liabilities
- Debt to Equity = Total Debt / Total Equity
""",
            
            DocumentType.PROFIT_LOSS: """
You are extracting data from a Profit & Loss Statement (Income Statement).

CRITICAL EXTRACTION RULES:
1. Identify the period covered (month, quarter, year)
2. Look for comparative periods
3. Calculate gross margin % if not shown
4. EBITDA may be shown or calculable

Key sections to extract:
REVENUE:
- Gross Sales/Revenue
- Returns and Allowances
- Net Revenue

COSTS:
- Cost of Goods Sold (COGS)
- Gross Profit (Revenue - COGS)

OPERATING EXPENSES:
- Salaries and Wages
- Rent
- Utilities
- Marketing
- Total Operating Expenses

BOTTOM LINE:
- Operating Income (EBIT)
- Interest Expense
- Net Income Before Tax
- Tax Expense
- Net Income

Key metrics:
- Gross Margin = Gross Profit / Revenue
- Operating Margin = Operating Income / Revenue
- Net Margin = Net Income / Revenue
""",
            
            DocumentType.DEBT_SCHEDULE: """
You are extracting data from a Debt Schedule.

CRITICAL EXTRACTION RULES:
1. Each debt must have at minimum: creditor and balance
2. Sum of individual debts should equal total debt
3. Payment amounts may be monthly or annual
4. Interest rates may be APR or monthly

For each debt, extract:
- Creditor/Lender Name
- Account Number (if shown)
- Original Loan Amount
- Current Balance
- Monthly Payment
- Interest Rate
- Maturity Date
- Collateral/Security
- Personal Guarantee (Y/N)

Calculations to verify:
- Total Debt = Sum of all current balances
- Total Monthly Payments = Sum of all monthly payments
- Weighted Average Interest Rate

Special attention:
- SBA loans often have different terms
- Lines of credit show limit vs balance
- Some debts may be in forbearance/deferment
""",
            
            DocumentType.AR_AGING: """
You are extracting data from an Accounts Receivable Aging Report.

CRITICAL EXTRACTION RULES:
1. Aging buckets typically: Current, 30, 60, 90, 120+ days
2. Sum of buckets = Total AR
3. May show by customer or summary only

Extract:
- Report Date
- Aging Buckets:
  * Current (0-30 days)
  * 31-60 days
  * 61-90 days
  * 91-120 days
  * Over 120 days
- Total Accounts Receivable
- Number of Customers
- Largest Customer Balances

Quality indicators:
- High % in current = good
- Large amounts 90+ days = collection risk
- Concentration risk if few customers
""",
            
            DocumentType.MANAGEMENT_BIOS: """
You are extracting data from Management Biographies.

CRITICAL EXTRACTION RULES:
1. Each person is a separate record
2. Look for ownership percentages
3. Industry experience is key for loan approval

For each person, extract:
- Full Name
- Title/Position
- Years with Company
- Total Industry Experience
- Education (degree, school, year)
- Previous Employment
- Ownership Percentage
- Key Achievements
- Professional Certifications

Red flags to note:
- Limited industry experience
- Recent management changes
- Concentration of ownership
""",
            
            DocumentType.ORG_CHART: """
You are analyzing an Organizational Chart.

CRITICAL EXTRACTION RULES:
1. Identify reporting relationships
2. Note any dual reporting structures
3. Count total employees if shown
4. Identify key positions

Extract:
- Top Leadership (CEO, President, Owner)
- Department Heads
- Total Employee Count
- Number of Management Levels
- Key Positions:
  * CFO/Financial Manager
  * Operations Manager
  * Sales/Marketing Head
  
Structural observations:
- Span of control (direct reports per manager)
- Presence of advisory board
- Family members in key positions
""",
        }
    
    def _build_extraction_guidelines(self) -> Dict[str, str]:
        """Build general extraction guidelines by category."""
        return {
            'monetary_values': """
MONETARY VALUE EXTRACTION:
- Extract as shown in document (do not convert units)
- Preserve negative values (shown as () or -)
- Handle abbreviations: K=thousand, M/MM=million, B=billion
- If unclear, include both possible interpretations with confidence scores
""",
            
            'dates': """
DATE EXTRACTION:
- Use ISO format: YYYY-MM-DD
- For partial dates (month/year), use first day: YYYY-MM-01
- For fiscal years, note if different from calendar year
- Extract both document date and reporting period
""",
            
            'identifiers': """
IDENTIFIER EXTRACTION:
- SSN: Format as XXX-XX-XXXX
- EIN: Format as XX-XXXXXXX
- Phone: Include area code
- Email: Preserve exact format
- Account numbers: Include all characters
""",
            
            'calculations': """
CALCULATION VERIFICATION:
- Verify totals sum correctly
- Check percentage calculations
- Note any discrepancies in 'validation_errors' field
- Calculate missing totals if components are present
""",
        }
    
    def _build_validation_rules(self) -> Dict[str, List[str]]:
        """Build cross-field validation rules."""
        return {
            'balance_sheet': [
                'assets_equal_liabilities_plus_equity',
                'current_assets_includes_cash',
                'total_assets_greater_than_zero',
            ],
            'pfs': [
                'net_worth_equals_assets_minus_liabilities',
                'total_income_includes_salary_if_present',
                'real_estate_value_greater_than_mortgage',
            ],
            'tax_return': [
                'agi_includes_wage_income',
                'taxable_income_less_than_agi',
                'business_income_matches_schedule_c',
            ],
            'debt_schedule': [
                'total_debt_equals_sum_of_debts',
                'monthly_payments_reasonable_vs_balances',
                'interest_rates_within_normal_range',
            ],
        }
    
    def build_extraction_prompt(
        self,
        document_type: DocumentType,
        schema: Dict[str, Any],
        include_examples: bool = True,
        validation_focus: Optional[List[str]] = None
    ) -> str:
        """
        Build optimized extraction prompt for document type.
        
        Args:
            document_type: Type of document being processed
            schema: JSON schema for extraction
            include_examples: Whether to include few-shot examples
            validation_focus: Specific validation rules to emphasize
            
        Returns:
            Complete extraction prompt
        """
        # Get document-specific prompt
        base_prompt = self.document_prompts.get(
            document_type,
            "Extract all relevant information from this document."
        )
        
        # Add schema instruction
        schema_prompt = f"""

EXTRACTION SCHEMA:
You must extract data according to this JSON schema:
```json
{json.dumps(schema, indent=2)}
```

Return your extraction as valid JSON matching this schema exactly.
Include confidence scores (0-1) for each field.
"""
        
        # Add relevant guidelines
        guidelines = []
        if 'monetary' in str(document_type).lower() or 'financial' in str(document_type).lower():
            guidelines.append(self.extraction_guidelines['monetary_values'])
        
        guidelines.append(self.extraction_guidelines['dates'])
        guidelines.append(self.extraction_guidelines['identifiers'])
        guidelines.append(self.extraction_guidelines['calculations'])
        
        guidelines_prompt = "\n".join(guidelines)
        
        # Add validation rules if applicable
        validation_prompt = ""
        if validation_focus:
            validation_prompt = f"""

VALIDATION REQUIREMENTS:
Please verify the following:
{chr(10).join(f'- {rule}' for rule in validation_focus)}
"""
        
        # Add examples if requested
        examples_prompt = ""
        if include_examples:
            examples_prompt = self._get_examples_for_type(document_type)
        
        # Combine all parts
        full_prompt = f"""{base_prompt}
{schema_prompt}
{guidelines_prompt}
{validation_prompt}
{examples_prompt}

FINAL INSTRUCTIONS:
1. Extract ONLY information visible in the document
2. Return null for missing fields
3. Include confidence scores for all fields
4. Flag any validation errors found
5. Provide clean, valid JSON output
"""
        
        return full_prompt
    
    def _get_examples_for_type(self, document_type: DocumentType) -> str:
        """Get few-shot examples for document type."""
        examples = {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: """

EXAMPLE EXTRACTION:
```json
{
  "firstName": {"value": "John", "confidence": 0.95},
  "lastName": {"value": "Smith", "confidence": 0.95},
  "totalAssets": {"value": 1500000, "confidence": 0.98},
  "totalLiabilities": {"value": 500000, "confidence": 0.97},
  "netWorth": {"value": 1000000, "confidence": 0.99},
  "validation_notes": "Net worth correctly calculated as assets - liabilities"
}
```
""",
            DocumentType.TAX_RETURN_1040: """

EXAMPLE EXTRACTION:
```json
{
  "taxYear": {"value": 2023, "confidence": 1.0},
  "filingStatus": {"value": "Married Filing Jointly", "confidence": 0.95},
  "wagesLine1": {"value": 125000, "confidence": 0.98},
  "adjustedGrossIncome": {"value": 118000, "confidence": 0.97},
  "taxableIncome": {"value": 93000, "confidence": 0.96},
  "totalTax": {"value": 15234, "confidence": 0.95}
}
```
""",
        }
        
        return examples.get(document_type, "")
    
    def build_validation_prompt(
        self,
        document_type: DocumentType,
        extracted_data: Dict[str, Any],
        related_documents: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for validating extracted data.
        
        Args:
            document_type: Type of document
            extracted_data: Data that was extracted
            related_documents: Data from related documents for cross-validation
            
        Returns:
            Validation prompt
        """
        prompt = f"""
Please validate the following extracted data from a {document_type.value}:

EXTRACTED DATA:
```json
{json.dumps(extracted_data, indent=2)}
```
"""
        
        if related_documents:
            prompt += f"""

RELATED DOCUMENT DATA FOR CROSS-VALIDATION:
```json
{json.dumps(related_documents, indent=2)}
```

Please check for consistency between documents:
- Income amounts should align between PFS and tax returns
- Debt totals should match between PFS and debt schedule
- Business income should match between tax returns and financial statements
"""
        
        # Add specific validation rules
        doc_type_key = document_type.value.split('_')[0]
        if doc_type_key in self.validation_rules:
            rules = self.validation_rules[doc_type_key]
            prompt += f"""

VALIDATION RULES TO CHECK:
{chr(10).join(f'- {rule}' for rule in rules)}
"""
        
        prompt += """

Return a validation report with:
1. Overall validation status (PASS/FAIL/WARNING)
2. Specific issues found
3. Confidence in the validation
4. Recommendations for manual review
"""
        
        return prompt