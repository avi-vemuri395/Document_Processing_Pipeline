"""
Business Financial Statement generators for creating realistic Balance Sheets,
Income Statements (P&L), and Cash Flow Statements with proper formatting.
"""

from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

from faker import Faker
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import Color, black, blue, darkblue, grey, lightgrey, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Frame, PageTemplate, BaseDocTemplate
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from .document_templates import DocumentTemplates


class BusinessFinancialStatementGenerator:
    """
    Generator for creating realistic business financial statements including
    Balance Sheets, Income Statements (P&L), and Cash Flow Statements.
    """
    
    def __init__(self):
        """Initialize Business Financial Statement generator."""
        self.fake = Faker()
        self.templates = DocumentTemplates()
        self.page_width, self.page_height = letter
        
    def generate_financial_statement(
        self,
        file_path: Path,
        statement_type: str,
        financial_data: Dict[str, Any],
        business_info: Dict[str, Any],
        statement_date: date = None
    ) -> None:
        """Generate business financial statement based on type."""
        if statement_date is None:
            statement_date = date.today()
            
        if statement_type == 'balance_sheet':
            self._generate_balance_sheet(file_path, financial_data, business_info, statement_date)
        elif statement_type == 'income_statement':
            self._generate_income_statement(file_path, financial_data, business_info, statement_date)
        elif statement_type == 'cash_flow':
            self._generate_cash_flow_statement(file_path, financial_data, business_info, statement_date)
        else:
            raise ValueError(f"Unsupported statement type: {statement_type}")
    
    def _generate_balance_sheet(
        self,
        file_path: Path,
        financial_data: Dict[str, Any],
        business_info: Dict[str, Any],
        statement_date: date
    ) -> None:
        """Generate Balance Sheet PDF."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def balance_sheet_header_footer(canvas, doc):
            """Draw Balance Sheet header and footer."""
            canvas.saveState()
            
            # Company logo placeholder
            canvas.setFillColor(darkblue)
            canvas.rect(72, self.page_height - 80, 120, 30, fill=1)
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 10)
            canvas.drawCentredString(132, self.page_height - 70, "COMPANY")
            canvas.drawCentredString(132, self.page_height - 60, "LOGO")
            
            # Company name and statement title
            canvas.setFillColor(black)
            canvas.setFont('Helvetica-Bold', 16)
            company_name = business_info.get('name', 'Sample Corporation')
            canvas.drawCentredString(self.page_width / 2, self.page_height - 50, company_name.upper())
            
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 70, "BALANCE SHEET")
            
            canvas.setFont('Helvetica', 11)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 85, 
                                  f"As of {statement_date.strftime('%B %d, %Y')}")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(grey)
            footer_text = f"Prepared by: Management • {datetime.now().strftime('%B %Y')}"
            canvas.drawCentredString(self.page_width / 2, 30, footer_text)
            
            canvas.restoreState()
        
        frame = Frame(
            72, 70,
            self.page_width - 144,
            self.page_height - 170,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='balance_sheet',
            frames=[frame],
            onPage=balance_sheet_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_balance_sheet_content(financial_data)
        doc.build(story)
    
    def _generate_income_statement(
        self,
        file_path: Path,
        financial_data: Dict[str, Any],
        business_info: Dict[str, Any],
        statement_date: date
    ) -> None:
        """Generate Income Statement (P&L) PDF."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def income_statement_header_footer(canvas, doc):
            """Draw Income Statement header and footer."""
            canvas.saveState()
            
            # Company logo placeholder
            canvas.setFillColor(darkblue)
            canvas.rect(72, self.page_height - 80, 120, 30, fill=1)
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 10)
            canvas.drawCentredString(132, self.page_height - 70, "COMPANY")
            canvas.drawCentredString(132, self.page_height - 60, "LOGO")
            
            # Company name and statement title
            canvas.setFillColor(black)
            canvas.setFont('Helvetica-Bold', 16)
            company_name = business_info.get('name', 'Sample Corporation')
            canvas.drawCentredString(self.page_width / 2, self.page_height - 50, company_name.upper())
            
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 70, "INCOME STATEMENT")
            
            canvas.setFont('Helvetica', 11)
            year_end = statement_date.strftime('%B %d, %Y')
            canvas.drawCentredString(self.page_width / 2, self.page_height - 85, 
                                  f"For the Year Ended {year_end}")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(grey)
            footer_text = f"See accompanying notes to financial statements"
            canvas.drawCentredString(self.page_width / 2, 30, footer_text)
            
            canvas.restoreState()
        
        frame = Frame(
            72, 70,
            self.page_width - 144,
            self.page_height - 170,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='income_statement',
            frames=[frame],
            onPage=income_statement_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_income_statement_content(financial_data)
        doc.build(story)
    
    def _generate_cash_flow_statement(
        self,
        file_path: Path,
        financial_data: Dict[str, Any],
        business_info: Dict[str, Any],
        statement_date: date
    ) -> None:
        """Generate Cash Flow Statement PDF."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def cash_flow_header_footer(canvas, doc):
            """Draw Cash Flow Statement header and footer."""
            canvas.saveState()
            
            # Company logo placeholder
            canvas.setFillColor(darkblue)
            canvas.rect(72, self.page_height - 80, 120, 30, fill=1)
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 10)
            canvas.drawCentredString(132, self.page_height - 70, "COMPANY")
            canvas.drawCentredString(132, self.page_height - 60, "LOGO")
            
            # Company name and statement title
            canvas.setFillColor(black)
            canvas.setFont('Helvetica-Bold', 16)
            company_name = business_info.get('name', 'Sample Corporation')
            canvas.drawCentredString(self.page_width / 2, self.page_height - 50, company_name.upper())
            
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 70, "STATEMENT OF CASH FLOWS")
            
            canvas.setFont('Helvetica', 11)
            year_end = statement_date.strftime('%B %d, %Y')
            canvas.drawCentredString(self.page_width / 2, self.page_height - 85, 
                                  f"For the Year Ended {year_end}")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(grey)
            footer_text = f"See accompanying notes to financial statements"
            canvas.drawCentredString(self.page_width / 2, 30, footer_text)
            
            canvas.restoreState()
        
        frame = Frame(
            72, 70,
            self.page_width - 144,
            self.page_height - 170,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='cash_flow_statement',
            frames=[frame],
            onPage=cash_flow_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_cash_flow_statement_content(financial_data)
        doc.build(story)
    
    def _build_balance_sheet_content(self, financial_data: Dict[str, Any]) -> List:
        """Build Balance Sheet content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 30))
        
        # Calculate financial figures based on business data
        annual_revenue = financial_data.get('annual_revenue', 500000)
        
        # ASSETS
        cash = annual_revenue * 0.1
        accounts_receivable = annual_revenue * 0.15
        inventory = annual_revenue * 0.2
        prepaid_expenses = annual_revenue * 0.02
        total_current_assets = cash + accounts_receivable + inventory + prepaid_expenses
        
        equipment = annual_revenue * 0.3
        furniture_fixtures = annual_revenue * 0.05
        vehicles = annual_revenue * 0.08
        accumulated_depreciation = -(annual_revenue * 0.1)
        total_fixed_assets = equipment + furniture_fixtures + vehicles + accumulated_depreciation
        
        intangible_assets = annual_revenue * 0.02
        investments = annual_revenue * 0.05
        other_assets = annual_revenue * 0.01
        total_other_assets = intangible_assets + investments + other_assets
        
        total_assets = total_current_assets + total_fixed_assets + total_other_assets
        
        # ASSETS SECTION
        story.append(Paragraph("<b>ASSETS</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        assets_data = [
            ['CURRENT ASSETS:', ''],
            ['  Cash and Cash Equivalents', f'${cash:,.2f}'],
            ['  Accounts Receivable', f'${accounts_receivable:,.2f}'],
            ['  Inventory', f'${inventory:,.2f}'],
            ['  Prepaid Expenses', f'${prepaid_expenses:,.2f}'],
            ['    Total Current Assets', f'${total_current_assets:,.2f}'],
            ['', ''],
            ['PROPERTY, PLANT & EQUIPMENT:', ''],
            ['  Equipment', f'${equipment:,.2f}'],
            ['  Furniture and Fixtures', f'${furniture_fixtures:,.2f}'],
            ['  Vehicles', f'${vehicles:,.2f}'],
            ['  Less: Accumulated Depreciation', f'${accumulated_depreciation:,.2f}'],
            ['    Total Property, Plant & Equipment', f'${total_fixed_assets:,.2f}'],
            ['', ''],
            ['OTHER ASSETS:', ''],
            ['  Intangible Assets', f'${intangible_assets:,.2f}'],
            ['  Investments', f'${investments:,.2f}'],
            ['  Other Assets', f'${other_assets:,.2f}'],
            ['    Total Other Assets', f'${total_other_assets:,.2f}'],
            ['', ''],
            ['TOTAL ASSETS', f'${total_assets:,.2f}']
        ]
        
        assets_table = Table(assets_data, colWidths=[350, 120])
        assets_table.setStyle(TableStyle([
            # Section headers
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 7), (0, 7), 'Helvetica-Bold'),
            ('FONTNAME', (0, 14), (0, 14), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            
            # Subtotals
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTNAME', (0, 12), (-1, 12), 'Helvetica-Bold'),
            ('FONTNAME', (0, 17), (-1, 17), 'Helvetica-Bold'),
            
            # Grand total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
            
            # Alignment
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(assets_table)
        story.append(Spacer(1, 20))
        
        # LIABILITIES AND EQUITY
        story.append(Paragraph("<b>LIABILITIES AND SHAREHOLDERS' EQUITY</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        # Calculate liabilities
        accounts_payable = annual_revenue * 0.12
        accrued_expenses = annual_revenue * 0.08
        short_term_debt = annual_revenue * 0.05
        current_portion_lt_debt = annual_revenue * 0.03
        total_current_liabilities = accounts_payable + accrued_expenses + short_term_debt + current_portion_lt_debt
        
        long_term_debt = annual_revenue * 0.15
        notes_payable = annual_revenue * 0.08
        other_lt_liabilities = annual_revenue * 0.02
        total_long_term_liabilities = long_term_debt + notes_payable + other_lt_liabilities
        
        total_liabilities = total_current_liabilities + total_long_term_liabilities
        
        # Calculate equity
        common_stock = annual_revenue * 0.1
        retained_earnings = total_assets - total_liabilities - common_stock
        total_equity = common_stock + retained_earnings
        
        total_liabilities_equity = total_liabilities + total_equity
        
        liabilities_equity_data = [
            ['CURRENT LIABILITIES:', ''],
            ['  Accounts Payable', f'${accounts_payable:,.2f}'],
            ['  Accrued Expenses', f'${accrued_expenses:,.2f}'],
            ['  Short-term Debt', f'${short_term_debt:,.2f}'],
            ['  Current Portion of Long-term Debt', f'${current_portion_lt_debt:,.2f}'],
            ['    Total Current Liabilities', f'${total_current_liabilities:,.2f}'],
            ['', ''],
            ['LONG-TERM LIABILITIES:', ''],
            ['  Long-term Debt', f'${long_term_debt:,.2f}'],
            ['  Notes Payable', f'${notes_payable:,.2f}'],
            ['  Other Long-term Liabilities', f'${other_lt_liabilities:,.2f}'],
            ['    Total Long-term Liabilities', f'${total_long_term_liabilities:,.2f}'],
            ['', ''],
            ['    Total Liabilities', f'${total_liabilities:,.2f}'],
            ['', ''],
            ['SHAREHOLDERS\' EQUITY:', ''],
            ['  Common Stock', f'${common_stock:,.2f}'],
            ['  Retained Earnings', f'${retained_earnings:,.2f}'],
            ['    Total Shareholders\' Equity', f'${total_equity:,.2f}'],
            ['', ''],
            ['TOTAL LIABILITIES AND SHAREHOLDERS\' EQUITY', f'${total_liabilities_equity:,.2f}']
        ]
        
        liabilities_equity_table = Table(liabilities_equity_data, colWidths=[350, 120])
        liabilities_equity_table.setStyle(TableStyle([
            # Section headers
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 7), (0, 7), 'Helvetica-Bold'),
            ('FONTNAME', (0, 15), (0, 15), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            
            # Subtotals
            ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
            ('FONTNAME', (0, 11), (-1, 11), 'Helvetica-Bold'),
            ('FONTNAME', (0, 13), (-1, 13), 'Helvetica-Bold'),
            ('FONTNAME', (0, 18), (-1, 18), 'Helvetica-Bold'),
            
            # Grand total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
            
            # Alignment
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(liabilities_equity_table)
        
        return story
    
    def _build_income_statement_content(self, financial_data: Dict[str, Any]) -> List:
        """Build Income Statement content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 30))
        
        # Calculate income statement figures
        annual_revenue = financial_data.get('annual_revenue', 500000)
        gross_sales = annual_revenue * 1.02  # Slight gross-up
        returns_allowances = gross_sales * 0.02
        net_revenue = gross_sales - returns_allowances
        
        # Cost of Goods Sold
        beginning_inventory = annual_revenue * 0.15
        purchases = annual_revenue * 0.45
        direct_labor = annual_revenue * 0.12
        manufacturing_overhead = annual_revenue * 0.08
        ending_inventory = annual_revenue * 0.18
        cost_of_goods_sold = beginning_inventory + purchases + direct_labor + manufacturing_overhead - ending_inventory
        
        gross_profit = net_revenue - cost_of_goods_sold
        
        # Operating Expenses
        salaries_wages = annual_revenue * 0.15
        rent_expense = annual_revenue * 0.08
        utilities = annual_revenue * 0.02
        insurance = annual_revenue * 0.015
        depreciation = annual_revenue * 0.03
        marketing = annual_revenue * 0.025
        professional_services = annual_revenue * 0.01
        office_expenses = annual_revenue * 0.008
        travel_entertainment = annual_revenue * 0.005
        other_operating_expenses = annual_revenue * 0.02
        
        total_operating_expenses = (salaries_wages + rent_expense + utilities + insurance + 
                                  depreciation + marketing + professional_services + 
                                  office_expenses + travel_entertainment + other_operating_expenses)
        
        operating_income = gross_profit - total_operating_expenses
        
        # Other Income/Expenses
        interest_income = annual_revenue * 0.002
        interest_expense = annual_revenue * 0.015
        other_income = annual_revenue * 0.001
        other_expenses = annual_revenue * 0.003
        
        total_other_income_expenses = interest_income - interest_expense + other_income - other_expenses
        
        income_before_taxes = operating_income + total_other_income_expenses
        income_tax_expense = income_before_taxes * 0.21  # 21% corporate tax rate
        net_income = income_before_taxes - income_tax_expense
        
        # REVENUE SECTION
        story.append(Paragraph("<b>REVENUE</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        revenue_data = [
            ['Gross Sales', f'${gross_sales:,.2f}'],
            ['Less: Returns and Allowances', f'${returns_allowances:,.2f}'],
            ['Net Revenue', f'${net_revenue:,.2f}']
        ]
        
        revenue_table = Table(revenue_data, colWidths=[350, 120])
        revenue_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(revenue_table)
        story.append(Spacer(1, 10))
        
        # COST OF GOODS SOLD SECTION
        story.append(Paragraph("<b>COST OF GOODS SOLD</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        cogs_data = [
            ['Beginning Inventory', f'${beginning_inventory:,.2f}'],
            ['Purchases', f'${purchases:,.2f}'],
            ['Direct Labor', f'${direct_labor:,.2f}'],
            ['Manufacturing Overhead', f'${manufacturing_overhead:,.2f}'],
            ['Less: Ending Inventory', f'${ending_inventory:,.2f}'],
            ['Total Cost of Goods Sold', f'${cost_of_goods_sold:,.2f}']
        ]
        
        cogs_table = Table(cogs_data, colWidths=[350, 120])
        cogs_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(cogs_table)
        story.append(Spacer(1, 10))
        
        # GROSS PROFIT
        gross_profit_data = [['GROSS PROFIT', f'${gross_profit:,.2f}']]
        gross_profit_table = Table(gross_profit_data, colWidths=[350, 120])
        gross_profit_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, black),
        ]))
        story.append(gross_profit_table)
        story.append(Spacer(1, 15))
        
        # OPERATING EXPENSES SECTION
        story.append(Paragraph("<b>OPERATING EXPENSES</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        operating_expenses_data = [
            ['Salaries and Wages', f'${salaries_wages:,.2f}'],
            ['Rent Expense', f'${rent_expense:,.2f}'],
            ['Utilities', f'${utilities:,.2f}'],
            ['Insurance', f'${insurance:,.2f}'],
            ['Depreciation', f'${depreciation:,.2f}'],
            ['Marketing and Advertising', f'${marketing:,.2f}'],
            ['Professional Services', f'${professional_services:,.2f}'],
            ['Office Expenses', f'${office_expenses:,.2f}'],
            ['Travel and Entertainment', f'${travel_entertainment:,.2f}'],
            ['Other Operating Expenses', f'${other_operating_expenses:,.2f}'],
            ['Total Operating Expenses', f'${total_operating_expenses:,.2f}']
        ]
        
        operating_expenses_table = Table(operating_expenses_data, colWidths=[350, 120])
        operating_expenses_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(operating_expenses_table)
        story.append(Spacer(1, 10))
        
        # OPERATING INCOME
        operating_income_data = [['OPERATING INCOME', f'${operating_income:,.2f}']]
        operating_income_table = Table(operating_income_data, colWidths=[350, 120])
        operating_income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, black),
        ]))
        story.append(operating_income_table)
        story.append(Spacer(1, 15))
        
        # OTHER INCOME (EXPENSES) SECTION
        story.append(Paragraph("<b>OTHER INCOME (EXPENSES)</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        other_income_data = [
            ['Interest Income', f'${interest_income:,.2f}'],
            ['Interest Expense', f'${interest_expense:,.2f}'],
            ['Other Income', f'${other_income:,.2f}'],
            ['Other Expenses', f'${other_expenses:,.2f}'],
            ['Total Other Income (Expenses)', f'${total_other_income_expenses:,.2f}']
        ]
        
        other_income_table = Table(other_income_data, colWidths=[350, 120])
        other_income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(other_income_table)
        story.append(Spacer(1, 15))
        
        # NET INCOME SECTION
        net_income_data = [
            ['Income Before Taxes', f'${income_before_taxes:,.2f}'],
            ['Income Tax Expense', f'${income_tax_expense:,.2f}'],
            ['NET INCOME', f'${net_income:,.2f}']
        ]
        
        net_income_table = Table(net_income_data, colWidths=[350, 120])
        net_income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(net_income_table)
        
        return story
    
    def _build_cash_flow_statement_content(self, financial_data: Dict[str, Any]) -> List:
        """Build Cash Flow Statement content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 30))
        
        # Calculate cash flow figures
        annual_revenue = financial_data.get('annual_revenue', 500000)
        net_income = annual_revenue * 0.12  # 12% net margin
        
        # Operating Activities adjustments
        depreciation = annual_revenue * 0.03
        amortization = annual_revenue * 0.005
        change_accounts_receivable = -(annual_revenue * 0.02)  # Increase in AR
        change_inventory = -(annual_revenue * 0.015)  # Increase in inventory
        change_prepaid = -(annual_revenue * 0.003)  # Increase in prepaid
        change_accounts_payable = annual_revenue * 0.01  # Increase in AP
        change_accrued_liabilities = annual_revenue * 0.008  # Increase in accrued
        
        net_cash_operating = (net_income + depreciation + amortization + 
                            change_accounts_receivable + change_inventory + 
                            change_prepaid + change_accounts_payable + change_accrued_liabilities)
        
        # Investing Activities
        equipment_purchases = -(annual_revenue * 0.08)
        investment_purchases = -(annual_revenue * 0.02)
        equipment_sales = annual_revenue * 0.005
        investment_sales = annual_revenue * 0.01
        
        net_cash_investing = equipment_purchases + investment_purchases + equipment_sales + investment_sales
        
        # Financing Activities
        debt_proceeds = annual_revenue * 0.05
        debt_payments = -(annual_revenue * 0.04)
        owner_contributions = annual_revenue * 0.02
        owner_distributions = -(annual_revenue * 0.03)
        credit_line_proceeds = annual_revenue * 0.01
        credit_line_payments = -(annual_revenue * 0.015)
        
        net_cash_financing = (debt_proceeds + debt_payments + owner_contributions + 
                            owner_distributions + credit_line_proceeds + credit_line_payments)
        
        net_change_cash = net_cash_operating + net_cash_investing + net_cash_financing
        beginning_cash = annual_revenue * 0.08
        ending_cash = beginning_cash + net_change_cash
        
        # OPERATING ACTIVITIES SECTION
        story.append(Paragraph("<b>CASH FLOWS FROM OPERATING ACTIVITIES</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        operating_data = [
            ['Net Income', f'${net_income:,.2f}'],
            ['Adjustments to reconcile net income to net cash:', ''],
            ['  Depreciation', f'${depreciation:,.2f}'],
            ['  Amortization', f'${amortization:,.2f}'],
            ['  (Increase) Decrease in Accounts Receivable', f'${change_accounts_receivable:,.2f}'],
            ['  (Increase) Decrease in Inventory', f'${change_inventory:,.2f}'],
            ['  (Increase) Decrease in Prepaid Expenses', f'${change_prepaid:,.2f}'],
            ['  Increase (Decrease) in Accounts Payable', f'${change_accounts_payable:,.2f}'],
            ['  Increase (Decrease) in Accrued Liabilities', f'${change_accrued_liabilities:,.2f}'],
            ['Net Cash Provided by Operating Activities', f'${net_cash_operating:,.2f}']
        ]
        
        operating_table = Table(operating_data, colWidths=[350, 120])
        operating_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(operating_table)
        story.append(Spacer(1, 15))
        
        # INVESTING ACTIVITIES SECTION
        story.append(Paragraph("<b>CASH FLOWS FROM INVESTING ACTIVITIES</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        investing_data = [
            ['Purchase of Equipment', f'${equipment_purchases:,.2f}'],
            ['Purchase of Investments', f'${investment_purchases:,.2f}'],
            ['Sale of Equipment', f'${equipment_sales:,.2f}'],
            ['Sale of Investments', f'${investment_sales:,.2f}'],
            ['Net Cash Used in Investing Activities', f'${net_cash_investing:,.2f}']
        ]
        
        investing_table = Table(investing_data, colWidths=[350, 120])
        investing_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(investing_table)
        story.append(Spacer(1, 15))
        
        # FINANCING ACTIVITIES SECTION
        story.append(Paragraph("<b>CASH FLOWS FROM FINANCING ACTIVITIES</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        financing_data = [
            ['Proceeds from Long-term Debt', f'${debt_proceeds:,.2f}'],
            ['Repayment of Long-term Debt', f'${debt_payments:,.2f}'],
            ['Owner Contributions', f'${owner_contributions:,.2f}'],
            ['Owner Distributions', f'${owner_distributions:,.2f}'],
            ['Proceeds from Line of Credit', f'${credit_line_proceeds:,.2f}'],
            ['Repayment of Line of Credit', f'${credit_line_payments:,.2f}'],
            ['Net Cash Provided by (Used in) Financing Activities', f'${net_cash_financing:,.2f}']
        ]
        
        financing_table = Table(financing_data, colWidths=[350, 120])
        financing_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(financing_table)
        story.append(Spacer(1, 15))
        
        # NET CHANGE IN CASH SECTION
        net_change_data = [
            ['Net Increase (Decrease) in Cash', f'${net_change_cash:,.2f}'],
            ['Cash at Beginning of Year', f'${beginning_cash:,.2f}'],
            ['CASH AT END OF YEAR', f'${ending_cash:,.2f}']
        ]
        
        net_change_table = Table(net_change_data, colWidths=[350, 120])
        net_change_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('BACKGROUND', (0, -1), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(net_change_table)
        
        return story