"""
Realistic document generator for creating documents that mimic real bank statements, 
tax returns, and financial statements with proper formatting and layouts.

This module generates documents that look like they came from real institutions
but contain synthetic test data.
"""

import io
import json
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

import pandas as pd
from faker import Faker
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import black, blue, red, grey
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    Frame, PageTemplate, BaseDocTemplate
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors

from .document_templates import DocumentTemplates


class RealisticDocumentGenerator:
    """
    Generator for creating realistic-looking financial documents with proper
    formatting, headers, footers, and institutional branding placeholders.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the realistic document generator."""
        self.config = config or {}
        self.fake = Faker()
        self.templates = DocumentTemplates()
        
        # Standard document dimensions and styles
        self.page_width, self.page_height = letter
        self.margin = 72  # 1 inch margins
        self.styles = getSampleStyleSheet()
        
        # Custom styles for financial documents
        self._setup_document_styles()
    
    def _setup_document_styles(self):
        """Setup custom styles for financial documents."""
        # Header style
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading1'],
            fontSize=14,
            fontName='Helvetica-Bold',
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Bank name style
        self.bank_name_style = ParagraphStyle(
            'BankName',
            parent=self.styles['Title'],
            fontSize=18,
            fontName='Helvetica-Bold',
            textColor=colors.darkblue,
            spaceAfter=6
        )
        
        # Account info style
        self.account_info_style = ParagraphStyle(
            'AccountInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica',
            spaceAfter=4
        )
        
        # Disclaimer style
        self.disclaimer_style = ParagraphStyle(
            'Disclaimer',
            parent=self.styles['Normal'],
            fontSize=8,
            fontName='Helvetica',
            textColor=colors.grey,
            alignment=TA_CENTER
        )
    
    def generate_bank_statement_pdf(
        self,
        file_path: Path,
        bank_name: str,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> None:
        """Generate a realistic bank statement PDF."""
        # Create PDF document
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        # Create custom page template with header and footer
        def header_footer(canvas, doc):
            """Draw header and footer on each page."""
            # Header
            canvas.saveState()
            
            # Bank logo placeholder
            canvas.setFillColor(colors.darkblue)
            canvas.rect(72, self.page_height - 100, 150, 40, fill=1)
            canvas.setFillColor(colors.white)
            canvas.setFont('Helvetica-Bold', 12)
            canvas.drawString(78, self.page_height - 85, f"{bank_name.upper()}")
            canvas.drawString(78, self.page_height - 96, "LOGO PLACEHOLDER")
            
            # Statement title
            canvas.setFillColor(colors.black)
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(250, self.page_height - 75, "ACCOUNT STATEMENT")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.grey)
            footer_text = f"Member FDIC • Equal Housing Lender • {bank_name} • Page {doc.page}"
            canvas.drawCentredString(self.page_width / 2, 50, footer_text)
            
            # Disclaimer
            disclaimer = (
                "This statement is provided for informational purposes. Please retain for your records. "
                "Call customer service for questions or to report unauthorized transactions."
            )
            canvas.drawCentredString(self.page_width / 2, 30, disclaimer)
            
            canvas.restoreState()
        
        # Create page template
        frame = Frame(
            self.margin, self.margin + 50,  # x, y (leaving space for footer)
            self.page_width - 2 * self.margin,  # width
            self.page_height - 200,  # height (leaving space for header)
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='bank_statement',
            frames=[frame],
            onPage=header_footer
        )
        doc.addPageTemplates([template])
        
        # Build document content
        story = []
        
        # Account information section
        story.append(Spacer(1, 30))  # Space after header
        
        account_info_data = [
            ['Account Holder:', account_data['account_holder']],
            ['Account Number:', f"****{account_data['account_number'][-4:]}"],
            ['Routing Number:', account_data['routing_number']],
            ['Statement Period:', f"{statement_period[0].strftime('%m/%d/%Y')} - {statement_period[1].strftime('%m/%d/%Y')}"],
            ['Statement Date:', statement_period[1].strftime('%m/%d/%Y')]
        ]
        
        account_table = Table(account_info_data, colWidths=[120, 200])
        account_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(account_table)
        story.append(Spacer(1, 20))
        
        # Account summary
        beginning_balance = account_data.get('beginning_balance', 0)
        ending_balance = account_data.get('ending_balance', 0)
        total_deposits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_withdrawals = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        summary_data = [
            ['ACCOUNT SUMMARY', '', ''],
            ['Beginning Balance', f"${beginning_balance:,.2f}", ''],
            ['Total Deposits/Credits', f"${total_deposits:,.2f}", f"({len([t for t in transactions if t['type'] == 'credit'])} items)"],
            ['Total Withdrawals/Debits', f"-${total_withdrawals:,.2f}", f"({len([t for t in transactions if t['type'] == 'debit'])} items)"],
            ['Ending Balance', f"${ending_balance:,.2f}", '']
        ]
        
        summary_table = Table(summary_data, colWidths=[150, 100, 100])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Transaction details
        story.append(Paragraph("TRANSACTION DETAILS", self.header_style))
        story.append(Spacer(1, 10))
        
        # Prepare transaction data for table
        transaction_data = [['Date', 'Description', 'Amount', 'Balance']]
        running_balance = beginning_balance
        
        for txn in sorted(transactions, key=lambda x: x['date']):
            if txn['type'] == 'credit':
                running_balance += txn['amount']
                amount_str = f"${txn['amount']:,.2f}"
            else:
                running_balance -= txn['amount']
                amount_str = f"-${txn['amount']:,.2f}"
            
            transaction_data.append([
                txn['date'].strftime('%m/%d/%Y'),
                txn['description'][:40] + ('...' if len(txn['description']) > 40 else ''),
                amount_str,
                f"${running_balance:,.2f}"
            ])
        
        # Create transaction table
        transaction_table = Table(transaction_data, colWidths=[80, 250, 80, 80])
        transaction_table.setStyle(TableStyle([
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # Date column
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),  # Description column
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), # Amount and balance columns
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        story.append(transaction_table)
        
        # Build the PDF
        doc.build(story)
    
    def generate_tax_return_pdf(
        self,
        file_path: Path,
        form_type: str,  # '1120', '1120S', '1040_schedule_c'
        business_data: Dict[str, Any],
        tax_year: int
    ) -> None:
        """Generate a realistic tax return PDF."""
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # IRS Form header
        story.append(Paragraph(f"Form {form_type}", self.bank_name_style))
        story.append(Paragraph(
            self._get_form_title(form_type),
            self.header_style
        ))
        story.append(Paragraph(
            f"Department of the Treasury - Internal Revenue Service<br/>Tax Year {tax_year}",
            self.account_info_style
        ))
        story.append(Spacer(1, 20))
        
        # Form content based on type
        if form_type == '1120':
            story.extend(self._generate_form_1120_content(business_data, tax_year))
        elif form_type == '1120S':
            story.extend(self._generate_form_1120s_content(business_data, tax_year))
        elif form_type == '1040_schedule_c':
            story.extend(self._generate_schedule_c_content(business_data, tax_year))
        
        # IRS footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(
            "For Paperwork Reduction Act Notice, see separate instructions.",
            self.disclaimer_style
        ))
        
        doc.build(story)
    
    def generate_personal_financial_statement_pdf(
        self,
        file_path: Path,
        pfs_data: Dict[str, Any],
        owner_info: Dict[str, Any]
    ) -> None:
        """Generate SBA Form 413 - Personal Financial Statement PDF."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def pfs_header_footer(canvas, doc):
            """Draw header and footer for PFS."""
            canvas.saveState()
            
            # Header
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 50, 
                                  "SBA FORM 413")
            canvas.drawCentredString(self.page_width / 2, self.page_height - 70,
                                  "PERSONAL FINANCIAL STATEMENT")
            
            canvas.setFont('Helvetica', 10)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 85,
                                  "U.S. Small Business Administration")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.grey)
            canvas.drawCentredString(self.page_width / 2, 30,
                                  f"SBA Form 413 (Rev. 01-2021) • Page {doc.page}")
            
            canvas.restoreState()
        
        # Create frame
        frame = Frame(
            self.margin, self.margin + 30,
            self.page_width - 2 * self.margin,
            self.page_height - 150,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='pfs',
            frames=[frame],
            onPage=pfs_header_footer
        )
        doc.addPageTemplates([template])
        
        story = []
        
        # Personal information
        story.append(Spacer(1, 30))
        story.append(Paragraph("PERSONAL INFORMATION", self.header_style))
        
        personal_info_data = [
            ['Name:', owner_info.get('name', ''), 'SSN:', owner_info.get('ssn', '')],
            ['Address:', owner_info.get('address', {}).get('street', ''), 'Phone:', owner_info.get('phone', '')],
            ['City, State, Zip:', f"{owner_info.get('address', {}).get('city', '')}, {owner_info.get('address', {}).get('state', '')} {owner_info.get('address', {}).get('zip_code', '')}", 'Email:', owner_info.get('email', '')]
        ]
        
        personal_table = Table(personal_info_data, colWidths=[80, 150, 80, 150])
        personal_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(personal_table)
        story.append(Spacer(1, 20))
        
        # Assets section
        story.append(Paragraph("ASSETS", self.header_style))
        assets_data = self._format_pfs_assets_for_table(pfs_data.get('assets', {}))
        assets_table = Table(assets_data, colWidths=[300, 150])
        assets_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(assets_table)
        story.append(Spacer(1, 20))
        
        # Liabilities section
        story.append(Paragraph("LIABILITIES", self.header_style))
        liabilities_data = self._format_pfs_liabilities_for_table(pfs_data.get('liabilities', {}))
        liabilities_table = Table(liabilities_data, colWidths=[300, 150])
        liabilities_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(liabilities_table)
        story.append(Spacer(1, 20))
        
        # Net Worth calculation
        net_worth_data = [
            ['TOTAL ASSETS', f"${pfs_data.get('total_assets', 0):,.2f}"],
            ['TOTAL LIABILITIES', f"${pfs_data.get('total_liabilities', 0):,.2f}"],
            ['NET WORTH', f"${pfs_data.get('net_worth', 0):,.2f}"]
        ]
        net_worth_table = Table(net_worth_data, colWidths=[300, 150])
        net_worth_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
        ]))
        story.append(net_worth_table)
        
        doc.build(story)
    
    def generate_business_financial_statement_pdf(
        self,
        file_path: Path,
        statement_type: str,  # 'balance_sheet', 'income_statement', 'cash_flow'
        financial_data: Dict[str, Any],
        business_info: Dict[str, Any]
    ) -> None:
        """Generate business financial statement PDF."""
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Header
        story.append(Paragraph(business_info.get('name', 'Business Name'), self.bank_name_style))
        story.append(Paragraph(
            self._get_statement_title(statement_type),
            self.header_style
        ))
        story.append(Paragraph(
            f"For the Year Ended {datetime.now().strftime('%B %d, %Y')}",
            self.account_info_style
        ))
        story.append(Spacer(1, 20))
        
        # Statement content based on type
        if statement_type == 'balance_sheet':
            story.extend(self._generate_balance_sheet_content(financial_data))
        elif statement_type == 'income_statement':
            story.extend(self._generate_income_statement_content(financial_data))
        elif statement_type == 'cash_flow':
            story.extend(self._generate_cash_flow_content(financial_data))
        
        doc.build(story)
    
    def generate_debt_schedule_pdf(
        self,
        file_path: Path,
        debt_data: List[Dict[str, Any]],
        business_info: Dict[str, Any]
    ) -> None:
        """Generate business debt schedule PDF."""
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Header
        story.append(Paragraph(business_info.get('name', 'Business Name'), self.bank_name_style))
        story.append(Paragraph("BUSINESS DEBT SCHEDULE", self.header_style))
        story.append(Paragraph(
            f"As of {datetime.now().strftime('%B %d, %Y')}",
            self.account_info_style
        ))
        story.append(Spacer(1, 20))
        
        # Debt schedule table
        debt_schedule_data = [
            ['Creditor', 'Original Amount', 'Current Balance', 'Monthly Payment', 'Interest Rate', 'Maturity Date']
        ]
        
        total_original = 0
        total_current = 0
        total_monthly = 0
        
        for debt in debt_data:
            debt_schedule_data.append([
                debt.get('creditor_name', '')[:25],
                f"${debt.get('original_amount', 0):,.2f}",
                f"${debt.get('current_balance', 0):,.2f}",
                f"${debt.get('monthly_payment', 0):,.2f}",
                f"{debt.get('interest_rate', 0):.2f}%",
                debt.get('maturity_date', '')
            ])
            total_original += debt.get('original_amount', 0)
            total_current += debt.get('current_balance', 0)
            total_monthly += debt.get('monthly_payment', 0)
        
        # Add totals row
        debt_schedule_data.append([
            'TOTALS',
            f"${total_original:,.2f}",
            f"${total_current:,.2f}",
            f"${total_monthly:,.2f}",
            '',
            ''
        ])
        
        debt_table = Table(debt_schedule_data, colWidths=[100, 80, 80, 80, 60, 80])
        debt_table.setStyle(TableStyle([
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            
            # Totals row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightblue),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(debt_table)
        
        doc.build(story)
    
    # Helper methods for formatting and content generation
    
    def _get_form_title(self, form_type: str) -> str:
        """Get the title for tax forms."""
        titles = {
            '1120': 'U.S. Corporation Income Tax Return',
            '1120S': 'U.S. Income Tax Return for an S Corporation',
            '1040_schedule_c': 'Schedule C - Profit or Loss From Business'
        }
        return titles.get(form_type, 'Tax Return')
    
    def _get_statement_title(self, statement_type: str) -> str:
        """Get the title for financial statements."""
        titles = {
            'balance_sheet': 'BALANCE SHEET',
            'income_statement': 'INCOME STATEMENT',
            'cash_flow': 'STATEMENT OF CASH FLOWS'
        }
        return titles.get(statement_type, 'FINANCIAL STATEMENT')
    
    def _generate_form_1120_content(self, business_data: Dict[str, Any], tax_year: int) -> List:
        """Generate Form 1120 content."""
        content = []
        
        # Business identification
        business_info_data = [
            ['Business Name:', business_data.get('name', '')],
            ['EIN:', business_data.get('ein', '')],
            ['Address:', business_data.get('address', {}).get('street', '')],
            ['City, State, ZIP:', f"{business_data.get('address', {}).get('city', '')}, {business_data.get('address', {}).get('state', '')} {business_data.get('address', {}).get('zip_code', '')}"]
        ]
        
        business_table = Table(business_info_data, colWidths=[120, 300])
        business_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        content.append(business_table)
        content.append(Spacer(1, 20))
        
        # Income section
        content.append(Paragraph("INCOME", self.header_style))
        
        revenue = business_data.get('annual_revenue', 0)
        net_income = business_data.get('net_income', 0)
        expenses = revenue - net_income
        
        income_data = [
            ['1. Total receipts or sales', f"${revenue:,.2f}"],
            ['2. Cost of goods sold', f"${expenses * 0.6:,.2f}"],
            ['3. Gross profit (line 1 minus line 2)', f"${revenue - (expenses * 0.6):,.2f}"],
            ['4. Total deductions', f"${expenses * 0.4:,.2f}"],
            ['30. Taxable income (line 3 minus line 4)', f"${net_income:,.2f}"],
            ['31. Total tax', f"${net_income * 0.21:,.2f}"]  # 21% corporate rate
        ]
        
        income_table = Table(income_data, colWidths=[300, 120])
        income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        content.append(income_table)
        
        return content
    
    def _generate_form_1120s_content(self, business_data: Dict[str, Any], tax_year: int) -> List:
        """Generate Form 1120S content."""
        # Similar to 1120 but for S-Corporation
        return self._generate_form_1120_content(business_data, tax_year)
    
    def _generate_schedule_c_content(self, business_data: Dict[str, Any], tax_year: int) -> List:
        """Generate Schedule C content."""
        content = []
        
        # Business information
        content.append(Paragraph("BUSINESS INFORMATION", self.header_style))
        
        business_info_data = [
            ['Business name:', business_data.get('name', '')],
            ['Principal business:', business_data.get('type', '')],
            ['Business address:', business_data.get('address', {}).get('street', '')],
            ['EIN:', business_data.get('ein', '')]
        ]
        
        business_table = Table(business_info_data, colWidths=[120, 300])
        business_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        content.append(business_table)
        content.append(Spacer(1, 20))
        
        # Income and expenses
        content.append(Paragraph("INCOME AND EXPENSES", self.header_style))
        
        revenue = business_data.get('annual_revenue', 0)
        net_income = business_data.get('net_income', 0)
        expenses = revenue - net_income
        
        schedule_c_data = [
            ['1. Gross receipts or sales', f"${revenue:,.2f}"],
            ['4. Cost of goods sold', f"${expenses * 0.5:,.2f}"],
            ['5. Gross profit (line 1 minus line 4)', f"${revenue - (expenses * 0.5):,.2f}"],
            ['28. Total expenses', f"${expenses * 0.5:,.2f}"],
            ['31. Net profit or (loss)', f"${net_income:,.2f}"]
        ]
        
        schedule_c_table = Table(schedule_c_data, colWidths=[300, 120])
        schedule_c_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        content.append(schedule_c_table)
        
        return content
    
    def _format_pfs_assets_for_table(self, assets: Dict[str, Any]) -> List[List[str]]:
        """Format PFS assets data for table display."""
        data = []
        
        # Cash and cash equivalents
        if 'cash_and_cash_equivalents' in assets:
            cash_data = assets['cash_and_cash_equivalents']
            data.append(['Cash on hand', f"${cash_data.get('cash_on_hand', 0):,.2f}"])
            
            for account in cash_data.get('checking_accounts', []):
                data.append([f"Checking - {account.get('bank_name', '')}", f"${account.get('balance', 0):,.2f}"])
            
            for account in cash_data.get('savings_accounts', []):
                data.append([f"Savings - {account.get('bank_name', '')}", f"${account.get('balance', 0):,.2f}"])
        
        # Real estate
        if 'real_estate' in assets:
            for property in assets['real_estate']:
                data.append([f"Real Estate - {property.get('property_type', '')}", f"${property.get('market_value', 0):,.2f}"])
        
        # Securities
        if 'securities' in assets:
            securities = assets['securities']
            data.append(['Stocks and Bonds', f"${securities.get('mutual_funds', 0):,.2f}"])
            data.append(['401(k)/Retirement Accounts', f"${securities.get('retirement_accounts_401k', 0):,.2f}"])
        
        return data
    
    def _format_pfs_liabilities_for_table(self, liabilities: Dict[str, Any]) -> List[List[str]]:
        """Format PFS liabilities data for table display."""
        data = []
        
        # Credit cards
        if 'current_liabilities' in liabilities:
            current = liabilities['current_liabilities']
            for card in current.get('credit_cards', []):
                data.append([f"Credit Card - {card.get('creditor', '')}", f"${card.get('balance', 0):,.2f}"])
        
        # Long-term liabilities
        if 'long_term_liabilities' in liabilities:
            long_term = liabilities['long_term_liabilities']
            
            for mortgage in long_term.get('real_estate_mortgages', []):
                data.append([f"Mortgage - {mortgage.get('property', '')}", f"${mortgage.get('current_balance', 0):,.2f}"])
            
            for loan in long_term.get('vehicle_loans', []):
                data.append([f"Auto Loan - {loan.get('vehicle', '')}", f"${loan.get('current_balance', 0):,.2f}"])
        
        return data
    
    def _generate_balance_sheet_content(self, financial_data: Dict[str, Any]) -> List:
        """Generate balance sheet content."""
        content = []
        
        # Assets section
        content.append(Paragraph("ASSETS", self.header_style))
        
        # Current Assets
        current_assets_data = [
            ['Cash', f"${financial_data.get('cash', 50000):,.2f}"],
            ['Accounts Receivable', f"${financial_data.get('accounts_receivable', 75000):,.2f}"],
            ['Inventory', f"${financial_data.get('inventory', 100000):,.2f}"],
            ['Total Current Assets', f"${financial_data.get('total_current_assets', 225000):,.2f}"]
        ]
        
        current_assets_table = Table(current_assets_data, colWidths=[300, 120])
        current_assets_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        content.append(current_assets_table)
        content.append(Spacer(1, 10))
        
        return content
    
    def _generate_income_statement_content(self, financial_data: Dict[str, Any]) -> List:
        """Generate income statement content."""
        content = []
        
        revenue = financial_data.get('revenue', 500000)
        cogs = financial_data.get('cost_of_goods_sold', revenue * 0.4)
        operating_expenses = financial_data.get('operating_expenses', revenue * 0.35)
        net_income = revenue - cogs - operating_expenses
        
        income_data = [
            ['Revenue', f"${revenue:,.2f}"],
            ['Cost of Goods Sold', f"${cogs:,.2f}"],
            ['Gross Profit', f"${revenue - cogs:,.2f}"],
            ['Operating Expenses', f"${operating_expenses:,.2f}"],
            ['Net Income', f"${net_income:,.2f}"]
        ]
        
        income_table = Table(income_data, colWidths=[300, 120])
        income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        content.append(income_table)
        
        return content
    
    def _generate_cash_flow_content(self, financial_data: Dict[str, Any]) -> List:
        """Generate cash flow statement content."""
        content = []
        
        net_income = financial_data.get('net_income', 75000)
        operating_cf = net_income * 1.2
        investing_cf = -50000
        financing_cf = -25000
        net_cf = operating_cf + investing_cf + financing_cf
        
        cash_flow_data = [
            ['OPERATING ACTIVITIES', ''],
            ['Net Income', f"${net_income:,.2f}"],
            ['Adjustments', f"${operating_cf - net_income:,.2f}"],
            ['Net Cash from Operating Activities', f"${operating_cf:,.2f}"],
            ['', ''],
            ['INVESTING ACTIVITIES', ''],
            ['Equipment Purchases', f"${investing_cf:,.2f}"],
            ['Net Cash from Investing Activities', f"${investing_cf:,.2f}"],
            ['', ''],
            ['FINANCING ACTIVITIES', ''],
            ['Loan Payments', f"${financing_cf:,.2f}"],
            ['Net Cash from Financing Activities', f"${financing_cf:,.2f}"],
            ['', ''],
            ['NET CHANGE IN CASH', f"${net_cf:,.2f}"]
        ]
        
        cash_flow_table = Table(cash_flow_data, colWidths=[300, 120])
        cash_flow_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        content.append(cash_flow_table)
        
        return content