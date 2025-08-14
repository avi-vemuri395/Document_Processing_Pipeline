"""
Personal Financial Statement generator for creating realistic SBA Form 413
with proper formatting and layout that matches the official SBA form.
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


class PersonalFinancialStatementGenerator:
    """
    Generator for creating realistic SBA Form 413 - Personal Financial Statement
    with proper formatting that matches the official SBA form layout.
    """
    
    def __init__(self):
        """Initialize Personal Financial Statement generator."""
        self.fake = Faker()
        self.templates = DocumentTemplates()
        self.page_width, self.page_height = letter
        
    def generate_pfs(
        self,
        file_path: Path,
        pfs_data: Dict[str, Any],
        owner_info: Dict[str, Any],
        statement_date: date = None
    ) -> None:
        """Generate SBA Form 413 Personal Financial Statement PDF."""
        if statement_date is None:
            statement_date = date.today()
            
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def pfs_header_footer(canvas, doc):
            """Draw SBA Form 413 header and footer."""
            canvas.saveState()
            
            # SBA Form 413 Header
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 40, "SBA FORM 413")
            
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 58, "PERSONAL FINANCIAL STATEMENT")
            
            canvas.setFont('Helvetica', 10)
            canvas.drawCentredString(self.page_width / 2, self.page_height - 75, "U.S. Small Business Administration")
            
            # Form information box
            canvas.setFont('Helvetica', 8)
            canvas.drawString(450, self.page_height - 90, f"Complete as of: {statement_date.strftime('%m/%d/%Y')}")
            canvas.drawString(450, self.page_height - 102, "SBA Form 413 (Rev. 01-2021)")
            
            # Footer with SBA information
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(grey)
            footer_text = "SBA Form 413 (Rev. 01-2021) • This form was approved by OMB under control number 3245-0188"
            text_width = canvas.stringWidth(footer_text, 'Helvetica', 8)
            canvas.drawString((self.page_width - text_width) / 2, 30, footer_text)
            
            # Privacy notice
            canvas.setFont('Helvetica', 7)
            privacy_text = "Privacy Act Notice: See attached sheet for important information."
            privacy_width = canvas.stringWidth(privacy_text, 'Helvetica', 7)
            canvas.drawString((self.page_width - privacy_width) / 2, 18, privacy_text)
            
            canvas.restoreState()
        
        frame = Frame(
            60, 60,
            self.page_width - 120,
            self.page_height - 180,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='sba_form_413',
            frames=[frame],
            onPage=pfs_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_pfs_content(pfs_data, owner_info, statement_date)
        doc.build(story)
    
    def _build_pfs_content(
        self,
        pfs_data: Dict[str, Any],
        owner_info: Dict[str, Any],
        statement_date: date
    ) -> List:
        """Build Personal Financial Statement content."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 30))
        
        # SECTION 1: PERSONAL INFORMATION
        story.append(Paragraph("<b>SECTION 1 - PERSONAL INFORMATION</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Personal info layout - SBA style
        personal_data = [
            ['Name (Last, First, Middle)', owner_info.get('name', 'Smith, John A.')],
            ['Residence Address', owner_info.get('address', {}).get('street', '123 Main Street')],
            ['City, State, Zip', f"{owner_info.get('address', {}).get('city', 'Anytown')}, {owner_info.get('address', {}).get('state', 'ST')} {owner_info.get('address', {}).get('zip_code', '12345')}"],
            ['Business Phone', owner_info.get('business_phone', '(555) 123-4567')],
            ['Residence Phone', owner_info.get('phone', '(555) 987-6543')],
            ['Social Security Number', owner_info.get('ssn', 'XXX-XX-1234')],
            ['Date of Birth', owner_info.get('date_of_birth', '01/01/1980')],
            ['Number of Dependents', str(owner_info.get('dependents', 2))],
            ['Position/Title/Occupation', owner_info.get('title', 'Business Owner')],
            ['Name of Employer/Company', owner_info.get('employer', 'Self-Employed')]
        ]
        
        personal_table = Table(personal_data, colWidths=[200, 280])
        personal_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (0, -1), lightgrey),
        ]))
        story.append(personal_table)
        story.append(Spacer(1, 20))
        
        # SECTION 2: ASSETS
        story.append(Paragraph("<b>SECTION 2 - ASSETS</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Build assets table
        assets = pfs_data.get('assets', {})
        assets_data = [
            ['DESCRIPTION', 'CURRENT MARKET VALUE']
        ]
        
        # Cash and Cash Equivalents
        cash_equiv = assets.get('cash_and_cash_equivalents', {})
        assets_data.extend([
            ['Cash on hand', f"${cash_equiv.get('cash_on_hand', 0):,.2f}"],
        ])
        
        # Checking accounts
        for i, account in enumerate(cash_equiv.get('checking_accounts', []), 1):
            bank_name = account.get('bank_name', f'Bank {i}')
            account_num = account.get('account_number', '****1234')
            balance = account.get('balance', 0)
            assets_data.append([
                f'Checking Account - {bank_name} ({account_num})',
                f"${balance:,.2f}"
            ])
        
        # Savings accounts
        for i, account in enumerate(cash_equiv.get('savings_accounts', []), 1):
            bank_name = account.get('bank_name', f'Savings Bank {i}')
            account_num = account.get('account_number', '****5678')
            balance = account.get('balance', 0)
            assets_data.append([
                f'Savings Account - {bank_name} ({account_num})',
                f"${balance:,.2f}"
            ])
        
        # Money Market and CDs
        assets_data.extend([
            ['Money Market Accounts', f"${cash_equiv.get('money_market_accounts', 0):,.2f}"],
            ['Certificates of Deposit', f"${cash_equiv.get('certificates_of_deposit', 0):,.2f}"],
        ])
        
        # Securities
        securities = assets.get('securities', {})
        if securities.get('publicly_traded_stocks'):
            for stock in securities['publicly_traded_stocks']:
                assets_data.append([
                    f"Stock - {stock.get('symbol', 'STOCK')} ({stock.get('shares', 0)} shares)",
                    f"${stock.get('market_value', 0):,.2f}"
                ])
        
        assets_data.extend([
            ['Bonds', f"${securities.get('bonds', 0):,.2f}"],
            ['Mutual Funds', f"${securities.get('mutual_funds', 0):,.2f}"],
            ['IRA/401(k) Accounts', f"${securities.get('retirement_accounts_401k', 0) + securities.get('retirement_accounts_ira', 0):,.2f}"],
        ])
        
        # Real Estate
        real_estate = assets.get('real_estate', [])
        for property in real_estate:
            prop_type = property.get('property_type', 'Real Estate')
            market_value = property.get('market_value', 0)
            address = property.get('address', {})
            location = f"{address.get('city', 'City')}, {address.get('state', 'ST')}"
            assets_data.append([
                f'{prop_type} - {location}',
                f"${market_value:,.2f}"
            ])
        
        # Personal Property
        personal_property = assets.get('personal_property', {})
        vehicles = personal_property.get('vehicles', [])
        for vehicle in vehicles:
            year = vehicle.get('year', 2020)
            make = vehicle.get('make', 'Vehicle')
            model = vehicle.get('model', 'Model')
            market_value = vehicle.get('market_value', 0)
            assets_data.append([
                f'{year} {make} {model}',
                f"${market_value:,.2f}"
            ])
        
        assets_data.extend([
            ['Jewelry and Collectibles', f"${personal_property.get('jewelry_and_collectibles', 0):,.2f}"],
            ['Furniture and Fixtures', f"${personal_property.get('furniture_and_fixtures', 0):,.2f}"],
            ['Other Personal Property', f"${personal_property.get('other_personal_property', 0):,.2f}"],
        ])
        
        # Business Interests
        business_interests = assets.get('business_interests', {})
        assets_data.extend([
            ['Business Ownership Interest', f"${business_interests.get('ownership_in_business', 0):,.2f}"],
            ['Business Equipment', f"${business_interests.get('business_equipment', 0):,.2f}"],
            ['Accounts Receivable', f"${business_interests.get('accounts_receivable', 0):,.2f}"],
        ])
        
        # Other Assets
        other_assets = assets.get('other_assets', {})
        assets_data.extend([
            ['Life Insurance Cash Value', f"${other_assets.get('life_insurance_cash_value', 0):,.2f}"],
            ['Notes Receivable', f"${other_assets.get('notes_receivable', 0):,.2f}"],
            ['Other Assets', f"${other_assets.get('other_miscellaneous', 0):,.2f}"],
        ])
        
        # Total Assets
        total_assets = pfs_data.get('total_assets', 0)
        assets_data.append(['TOTAL ASSETS', f"${total_assets:,.2f}"])
        
        assets_table = Table(assets_data, colWidths=[350, 130])
        assets_table.setStyle(TableStyle([
            # Header
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 0), (-1, 0), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(assets_table)
        story.append(Spacer(1, 20))
        
        # SECTION 3: LIABILITIES
        story.append(Paragraph("<b>SECTION 3 - LIABILITIES</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Build liabilities table
        liabilities = pfs_data.get('liabilities', {})
        liabilities_data = [
            ['CREDITOR', 'ORIGINAL AMOUNT', 'CURRENT BALANCE', 'MONTHLY PAYMENT']
        ]
        
        # Current Liabilities
        current_liabilities = liabilities.get('current_liabilities', {})
        
        # Credit Cards
        for card in current_liabilities.get('credit_cards', []):
            liabilities_data.append([
                card.get('creditor', 'Credit Card'),
                f"${card.get('credit_limit', 0):,.2f}",
                f"${card.get('balance', 0):,.2f}",
                f"${card.get('monthly_payment', 0):,.2f}"
            ])
        
        # Short-term notes
        if current_liabilities.get('short_term_notes_payable', 0) > 0:
            liabilities_data.append([
                'Short-term Notes Payable',
                f"${current_liabilities['short_term_notes_payable']:,.2f}",
                f"${current_liabilities['short_term_notes_payable']:,.2f}",
                f"${current_liabilities['short_term_notes_payable'] / 12:,.2f}"
            ])
        
        # Long-term Liabilities
        long_term_liabilities = liabilities.get('long_term_liabilities', {})
        
        # Real Estate Mortgages
        for mortgage in long_term_liabilities.get('real_estate_mortgages', []):
            liabilities_data.append([
                f"Mortgage - {mortgage.get('property', 'Property')}",
                f"${mortgage.get('original_amount', 0):,.2f}",
                f"${mortgage.get('current_balance', 0):,.2f}",
                f"${mortgage.get('monthly_payment', 0):,.2f}"
            ])
        
        # Vehicle Loans
        for loan in long_term_liabilities.get('vehicle_loans', []):
            liabilities_data.append([
                f"Auto Loan - {loan.get('vehicle', 'Vehicle')}",
                f"${loan.get('original_amount', 0):,.2f}",
                f"${loan.get('current_balance', 0):,.2f}",
                f"${loan.get('monthly_payment', 0):,.2f}"
            ])
        
        # Student Loans
        for loan in long_term_liabilities.get('student_loans', []):
            liabilities_data.append([
                f"Student Loan - {loan.get('lender', 'Federal')}",
                f"${loan.get('original_amount', 0):,.2f}",
                f"${loan.get('current_balance', 0):,.2f}",
                f"${loan.get('monthly_payment', 0):,.2f}"
            ])
        
        # Business Loans
        for loan in long_term_liabilities.get('business_loans', []):
            liabilities_data.append([
                f"Business Loan - {loan.get('lender', 'Bank')}",
                f"${loan.get('original_amount', 0):,.2f}",
                f"${loan.get('current_balance', 0):,.2f}",
                f"${loan.get('monthly_payment', 0):,.2f}"
            ])
        
        # Total Liabilities
        total_liabilities = pfs_data.get('total_liabilities', 0)
        total_monthly_payments = sum([
            sum(card.get('monthly_payment', 0) for card in current_liabilities.get('credit_cards', [])),
            sum(mortgage.get('monthly_payment', 0) for mortgage in long_term_liabilities.get('real_estate_mortgages', [])),
            sum(loan.get('monthly_payment', 0) for loan in long_term_liabilities.get('vehicle_loans', [])),
            sum(loan.get('monthly_payment', 0) for loan in long_term_liabilities.get('student_loans', [])),
            sum(loan.get('monthly_payment', 0) for loan in long_term_liabilities.get('business_loans', []))
        ])
        
        liabilities_data.append([
            'TOTAL LIABILITIES',
            '',
            f"${total_liabilities:,.2f}",
            f"${total_monthly_payments:,.2f}"
        ])
        
        liabilities_table = Table(liabilities_data, colWidths=[180, 100, 100, 100])
        liabilities_table.setStyle(TableStyle([
            # Header
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 0), (-1, 0), darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            
            # Total row
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            
            # Borders
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(liabilities_table)
        story.append(Spacer(1, 20))
        
        # NET WORTH CALCULATION
        net_worth = pfs_data.get('net_worth', total_assets - total_liabilities)
        
        net_worth_data = [
            ['TOTAL ASSETS', f"${total_assets:,.2f}"],
            ['LESS: TOTAL LIABILITIES', f"${total_liabilities:,.2f}"],
            ['NET WORTH', f"${net_worth:,.2f}"]
        ]
        
        net_worth_table = Table(net_worth_data, colWidths=[350, 130])
        net_worth_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, -1), (-1, -1), darkblue),
            ('TEXTCOLOR', (0, -1), (-1, -1), white),
            ('BOX', (0, 0), (-1, -1), 2, black),
            ('INNERGRID', (0, 0), (-1, -1), 1, grey),
        ]))
        story.append(net_worth_table)
        story.append(Spacer(1, 20))
        
        # SECTION 4: INCOME AND EXPENSES (ANNUAL)
        story.append(Paragraph("<b>SECTION 4 - ANNUAL INCOME AND EXPENSES</b>", styles['Heading2']))
        story.append(Spacer(1, 10))
        
        # Income and Expenses side by side
        income = pfs_data.get('income', {})
        expenses = pfs_data.get('expenses', {})
        
        # Income side
        income_data = [
            ['INCOME SOURCE', 'ANNUAL AMOUNT'],
            ['Salary/Wages', f"${income.get('salary_wages', 0):,.2f}"],
            ['Business Income', f"${income.get('business_income', 0):,.2f}"],
            ['Rental Income', f"${income.get('rental_income', 0):,.2f}"],
            ['Investment Income', f"${income.get('investment_income', 0):,.2f}"],
            ['Other Income', f"${income.get('other_income', 0):,.2f}"],
            ['TOTAL INCOME', f"${income.get('total_monthly_income', 0) * 12:,.2f}"]
        ]
        
        # Expenses side
        expenses_data = [
            ['EXPENSE TYPE', 'ANNUAL AMOUNT'],
            ['Housing/Rent', f"${expenses.get('housing_mortgage_rent', 0) * 12:,.2f}"],
            ['Transportation', f"${expenses.get('transportation', 0) * 12:,.2f}"],
            ['Insurance', f"${expenses.get('insurance_life_health', 0) * 12:,.2f}"],
            ['Taxes', f"${expenses.get('taxes_income', 0) * 12:,.2f}"],
            ['Other Expenses', f"${expenses.get('other_expenses', 0) * 12:,.2f}"],
            ['TOTAL EXPENSES', f"${expenses.get('total_monthly_expenses', 0) * 12:,.2f}"]
        ]
        
        income_table = Table(income_data, colWidths=[140, 100])
        expenses_table = Table(expenses_data, colWidths=[140, 100])
        
        for table in [income_table, expenses_table]:
            table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BACKGROUND', (0, 0), (-1, 0), darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), white),
                ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOX', (0, 0), (-1, -1), 1, black),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
            ]))
        
        # Combine income and expenses tables
        combined_table = Table([[income_table, expenses_table]], colWidths=[240, 240])
        story.append(combined_table)
        story.append(Spacer(1, 20))
        
        # SIGNATURES SECTION
        story.append(Paragraph("<b>CERTIFICATION</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        certification_text = """
        I certify that the information provided in this Personal Financial Statement is true and complete 
        to the best of my knowledge and is submitted to obtain credit. I understand FALSE statements may 
        result in forfeiture of benefits and possible prosecution by the U.S. Attorney General.
        """
        
        story.append(Paragraph(certification_text, styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Signature lines
        signature_data = [
            ['Signature:', '_' * 40, 'Date:', '_' * 15],
            ['', owner_info.get('name', 'John Smith'), '', statement_date.strftime('%m/%d/%Y')]
        ]
        
        signature_table = Table(signature_data, colWidths=[80, 200, 50, 150])
        signature_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (3, 0), (3, 0), 'CENTER'),
        ]))
        story.append(signature_table)
        
        return story