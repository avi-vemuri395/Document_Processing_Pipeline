"""
Business Debt Schedule generator for creating realistic debt schedules
with proper formatting and detailed creditor information.
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


class DebtScheduleGenerator:
    """
    Generator for creating realistic business debt schedules with detailed
    creditor information, payment terms, and collateral details.
    """
    
    def __init__(self):
        """Initialize Debt Schedule generator."""
        self.fake = Faker()
        self.templates = DocumentTemplates()
        self.page_width, self.page_height = letter
        
    def generate_debt_schedule(
        self,
        file_path: Path,
        debt_data: List[Dict[str, Any]],
        business_info: Dict[str, Any],
        statement_date: date = None
    ) -> None:
        """Generate Business Debt Schedule PDF."""
        if statement_date is None:
            statement_date = date.today()
            
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def debt_schedule_header_footer(canvas, doc):
            """Draw Debt Schedule header and footer."""
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
            canvas.drawCentredString(self.page_width / 2, self.page_height - 70, "BUSINESS DEBT SCHEDULE")
            
            canvas.setFont('Helvetica', 11)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 85, 
                                  f"As of {statement_date.strftime('%B %d, %Y')}")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(grey)
            footer_text = f"Confidential Business Information • Prepared {datetime.now().strftime('%B %Y')}"
            canvas.drawCentredString(self.page_width / 2, 30, footer_text)
            
            canvas.restoreState()
        
        frame = Frame(
            50, 70,
            self.page_width - 100,
            self.page_height - 170,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='debt_schedule',
            frames=[frame],
            onPage=debt_schedule_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_debt_schedule_content(debt_data, business_info, statement_date)
        doc.build(story)
    
    def _build_debt_schedule_content(
        self,
        debt_data: List[Dict[str, Any]],
        business_info: Dict[str, Any],
        statement_date: date
    ) -> List:
        """Build Debt Schedule content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 30))
        
        # DEBT SUMMARY OVERVIEW
        story.append(Paragraph("<b>DEBT SUMMARY OVERVIEW</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Calculate totals
        total_original = sum(debt.get('original_amount', 0) for debt in debt_data)
        total_current = sum(debt.get('current_balance', 0) for debt in debt_data)
        total_monthly = sum(debt.get('monthly_payment', 0) for debt in debt_data)
        
        # Calculate weighted average interest rate
        weighted_rate_sum = sum(
            debt.get('current_balance', 0) * debt.get('interest_rate', 0) / 100 
            for debt in debt_data if debt.get('current_balance', 0) > 0
        )
        avg_interest_rate = (weighted_rate_sum / total_current * 100) if total_current > 0 else 0
        
        # Calculate debt-to-income ratio (assuming annual revenue is available)
        annual_revenue = business_info.get('annual_revenue', 500000)
        debt_to_income_ratio = (total_monthly * 12 / annual_revenue * 100) if annual_revenue > 0 else 0
        
        summary_overview_data = [
            ['Total Outstanding Debt:', f'${total_current:,.2f}'],
            ['Total Monthly Payments:', f'${total_monthly:,.2f}'],
            ['Average Interest Rate:', f'{avg_interest_rate:.2f}%'],
            ['Annual Debt Service:', f'${total_monthly * 12:,.2f}'],
            ['Debt-to-Income Ratio:', f'{debt_to_income_ratio:.1f}%'],
            ['Number of Creditors:', str(len(debt_data))]
        ]
        
        summary_overview_table = Table(summary_overview_data, colWidths=[200, 150])
        summary_overview_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 0), (0, -1), lightgrey),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(summary_overview_table)
        story.append(Spacer(1, 20))
        
        # DETAILED DEBT SCHEDULE
        story.append(Paragraph("<b>DETAILED DEBT SCHEDULE</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Main debt table
        debt_table_data = [
            ['CREDITOR', 'ORIGINAL\nAMOUNT', 'CURRENT\nBALANCE', 'MONTHLY\nPAYMENT', 'INTEREST\nRATE', 'MATURITY\nDATE']
        ]
        
        for debt in debt_data:
            maturity_date = debt.get('maturity_date', 'N/A')
            if isinstance(maturity_date, str) and maturity_date not in ['N/A', 'Revolving Credit']:
                try:
                    # Try to parse and reformat date
                    parsed_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                    maturity_date = parsed_date.strftime('%m/%d/%Y')
                except:
                    pass  # Keep original format if parsing fails
            
            debt_table_data.append([
                debt.get('creditor_name', 'Unknown Creditor')[:20],  # Truncate long names
                f"${debt.get('original_amount', 0):,.0f}",
                f"${debt.get('current_balance', 0):,.0f}",
                f"${debt.get('monthly_payment', 0):,.0f}",
                f"{debt.get('interest_rate', 0):.2f}%",
                str(maturity_date)
            ])
        
        # Add totals row
        debt_table_data.append([
            'TOTALS',
            f"${total_original:,.0f}",
            f"${total_current:,.0f}",
            f"${total_monthly:,.0f}",
            f"{avg_interest_rate:.2f}%",
            ''
        ])
        
        debt_table = Table(debt_table_data, colWidths=[120, 70, 70, 70, 60, 70])
        debt_table.setStyle(TableStyle([
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            
            # Totals row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(debt_table)
        story.append(Spacer(1, 20))
        
        # DETAILED CREDITOR INFORMATION
        story.append(Paragraph("<b>DETAILED CREDITOR INFORMATION</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        for i, debt in enumerate(debt_data, 1):
            # Individual creditor section
            creditor_title = f"{i}. {debt.get('creditor_name', 'Unknown Creditor')}"
            story.append(Paragraph(f"<b>{creditor_title}</b>", styles['Heading3']))
            story.append(Spacer(1, 5))
            
            # Creditor details table
            creditor_details = []
            
            # Basic loan information
            creditor_details.extend([
                ['Loan Type:', debt.get('debt_type', 'Business Loan').replace('_', ' ').title()],
                ['Original Amount:', f"${debt.get('original_amount', 0):,.2f}"],
                ['Current Balance:', f"${debt.get('current_balance', 0):,.2f}"],
                ['Monthly Payment:', f"${debt.get('monthly_payment', 0):,.2f}"],
                ['Interest Rate:', f"{debt.get('interest_rate', 0):.2f}% {'Fixed' if debt.get('rate_type') != 'Variable' else 'Variable'}"],
                ['Payment Terms:', debt.get('payment_terms', 'Monthly Principal and Interest')],
            ])
            
            # Maturity date
            maturity_date = debt.get('maturity_date', 'N/A')
            if isinstance(maturity_date, str) and maturity_date not in ['N/A', 'Revolving Credit']:
                try:
                    parsed_date = datetime.strptime(maturity_date, '%Y-%m-%d').date()
                    maturity_date = parsed_date.strftime('%B %d, %Y')
                    # Calculate remaining term
                    remaining_months = (parsed_date.year - statement_date.year) * 12 + (parsed_date.month - statement_date.month)
                    creditor_details.append(['Remaining Term:', f'{remaining_months} months'])
                except:
                    pass
            
            creditor_details.extend([
                ['Maturity Date:', str(maturity_date)],
                ['Collateral:', debt.get('collateral', 'General Business Assets')],
            ])
            
            # Lender contact information
            lender_contact = debt.get('lender_contact', {})
            if lender_contact:
                creditor_details.extend([
                    ['Lender Contact:', lender_contact.get('name', 'N/A')],
                    ['Phone:', lender_contact.get('phone', 'N/A')],
                    ['Address:', lender_contact.get('address', 'N/A')[:50]],
                ])
            
            # Special terms for credit cards
            if debt.get('debt_type') == 'BUSINESS_CREDIT_CARD':
                credit_limit = debt.get('credit_limit', 0)
                if credit_limit > 0:
                    utilization = debt.get('current_balance', 0) / credit_limit * 100
                    creditor_details.extend([
                        ['Credit Limit:', f"${credit_limit:,.2f}"],
                        ['Credit Utilization:', f"{utilization:.1f}%"],
                    ])
            
            creditor_table = Table(creditor_details, colWidths=[150, 300])
            creditor_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOX', (0, 0), (-1, -1), 1, black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
            ]))
            story.append(creditor_table)
            story.append(Spacer(1, 15))
        
        # DEBT ANALYSIS
        story.append(Paragraph("<b>DEBT ANALYSIS</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Debt by type analysis
        debt_by_type = {}
        for debt in debt_data:
            debt_type = debt.get('debt_type', 'OTHER')
            if debt_type not in debt_by_type:
                debt_by_type[debt_type] = {'count': 0, 'balance': 0, 'payment': 0}
            debt_by_type[debt_type]['count'] += 1
            debt_by_type[debt_type]['balance'] += debt.get('current_balance', 0)
            debt_by_type[debt_type]['payment'] += debt.get('monthly_payment', 0)
        
        debt_analysis_data = [
            ['DEBT TYPE', 'COUNT', 'TOTAL BALANCE', 'MONTHLY PAYMENT', '% OF TOTAL']
        ]
        
        for debt_type, info in debt_by_type.items():
            pct_of_total = (info['balance'] / total_current * 100) if total_current > 0 else 0
            debt_analysis_data.append([
                debt_type.replace('_', ' ').title(),
                str(info['count']),
                f"${info['balance']:,.0f}",
                f"${info['payment']:,.0f}",
                f"{pct_of_total:.1f}%"
            ])
        
        debt_analysis_table = Table(debt_analysis_data, colWidths=[140, 50, 90, 90, 70])
        debt_analysis_table.setStyle(TableStyle([
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(debt_analysis_table)
        story.append(Spacer(1, 20))
        
        # PAYMENT SCHEDULE PROJECTION (Next 12 months)
        story.append(Paragraph("<b>12-MONTH PAYMENT SCHEDULE PROJECTION</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        monthly_schedule_data = [
            ['MONTH', 'TOTAL PAYMENT', 'PRINCIPAL', 'INTEREST', 'REMAINING BALANCE']
        ]
        
        current_balance = total_current
        for month in range(1, 13):
            # Simple calculation - in reality would be more complex
            interest_payment = current_balance * (avg_interest_rate / 100 / 12)
            principal_payment = total_monthly - interest_payment
            current_balance = max(0, current_balance - principal_payment)
            
            future_date = statement_date + timedelta(days=30 * month)
            
            monthly_schedule_data.append([
                future_date.strftime('%b %Y'),
                f"${total_monthly:,.0f}",
                f"${max(0, principal_payment):,.0f}",
                f"${interest_payment:,.0f}",
                f"${current_balance:,.0f}"
            ])
        
        monthly_schedule_table = Table(monthly_schedule_data, colWidths=[80, 80, 80, 80, 100])
        monthly_schedule_table.setStyle(TableStyle([
            # Header row
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(monthly_schedule_table)
        story.append(Spacer(1, 20))
        
        # COVENANT AND COMPLIANCE STATUS
        story.append(Paragraph("<b>COVENANT AND COMPLIANCE STATUS</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        compliance_text = f"""
        <b>Current Status:</b> All debt obligations are current with no past due amounts as of {statement_date.strftime('%B %d, %Y')}.
        
        <b>Financial Covenants:</b> The Company is in compliance with all financial covenants and reporting requirements 
        for existing debt agreements.
        
        <b>Collateral Status:</b> All pledged collateral remains in good condition and properly insured according to 
        lender requirements.
        
        <b>Reporting:</b> All required financial reports and compliance certificates have been submitted to lenders 
        on schedule.
        """
        
        story.append(Paragraph(compliance_text, styles['Normal']))
        story.append(Spacer(1, 15))
        
        # NOTES AND DISCLOSURES
        story.append(Paragraph("<b>NOTES AND DISCLOSURES</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        notes_text = f"""
        1. All amounts are stated as of {statement_date.strftime('%B %d, %Y')} and may vary from actual balances due to timing differences.
        
        2. Interest rates shown are current rates and may be subject to change based on loan agreements.
        
        3. Payment projections are estimates based on current terms and do not account for potential rate changes or early payments.
        
        4. This schedule includes all material debt obligations. Minor obligations under $1,000 may be excluded.
        
        5. All personal guarantees and cross-default provisions are disclosed in individual loan agreements.
        """
        
        story.append(Paragraph(notes_text, styles['Normal']))
        
        return story