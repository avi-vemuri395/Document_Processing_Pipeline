"""
Bank-specific statement generators for creating realistic bank statements
that mimic the format and styling of major financial institutions.
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
import uuid

import pandas as pd
from faker import Faker
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.lib.colors import Color, black, blue, darkblue, grey, lightgrey, red, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Frame, PageTemplate, BaseDocTemplate
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from .document_templates import DocumentTemplates


class BankStatementGenerator:
    """
    Base class for bank statement generation with common functionality
    across different bank formats.
    """
    
    def __init__(self):
        """Initialize bank statement generator."""
        self.fake = Faker()
        self.templates = DocumentTemplates()
        self.page_width, self.page_height = letter
        
    def generate_statement(
        self,
        file_path: Path,
        bank_name: str,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date],
        format_type: str = 'pdf'
    ) -> None:
        """Generate bank statement in specified format."""
        if format_type == 'pdf':
            if bank_name.lower().replace(' ', '_') == 'chase':
                self._generate_chase_statement_pdf(file_path, account_data, transactions, statement_period)
            elif bank_name.lower().replace(' ', '_') == 'bank_of_america':
                self._generate_boa_statement_pdf(file_path, account_data, transactions, statement_period)
            elif bank_name.lower().replace(' ', '_') == 'wells_fargo':
                self._generate_wells_fargo_statement_pdf(file_path, account_data, transactions, statement_period)
            else:
                # Default to Chase format for unknown banks
                self._generate_chase_statement_pdf(file_path, account_data, transactions, statement_period)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    def _generate_chase_statement_pdf(
        self,
        file_path: Path,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> None:
        """Generate Chase Bank statement PDF."""
        template = self.templates.get_bank_template('chase')
        
        # Create PDF document
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def chase_header_footer(canvas, doc):
            """Draw Chase-specific header and footer."""
            canvas.saveState()
            
            # Chase blue header with logo placeholder
            canvas.setFillColor(darkblue)
            canvas.rect(50, self.page_height - 120, self.page_width - 100, 70, fill=1)
            
            # Logo area
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawString(60, self.page_height - 80, "CHASE")
            canvas.setFont('Helvetica', 8)
            canvas.drawString(60, self.page_height - 95, "LOGO PLACEHOLDER")
            
            # Statement title
            canvas.setFont('Helvetica-Bold', 18)
            canvas.drawString(280, self.page_height - 75, "ACCOUNT STATEMENT")
            
            # Account info in header
            canvas.setFont('Helvetica', 10)
            canvas.drawString(400, self.page_height - 90, f"Statement Date: {statement_period[1].strftime('%m/%d/%Y')}")
            canvas.drawString(400, self.page_height - 105, f"Account: ****{account_data.get('account_number', '0000')[-4:]}")
            
            # Footer with Chase branding
            canvas.setFillColor(grey)
            canvas.setFont('Helvetica', 8)
            footer_text = (
                "Member FDIC • Equal Housing Lender • "
                "JPMorgan Chase Bank, N.A. • "
                f"Page {doc.page} • "
                "Questions? Call 1-800-CHASE24"
            )
            text_width = canvas.stringWidth(footer_text, 'Helvetica', 8)
            canvas.drawString((self.page_width - text_width) / 2, 40, footer_text)
            
            # Privacy notice
            canvas.setFont('Helvetica', 7)
            privacy_text = "Please retain this statement for your records. Report unauthorized transactions immediately."
            privacy_width = canvas.stringWidth(privacy_text, 'Helvetica', 7)
            canvas.drawString((self.page_width - privacy_width) / 2, 25, privacy_text)
            
            canvas.restoreState()
        
        # Create page template
        frame = Frame(
            50, 80,  # x, y
            self.page_width - 100,  # width
            self.page_height - 200,  # height
            leftPadding=10, bottomPadding=10,
            rightPadding=10, topPadding=10
        )
        
        template_obj = PageTemplate(
            id='chase_statement',
            frames=[frame],
            onPage=chase_header_footer
        )
        doc.addPageTemplates([template_obj])
        
        # Build content
        story = self._build_chase_content(account_data, transactions, statement_period)
        doc.build(story)
    
    def _generate_boa_statement_pdf(
        self,
        file_path: Path,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> None:
        """Generate Bank of America statement PDF."""
        template = self.templates.get_bank_template('bank_of_america')
        
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def boa_header_footer(canvas, doc):
            """Draw Bank of America header and footer."""
            canvas.saveState()
            
            # Bank of America red header
            canvas.setFillColor(red)
            canvas.rect(50, self.page_height - 130, self.page_width - 100, 80, fill=1)
            
            # Bank name
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(60, self.page_height - 85, "BANK OF AMERICA")
            canvas.setFont('Helvetica', 9)
            canvas.drawString(60, self.page_height - 100, "LOGO PLACEHOLDER")
            
            # Statement type
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawString(300, self.page_height - 75, "CHECKING ACCOUNT")
            canvas.drawString(300, self.page_height - 90, "STATEMENT")
            
            # Account details in header
            canvas.setFont('Helvetica', 9)
            canvas.drawString(450, self.page_height - 110, f"Statement Period:")
            canvas.drawString(450, self.page_height - 122, f"{statement_period[0].strftime('%m/%d/%Y')} -")
            canvas.drawString(450, self.page_height - 134, f"{statement_period[1].strftime('%m/%d/%Y')}")
            
            # Footer
            canvas.setFillColor(grey)
            canvas.setFont('Helvetica', 8)
            footer_text = (
                "Member FDIC • Equal Housing Lender • "
                "Bank of America, N.A. • "
                f"Page {doc.page} of [Total Pages]"
            )
            text_width = canvas.stringWidth(footer_text, 'Helvetica', 8)
            canvas.drawString((self.page_width - text_width) / 2, 45, footer_text)
            
            # Customer service
            canvas.setFont('Helvetica', 7)
            service_text = "24/7 Customer Service: 1-800-432-1000 • bankofamerica.com"
            service_width = canvas.stringWidth(service_text, 'Helvetica', 7)
            canvas.drawString((self.page_width - service_width) / 2, 30, service_text)
            
            canvas.restoreState()
        
        frame = Frame(
            50, 90,
            self.page_width - 100,
            self.page_height - 220,
            leftPadding=10, bottomPadding=10,
            rightPadding=10, topPadding=10
        )
        
        template_obj = PageTemplate(
            id='boa_statement',
            frames=[frame],
            onPage=boa_header_footer
        )
        doc.addPageTemplates([template_obj])
        
        story = self._build_boa_content(account_data, transactions, statement_period)
        doc.build(story)
    
    def _generate_wells_fargo_statement_pdf(
        self,
        file_path: Path,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> None:
        """Generate Wells Fargo statement PDF."""
        template = self.templates.get_bank_template('wells_fargo')
        
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def wells_fargo_header_footer(canvas, doc):
            """Draw Wells Fargo header and footer."""
            canvas.saveState()
            
            # Wells Fargo stagecoach red header
            canvas.setFillColor(red)
            canvas.rect(50, self.page_height - 125, self.page_width - 100, 75, fill=1)
            
            # Bank name with stagecoach reference
            canvas.setFillColor(white)
            canvas.setFont('Helvetica-Bold', 18)
            canvas.drawString(60, self.page_height - 80, "WELLS FARGO")
            canvas.setFont('Helvetica', 8)
            canvas.drawString(60, self.page_height - 95, "STAGECOACH LOGO")
            canvas.drawString(60, self.page_height - 105, "PLACEHOLDER")
            
            # Statement info
            canvas.setFont('Helvetica-Bold', 12)
            canvas.drawString(300, self.page_height - 70, "ACCOUNT STATEMENT")
            canvas.setFont('Helvetica', 10)
            canvas.drawString(300, self.page_height - 90, f"Statement Date: {statement_period[1].strftime('%B %d, %Y')}")
            
            # Account summary box in header
            canvas.setFillColor(white)
            canvas.rect(400, self.page_height - 118, 150, 60, fill=1, stroke=1)
            canvas.setFillColor(black)
            canvas.setFont('Helvetica-Bold', 9)
            canvas.drawString(405, self.page_height - 68, "ACCOUNT SUMMARY")
            canvas.setFont('Helvetica', 8)
            canvas.drawString(405, self.page_height - 80, f"Account: ****{account_data.get('account_number', '0000')[-4:]}")
            canvas.drawString(405, self.page_height - 92, f"Customer since: 2018")
            
            # Footer with Wells Fargo branding
            canvas.setFillColor(grey)
            canvas.setFont('Helvetica', 8)
            footer_text = (
                "Member FDIC • Wells Fargo Bank, N.A. • "
                f"Page {doc.page} • "
                "1-800-TO-WELLS (1-800-869-3557)"
            )
            text_width = canvas.stringWidth(footer_text, 'Helvetica', 8)
            canvas.drawString((self.page_width - text_width) / 2, 50, footer_text)
            
            # Security notice
            canvas.setFont('Helvetica', 7)
            security_text = "Report unauthorized transactions within 60 days. Visit wellsfargo.com for online banking."
            security_width = canvas.stringWidth(security_text, 'Helvetica', 7)
            canvas.drawString((self.page_width - security_width) / 2, 35, security_text)
            
            canvas.restoreState()
        
        frame = Frame(
            50, 95,
            self.page_width - 100,
            self.page_height - 220,
            leftPadding=10, bottomPadding=10,
            rightPadding=10, topPadding=10
        )
        
        template_obj = PageTemplate(
            id='wells_fargo_statement',
            frames=[frame],
            onPage=wells_fargo_header_footer
        )
        doc.addPageTemplates([template_obj])
        
        story = self._build_wells_fargo_content(account_data, transactions, statement_period)
        doc.build(story)
    
    def _build_chase_content(
        self,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> List:
        """Build Chase-specific statement content."""
        story = []
        styles = getSampleStyleSheet()
        
        # Account holder information
        story.append(Spacer(1, 20))
        
        # Customer info section
        customer_info = f"""
        <b>{account_data.get('account_holder', 'Business Name')}</b><br/>
        {account_data.get('business_address', '123 Business St')}<br/>
        {account_data.get('city_state_zip', 'City, ST 12345')}
        """
        story.append(Paragraph(customer_info, styles['Normal']))
        story.append(Spacer(1, 15))
        
        # Account summary in Chase style
        summary_title = Paragraph("<b>ACCOUNT SUMMARY</b>", styles['Heading2'])
        story.append(summary_title)
        
        beginning_balance = account_data.get('beginning_balance', 0)
        ending_balance = account_data.get('ending_balance', 0)
        total_deposits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_withdrawals = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        summary_data = [
            ['Beginning Balance on ' + statement_period[0].strftime('%m/%d/%Y'), f'${beginning_balance:,.2f}'],
            ['Deposits/Credits', f'${total_deposits:,.2f}'],
            ['Withdrawals/Debits', f'${total_withdrawals:,.2f}'],
            ['Ending Balance on ' + statement_period[1].strftime('%m/%d/%Y'), f'${ending_balance:,.2f}']
        ]
        
        summary_table = Table(summary_data, colWidths=[300, 150])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Transaction history
        transaction_title = Paragraph("<b>TRANSACTION HISTORY</b>", styles['Heading2'])
        story.append(transaction_title)
        story.append(Spacer(1, 10))
        
        # Build transaction table
        transaction_data = [['Date', 'Description', 'Amount', 'Balance']]
        running_balance = beginning_balance
        
        for txn in sorted(transactions, key=lambda x: x['date']):
            if txn['type'] == 'credit':
                running_balance += txn['amount']
                amount_str = f"${txn['amount']:,.2f}"
            else:
                running_balance -= txn['amount']
                amount_str = f"-${txn['amount']:,.2f}"
            
            # Format description for Chase style
            description = txn['description'][:50]
            if len(txn['description']) > 50:
                description += "..."
            
            transaction_data.append([
                txn['date'].strftime('%m/%d'),
                description,
                amount_str,
                f"${running_balance:,.2f}"
            ])
        
        transaction_table = Table(transaction_data, colWidths=[60, 280, 80, 80])
        transaction_table.setStyle(TableStyle([
            # Header styling
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 0), (-1, 0), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            
            # Borders and grid
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, lightgrey]),
        ]))
        story.append(transaction_table)
        
        return story
    
    def _build_boa_content(
        self,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> List:
        """Build Bank of America specific statement content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 20))
        
        # Account information box (BoA style)
        account_info_data = [
            ['Account Number:', f"****-****-{account_data.get('account_number', '0000')[-4:]}"],
            ['Account Type:', 'Business Checking'],
            ['Customer Since:', '2019'],
            ['Statement Period:', f"{statement_period[0].strftime('%m/%d/%Y')} to {statement_period[1].strftime('%m/%d/%Y')}"]
        ]
        
        account_info_table = Table(account_info_data, colWidths=[150, 200])
        account_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 2, red),
            ('BACKGROUND', (0, 0), (-1, -1), white),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(account_info_table)
        story.append(Spacer(1, 20))
        
        # Account Activity Summary (BoA specific layout)
        summary_title = Paragraph("<b>ACCOUNT ACTIVITY SUMMARY</b>", styles['Heading2'])
        story.append(summary_title)
        
        beginning_balance = account_data.get('beginning_balance', 0)
        ending_balance = account_data.get('ending_balance', 0)
        total_deposits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_withdrawals = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        # BoA uses a two-column layout for summary
        left_column_data = [
            ['Previous Balance', f'${beginning_balance:,.2f}'],
            ['Deposits and Credits', f'${total_deposits:,.2f}'],
            ['Electronic Deposits', f'${total_deposits * 0.7:,.2f}']
        ]
        
        right_column_data = [
            ['Withdrawals and Debits', f'${total_withdrawals:,.2f}'],
            ['Service Charges', '$0.00'],
            ['Current Balance', f'${ending_balance:,.2f}']
        ]
        
        # Create side-by-side tables
        left_table = Table(left_column_data, colWidths=[150, 100])
        right_table = Table(right_column_data, colWidths=[150, 100])
        
        for table in [left_table, right_table]:
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOX', (0, 0), (-1, -1), 1, black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
            ]))
        
        # Combine tables side by side
        combined_table = Table([[left_table, right_table]], colWidths=[250, 250])
        story.append(combined_table)
        story.append(Spacer(1, 20))
        
        # Transaction Details (BoA format with separate withdrawal/deposit columns)
        transaction_title = Paragraph("<b>TRANSACTION DETAILS</b>", styles['Heading2'])
        story.append(transaction_title)
        story.append(Spacer(1, 10))
        
        transaction_data = [['Date', 'Description', 'Withdrawals', 'Deposits', 'Balance']]
        running_balance = beginning_balance
        
        for txn in sorted(transactions, key=lambda x: x['date']):
            withdrawal_str = ""
            deposit_str = ""
            
            if txn['type'] == 'credit':
                running_balance += txn['amount']
                deposit_str = f"${txn['amount']:,.2f}"
            else:
                running_balance -= txn['amount']
                withdrawal_str = f"${txn['amount']:,.2f}"
            
            transaction_data.append([
                txn['date'].strftime('%m/%d'),
                txn['description'][:45],
                withdrawal_str,
                deposit_str,
                f"${running_balance:,.2f}"
            ])
        
        transaction_table = Table(transaction_data, colWidths=[50, 240, 70, 70, 70])
        transaction_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), red),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(transaction_table)
        
        return story
    
    def _build_wells_fargo_content(
        self,
        account_data: Dict[str, Any],
        transactions: List[Dict[str, Any]],
        statement_period: Tuple[date, date]
    ) -> List:
        """Build Wells Fargo specific statement content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 20))
        
        # Wells Fargo account overview box
        overview_data = [
            ['Account Name:', account_data.get('account_holder', 'Business Account')],
            ['Account Number:', f"{account_data.get('routing_number', '121000248')} {account_data.get('account_number', '0000000000')[-10:]}"],
            ['Statement Period:', f"{statement_period[0].strftime('%B %d, %Y')} through {statement_period[1].strftime('%B %d, %Y')}"]
        ]
        
        overview_table = Table(overview_data, colWidths=[120, 300])
        overview_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 2, black),
            ('BACKGROUND', (0, 0), (-1, -1), lightgrey),
        ]))
        story.append(overview_table)
        story.append(Spacer(1, 20))
        
        # Wells Fargo balance summary
        summary_title = Paragraph("<b>ACCOUNT BALANCE SUMMARY</b>", styles['Heading2'])
        story.append(summary_title)
        
        beginning_balance = account_data.get('beginning_balance', 0)
        ending_balance = account_data.get('ending_balance', 0)
        total_deposits = sum(t['amount'] for t in transactions if t['type'] == 'credit')
        total_withdrawals = sum(t['amount'] for t in transactions if t['type'] == 'debit')
        
        balance_data = [
            ['Previous Statement Balance', f'${beginning_balance:,.2f}'],
            ['Deposits and Other Additions', f'${total_deposits:,.2f}'],
            ['Withdrawals and Other Subtractions', f'${total_withdrawals:,.2f}'],
            ['Current Statement Balance', f'${ending_balance:,.2f}'],
            ['Available Balance*', f'${ending_balance + 5000:,.2f}']  # Assuming credit line
        ]
        
        balance_table = Table(balance_data, colWidths=[250, 120])
        balance_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 3), (-1, 4), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 3), (-1, 4), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(balance_table)
        story.append(Spacer(1, 10))
        
        # Available balance footnote
        footnote = Paragraph(
            "*Available Balance includes your Current Balance plus any unused portion of credit arrangements.",
            styles['Normal']
        )
        footnote.fontSize = 8
        story.append(footnote)
        story.append(Spacer(1, 20))
        
        # Account Activity (Wells Fargo format)
        activity_title = Paragraph("<b>ACCOUNT ACTIVITY</b>", styles['Heading2'])
        story.append(activity_title)
        story.append(Spacer(1, 10))
        
        # Wells Fargo uses check number column
        transaction_data = [['Check#', 'Date', 'Description of Transaction', 'Amount', 'Balance']]
        running_balance = beginning_balance
        check_number = 1001
        
        for txn in sorted(transactions, key=lambda x: x['date']):
            # Assign check numbers to debit transactions that look like checks
            check_num = ""
            if txn['type'] == 'debit' and any(keyword in txn['description'].lower() 
                                           for keyword in ['payment', 'check', 'withdrawal']):
                check_num = str(check_number)
                check_number += 1
            
            if txn['type'] == 'credit':
                running_balance += txn['amount']
                amount_str = f"${txn['amount']:,.2f}"
            else:
                running_balance -= txn['amount']
                amount_str = f"-${txn['amount']:,.2f}"
            
            transaction_data.append([
                check_num,
                txn['date'].strftime('%m/%d'),
                txn['description'][:40],
                amount_str,
                f"${running_balance:,.2f}"
            ])
        
        transaction_table = Table(transaction_data, colWidths=[50, 50, 240, 80, 80])
        transaction_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), red),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Check number column
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Date column
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Description column
            ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),  # Amount and balance columns
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(transaction_table)
        
        return story