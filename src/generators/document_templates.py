"""
Document templates and configurations for realistic financial document generation.

This module contains template configurations, formatting rules, and layout 
specifications for different types of financial documents including bank 
statements, tax returns, and financial statements.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, date
from dataclasses import dataclass
from reportlab.lib.colors import Color, black, blue, darkblue, grey, lightgrey, red


@dataclass
class DocumentTemplate:
    """Base template configuration for documents."""
    name: str
    institution_name: str
    logo_placeholder: str
    header_color: Color
    accent_color: Color
    fonts: Dict[str, str]
    layout: Dict[str, Any]


@dataclass
class BankStatementTemplate(DocumentTemplate):
    """Template configuration for bank statements."""
    routing_number_prefix: str
    account_number_format: str
    statement_format: str
    disclaimer_text: str


@dataclass
class TaxFormTemplate(DocumentTemplate):
    """Template configuration for tax forms."""
    form_number: str
    form_title: str
    tax_year_format: str
    irs_header_text: str
    footer_disclaimer: str


@dataclass
class FinancialStatementTemplate(DocumentTemplate):
    """Template configuration for financial statements."""
    statement_type: str
    title_format: str
    date_format: str
    currency_format: str
    section_headers: List[str]


class DocumentTemplates:
    """
    Central repository for all document templates and configurations.
    Provides realistic formatting and layout specifications for various
    financial document types.
    """
    
    def __init__(self):
        """Initialize document templates."""
        self._initialize_common_elements()
        self._initialize_bank_templates()
        self._initialize_tax_form_templates()
        self._initialize_financial_statement_templates()
    
    def _initialize_common_elements(self):
        """Initialize common elements used across documents."""
        self.common_fonts = {
            'title': 'Helvetica-Bold',
            'header': 'Helvetica-Bold',
            'body': 'Helvetica',
            'footer': 'Helvetica',
            'disclaimer': 'Helvetica',
            'monospace': 'Courier'
        }
        
        self.common_colors = {
            'black': black,
            'blue': blue,
            'darkblue': darkblue,
            'grey': grey,
            'lightgrey': lightgrey,
            'red': red
        }
        
        self.standard_disclaimers = {
            'fdic': "Member FDIC • Equal Housing Lender",
            'privacy': "We are committed to protecting your privacy. Please see our Privacy Policy for details.",
            'accuracy': "Please review this statement carefully and report any discrepancies immediately.",
            'irs': "For Paperwork Reduction Act Notice, see separate instructions.",
            'sba': "This form was approved by OMB under control number 3245-0188."
        }
    
    def _initialize_bank_templates(self):
        """Initialize bank statement templates for major banks."""
        
        # Chase Bank Template
        self.chase_template = BankStatementTemplate(
            name="chase_bank_statement",
            institution_name="Chase Bank",
            logo_placeholder="CHASE",
            header_color=darkblue,
            accent_color=blue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 100,
                'footer_height': 80,
                'margin': 72,
                'logo_position': (72, 'top-100'),
                'account_info_position': (72, 'top-150'),
                'summary_position': (72, 'top-250'),
                'transactions_position': (72, 'top-350')
            },
            routing_number_prefix="021000021",
            account_number_format="####-####-####",
            statement_format="monthly",
            disclaimer_text=(
                "Member FDIC • Equal Housing Lender • "
                "JPMorgan Chase Bank, N.A. • "
                "This statement reflects account activity through the statement date shown."
            )
        )
        
        # Bank of America Template
        self.boa_template = BankStatementTemplate(
            name="boa_bank_statement",
            institution_name="Bank of America",
            logo_placeholder="BANK OF AMERICA",
            header_color=red,
            accent_color=darkblue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 120,
                'footer_height': 100,
                'margin': 72,
                'logo_position': (72, 'top-120'),
                'account_info_position': (300, 'top-120'),
                'summary_position': (72, 'top-200'),
                'transactions_position': (72, 'top-300')
            },
            routing_number_prefix="026009593",
            account_number_format="####-####-####",
            statement_format="monthly",
            disclaimer_text=(
                "Member FDIC • Equal Housing Lender • "
                "Bank of America, N.A. • "
                "Please retain this statement for your records."
            )
        )
        
        # Wells Fargo Template
        self.wells_fargo_template = BankStatementTemplate(
            name="wells_fargo_bank_statement",
            institution_name="Wells Fargo",
            logo_placeholder="WELLS FARGO",
            header_color=red,
            accent_color=darkblue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 110,
                'footer_height': 90,
                'margin': 72,
                'logo_position': (72, 'top-110'),
                'account_info_position': (350, 'top-110'),
                'summary_position': (72, 'top-220'),
                'transactions_position': (72, 'top-320')
            },
            routing_number_prefix="121000248",
            account_number_format="####-####-####",
            statement_format="monthly",
            disclaimer_text=(
                "Member FDIC • "
                "Wells Fargo Bank, N.A. • "
                "Please review your statement and report any errors immediately."
            )
        )
        
        self.bank_templates = {
            'chase': self.chase_template,
            'bank_of_america': self.boa_template,
            'wells_fargo': self.wells_fargo_template
        }
    
    def _initialize_tax_form_templates(self):
        """Initialize tax form templates."""
        
        # Form 1120 Template
        self.form_1120_template = TaxFormTemplate(
            name="form_1120",
            institution_name="Internal Revenue Service",
            logo_placeholder="IRS",
            header_color=black,
            accent_color=darkblue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 120,
                'footer_height': 60,
                'margin': 72,
                'form_number_position': (72, 'top-50'),
                'title_position': (72, 'top-80'),
                'tax_year_position': (400, 'top-50'),
                'content_start_position': (72, 'top-140')
            },
            form_number="1120",
            form_title="U.S. Corporation Income Tax Return",
            tax_year_format="Tax Year {year}",
            irs_header_text="Department of the Treasury - Internal Revenue Service",
            footer_disclaimer="For Paperwork Reduction Act Notice, see separate instructions."
        )
        
        # Form 1120S Template
        self.form_1120s_template = TaxFormTemplate(
            name="form_1120s",
            institution_name="Internal Revenue Service",
            logo_placeholder="IRS",
            header_color=black,
            accent_color=darkblue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 120,
                'footer_height': 60,
                'margin': 72,
                'form_number_position': (72, 'top-50'),
                'title_position': (72, 'top-80'),
                'tax_year_position': (400, 'top-50'),
                'content_start_position': (72, 'top-140')
            },
            form_number="1120S",
            form_title="U.S. Income Tax Return for an S Corporation",
            tax_year_format="Tax Year {year}",
            irs_header_text="Department of the Treasury - Internal Revenue Service",
            footer_disclaimer="For Paperwork Reduction Act Notice, see separate instructions."
        )
        
        # Schedule C Template
        self.schedule_c_template = TaxFormTemplate(
            name="schedule_c",
            institution_name="Internal Revenue Service",
            logo_placeholder="IRS",
            header_color=black,
            accent_color=darkblue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 120,
                'footer_height': 60,
                'margin': 72,
                'form_number_position': (72, 'top-50'),
                'title_position': (72, 'top-80'),
                'tax_year_position': (400, 'top-50'),
                'content_start_position': (72, 'top-140')
            },
            form_number="Schedule C",
            form_title="Profit or Loss From Business (Sole Proprietorship)",
            tax_year_format="Tax Year {year}",
            irs_header_text="Department of the Treasury - Internal Revenue Service",
            footer_disclaimer="For Paperwork Reduction Act Notice, see separate instructions."
        )
        
        self.tax_form_templates = {
            '1120': self.form_1120_template,
            '1120S': self.form_1120s_template,
            '1040_schedule_c': self.schedule_c_template
        }
    
    def _initialize_financial_statement_templates(self):
        """Initialize financial statement templates."""
        
        # Balance Sheet Template
        self.balance_sheet_template = FinancialStatementTemplate(
            name="balance_sheet",
            institution_name="Business Financial Statements",
            logo_placeholder="COMPANY LOGO",
            header_color=darkblue,
            accent_color=blue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 100,
                'footer_height': 50,
                'margin': 72,
                'title_position': (72, 'top-50'),
                'date_position': (72, 'top-80'),
                'content_start_position': (72, 'top-120')
            },
            statement_type="balance_sheet",
            title_format="{company_name}\nBALANCE SHEET\nAs of {date}",
            date_format="%B %d, %Y",
            currency_format="${:,.2f}",
            section_headers=[
                "ASSETS",
                "Current Assets:",
                "Fixed Assets:",
                "LIABILITIES",
                "Current Liabilities:",
                "Long-term Liabilities:",
                "EQUITY"
            ]
        )
        
        # Income Statement Template
        self.income_statement_template = FinancialStatementTemplate(
            name="income_statement",
            institution_name="Business Financial Statements",
            logo_placeholder="COMPANY LOGO",
            header_color=darkblue,
            accent_color=blue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 100,
                'footer_height': 50,
                'margin': 72,
                'title_position': (72, 'top-50'),
                'date_position': (72, 'top-80'),
                'content_start_position': (72, 'top-120')
            },
            statement_type="income_statement",
            title_format="{company_name}\nINCOME STATEMENT\nFor the Year Ended {date}",
            date_format="%B %d, %Y",
            currency_format="${:,.2f}",
            section_headers=[
                "REVENUE",
                "COST OF GOODS SOLD",
                "GROSS PROFIT",
                "OPERATING EXPENSES",
                "NET INCOME"
            ]
        )
        
        # Cash Flow Statement Template
        self.cash_flow_template = FinancialStatementTemplate(
            name="cash_flow_statement",
            institution_name="Business Financial Statements",
            logo_placeholder="COMPANY LOGO",
            header_color=darkblue,
            accent_color=blue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 100,
                'footer_height': 50,
                'margin': 72,
                'title_position': (72, 'top-50'),
                'date_position': (72, 'top-80'),
                'content_start_position': (72, 'top-120')
            },
            statement_type="cash_flow_statement",
            title_format="{company_name}\nSTATEMENT OF CASH FLOWS\nFor the Year Ended {date}",
            date_format="%B %d, %Y",
            currency_format="${:,.2f}",
            section_headers=[
                "CASH FLOWS FROM OPERATING ACTIVITIES",
                "CASH FLOWS FROM INVESTING ACTIVITIES", 
                "CASH FLOWS FROM FINANCING ACTIVITIES",
                "NET CHANGE IN CASH"
            ]
        )
        
        # Personal Financial Statement (SBA Form 413) Template
        self.pfs_template = FinancialStatementTemplate(
            name="personal_financial_statement",
            institution_name="U.S. Small Business Administration",
            logo_placeholder="SBA LOGO",
            header_color=darkblue,
            accent_color=blue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 120,
                'footer_height': 80,
                'margin': 72,
                'form_number_position': (72, 'top-40'),
                'title_position': (72, 'top-60'),
                'subtitle_position': (72, 'top-80'),
                'content_start_position': (72, 'top-140')
            },
            statement_type="personal_financial_statement",
            title_format="SBA FORM 413\nPERSONAL FINANCIAL STATEMENT\nU.S. Small Business Administration",
            date_format="%B %d, %Y",
            currency_format="${:,.2f}",
            section_headers=[
                "PERSONAL INFORMATION",
                "ASSETS",
                "LIABILITIES",
                "INCOME AND EXPENSES",
                "NET WORTH"
            ]
        )
        
        # Debt Schedule Template
        self.debt_schedule_template = FinancialStatementTemplate(
            name="debt_schedule",
            institution_name="Business Financial Statements",
            logo_placeholder="COMPANY LOGO",
            header_color=darkblue,
            accent_color=blue,
            fonts=self.common_fonts.copy(),
            layout={
                'header_height': 100,
                'footer_height': 50,
                'margin': 72,
                'title_position': (72, 'top-50'),
                'date_position': (72, 'top-80'),
                'content_start_position': (72, 'top-120')
            },
            statement_type="debt_schedule",
            title_format="{company_name}\nBUSINESS DEBT SCHEDULE\nAs of {date}",
            date_format="%B %d, %Y",
            currency_format="${:,.2f}",
            section_headers=[
                "DEBT SUMMARY",
                "CREDITOR DETAILS",
                "PAYMENT SCHEDULE",
                "TOTALS"
            ]
        )
        
        self.financial_statement_templates = {
            'balance_sheet': self.balance_sheet_template,
            'income_statement': self.income_statement_template,
            'cash_flow': self.cash_flow_template,
            'personal_financial_statement': self.pfs_template,
            'debt_schedule': self.debt_schedule_template
        }
    
    def get_bank_template(self, bank_name: str) -> BankStatementTemplate:
        """Get bank statement template by bank name."""
        bank_key = bank_name.lower().replace(' ', '_')
        return self.bank_templates.get(bank_key, self.chase_template)
    
    def get_tax_form_template(self, form_type: str) -> TaxFormTemplate:
        """Get tax form template by form type."""
        return self.tax_form_templates.get(form_type, self.form_1120_template)
    
    def get_financial_statement_template(self, statement_type: str) -> FinancialStatementTemplate:
        """Get financial statement template by statement type."""
        return self.financial_statement_templates.get(statement_type, self.balance_sheet_template)
    
    def get_all_bank_names(self) -> List[str]:
        """Get list of all supported bank names."""
        return ['Chase Bank', 'Bank of America', 'Wells Fargo']
    
    def get_all_tax_forms(self) -> List[str]:
        """Get list of all supported tax form types."""
        return ['1120', '1120S', '1040_schedule_c']
    
    def get_all_financial_statements(self) -> List[str]:
        """Get list of all supported financial statement types."""
        return [
            'balance_sheet', 
            'income_statement', 
            'cash_flow', 
            'personal_financial_statement',
            'debt_schedule'
        ]
    
    def format_currency(self, amount: float, template: DocumentTemplate = None) -> str:
        """Format currency according to template specifications."""
        if template and hasattr(template, 'currency_format'):
            return template.currency_format.format(amount)
        return f"${amount:,.2f}"
    
    def format_date(self, date_obj: date, template: DocumentTemplate = None) -> str:
        """Format date according to template specifications."""
        if template and hasattr(template, 'date_format'):
            return date_obj.strftime(template.date_format)
        return date_obj.strftime("%m/%d/%Y")
    
    def get_disclaimer_text(self, disclaimer_type: str) -> str:
        """Get standard disclaimer text by type."""
        return self.standard_disclaimers.get(disclaimer_type, "")
    
    def generate_account_number(self, bank_name: str) -> str:
        """Generate realistic account number for given bank."""
        template = self.get_bank_template(bank_name)
        
        # Generate random digits based on format
        import random
        account_format = template.account_number_format
        account_number = ""
        
        for char in account_format:
            if char == '#':
                account_number += str(random.randint(0, 9))
            else:
                account_number += char
        
        return account_number
    
    def generate_routing_number(self, bank_name: str) -> str:
        """Generate realistic routing number for given bank."""
        template = self.get_bank_template(bank_name)
        return template.routing_number_prefix
    
    def get_transaction_descriptions(self, transaction_type: str = 'business') -> List[str]:
        """Get realistic transaction descriptions by type."""
        
        business_credits = [
            "Customer Payment - Invoice #{}",
            "Sales Deposit",
            "Credit Card Processing Deposit", 
            "Wire Transfer In - Customer Payment",
            "ACH Credit - Customer Payment",
            "Cash Deposit",
            "Online Payment Received",
            "Check Deposit - Customer Payment"
        ]
        
        business_debits = [
            "Rent Payment - {} Properties",
            "Payroll Direct Deposit",
            "Utilities - {} Electric",
            "Office Supplies - {} Corp",
            "Insurance Payment - {} Insurance",
            "Marketing Expense - {} Advertising",
            "Equipment Purchase - {} Equipment",
            "Professional Services - {} CPA",
            "Loan Payment - {} Bank",
            "Credit Card Payment"
        ]
        
        personal_credits = [
            "Salary Direct Deposit",
            "Bonus Payment",
            "Interest Payment",
            "Dividend Payment",
            "Tax Refund",
            "Transfer In",
            "Check Deposit"
        ]
        
        personal_debits = [
            "Mortgage Payment",
            "Auto Loan Payment",
            "Credit Card Payment",
            "Utilities",
            "Grocery Store",
            "Gas Station",
            "Restaurant",
            "ATM Withdrawal",
            "Online Purchase"
        ]
        
        descriptions = {
            'business': {
                'credit': business_credits,
                'debit': business_debits
            },
            'personal': {
                'credit': personal_credits,
                'debit': personal_debits
            }
        }
        
        return descriptions.get(transaction_type, descriptions['business'])