"""
Tax return generators for creating realistic IRS tax forms including
Form 1120, 1120S, and 1040 Schedule C with proper formatting and layouts.
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple
import uuid

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


class TaxReturnGenerator:
    """
    Generator for creating realistic IRS tax return forms with proper
    formatting, line numbers, and official layouts.
    """
    
    def __init__(self):
        """Initialize tax return generator."""
        self.fake = Faker()
        self.templates = DocumentTemplates()
        self.page_width, self.page_height = letter
        
    def generate_tax_return(
        self,
        file_path: Path,
        form_type: str,
        business_data: Dict[str, Any],
        tax_year: int
    ) -> None:
        """Generate tax return PDF based on form type."""
        if form_type == '1120':
            self._generate_form_1120(file_path, business_data, tax_year)
        elif form_type == '1120S':
            self._generate_form_1120s(file_path, business_data, tax_year)
        elif form_type == '1040_schedule_c':
            self._generate_schedule_c(file_path, business_data, tax_year)
        else:
            raise ValueError(f"Unsupported tax form type: {form_type}")
    
    def _generate_form_1120(
        self,
        file_path: Path,
        business_data: Dict[str, Any],
        tax_year: int
    ) -> None:
        """Generate IRS Form 1120 - U.S. Corporation Income Tax Return."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def form_1120_header_footer(canvas, doc):
            """Draw Form 1120 header and footer."""
            canvas.saveState()
            
            # IRS header
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(72, self.page_height - 50, "Form 1120")
            canvas.setFont('Helvetica', 10)
            canvas.drawString(520, self.page_height - 50, f"Tax Year {tax_year}")
            
            canvas.setFont('Helvetica-Bold', 14)
            canvas.drawString(72, self.page_height - 70, "U.S. Corporation Income Tax Return")
            
            canvas.setFont('Helvetica', 10)
            canvas.drawString(72, self.page_height - 90, "Department of the Treasury—Internal Revenue Service")
            
            # Form identifier box (upper right)
            canvas.rect(450, self.page_height - 120, 120, 60)
            canvas.setFont('Helvetica-Bold', 8)
            canvas.drawString(455, self.page_height - 75, "For calendar year")
            canvas.drawString(455, self.page_height - 85, f"{tax_year}")
            canvas.drawString(455, self.page_height - 100, "or tax year beginning")
            canvas.drawString(455, self.page_height - 115, "____________, and ending")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(self.page_width / 2, 30, 
                                  "For Paperwork Reduction Act Notice, see separate instructions.")
            canvas.drawString(520, 30, f"Form 1120 ({tax_year})")
            
            canvas.restoreState()
        
        frame = Frame(
            72, 80,
            self.page_width - 144,
            self.page_height - 200,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='form_1120',
            frames=[frame],
            onPage=form_1120_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_form_1120_content(business_data, tax_year)
        doc.build(story)
    
    def _generate_form_1120s(
        self,
        file_path: Path,
        business_data: Dict[str, Any],
        tax_year: int
    ) -> None:
        """Generate IRS Form 1120S - U.S. Income Tax Return for an S Corporation."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def form_1120s_header_footer(canvas, doc):
            """Draw Form 1120S header and footer."""
            canvas.saveState()
            
            # IRS header
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(72, self.page_height - 50, "Form 1120S")
            canvas.setFont('Helvetica', 10)
            canvas.drawString(520, self.page_height - 50, f"Tax Year {tax_year}")
            
            canvas.setFont('Helvetica-Bold', 12)
            canvas.drawString(72, self.page_height - 70, "U.S. Income Tax Return for an S Corporation")
            canvas.setFont('Helvetica', 10)
            canvas.drawString(72, self.page_height - 85, "► Do not file this form unless the corporation has filed or is")
            canvas.drawString(72, self.page_height - 95, "   attaching Form 2553 to elect to be an S corporation.")
            
            canvas.drawString(72, self.page_height - 110, "Department of the Treasury—Internal Revenue Service")
            
            # S Corporation election checkbox
            canvas.rect(500, self.page_height - 130, 10, 10)
            canvas.setFont('Helvetica', 8)
            canvas.drawString(515, self.page_height - 128, "S election in effect")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(self.page_width / 2, 30,
                                  "For Paperwork Reduction Act Notice, see separate instructions.")
            canvas.drawString(520, 30, f"Form 1120S ({tax_year})")
            
            canvas.restoreState()
        
        frame = Frame(
            72, 80,
            self.page_width - 144,
            self.page_height - 220,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='form_1120s',
            frames=[frame],
            onPage=form_1120s_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_form_1120s_content(business_data, tax_year)
        doc.build(story)
    
    def _generate_schedule_c(
        self,
        file_path: Path,
        business_data: Dict[str, Any],
        tax_year: int
    ) -> None:
        """Generate IRS Schedule C - Profit or Loss From Business."""
        doc = BaseDocTemplate(str(file_path), pagesize=letter)
        
        def schedule_c_header_footer(canvas, doc):
            """Draw Schedule C header and footer."""
            canvas.saveState()
            
            # Schedule C header
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(72, self.page_height - 50, "SCHEDULE C")
            canvas.setFont('Helvetica', 10)
            canvas.drawString(200, self.page_height - 50, "(Form 1040)")
            canvas.drawString(520, self.page_height - 50, f"Tax Year {tax_year}")
            
            canvas.setFont('Helvetica-Bold', 12)
            canvas.drawString(72, self.page_height - 70, "Profit or Loss From Business")
            canvas.setFont('Helvetica', 10)
            canvas.drawString(300, self.page_height - 70, "(Sole Proprietorship)")
            
            canvas.drawString(72, self.page_height - 90, 
                            "► Go to www.irs.gov/ScheduleC for instructions and the latest information.")
            canvas.drawString(72, self.page_height - 105,
                            "► Attach to Form 1040, 1040-SR, 1040-NR, or 1041; partnerships generally must file Form 1065.")
            
            # SSN box
            canvas.rect(450, self.page_height - 130, 120, 20)
            canvas.setFont('Helvetica', 8)
            canvas.drawString(455, self.page_height - 125, "Social security number (SSN)")
            
            # Footer
            canvas.setFont('Helvetica', 8)
            canvas.drawCentredString(self.page_width / 2, 30,
                                  "For Paperwork Reduction Act Notice, see your tax return instructions.")
            canvas.drawString(520, 30, f"Schedule C (Form 1040) {tax_year}")
            
            canvas.restoreState()
        
        frame = Frame(
            72, 80,
            self.page_width - 144,
            self.page_height - 220,
            leftPadding=0, bottomPadding=0,
            rightPadding=0, topPadding=0
        )
        
        template = PageTemplate(
            id='schedule_c',
            frames=[frame],
            onPage=schedule_c_header_footer
        )
        doc.addPageTemplates([template])
        
        story = self._build_schedule_c_content(business_data, tax_year)
        doc.build(story)
    
    def _build_form_1120_content(self, business_data: Dict[str, Any], tax_year: int) -> List:
        """Build Form 1120 content with proper line items and calculations."""
        story = []
        styles = getSampleStyleSheet()
        
        # Top section - Business identification
        story.append(Spacer(1, 20))
        
        # Name and address
        business_name = business_data.get('name', 'Sample Corporation')
        business_address = business_data.get('address', {})
        address_str = f"{business_address.get('street', '123 Business St')}"
        city_state_zip = f"{business_address.get('city', 'City')}, {business_address.get('state', 'ST')} {business_address.get('zip_code', '12345')}"
        
        name_address_data = [
            ['Name', business_name],
            ['Number, street, and room or suite no.', address_str],
            ['City or town, state or province, country, and ZIP or foreign postal code', city_state_zip]
        ]
        
        name_address_table = Table(name_address_data, colWidths=[200, 300])
        name_address_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(name_address_table)
        story.append(Spacer(1, 10))
        
        # EIN and other identification
        ein = business_data.get('ein', self.fake.ein())
        incorporation_date = business_data.get('date_established', '01/01/2015')
        
        id_data = [
            ['A Check if:', '□ Initial return  □ Final return  ☑ Amended return'],
            ['B Employer identification number (EIN)', ein],
            ['C Date incorporated', incorporation_date],
            ['D Total assets (see instructions)', f"${business_data.get('total_assets', 500000):,.2f}"]
        ]
        
        id_table = Table(id_data, colWidths=[150, 350])
        id_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(id_table)
        story.append(Spacer(1, 20))
        
        # INCOME section
        story.append(Paragraph("<b>Income</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        # Calculate income figures based on business data
        gross_receipts = business_data.get('annual_revenue', 500000)
        cost_of_goods_sold = gross_receipts * 0.4  # 40% COGS
        gross_profit = gross_receipts - cost_of_goods_sold
        dividends = 0
        interest = gross_receipts * 0.005  # 0.5% interest income
        gross_rents = 0
        gross_royalties = 0
        capital_gain = 0
        net_gain_form_4797 = 0
        other_income = gross_receipts * 0.01  # 1% other income
        total_income = gross_profit + dividends + interest + gross_rents + gross_royalties + capital_gain + net_gain_form_4797 + other_income
        
        income_data = [
            ['1a', 'Gross receipts or sales', f'{gross_receipts:,.2f}'],
            ['1c', 'Total receipts (add lines 1a and 1b)', f'{gross_receipts:,.2f}'],
            ['2', 'Cost of goods sold (from Form 1125-A)', f'{cost_of_goods_sold:,.2f}'],
            ['3', 'Gross profit (subtract line 2 from line 1c)', f'{gross_profit:,.2f}'],
            ['4', 'Dividends (Schedule C, line 19)', f'{dividends:,.2f}'],
            ['5', 'Interest', f'{interest:,.2f}'],
            ['6', 'Gross rents', f'{gross_rents:,.2f}'],
            ['7', 'Gross royalties', f'{gross_royalties:,.2f}'],
            ['8', 'Capital gain net income', f'{capital_gain:,.2f}'],
            ['9', 'Net gain or (loss) from Form 4797', f'{net_gain_form_4797:,.2f}'],
            ['10', 'Other income (see instructions—attach statement)', f'{other_income:,.2f}'],
            ['11', 'Total income (add lines 3 through 10)', f'{total_income:,.2f}']
        ]
        
        income_table = Table(income_data, colWidths=[30, 350, 120])
        income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(income_table)
        story.append(Spacer(1, 15))
        
        # DEDUCTIONS section
        story.append(Paragraph("<b>Deductions</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        # Calculate deduction figures
        compensation_officers = total_income * 0.15
        salaries_wages = total_income * 0.25
        repairs_maintenance = total_income * 0.02
        bad_debts = total_income * 0.005
        rents = total_income * 0.08
        taxes_licenses = total_income * 0.02
        interest_expense = total_income * 0.03
        charitable_contributions = total_income * 0.005
        depreciation = total_income * 0.05
        advertising = total_income * 0.03
        other_deductions = total_income * 0.05
        total_deductions = (compensation_officers + salaries_wages + repairs_maintenance + 
                          bad_debts + rents + taxes_licenses + interest_expense + 
                          charitable_contributions + depreciation + advertising + other_deductions)
        
        deductions_data = [
            ['12', 'Compensation of officers (from Form 1125-E)', f'{compensation_officers:,.2f}'],
            ['13', 'Salaries and wages (less employment credits)', f'{salaries_wages:,.2f}'],
            ['14', 'Repairs and maintenance', f'{repairs_maintenance:,.2f}'],
            ['15', 'Bad debts', f'{bad_debts:,.2f}'],
            ['16', 'Rents', f'{rents:,.2f}'],
            ['17', 'Taxes and licenses', f'{taxes_licenses:,.2f}'],
            ['18', 'Interest', f'{interest_expense:,.2f}'],
            ['19', 'Charitable contributions', f'{charitable_contributions:,.2f}'],
            ['20', 'Depreciation from Form 4562', f'{depreciation:,.2f}'],
            ['21', 'Advertising', f'{advertising:,.2f}'],
            ['26', 'Other deductions (attach statement)', f'{other_deductions:,.2f}'],
            ['27', 'Total deductions (add lines 12 through 26)', f'{total_deductions:,.2f}']
        ]
        
        deductions_table = Table(deductions_data, colWidths=[30, 350, 120])
        deductions_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(deductions_table)
        story.append(Spacer(1, 15))
        
        # TAX COMPUTATION
        story.append(Paragraph("<b>Tax Computation and Payment</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        taxable_income = max(0, total_income - total_deductions)
        total_tax = taxable_income * 0.21  # 21% corporate tax rate
        payments_credits = total_tax * 0.85  # Assume 85% paid through estimated payments
        amount_owed = max(0, total_tax - payments_credits)
        overpayment = max(0, payments_credits - total_tax)
        
        tax_data = [
            ['30', 'Taxable income (subtract line 27 from line 11)', f'{taxable_income:,.2f}'],
            ['31', 'Total tax (Schedule J, Part I, line 11)', f'{total_tax:,.2f}'],
            ['32a', '2023 overpayment credited to 2024', '0.00'],
            ['32b', '2024 estimated tax payments', f'{payments_credits:,.2f}'],
            ['35', 'Amount owed (subtract line 34 from line 31)', f'{amount_owed:,.2f}'],
            ['36', 'Overpayment (subtract line 31 from line 34)', f'{overpayment:,.2f}']
        ]
        
        tax_table = Table(tax_data, colWidths=[30, 350, 120])
        tax_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(tax_table)
        
        return story
    
    def _build_form_1120s_content(self, business_data: Dict[str, Any], tax_year: int) -> List:
        """Build Form 1120S content for S Corporation."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 20))
        
        # Business identification similar to 1120 but with S Corp specifics
        business_name = business_data.get('name', 'Sample S Corporation')
        business_address = business_data.get('address', {})
        address_str = f"{business_address.get('street', '123 Business St')}"
        city_state_zip = f"{business_address.get('city', 'City')}, {business_address.get('state', 'ST')} {business_address.get('zip_code', '12345')}"
        
        name_address_data = [
            ['Name', business_name],
            ['Number, street, and room or suite no.', address_str],
            ['City or town, state or province, country, and ZIP or foreign postal code', city_state_zip]
        ]
        
        name_address_table = Table(name_address_data, colWidths=[200, 300])
        name_address_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(name_address_table)
        story.append(Spacer(1, 10))
        
        # S Corporation specific information
        ein = business_data.get('ein', self.fake.ein())
        s_corp_data = [
            ['B Employer identification number (EIN)', ein],
            ['C Date incorporated', business_data.get('date_established', '01/01/2015')],
            ['D Total assets (see instructions)', f"${business_data.get('total_assets', 300000):,.2f}"],
            ['E Check if: (1) □ Final S election  (2) ☑ Amended return'],
            ['F Check applicable boxes:', '☑ (1) Initial return (2) □ Final return'],
            ['G Number of shareholders at end of tax year', '2']
        ]
        
        s_corp_table = Table(s_corp_data, colWidths=[150, 350])
        s_corp_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(s_corp_table)
        story.append(Spacer(1, 20))
        
        # INCOME section for S Corp
        story.append(Paragraph("<b>Income</b>", styles['Heading2']))
        
        gross_receipts = business_data.get('annual_revenue', 300000)
        returns_allowances = gross_receipts * 0.02
        net_receipts = gross_receipts - returns_allowances
        cost_of_goods_sold = net_receipts * 0.45
        gross_profit = net_receipts - cost_of_goods_sold
        net_gain_form_4797 = 0
        other_income = net_receipts * 0.005
        total_income = gross_profit + net_gain_form_4797 + other_income
        
        s_income_data = [
            ['1a', 'Gross receipts or sales', f'{gross_receipts:,.2f}'],
            ['1b', 'Returns and allowances', f'{returns_allowances:,.2f}'],
            ['1c', 'Balance (subtract 1b from 1a)', f'{net_receipts:,.2f}'],
            ['2', 'Cost of goods sold (attach Form 1125-A)', f'{cost_of_goods_sold:,.2f}'],
            ['3', 'Gross profit (subtract line 2 from line 1c)', f'{gross_profit:,.2f}'],
            ['4', 'Net gain (loss) from Form 4797', f'{net_gain_form_4797:,.2f}'],
            ['5', 'Other income (loss) (see instructions)', f'{other_income:,.2f}'],
            ['6', 'Total income (loss) (add lines 3 through 5)', f'{total_income:,.2f}']
        ]
        
        s_income_table = Table(s_income_data, colWidths=[30, 350, 120])
        s_income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(s_income_table)
        story.append(Spacer(1, 15))
        
        # DEDUCTIONS section for S Corp
        story.append(Paragraph("<b>Deductions</b>", styles['Heading2']))
        
        # S Corp deductions (no compensation of officers since they're shareholders)
        salaries_wages = total_income * 0.20
        repairs_maintenance = total_income * 0.02
        bad_debts = 0
        rents = total_income * 0.08
        taxes_licenses = total_income * 0.015
        interest_expense = total_income * 0.025
        depreciation = total_income * 0.04
        advertising = total_income * 0.025
        pension_plans = total_income * 0.03
        employee_benefits = total_income * 0.02
        other_deductions = total_income * 0.04
        total_deductions_s = (salaries_wages + repairs_maintenance + bad_debts + rents + 
                            taxes_licenses + interest_expense + depreciation + advertising + 
                            pension_plans + employee_benefits + other_deductions)
        
        s_deductions_data = [
            ['7', 'Compensation of officers', '0.00'],  # S Corp shareholders
            ['8', 'Salaries and wages', f'{salaries_wages:,.2f}'],
            ['9', 'Repairs and maintenance', f'{repairs_maintenance:,.2f}'],
            ['10', 'Bad debts', f'{bad_debts:,.2f}'],
            ['11', 'Rents', f'{rents:,.2f}'],
            ['12', 'Taxes and licenses', f'{taxes_licenses:,.2f}'],
            ['13', 'Interest', f'{interest_expense:,.2f}'],
            ['14', 'Depreciation not claimed on Form 1125-A', f'{depreciation:,.2f}'],
            ['15', 'Advertising', f'{advertising:,.2f}'],
            ['16', 'Pension, profit-sharing, etc., plans', f'{pension_plans:,.2f}'],
            ['17', 'Employee benefit programs', f'{employee_benefits:,.2f}'],
            ['19', 'Other deductions (attach statement)', f'{other_deductions:,.2f}'],
            ['20', 'Total deductions (add lines 7 through 19)', f'{total_deductions_s:,.2f}']
        ]
        
        s_deductions_table = Table(s_deductions_data, colWidths=[30, 350, 120])
        s_deductions_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(s_deductions_table)
        story.append(Spacer(1, 15))
        
        # Ordinary business income (loss) - key for S Corp
        ordinary_income = total_income - total_deductions_s
        
        summary_data = [
            ['21', f'Ordinary business income (loss) (subtract line 20 from line 6)', f'{ordinary_income:,.2f}']
        ]
        
        summary_table = Table(summary_data, colWidths=[30, 350, 120])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, black),
        ]))
        story.append(summary_table)
        
        return story
    
    def _build_schedule_c_content(self, business_data: Dict[str, Any], tax_year: int) -> List:
        """Build Schedule C content for sole proprietorship."""
        story = []
        styles = getSampleStyleSheet()
        
        story.append(Spacer(1, 20))
        
        # Business identification
        owner_name = business_data.get('owner_name', 'John Smith')
        business_name = business_data.get('name', 'Sample Business')
        business_address = business_data.get('address', {})
        
        business_info_data = [
            ['A    Principal business or profession, including product or service', business_data.get('type', 'Professional Services')],
            ['B    Business name. If no separate business name, leave blank.', business_name],
            ['C    Business address (including suite or room no.)', business_address.get('street', '123 Business St')],
            ['     City, town or post office, state, and ZIP code', f"{business_address.get('city', 'City')}, {business_address.get('state', 'ST')} {business_address.get('zip_code', '12345')}"],
            ['E    Business code (see instructions)', business_data.get('naics_code', '541990')],
            ['F    Accounting method: (1) ☑ Cash (2) □ Accrual (3) □ Other', '']
        ]
        
        business_info_table = Table(business_info_data, colWidths=[120, 380])
        business_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(business_info_table)
        story.append(Spacer(1, 20))
        
        # PART I - INCOME
        story.append(Paragraph("<b>Part I    Income</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        gross_receipts = business_data.get('annual_revenue', 150000)
        returns_allowances = gross_receipts * 0.01
        net_receipts = gross_receipts - returns_allowances
        cost_of_goods_sold = net_receipts * 0.35 if business_data.get('type', '').lower() in ['retail', 'manufacturing'] else 0
        gross_profit = net_receipts - cost_of_goods_sold
        other_income = gross_receipts * 0.005
        gross_income = gross_profit + other_income
        
        income_data = [
            ['1', 'Gross receipts or sales. See instructions for line 1 and check the box if this income was reported to you on Form 1099-NEC. Check the box if this income was reported to you on Form 1099-K ► □', f'{gross_receipts:,.2f}'],
            ['2', 'Returns and allowances', f'{returns_allowances:,.2f}'],
            ['3', 'Subtract line 2 from line 1', f'{net_receipts:,.2f}'],
            ['4', 'Cost of goods sold (from line 42)', f'{cost_of_goods_sold:,.2f}'],
            ['5', 'Gross profit. Subtract line 4 from line 3', f'{gross_profit:,.2f}'],
            ['6', 'Other income, including federal and state gasoline or fuel tax credit or refund (see instructions)', f'{other_income:,.2f}'],
            ['7', 'Gross income. Add lines 5 and 6', f'{gross_income:,.2f}']
        ]
        
        income_table = Table(income_data, colWidths=[30, 350, 120])
        income_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(income_table)
        story.append(Spacer(1, 15))
        
        # PART II - EXPENSES
        story.append(Paragraph("<b>Part II   Expenses</b>", styles['Heading2']))
        story.append(Spacer(1, 5))
        
        # Calculate expenses for sole proprietorship
        advertising = gross_income * 0.03
        car_truck = gross_income * 0.04
        commissions_fees = gross_income * 0.02
        contract_labor = gross_income * 0.05
        depreciation = gross_income * 0.04
        insurance = gross_income * 0.025
        interest = gross_income * 0.02
        legal_professional = gross_income * 0.015
        office_expense = gross_income * 0.02
        rent_lease = gross_income * 0.08
        repairs_maintenance = gross_income * 0.015
        supplies = gross_income * 0.02
        taxes_licenses = gross_income * 0.015
        travel_meals = gross_income * 0.02
        utilities = gross_income * 0.025
        wages = gross_income * 0.15
        other_expenses = gross_income * 0.03
        
        total_expenses = (advertising + car_truck + commissions_fees + contract_labor + 
                         depreciation + insurance + interest + legal_professional + 
                         office_expense + rent_lease + repairs_maintenance + supplies + 
                         taxes_licenses + travel_meals + utilities + wages + other_expenses)
        
        expenses_data = [
            ['8', 'Advertising', f'{advertising:,.2f}'],
            ['9', 'Car and truck expenses (see instructions)', f'{car_truck:,.2f}'],
            ['10', 'Commissions and fees', f'{commissions_fees:,.2f}'],
            ['11', 'Contract labor (see instructions)', f'{contract_labor:,.2f}'],
            ['13', 'Depreciation and section 179 expense deduction (not included in Part III) (see instructions)', f'{depreciation:,.2f}'],
            ['15', 'Insurance (other than health)', f'{insurance:,.2f}'],
            ['16a', 'Interest on business indebtedness', f'{interest:,.2f}'],
            ['17', 'Legal and professional services', f'{legal_professional:,.2f}'],
            ['18', 'Office expense (see instructions)', f'{office_expense:,.2f}'],
            ['20a', 'Rent or lease (see instructions): Vehicles, machinery, and equipment', f'{rent_lease:,.2f}'],
            ['21', 'Repairs and maintenance', f'{repairs_maintenance:,.2f}'],
            ['22', 'Supplies (not included in Part III)', f'{supplies:,.2f}'],
            ['23', 'Taxes and licenses', f'{taxes_licenses:,.2f}'],
            ['24a', 'Travel', f'{travel_meals:,.2f}'],
            ['25', 'Utilities', f'{utilities:,.2f}'],
            ['26', 'Wages (less employment credits)', f'{wages:,.2f}'],
            ['27a', 'Other expenses (from line 48)', f'{other_expenses:,.2f}'],
            ['28', 'Total expenses before expenses for business use of home. Add lines 8 through 27a', f'{total_expenses:,.2f}']
        ]
        
        expenses_table = Table(expenses_data, colWidths=[30, 350, 120])
        expenses_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 1, black),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, grey),
        ]))
        story.append(expenses_table)
        story.append(Spacer(1, 15))
        
        # Net profit or loss
        net_profit = gross_income - total_expenses
        
        net_profit_data = [
            ['31', f'Net profit or (loss). Subtract line 28 from line 7. If a profit, enter on both Schedule 1 (Form 1040), line 3, and on Schedule SE, line 2. If a loss, you MUST go to line 32', f'{net_profit:,.2f}']
        ]
        
        net_profit_table = Table(net_profit_data, colWidths=[30, 350, 120])
        net_profit_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BACKGROUND', (0, 0), (-1, -1), lightgrey),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 2, black),
        ]))
        story.append(net_profit_table)
        
        return story