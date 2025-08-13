"""
Regex patterns for document data extraction.

This module contains compiled regex patterns for extracting various types
of data from different document types.
"""

import re
from typing import Dict, List, Pattern


class BasePatterns:
    """Base class for regex patterns."""
    
    def __init__(self):
        """Initialize patterns."""
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile all regex patterns."""
        pass


class CommonPatterns(BasePatterns):
    """Common regex patterns used across different document types."""
    
    def _compile_patterns(self):
        """Compile common patterns."""
        # Date patterns
        self.DATE_MDY = re.compile(r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b')
        self.DATE_DMY = re.compile(r'\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b')
        self.DATE_YMD = re.compile(r'\b(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})\b')
        self.DATE_MONTH_NAME = re.compile(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+(\d{1,2}),?\s+(\d{4})\b', re.IGNORECASE)
        
        # Currency patterns
        self.CURRENCY_USD = re.compile(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        self.CURRENCY_NEGATIVE = re.compile(r'\(\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\)')
        self.CURRENCY_GENERAL = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        
        # Phone number patterns
        self.PHONE_US = re.compile(r'\b(?:\+?1[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\b')
        
        # SSN pattern
        self.SSN = re.compile(r'\b(\d{3})[-\s]?(\d{2})[-\s]?(\d{4})\b')
        
        # Email pattern
        self.EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        
        # Address patterns
        self.ZIP_CODE = re.compile(r'\b(\d{5})(?:-(\d{4}))?\b')
        self.STATE_ABBR = re.compile(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b')
        
        # Name patterns
        self.PERSON_NAME = re.compile(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)(?:\s+([A-Z][a-z]+))?\b')


class BankStatementPatterns(BasePatterns):
    """Regex patterns specific to bank statements."""
    
    def _compile_patterns(self):
        """Compile bank statement patterns."""
        # Account number patterns
        self.ACCOUNT_NUMBER = re.compile(r'(?:Account\s+(?:Number|#)?:?\s*|Acct\s*#?:?\s*)(\d{4,20})', re.IGNORECASE)
        self.ROUTING_NUMBER = re.compile(r'(?:Routing\s+(?:Number|#)?:?\s*|RTN:?\s*)(\d{9})', re.IGNORECASE)
        
        # Account holder patterns
        self.ACCOUNT_HOLDER_NAME = re.compile(r'(?:Account\s+Holder|Primary\s+Account\s+Holder|Name)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.IGNORECASE)
        
        # Statement period patterns
        self.STATEMENT_PERIOD = re.compile(r'(?:Statement\s+Period|Period)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s*(?:to|through|-)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        self.STATEMENT_DATE = re.compile(r'(?:Statement\s+Date|As\s+of)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        
        # Balance patterns
        self.BEGINNING_BALANCE = re.compile(r'(?:Beginning\s+Balance|Opening\s+Balance|Previous\s+Balance)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.ENDING_BALANCE = re.compile(r'(?:Ending\s+Balance|Closing\s+Balance|Current\s+Balance)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.AVAILABLE_BALANCE = re.compile(r'(?:Available\s+Balance)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        
        # Transaction patterns
        self.TRANSACTION_LINE = re.compile(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})\s+(.{10,50}?)\s+(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\))')
        self.TRANSACTION_DETAILED = re.compile(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})?\s*(.{10,50}?)\s+(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\))\s+(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)')
        
        # Bank information patterns
        self.BANK_NAME = re.compile(r'(?:^|\n)([A-Z][A-Za-z\s&]+(?:Bank|Credit\s+Union|Financial|Fed(?:eral)?|National))', re.MULTILINE)
        self.BANK_ADDRESS = re.compile(r'(\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Way|Place|Pl))', re.IGNORECASE)
        
        # Fee patterns
        self.FEE_TRANSACTION = re.compile(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})\s+(.*?(?:fee|charge|penalty).*?)\s+(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        
        # Deposit patterns
        self.DEPOSIT_TRANSACTION = re.compile(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})\s+(.*?(?:deposit|credit|transfer\s+in).*?)\s+(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        
        # Withdrawal patterns
        self.WITHDRAWAL_TRANSACTION = re.compile(r'(\d{1,2}[\/\-]\d{1,2}[\/\-]?\d{0,4})\s+(.*?(?:withdrawal|debit|transfer\s+out|atm).*?)\s+(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\(\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?\))', re.IGNORECASE)


class TaxReturnPatterns(BasePatterns):
    """Regex patterns specific to tax returns."""
    
    def _compile_patterns(self):
        """Compile tax return patterns."""
        # Tax year
        self.TAX_YEAR = re.compile(r'(?:Tax\s+Year|For\s+the\s+year)[:\s]*(\d{4})', re.IGNORECASE)
        
        # Taxpayer information
        self.TAXPAYER_NAME = re.compile(r'(?:Your\s+first\s+name|First\s+name)[:\s]*([A-Z][a-z]+)', re.IGNORECASE)
        self.TAXPAYER_LAST_NAME = re.compile(r'(?:Last\s+name)[:\s]*([A-Z][a-z]+)', re.IGNORECASE)
        self.SPOUSE_NAME = re.compile(r'(?:Spouse.?s\s+first\s+name)[:\s]*([A-Z][a-z]+)', re.IGNORECASE)
        
        # Income patterns
        self.WAGES = re.compile(r'(?:Wages,\s+salaries,\s+tips|Total\s+income)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.AGI = re.compile(r'(?:Adjusted\s+gross\s+income|AGI)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        
        # Tax patterns
        self.TOTAL_TAX = re.compile(r'(?:Total\s+tax)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.REFUND_AMOUNT = re.compile(r'(?:Refund)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.AMOUNT_OWED = re.compile(r'(?:Amount\s+you\s+owe)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)


class PayStubPatterns(BasePatterns):
    """Regex patterns specific to pay stubs."""
    
    def _compile_patterns(self):
        """Compile pay stub patterns."""
        # Employee information
        self.EMPLOYEE_NAME = re.compile(r'(?:Employee\s+Name|Name)[:\s]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', re.IGNORECASE)
        self.EMPLOYEE_ID = re.compile(r'(?:Employee\s+ID|EMP\s+ID|ID)[:\s]*(\d+)', re.IGNORECASE)
        
        # Pay period
        self.PAY_PERIOD = re.compile(r'(?:Pay\s+Period|Period)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s*(?:to|through|-)\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        self.PAY_DATE = re.compile(r'(?:Pay\s+Date|Date\s+Paid)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        
        # Earnings
        self.GROSS_PAY = re.compile(r'(?:Gross\s+Pay|Total\s+Gross)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.NET_PAY = re.compile(r'(?:Net\s+Pay|Take\s+Home)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.REGULAR_HOURS = re.compile(r'(?:Regular\s+Hours|Reg\s+Hours)[:\s]*(\d+(?:\.\d{2})?)', re.IGNORECASE)
        self.OVERTIME_HOURS = re.compile(r'(?:Overtime\s+Hours|OT\s+Hours)[:\s]*(\d+(?:\.\d{2})?)', re.IGNORECASE)
        
        # Deductions
        self.FEDERAL_TAX = re.compile(r'(?:Federal\s+Tax|Fed\s+Tax|FIT)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.STATE_TAX = re.compile(r'(?:State\s+Tax|SIT)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.SOCIAL_SECURITY = re.compile(r'(?:Social\s+Security|FICA|SS)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.MEDICARE = re.compile(r'(?:Medicare|Med)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)


class InvoicePatterns(BasePatterns):
    """Regex patterns specific to invoices."""
    
    def _compile_patterns(self):
        """Compile invoice patterns."""
        # Invoice information
        self.INVOICE_NUMBER = re.compile(r'(?:Invoice\s+(?:Number|#)?|INV\s*#?)[:\s]*([A-Z0-9\-]+)', re.IGNORECASE)
        self.INVOICE_DATE = re.compile(r'(?:Invoice\s+Date|Date)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        self.DUE_DATE = re.compile(r'(?:Due\s+Date|Payment\s+Due)[:\s]*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})', re.IGNORECASE)
        
        # Amounts
        self.SUBTOTAL = re.compile(r'(?:Subtotal|Sub\s+Total)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.TAX_AMOUNT = re.compile(r'(?:Tax|Sales\s+Tax)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        self.TOTAL_AMOUNT = re.compile(r'(?:Total|Amount\s+Due|Balance\s+Due)[:\s]*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', re.IGNORECASE)
        
        # Vendor/Customer information
        self.VENDOR_NAME = re.compile(r'(?:From|Vendor|Bill\s+From)[:\s]*([A-Z][A-Za-z\s&,.-]+)', re.IGNORECASE)
        self.CUSTOMER_NAME = re.compile(r'(?:To|Bill\s+To|Customer)[:\s]*([A-Z][A-Za-z\s&,.-]+)', re.IGNORECASE)


class PersonalFinancialStatementPatterns(BasePatterns):
    """Patterns specific to Personal Financial Statements."""
    
    def _compile_patterns(self):
        """Compile PFS patterns."""
        # SBA Form 413 specific indicators
        self.SBA_FORM_413_INDICATORS = [
            re.compile(r'SBA\s+FORM\s+413', re.IGNORECASE),
            re.compile(r'FORM\s+413', re.IGNORECASE),
            re.compile(r'OMB.*3245-0188', re.IGNORECASE),
            re.compile(r'PERSONAL\s+FINANCIAL\s+STATEMENT.*SBA', re.IGNORECASE),
            re.compile(r'SMALL\s+BUSINESS\s+ADMINISTRATION', re.IGNORECASE),
        ]
        
        # Generic PFS indicators
        self.PFS_INDICATORS = [
            re.compile(r'PERSONAL\s+FINANCIAL\s+STATEMENT', re.IGNORECASE),
            re.compile(r'NET\s+WORTH\s+STATEMENT', re.IGNORECASE),
            re.compile(r'STATEMENT\s+OF\s+FINANCIAL\s+CONDITION', re.IGNORECASE),
            re.compile(r'ASSETS.*LIABILITIES.*NET\s+WORTH', re.IGNORECASE | re.DOTALL),
        ]
        
        # Personal information patterns
        self.PERSONAL_INFO_PATTERNS = {
            'name': [
                re.compile(r'(?:Name|INDIVIDUAL|BORROWER)[\s:]*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', re.IGNORECASE),
                re.compile(r'(?:First\s+Name|Last\s+Name)[\s:]*([A-Z][a-z]+)', re.IGNORECASE),
            ],
            'ssn': [
                re.compile(r'(?:Social\s+Security|SSN|S\.S\.N\.)[\s#:]*(\d{3}[-\s]?\d{2}[-\s]?\d{4})', re.IGNORECASE),
                re.compile(r'(?:Soc\.?\s+Sec\.?\s+No\.?)[\s:]*(\d{3}[-\s]?\d{2}[-\s]?\d{4})', re.IGNORECASE),
            ],
            'date_of_birth': [
                re.compile(r'(?:Date\s+of\s+Birth|DOB|Birth\s+Date)[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
            ],
        }
        
        # Asset patterns with improved specificity
        self.ASSET_PATTERNS = {
            'cash_and_equivalents': [
                re.compile(r'(?:Cash\s+(?:on\s+Hand|&\s+Equivalents?)|Checking\s+Account)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
                re.compile(r'(?:Cash|Liquid\s+Assets)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'savings_accounts': [
                re.compile(r'(?:Savings\s+Accounts?|Time\s+Deposits?|CDs?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'retirement_accounts': [
                re.compile(r'(?:IRA|401\(?k\)?|Retirement\s+Accounts?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
                re.compile(r'(?:Pension|Retirement\s+Savings)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'investments': [
                re.compile(r'(?:Stocks?|Bonds?|Securities|Mutual\s+Funds)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
                re.compile(r'(?:Investment\s+Portfolio|Brokerage\s+Account)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'real_estate': [
                re.compile(r'(?:Real\s+Estate|Property)\s+(?:Owned|Value)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
                re.compile(r'(?:Home\s+Value|Primary\s+Residence)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'vehicles': [
                re.compile(r'(?:Automobile|Vehicle|Car).*?(?:Present\s+)?Value[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'life_insurance': [
                re.compile(r'(?:Life\s+Insurance).*?Cash\s+Value[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'total_assets': [
                re.compile(r'(?:Total\s+Assets?|TOTAL\s+ASSETS?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
        }
        
        # Liability patterns
        self.LIABILITY_PATTERNS = {
            'credit_cards': [
                re.compile(r'(?:Credit\s+Cards?|Revolving\s+Credit)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'bank_loans': [
                re.compile(r'(?:Notes?\s+Payable.*?Banks?|Bank\s+Loans?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'installment_debt': [
                re.compile(r'(?:Installment\s+Debts?|Monthly\s+Payments?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'mortgages': [
                re.compile(r'(?:Mortgages?|Real\s+Estate\s+Loans?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
                re.compile(r'(?:Home\s+Loan|Property\s+Loan)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'other_liabilities': [
                re.compile(r'(?:Other\s+Liabilities?|Miscellaneous\s+Debts?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'total_liabilities': [
                re.compile(r'(?:Total\s+Liabilities?|TOTAL\s+LIABILITIES?)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
        }
        
        # Income patterns
        self.INCOME_PATTERNS = {
            'salary_wages': [
                re.compile(r'(?:Salary|Wages?|Employment\s+Income)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
                re.compile(r'(?:Annual\s+Salary|Gross\s+Income)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'investment_income': [
                re.compile(r'(?:Investment\s+Income|Dividends?|Interest)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'rental_income': [
                re.compile(r'(?:Real\s+Estate\s+Income|Rental\s+Income)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'other_income': [
                re.compile(r'(?:Other\s+Income|Miscellaneous\s+Income)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
            'total_income': [
                re.compile(r'(?:Total\s+Income|TOTAL\s+INCOME)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            ],
        }
        
        # Net worth patterns
        self.NET_WORTH_PATTERNS = [
            re.compile(r'(?:Net\s+Worth|NET\s+WORTH)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
            re.compile(r'(?:Total\s+Assets\s+Less\s+Total\s+Liabilities)[\s:$]*([0-9,]+\.?\d*)', re.IGNORECASE),
        ]


class BusinessFinancialStatementPatterns(BasePatterns):
    """Patterns for business financial statements."""
    
    def _compile_patterns(self):
        """Compile business financial statement patterns."""
        # Balance sheet patterns
        self.BALANCE_SHEET_PATTERNS = [
            re.compile(r'BALANCE\s+SHEET', re.IGNORECASE),
            re.compile(r'STATEMENT\s+OF\s+FINANCIAL\s+POSITION', re.IGNORECASE),
            re.compile(r'ASSETS.*LIABILITIES.*EQUITY', re.IGNORECASE | re.DOTALL),
            re.compile(r'CURRENT\s+ASSETS', re.IGNORECASE),
            re.compile(r'TOTAL\s+ASSETS.*TOTAL\s+LIABILITIES', re.IGNORECASE | re.DOTALL),
        ]
        
        # Income statement patterns
        self.INCOME_STATEMENT_PATTERNS = [
            re.compile(r'INCOME\s+STATEMENT', re.IGNORECASE),
            re.compile(r'STATEMENT\s+OF\s+OPERATIONS', re.IGNORECASE),
            re.compile(r'PROFIT\s+(?:AND|&)\s+LOSS', re.IGNORECASE),
            re.compile(r'REVENUE.*EXPENSES.*NET\s+INCOME', re.IGNORECASE | re.DOTALL),
            re.compile(r'GROSS\s+PROFIT', re.IGNORECASE),
        ]
        
        # Cash flow statement patterns
        self.CASH_FLOW_PATTERNS = [
            re.compile(r'CASH\s+FLOW\s+STATEMENT', re.IGNORECASE),
            re.compile(r'STATEMENT\s+OF\s+CASH\s+FLOWS', re.IGNORECASE),
            re.compile(r'OPERATING\s+ACTIVITIES', re.IGNORECASE),
            re.compile(r'INVESTING\s+ACTIVITIES', re.IGNORECASE),
            re.compile(r'FINANCING\s+ACTIVITIES', re.IGNORECASE),
        ]


class TaxReturnPatterns(BasePatterns):
    """Enhanced patterns for tax return documents."""
    
    def _compile_patterns(self):
        """Compile enhanced tax return patterns."""
        # Form 1040 patterns
        self.FORM_1040_PATTERNS = [
            re.compile(r'FORM\s+1040', re.IGNORECASE),
            re.compile(r'U\.?S\.?\s+INDIVIDUAL\s+INCOME\s+TAX\s+RETURN', re.IGNORECASE),
            re.compile(r'ADJUSTED\s+GROSS\s+INCOME', re.IGNORECASE),
            re.compile(r'FILING\s+STATUS', re.IGNORECASE),
            re.compile(r'STANDARD\s+DEDUCTION', re.IGNORECASE),
        ]
        
        # Form 1120S patterns
        self.FORM_1120S_PATTERNS = [
            re.compile(r'FORM\s+1120S?', re.IGNORECASE),
            re.compile(r'U\.?S\.?\s+INCOME\s+TAX\s+RETURN.*S\s+CORPORATION', re.IGNORECASE),
            re.compile(r'S\s+CORPORATION', re.IGNORECASE),
            re.compile(r'ORDINARY\s+BUSINESS\s+INCOME', re.IGNORECASE),
        ]
        
        # Form 1065 patterns
        self.FORM_1065_PATTERNS = [
            re.compile(r'FORM\s+1065', re.IGNORECASE),
            re.compile(r'U\.?S\.?\s+RETURN\s+OF\s+PARTNERSHIP\s+INCOME', re.IGNORECASE),
            re.compile(r'PARTNERSHIP', re.IGNORECASE),
            re.compile(r'ORDINARY\s+BUSINESS\s+INCOME.*LOSS', re.IGNORECASE),
        ]
        
        # Common tax patterns
        self.TAX_COMMON_PATTERNS = [
            re.compile(r'TAX\s+YEAR\s+(\d{4})', re.IGNORECASE),
            re.compile(r'EIN\s*:?\s*(\d{2}-\d{7})', re.IGNORECASE),
            re.compile(r'SSN\s*:?\s*(\d{3}-\d{2}-\d{4})', re.IGNORECASE),
            re.compile(r'INTERNAL\s+REVENUE\s+SERVICE', re.IGNORECASE),
            re.compile(r'DEPARTMENT\s+OF\s+THE\s+TREASURY', re.IGNORECASE),
        ]


class DocumentClassificationPatterns(BasePatterns):
    """Enhanced patterns for document type classification."""
    
    def _compile_patterns(self):
        """Compile document classification patterns."""
        # Bank statement indicators
        self.BANK_STATEMENT_INDICATORS = [
            re.compile(r'(?:bank\s+statement|account\s+statement)', re.IGNORECASE),
            re.compile(r'(?:beginning\s+balance|ending\s+balance)', re.IGNORECASE),
            re.compile(r'(?:account\s+number|routing\s+number)', re.IGNORECASE),
            re.compile(r'(?:transaction\s+history|statement\s+period)', re.IGNORECASE),
            re.compile(r'(?:deposits|withdrawals|transfers)', re.IGNORECASE),
        ]
        
        # Personal Financial Statement indicators
        self.PFS_INDICATORS = [
            re.compile(r'PERSONAL\s+FINANCIAL\s+STATEMENT', re.IGNORECASE),
            re.compile(r'SBA\s+FORM\s+413', re.IGNORECASE),
            re.compile(r'NET\s+WORTH', re.IGNORECASE),
            re.compile(r'ASSETS.*LIABILITIES', re.IGNORECASE | re.DOTALL),
            re.compile(r'STATEMENT\s+OF\s+FINANCIAL\s+CONDITION', re.IGNORECASE),
        ]
        
        # Tax return indicators
        self.TAX_RETURN_INDICATORS = [
            re.compile(r'(?:form\s+1040|form\s+1120|form\s+1065)', re.IGNORECASE),
            re.compile(r'(?:tax\s+return|income\s+tax)', re.IGNORECASE),
            re.compile(r'(?:adjusted\s+gross\s+income|agi)', re.IGNORECASE),
            re.compile(r'(?:internal\s+revenue\s+service|irs)', re.IGNORECASE),
            re.compile(r'(?:tax\s+year|filing\s+status)', re.IGNORECASE),
            re.compile(r'DEPARTMENT\s+OF\s+THE\s+TREASURY', re.IGNORECASE),
        ]
        
        # Business financial statement indicators
        self.BUSINESS_FINANCIAL_INDICATORS = [
            re.compile(r'(?:balance\s+sheet|income\s+statement)', re.IGNORECASE),
            re.compile(r'(?:cash\s+flow|statement\s+of\s+operations)', re.IGNORECASE),
            re.compile(r'(?:profit\s+and\s+loss|p&l)', re.IGNORECASE),
            re.compile(r'(?:assets.*liabilities.*equity)', re.IGNORECASE | re.DOTALL),
            re.compile(r'(?:revenue.*expenses.*net\s+income)', re.IGNORECASE | re.DOTALL),
        ]
        
        # Loan application indicators
        self.LOAN_APPLICATION_INDICATORS = [
            re.compile(r'LOAN\s+APPLICATION', re.IGNORECASE),
            re.compile(r'APPLICATION\s+FOR\s+(?:CREDIT|FINANCING)', re.IGNORECASE),
            re.compile(r'(?:BORROWER|APPLICANT)\s+INFORMATION', re.IGNORECASE),
            re.compile(r'REQUESTED\s+LOAN\s+AMOUNT', re.IGNORECASE),
            re.compile(r'PURPOSE\s+OF\s+LOAN', re.IGNORECASE),
        ]
        
        # Debt schedule indicators
        self.DEBT_SCHEDULE_INDICATORS = [
            re.compile(r'DEBT\s+SCHEDULE', re.IGNORECASE),
            re.compile(r'SCHEDULE\s+OF\s+DEBTS?', re.IGNORECASE),
            re.compile(r'OUTSTANDING\s+LOANS?', re.IGNORECASE),
            re.compile(r'CREDITOR.*BALANCE.*PAYMENT', re.IGNORECASE | re.DOTALL),
            re.compile(r'MONTHLY\s+PAYMENT\s+SCHEDULE', re.IGNORECASE),
        ]
        
        # Pay stub indicators
        self.PAY_STUB_INDICATORS = [
            re.compile(r'(?:pay\s+stub|payroll|paycheck)', re.IGNORECASE),
            re.compile(r'(?:gross\s+pay|net\s+pay)', re.IGNORECASE),
            re.compile(r'(?:pay\s+period|employee\s+id)', re.IGNORECASE),
            re.compile(r'(?:federal\s+tax|state\s+tax|fica)', re.IGNORECASE),
            re.compile(r'(?:earnings|deductions)', re.IGNORECASE),
        ]
        
        # Invoice indicators
        self.INVOICE_INDICATORS = [
            re.compile(r'(?:invoice|bill)', re.IGNORECASE),
            re.compile(r'(?:amount\s+due|payment\s+due)', re.IGNORECASE),
            re.compile(r'(?:invoice\s+number|invoice\s+date)', re.IGNORECASE),
            re.compile(r'(?:subtotal|tax\s+amount)', re.IGNORECASE),
            re.compile(r'(?:bill\s+to|sold\s+to)', re.IGNORECASE),
        ]
        
        # Business plan indicators
        self.BUSINESS_PLAN_INDICATORS = [
            re.compile(r'BUSINESS\s+PLAN', re.IGNORECASE),
            re.compile(r'EXECUTIVE\s+SUMMARY', re.IGNORECASE),
            re.compile(r'MARKET\s+ANALYSIS', re.IGNORECASE),
            re.compile(r'FINANCIAL\s+PROJECTIONS', re.IGNORECASE),
            re.compile(r'BUSINESS\s+MODEL', re.IGNORECASE),
        ]
        
        # Equipment quote indicators
        self.EQUIPMENT_QUOTE_INDICATORS = [
            re.compile(r'EQUIPMENT\s+(?:QUOTE|QUOTATION)', re.IGNORECASE),
            re.compile(r'QUOTE\s+(?:NUMBER|#)', re.IGNORECASE),
            re.compile(r'EQUIPMENT.*(?:COST|PRICE)', re.IGNORECASE),
            re.compile(r'MACHINERY\s+QUOTE', re.IGNORECASE),
        ]
        
        # Management bio indicators
        self.MANAGEMENT_BIO_INDICATORS = [
            re.compile(r'MANAGEMENT.*(?:BIO|BIOGRAPHY)', re.IGNORECASE),
            re.compile(r'BIOGRAPHICAL?\s+INFORMATION', re.IGNORECASE),
            re.compile(r'EXECUTIVE.*PROFILE', re.IGNORECASE),
            re.compile(r'MANAGEMENT\s+TEAM', re.IGNORECASE),
            re.compile(r'KEY\s+PERSONNEL', re.IGNORECASE),
        ]


def get_patterns_for_document_type(document_type: str) -> BasePatterns:
    """
    Get patterns object for a specific document type.
    
    Args:
        document_type: Type of document
        
    Returns:
        Patterns object for the document type
    """
    type_map = {
        'bank_statement': BankStatementPatterns,
        'tax_return': TaxReturnPatterns,
        'pay_stub': PayStubPatterns,
        'invoice': InvoicePatterns,
        'personal_financial_statement': PersonalFinancialStatementPatterns,
        'pfs': PersonalFinancialStatementPatterns,
        'sba_form_413': PersonalFinancialStatementPatterns,
        'business_financial_statement': BusinessFinancialStatementPatterns,
        'business_financial': BusinessFinancialStatementPatterns,
        'common': CommonPatterns,
        'classification': DocumentClassificationPatterns
    }
    
    pattern_class = type_map.get(document_type.lower())
    if pattern_class:
        return pattern_class()
    else:
        raise ValueError(f"Unknown document type: {document_type}")


def get_enhanced_classification_scores(text: str) -> Dict[str, float]:
    """
    Get enhanced classification scores using all available patterns.
    
    Args:
        text: Document text to analyze
        
    Returns:
        Dictionary with document type scores
    """
    scores = {}
    text_lower = text.lower()
    
    # Initialize pattern sets
    pfs_patterns = PersonalFinancialStatementPatterns()
    business_patterns = BusinessFinancialStatementPatterns()
    tax_patterns = TaxReturnPatterns()
    classification_patterns = DocumentClassificationPatterns()
    
    # Personal Financial Statement scoring
    pfs_score = 0.0
    sba_413_score = 0.0
    
    # Check SBA Form 413 indicators
    for pattern in pfs_patterns.SBA_FORM_413_INDICATORS:
        if pattern.search(text):
            sba_413_score += 0.25
    
    # Check generic PFS indicators
    for pattern in pfs_patterns.PFS_INDICATORS:
        if pattern.search(text):
            pfs_score += 0.2
    
    # Enhanced PFS scoring with field detection
    asset_field_count = 0
    for asset_type, patterns in pfs_patterns.ASSET_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                asset_field_count += 1
                break
    
    liability_field_count = 0
    for liability_type, patterns in pfs_patterns.LIABILITY_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(text):
                liability_field_count += 1
                break
    
    # Boost PFS score based on field detection
    if asset_field_count >= 3:
        pfs_score += 0.3
    if liability_field_count >= 2:
        pfs_score += 0.2
    
    # Net worth calculation presence
    for pattern in pfs_patterns.NET_WORTH_PATTERNS:
        if pattern.search(text):
            pfs_score += 0.3
            sba_413_score += 0.2
            break
    
    if sba_413_score > 0:
        scores['sba_form_413'] = min(1.0, sba_413_score)
    if pfs_score > 0:
        scores['personal_financial_statement'] = min(1.0, pfs_score)
    
    # Business Financial Statement scoring
    balance_sheet_score = 0.0
    income_statement_score = 0.0
    cash_flow_score = 0.0
    
    for pattern in business_patterns.BALANCE_SHEET_PATTERNS:
        if pattern.search(text):
            balance_sheet_score += 0.2
    
    for pattern in business_patterns.INCOME_STATEMENT_PATTERNS:
        if pattern.search(text):
            income_statement_score += 0.2
    
    for pattern in business_patterns.CASH_FLOW_PATTERNS:
        if pattern.search(text):
            cash_flow_score += 0.2
    
    if balance_sheet_score > 0:
        scores['balance_sheet'] = min(1.0, balance_sheet_score)
    if income_statement_score > 0:
        scores['income_statement'] = min(1.0, income_statement_score)
    if cash_flow_score > 0:
        scores['cash_flow_statement'] = min(1.0, cash_flow_score)
    
    # Tax Return scoring
    form_1040_score = 0.0
    form_1120s_score = 0.0
    form_1065_score = 0.0
    
    for pattern in tax_patterns.FORM_1040_PATTERNS:
        if pattern.search(text):
            form_1040_score += 0.25
    
    for pattern in tax_patterns.FORM_1120S_PATTERNS:
        if pattern.search(text):
            form_1120s_score += 0.25
    
    for pattern in tax_patterns.FORM_1065_PATTERNS:
        if pattern.search(text):
            form_1065_score += 0.25
    
    if form_1040_score > 0:
        scores['tax_return_1040'] = min(1.0, form_1040_score)
    if form_1120s_score > 0:
        scores['tax_return_1120s'] = min(1.0, form_1120s_score)
    if form_1065_score > 0:
        scores['tax_return_1065'] = min(1.0, form_1065_score)
    
    # Other document types using classification patterns
    other_types = {
        'bank_statement': classification_patterns.BANK_STATEMENT_INDICATORS,
        'loan_application': classification_patterns.LOAN_APPLICATION_INDICATORS,
        'debt_schedule': classification_patterns.DEBT_SCHEDULE_INDICATORS,
        'business_plan': classification_patterns.BUSINESS_PLAN_INDICATORS,
        'equipment_quote': classification_patterns.EQUIPMENT_QUOTE_INDICATORS,
        'management_bio': classification_patterns.MANAGEMENT_BIO_INDICATORS,
        'pay_stub': classification_patterns.PAY_STUB_INDICATORS,
        'invoice': classification_patterns.INVOICE_INDICATORS,
    }
    
    for doc_type, indicators in other_types.items():
        type_score = 0.0
        for pattern in indicators:
            if pattern.search(text):
                type_score += 0.2
        
        if type_score > 0:
            scores[doc_type] = min(1.0, type_score)
    
    return scores


def classify_document_by_patterns(text: str) -> Dict[str, float]:
    """
    Classify document type based on pattern matching.
    
    Args:
        text: Document text to analyze
        
    Returns:
        Dictionary with document type scores
    """
    classification_patterns = DocumentClassificationPatterns()
    scores = {}
    
    # Count matches for each document type
    bank_matches = sum(1 for pattern in classification_patterns.BANK_STATEMENT_INDICATORS 
                      if pattern.search(text))
    scores['bank_statement'] = bank_matches / len(classification_patterns.BANK_STATEMENT_INDICATORS)
    
    tax_matches = sum(1 for pattern in classification_patterns.TAX_RETURN_INDICATORS 
                     if pattern.search(text))
    scores['tax_return'] = tax_matches / len(classification_patterns.TAX_RETURN_INDICATORS)
    
    pay_matches = sum(1 for pattern in classification_patterns.PAY_STUB_INDICATORS 
                     if pattern.search(text))
    scores['pay_stub'] = pay_matches / len(classification_patterns.PAY_STUB_INDICATORS)
    
    invoice_matches = sum(1 for pattern in classification_patterns.INVOICE_INDICATORS 
                         if pattern.search(text))
    scores['invoice'] = invoice_matches / len(classification_patterns.INVOICE_INDICATORS)
    
    return scores