"""
SBA loan application synthetic data generator.

This module generates realistic SBA loan applications with complete document sets
including bank statements, tax returns, financial statements, and supporting documents.
"""

import json
import time
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid
from dataclasses import asdict

import pandas as pd
from faker import Faker
from faker.providers import company, person, address, phone_number
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

from .base import BaseGenerator, GenerationResult, GenerationStatus, DocumentSet
from .bank_statement_generators import BankStatementGenerator
from .tax_return_generators import TaxReturnGenerator
from .personal_financial_statement_generator import PersonalFinancialStatementGenerator
from .business_financial_statement_generator import BusinessFinancialStatementGenerator
from .debt_schedule_generator import DebtScheduleGenerator


class SBALoanApplicationGenerator(BaseGenerator):
    """
    Generator for SBA loan application document sets.
    
    Creates realistic, coherent document sets including:
    - Bank statements (Excel format)
    - Tax returns (PDF format) 
    - Financial statements (Excel format)
    - Business reports (PDF format)
    - Supporting documents
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize SBA loan application generator."""
        super().__init__(config)
        self.fake = Faker()
        self.fake.add_provider(company)
        self.fake.add_provider(person)
        self.fake.add_provider(address)
        self.fake.add_provider(phone_number)
        
        # Initialize realistic document generators
        self.bank_generator = BankStatementGenerator()
        self.tax_generator = TaxReturnGenerator()
        self.pfs_generator = PersonalFinancialStatementGenerator()
        self.business_financial_generator = BusinessFinancialStatementGenerator()
        self.debt_schedule_generator = DebtScheduleGenerator()
    
    def _setup_generator(self) -> None:
        """Setup SBA generator specific configuration."""
        # Loan amount ranges
        self.min_loan_amount = self.config.get('min_loan_amount', 25000)
        self.max_loan_amount = self.config.get('max_loan_amount', 500000)
        
        # Business parameters
        self.business_types = self.config.get('business_types', [
            'Restaurant', 'Retail Store', 'Manufacturing', 'Construction', 
            'Professional Services', 'Technology', 'Healthcare'
        ])
        
        # Financial statement parameters
        self.revenue_multiplier = self.config.get('revenue_multiplier', 3.5)  # Revenue to loan ratio
        self.profit_margin_range = self.config.get('profit_margin_range', (0.05, 0.25))
        
        # Statement periods
        self.statement_months = self.config.get('statement_months', 12)  # Months of statements
        
        # Template paths
        self.template_dir = Path(self.config.get('template_dir', 'templates/sba'))
    
    @property
    def supported_document_types(self) -> List[str]:
        """Return supported document types."""
        return ['sba_loan_application']
    
    @property
    def required_config_keys(self) -> List[str]:
        """Return required configuration keys."""
        return []  # All config is optional with defaults
    
    def generate(
        self, 
        output_dir: Path, 
        num_applications: int = 1,
        **kwargs
    ) -> GenerationResult:
        """
        Generate SBA loan application document sets.
        
        Args:
            output_dir: Directory to save generated documents
            num_applications: Number of applications to generate
            **kwargs: Additional generation parameters
            
        Returns:
            GenerationResult containing generated applications
        """
        start_time = time.time()
        document_sets = []
        errors = []
        
        try:
            self.logger.info(f"Generating {num_applications} SBA loan applications")
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(num_applications):
                try:
                    # Generate unique application ID
                    app_id = f"SBA_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"
                    
                    # Create application directory
                    app_dir = self.create_directory_structure(output_dir, app_id)
                    
                    # Generate coherent business profile
                    business_profile = self._generate_business_profile()
                    
                    # Generate document set
                    document_set = self._generate_document_set(app_id, app_dir, business_profile)
                    
                    # Validate generated documents
                    validation_errors = self.validate_generated_documents(document_set)
                    if validation_errors:
                        errors.extend(validation_errors)
                        continue
                    
                    # Create metadata file
                    metadata_file = self.create_metadata_file(document_set, output_dir)
                    document_set.add_file('metadata', metadata_file)
                    
                    document_sets.append(document_set)
                    
                    self.logger.info(f"Generated application {app_id}")
                    
                except Exception as e:
                    error_msg = f"Error generating application {i+1}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    continue
            
            # Determine status
            if not document_sets:
                status = GenerationStatus.FAILED
            elif errors:
                status = GenerationStatus.PARTIAL
            else:
                status = GenerationStatus.SUCCESS
            
            result = GenerationResult(
                status=status,
                document_sets=document_sets,
                generation_time=time.time() - start_time,
                errors=errors,
                metadata={
                    'generator': self.__class__.__name__,
                    'applications_requested': num_applications,
                    'applications_generated': len(document_sets),
                    'generation_timestamp': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"Generated {len(document_sets)} applications with status {status.value}")
            return result
            
        except Exception as e:
            error_msg = f"Fatal error in generation: {e}"
            self.logger.error(error_msg)
            
            return GenerationResult(
                status=GenerationStatus.FAILED,
                document_sets=document_sets,
                generation_time=time.time() - start_time,
                errors=[error_msg],
                metadata={}
            )
    
    def _generate_business_profile(self) -> Dict[str, Any]:
        """Generate a coherent business profile aligned with Prisma schema."""
        business_type = self.fake.random.choice(self.business_types)
        
        # Generate loan amount
        loan_amount = round(self.fake.random.uniform(self.min_loan_amount, self.max_loan_amount), -3)
        
        # Generate revenue based on loan amount
        revenue = loan_amount * self.revenue_multiplier * self.fake.random.uniform(0.8, 1.5)
        
        # Generate profit margin
        profit_margin = self.fake.random.uniform(*self.profit_margin_range)
        net_income = revenue * profit_margin
        
        # Generate multiple beneficial owners
        beneficial_owners = self._generate_beneficial_owners()
        
        # Generate comprehensive personal financial statement
        pfs_data = self._generate_personal_financial_statement(revenue)
        
        # Generate business metadata aligned with Prisma schema
        business_metadata = self._generate_business_metadata(business_type, revenue, net_income)
        
        # Generate business address
        business_address = business_metadata['address']
        business_address_str = f"{business_address['street']}\n{business_address['city']}, {business_address['state']} {business_address['zip_code']}"
        
        profile = {
            # Core business information
            'business_name': self.fake.company(),
            'business_type': business_type,
            'ein': self._generate_ein(),
            'years_in_business': self.fake.random.randint(2, 15),
            'loan_amount': loan_amount,
            'annual_revenue': round(revenue, 2),
            'net_income': round(net_income, 2),
            'profit_margin': profit_margin,
            'employees': self.fake.random.randint(1, 50),
            'bank_name': self.fake.random.choice([
                'Chase Bank', 'Bank of America', 'Wells Fargo', 'Citibank',
                'PNC Bank', 'TD Bank', 'Capital One', 'US Bank'
            ]),
            'account_number': str(self.fake.random.randint(100000000, 999999999)),
            'routing_number': str(self.fake.random.randint(100000000, 999999999)),
            
            # Business address information
            'business_address': business_address_str,
            'business_address_dict': business_address,
            'phone_number': business_metadata['phone'],
            'email': business_metadata['email'],
            
            # Prisma-aligned metadata
            'business_metadata': business_metadata,
            'beneficial_owners': beneficial_owners,
            'personal_financial_statement': pfs_data,
            
            # Additional SBA-specific fields
            'capital_usage': self._generate_capital_usage(loan_amount),
            'debt_schedule': self._generate_debt_schedule(revenue),
            'equipment_quotes': self._generate_equipment_quotes(loan_amount),
            'applicant_questionnaire': self._generate_applicant_questionnaire()
        }
        
        return profile
    
    def _generate_document_set(
        self, 
        app_id: str, 
        app_dir: Path, 
        profile: Dict[str, Any]
    ) -> DocumentSet:
        """Generate complete document set for an application using realistic generators."""
        
        document_set = DocumentSet(
            application_id=app_id,
            document_type='sba_loan_application',
            files={},
            metadata=self._build_prisma_metadata(profile),
            expected_values={},
            generation_timestamp=datetime.now()
        )
        
        # Generate bank statements (realistic PDF format)
        bank_statements = self._generate_realistic_bank_statements(app_dir, profile)
        document_set.files.update(bank_statements)
        
        # Generate tax returns (realistic PDF format)
        tax_returns = self._generate_realistic_tax_returns(app_dir, profile)
        document_set.files.update(tax_returns)
        
        # Generate financial statements (realistic PDF format)
        financial_statements = self._generate_realistic_financial_statements(app_dir, profile)
        document_set.files.update(financial_statements)
        
        # Generate Personal Financial Statement documents (SBA Form 413)
        pfs_documents = self._generate_realistic_pfs_documents(app_dir, profile)
        document_set.files.update(pfs_documents)
        
        # Generate debt schedule documents (realistic format)
        debt_schedule_docs = self._generate_realistic_debt_schedule_documents(app_dir, profile)
        document_set.files.update(debt_schedule_docs)
        
        # Generate equipment quotes documents (keep existing simple format)
        equipment_docs = self._generate_equipment_quote_documents(app_dir, profile)
        document_set.files.update(equipment_docs)
        
        # Generate business reports (PDF format)
        business_reports = self._generate_business_reports(app_dir, profile)
        document_set.files.update(business_reports)
        
        # Set expected values for testing
        document_set.expected_values = self._build_expected_values(profile)
        
        return document_set
    
    def _generate_bank_statements(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate bank statements in Excel format."""
        files = {}
        
        # Generate 12 months of statements
        end_date = datetime.now().date()
        
        for month_offset in range(self.statement_months):
            statement_date = end_date - timedelta(days=30 * month_offset)
            statement_start = statement_date.replace(day=1)
            
            # Calculate next month for end date
            if statement_date.month == 12:
                statement_end = statement_date.replace(year=statement_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                statement_end = statement_date.replace(month=statement_date.month + 1, day=1) - timedelta(days=1)
            
            # Generate transactions for the month
            transactions = self._generate_monthly_transactions(profile, statement_start, statement_end)
            
            # Create Excel file
            filename = f"bank_statement_{statement_date.strftime('%Y_%m')}.xlsx"
            file_path = app_dir / "bank_statements" / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._create_bank_statement_excel(file_path, profile, statement_start, statement_end, transactions)
            
            files[f'bank_statement_{statement_date.strftime("%Y_%m")}'] = file_path
        
        return files
    
    def _generate_monthly_transactions(
        self, 
        profile: Dict[str, Any], 
        start_date: date, 
        end_date: date
    ) -> List[Dict[str, Any]]:
        """Generate realistic monthly transactions."""
        transactions = []
        
        # Calculate expected monthly revenue
        monthly_revenue = profile['annual_revenue'] / 12
        
        # Generate revenue transactions (deposits)
        num_revenue_transactions = self.fake.random.randint(15, 30)
        total_deposits = 0
        
        for _ in range(num_revenue_transactions):
            # Vary transaction amounts
            amount = round(self.fake.random.uniform(monthly_revenue * 0.01, monthly_revenue * 0.15), 2)
            total_deposits += amount
            
            transaction_date = self.fake.date_between(start_date, end_date)
            
            transactions.append({
                'date': transaction_date,
                'description': self.fake.random.choice([
                    'Customer Payment', 'Sales Deposit', 'Credit Card Processing',
                    'Cash Deposit', 'Wire Transfer In', 'ACH Credit'
                ]),
                'amount': amount,
                'type': 'credit'
            })
        
        # Adjust total to match expected monthly revenue
        adjustment = monthly_revenue - total_deposits
        if abs(adjustment) > monthly_revenue * 0.1:  # Only adjust if significant difference
            transactions.append({
                'date': end_date,
                'description': 'Month End Adjustment',
                'amount': abs(adjustment),
                'type': 'credit' if adjustment > 0 else 'debit'
            })
        
        # Generate expense transactions (debits)
        expense_types = [
            ('Rent Payment', monthly_revenue * 0.08),
            ('Payroll', monthly_revenue * 0.35),
            ('Utilities', monthly_revenue * 0.02),
            ('Supplies', monthly_revenue * 0.05),
            ('Insurance', monthly_revenue * 0.02),
            ('Marketing', monthly_revenue * 0.03),
            ('Equipment', monthly_revenue * 0.02),
            ('Professional Services', monthly_revenue * 0.01),
        ]
        
        for desc, base_amount in expense_types:
            # Add some variance
            amount = round(base_amount * self.fake.random.uniform(0.7, 1.3), 2)
            transaction_date = self.fake.date_between(start_date, end_date)
            
            transactions.append({
                'date': transaction_date,
                'description': desc,
                'amount': amount,
                'type': 'debit'
            })
        
        # Sort by date
        transactions.sort(key=lambda x: x['date'])
        
        return transactions
    
    def _create_bank_statement_excel(
        self, 
        file_path: Path, 
        profile: Dict[str, Any], 
        start_date: date, 
        end_date: date, 
        transactions: List[Dict[str, Any]]
    ) -> None:
        """Create bank statement Excel file."""
        
        # Create header information
        header_data = {
            'Bank Name': profile['bank_name'],
            'Account Holder': profile['business_name'],
            'Account Number': profile['account_number'],
            'Routing Number': profile['routing_number'],
            'Statement Period': f"{start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}",
            'Statement Date': end_date.strftime('%m/%d/%Y')
        }
        
        # Calculate balances
        beginning_balance = round(self.fake.random.uniform(5000, 50000), 2)
        running_balance = beginning_balance
        
        # Prepare transaction data with running balance
        transaction_data = []
        for txn in transactions:
            if txn['type'] == 'credit':
                running_balance += txn['amount']
                amount_str = f"${txn['amount']:,.2f}"
            else:
                running_balance -= txn['amount']
                amount_str = f"-${txn['amount']:,.2f}"
            
            transaction_data.append({
                'Date': txn['date'].strftime('%m/%d/%Y'),
                'Description': txn['description'],
                'Amount': amount_str,
                'Balance': f"${running_balance:,.2f}"
            })
        
        ending_balance = running_balance
        
        # Create Excel workbook
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Header sheet
            header_df = pd.DataFrame(list(header_data.items()), columns=['Field', 'Value'])
            header_df.to_excel(writer, sheet_name='Account_Info', index=False)
            
            # Summary sheet
            summary_data = {
                'Beginning Balance': f"${beginning_balance:,.2f}",
                'Total Credits': f"${sum(t['amount'] for t in transactions if t['type'] == 'credit'):,.2f}",
                'Total Debits': f"${sum(t['amount'] for t in transactions if t['type'] == 'debit'):,.2f}",
                'Ending Balance': f"${ending_balance:,.2f}",
                'Number of Transactions': len(transactions)
            }
            summary_df = pd.DataFrame(list(summary_data.items()), columns=['Description', 'Amount'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Transactions sheet
            transactions_df = pd.DataFrame(transaction_data)
            transactions_df.to_excel(writer, sheet_name='Transactions', index=False)
    
    def _generate_tax_returns(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate tax returns in PDF format."""
        files = {}
        
        # Generate returns for the last 3 years
        current_year = datetime.now().year
        
        for year_offset in range(3):
            tax_year = current_year - 1 - year_offset  # Previous years only
            
            filename = f"tax_return_{tax_year}.pdf"
            file_path = app_dir / "tax_returns" / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._create_tax_return_pdf(file_path, profile, tax_year)
            
            files[f'tax_return_{tax_year}'] = file_path
        
        return files
    
    def _create_tax_return_pdf(self, file_path: Path, profile: Dict[str, Any], tax_year: int) -> None:
        """Create tax return PDF file."""
        c = canvas.Canvas(str(file_path), pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Form 1120 - U.S. Corporation Income Tax Return")
        c.drawString(50, height - 70, f"Tax Year: {tax_year}")
        
        # Business Information
        c.setFont("Helvetica", 12)
        y_pos = height - 120
        
        business_info = [
            f"Business Name: {profile['business_name']}",
            f"EIN: {profile['ein']}",
            f"Business Address: {profile['business_address'].replace(chr(10), ', ')}",
            f"Business Type: {profile['business_type']}",
        ]
        
        for info in business_info:
            c.drawString(50, y_pos, info)
            y_pos -= 20
        
        # Financial Information
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Financial Summary:")
        
        y_pos -= 20
        c.setFont("Helvetica", 12)
        
        # Calculate historical figures (slightly less than current year)
        years_ago = datetime.now().year - tax_year
        revenue_factor = 0.95 ** years_ago  # Slight growth each year
        
        historical_revenue = profile['annual_revenue'] * revenue_factor
        historical_expenses = historical_revenue * (1 - profile['profit_margin'])
        historical_net_income = historical_revenue - historical_expenses
        
        financial_info = [
            f"Gross Receipts: ${historical_revenue:,.2f}",
            f"Total Deductions: ${historical_expenses:,.2f}",
            f"Taxable Income: ${historical_net_income:,.2f}",
            f"Income Tax: ${historical_net_income * 0.21:,.2f}",  # 21% corporate rate
        ]
        
        for info in financial_info:
            c.drawString(50, y_pos, info)
            y_pos -= 20
        
        # Signature area
        c.drawString(50, 100, "Prepared by: [Tax Professional Name]")
        c.drawString(50, 80, "Date: " + date(tax_year + 1, 4, 15).strftime('%m/%d/%Y'))  # Tax filing date
        
        c.save()
    
    def _generate_financial_statements(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate financial statements in Excel format."""
        files = {}
        
        # Generate profit & loss statement
        pl_filename = "profit_loss_statement.xlsx"
        pl_file_path = app_dir / "financial" / pl_filename
        pl_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_profit_loss_excel(pl_file_path, profile)
        files['profit_loss_statement'] = pl_file_path
        
        # Generate balance sheet
        bs_filename = "balance_sheet.xlsx"
        bs_file_path = app_dir / "financial" / bs_filename
        self._create_balance_sheet_excel(bs_file_path, profile)
        files['balance_sheet'] = bs_file_path
        
        # Generate cash flow statement
        cf_filename = "cash_flow_statement.xlsx"
        cf_file_path = app_dir / "financial" / cf_filename
        self._create_cash_flow_excel(cf_file_path, profile)
        files['cash_flow_statement'] = cf_file_path
        
        return files
    
    def _create_profit_loss_excel(self, file_path: Path, profile: Dict[str, Any]) -> None:
        """Create profit & loss statement Excel file."""
        revenue = profile['annual_revenue']
        net_income = profile['net_income']
        expenses = revenue - net_income
        
        # Break down expenses by category
        expense_breakdown = {
            'Cost of Goods Sold': expenses * 0.4,
            'Salaries and Wages': expenses * 0.35,
            'Rent': expenses * 0.08,
            'Utilities': expenses * 0.02,
            'Marketing': expenses * 0.03,
            'Insurance': expenses * 0.02,
            'Professional Services': expenses * 0.02,
            'Depreciation': expenses * 0.03,
            'Other Operating Expenses': expenses * 0.05
        }
        
        # Create data
        pl_data = [
            ['REVENUE', ''],
            ['Gross Revenue', f'${revenue:,.2f}'],
            ['', ''],
            ['EXPENSES', ''],
        ]
        
        for expense_type, amount in expense_breakdown.items():
            pl_data.append([expense_type, f'${amount:,.2f}'])
        
        pl_data.extend([
            ['', ''],
            ['Total Expenses', f'${expenses:,.2f}'],
            ['', ''],
            ['NET INCOME', f'${net_income:,.2f}']
        ])
        
        # Create DataFrame and save
        df = pd.DataFrame(pl_data, columns=['Description', 'Amount'])
        df.to_excel(file_path, index=False)
    
    def _create_balance_sheet_excel(self, file_path: Path, profile: Dict[str, Any]) -> None:
        """Create balance sheet Excel file."""
        # Estimate balance sheet values based on business profile
        annual_revenue = profile['annual_revenue']
        
        # Assets (rough estimates based on business size)
        current_assets = {
            'Cash': annual_revenue * 0.1,
            'Accounts Receivable': annual_revenue * 0.15,
            'Inventory': annual_revenue * 0.2,
            'Prepaid Expenses': annual_revenue * 0.02
        }
        
        fixed_assets = {
            'Equipment': annual_revenue * 0.3,
            'Furniture & Fixtures': annual_revenue * 0.05,
            'Less: Accumulated Depreciation': -annual_revenue * 0.1
        }
        
        # Liabilities
        current_liabilities = {
            'Accounts Payable': annual_revenue * 0.12,
            'Accrued Expenses': annual_revenue * 0.08,
            'Short-term Debt': annual_revenue * 0.05
        }
        
        long_term_liabilities = {
            'Long-term Debt': annual_revenue * 0.15
        }
        
        # Equity (balancing figure)
        total_assets = sum(current_assets.values()) + sum(fixed_assets.values())
        total_liabilities = sum(current_liabilities.values()) + sum(long_term_liabilities.values())
        equity = total_assets - total_liabilities
        
        # Create data
        bs_data = [
            ['ASSETS', ''],
            ['Current Assets:', ''],
        ]
        
        for asset, amount in current_assets.items():
            bs_data.append([f'  {asset}', f'${amount:,.2f}'])
        
        bs_data.append(['Total Current Assets', f'${sum(current_assets.values()):,.2f}'])
        bs_data.extend([['', ''], ['Fixed Assets:', '']])
        
        for asset, amount in fixed_assets.items():
            bs_data.append([f'  {asset}', f'${amount:,.2f}'])
        
        bs_data.extend([
            ['Total Fixed Assets', f'${sum(fixed_assets.values()):,.2f}'],
            ['', ''],
            ['TOTAL ASSETS', f'${total_assets:,.2f}'],
            ['', ''],
            ['LIABILITIES', ''],
            ['Current Liabilities:', '']
        ])
        
        for liability, amount in current_liabilities.items():
            bs_data.append([f'  {liability}', f'${amount:,.2f}'])
        
        bs_data.append(['Total Current Liabilities', f'${sum(current_liabilities.values()):,.2f}'])
        bs_data.extend([['', ''], ['Long-term Liabilities:', '']])
        
        for liability, amount in long_term_liabilities.items():
            bs_data.append([f'  {liability}', f'${amount:,.2f}'])
        
        bs_data.extend([
            ['Total Long-term Liabilities', f'${sum(long_term_liabilities.values()):,.2f}'],
            ['', ''],
            ['TOTAL LIABILITIES', f'${total_liabilities:,.2f}'],
            ['', ''],
            ['EQUITY', ''],
            ['  Retained Earnings', f'${equity:,.2f}'],
            ['TOTAL EQUITY', f'${equity:,.2f}'],
            ['', ''],
            ['TOTAL LIABILITIES + EQUITY', f'${total_liabilities + equity:,.2f}']
        ])
        
        # Create DataFrame and save
        df = pd.DataFrame(bs_data, columns=['Description', 'Amount'])
        df.to_excel(file_path, index=False)
    
    def _create_cash_flow_excel(self, file_path: Path, profile: Dict[str, Any]) -> None:
        """Create cash flow statement Excel file."""
        net_income = profile['net_income']
        
        # Operating activities
        operating_cf = net_income * 1.2  # Usually higher than net income due to depreciation, etc.
        
        # Investing activities (equipment purchases, etc.)
        investing_cf = -profile['annual_revenue'] * 0.05
        
        # Financing activities (loan payments, owner contributions)
        financing_cf = -profile['annual_revenue'] * 0.02
        
        net_cf = operating_cf + investing_cf + financing_cf
        
        cf_data = [
            ['CASH FLOW FROM OPERATING ACTIVITIES', ''],
            ['Net Income', f'${net_income:,.2f}'],
            ['Adjustments:', ''],
            ['  Depreciation', f'${profile["annual_revenue"] * 0.03:,.2f}'],
            ['  Changes in Working Capital', f'${net_income * 0.1:,.2f}'],
            ['Net Cash from Operating Activities', f'${operating_cf:,.2f}'],
            ['', ''],
            ['CASH FLOW FROM INVESTING ACTIVITIES', ''],
            ['Equipment Purchases', f'${investing_cf:,.2f}'],
            ['Net Cash from Investing Activities', f'${investing_cf:,.2f}'],
            ['', ''],
            ['CASH FLOW FROM FINANCING ACTIVITIES', ''],
            ['Loan Payments', f'${financing_cf:,.2f}'],
            ['Net Cash from Financing Activities', f'${financing_cf:,.2f}'],
            ['', ''],
            ['NET CHANGE IN CASH', f'${net_cf:,.2f}'],
            ['Cash at Beginning of Year', f'${profile["annual_revenue"] * 0.08:,.2f}'],
            ['Cash at End of Year', f'${net_cf + profile["annual_revenue"] * 0.08:,.2f}']
        ]
        
        # Create DataFrame and save
        df = pd.DataFrame(cf_data, columns=['Description', 'Amount'])
        df.to_excel(file_path, index=False)
    
    def _generate_business_reports(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate business reports in PDF format."""
        files = {}
        
        # Generate business plan summary
        bp_filename = "business_plan_summary.pdf"
        bp_file_path = app_dir / "reports" / bp_filename
        bp_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_business_plan_pdf(bp_file_path, profile)
        files['business_plan_summary'] = bp_file_path
        
        # Generate loan application form
        app_filename = "loan_application_form.pdf"
        app_file_path = app_dir / "reports" / app_filename
        self._create_loan_application_pdf(app_file_path, profile)
        files['loan_application_form'] = app_file_path
        
        return files
    
    def _create_business_plan_pdf(self, file_path: Path, profile: Dict[str, Any]) -> None:
        """Create business plan summary PDF."""
        c = canvas.Canvas(str(file_path), pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, height - 50, "Business Plan Summary")
        
        # Business overview
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 100, "Business Overview")
        
        c.setFont("Helvetica", 12)
        y_pos = height - 130
        
        overview_text = [
            f"{profile['business_name']} is a {profile['business_type'].lower()} business",
            f"established {profile['years_in_business']} years ago. The company specializes in",
            "providing high-quality products/services to our customer base.",
            "",
            f"Current annual revenue: ${profile['annual_revenue']:,.2f}",
            f"Number of employees: {profile['employees']}",
            f"Requested loan amount: ${profile['loan_amount']:,.2f}"
        ]
        
        for line in overview_text:
            c.drawString(50, y_pos, line)
            y_pos -= 20
        
        # Market analysis section
        y_pos -= 20
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Market Analysis")
        
        y_pos -= 30
        c.setFont("Helvetica", 12)
        market_text = [
            f"The {profile['business_type'].lower()} industry has shown steady growth",
            "over the past several years. Our business is well-positioned to",
            "capitalize on market opportunities and expand our operations."
        ]
        
        for line in market_text:
            c.drawString(50, y_pos, line)
            y_pos -= 20
        
        # Use of funds section
        y_pos -= 20
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y_pos, "Use of Loan Proceeds")
        
        y_pos -= 30
        c.setFont("Helvetica", 12)
        
        # Allocate loan amount across categories
        equipment_pct = 0.4
        inventory_pct = 0.3
        working_capital_pct = 0.2
        marketing_pct = 0.1
        
        use_of_funds = [
            f"Equipment & Machinery: ${profile['loan_amount'] * equipment_pct:,.2f} ({equipment_pct*100:.0f}%)",
            f"Inventory: ${profile['loan_amount'] * inventory_pct:,.2f} ({inventory_pct*100:.0f}%)",
            f"Working Capital: ${profile['loan_amount'] * working_capital_pct:,.2f} ({working_capital_pct*100:.0f}%)",
            f"Marketing: ${profile['loan_amount'] * marketing_pct:,.2f} ({marketing_pct*100:.0f}%)"
        ]
        
        for line in use_of_funds:
            c.drawString(50, y_pos, line)
            y_pos -= 20
        
        c.save()
    
    def _create_loan_application_pdf(self, file_path: Path, profile: Dict[str, Any]) -> None:
        """Create loan application form PDF."""
        c = canvas.Canvas(str(file_path), pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, "SBA Loan Application Form")
        
        # Applicant Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, height - 100, "Applicant Information")
        
        c.setFont("Helvetica", 10)
        y_pos = height - 130
        
        applicant_info = [
            f"Business Legal Name: {profile['business_name']}",
            f"EIN: {profile['ein']}",
            f"Business Address: {profile['business_address'].replace(chr(10), ', ')}",
            f"Phone: {profile['phone_number']}",
            f"Email: {profile['email']}",
            f"Years in Business: {profile['years_in_business']}",
            f"Business Type: {profile['business_type']}",
            f"Number of Employees: {profile['employees']}"
        ]
        
        for info in applicant_info:
            c.drawString(50, y_pos, info)
            y_pos -= 15
        
        # Owner Information
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Principal Owner Information")
        
        y_pos -= 20
        c.setFont("Helvetica", 10)
        
        primary_owner = profile.get('beneficial_owners', [{}])[0] if profile.get('beneficial_owners') else {}
        owner_name = primary_owner.get('firstName', '') + ' ' + primary_owner.get('lastName', '') if primary_owner else 'Unknown'
        owner_ssn = primary_owner.get('ssn', 'XXX-XX-XXXX')
        
        owner_info = [
            f"Owner Name: {owner_name}",
            f"SSN: {owner_ssn}"
        ]
        
        for info in owner_info:
            c.drawString(50, y_pos, info)
            y_pos -= 15
        
        # Loan Information
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Loan Request Information")
        
        y_pos -= 20
        c.setFont("Helvetica", 10)
        
        loan_info = [
            f"Requested Loan Amount: ${profile['loan_amount']:,.2f}",
            "Loan Purpose: Business expansion and working capital",
            "Requested Loan Term: 5 years",
            f"Annual Revenue: ${profile['annual_revenue']:,.2f}",
            f"Net Income: ${profile['net_income']:,.2f}"
        ]
        
        for info in loan_info:
            c.drawString(50, y_pos, info)
            y_pos -= 15
        
        # Signature line
        c.drawString(50, 100, "Applicant Signature: _________________________  Date: _______________")
        
        c.save()
    
    def _generate_ein(self) -> str:
        """Generate a properly formatted EIN."""
        # EIN format: XX-XXXXXXX
        first_two = self.fake.random.randint(10, 99)
        last_seven = self.fake.random.randint(1000000, 9999999)
        return f"{first_two}-{last_seven}"
    
    def _generate_beneficial_owners(self) -> List[Dict[str, Any]]:
        """Generate multiple beneficial owners with ownership percentages that sum to 100%."""
        num_owners = self.fake.random.randint(1, 4)
        owners = []
        remaining_percentage = 100.0
        
        for i in range(num_owners):
            if i == num_owners - 1:
                # Last owner gets remaining percentage
                ownership_percentage = remaining_percentage
            else:
                # Generate percentage, leaving at least 10% for remaining owners
                max_percentage = min(90, remaining_percentage - (10 * (num_owners - i - 1)))
                ownership_percentage = round(self.fake.random.uniform(10, max_percentage), 1)
                remaining_percentage -= ownership_percentage
            
            owner = {
                'name': self.fake.name(),
                'ssn': self._generate_ssn(),
                'date_of_birth': self.fake.date_of_birth(minimum_age=25, maximum_age=75).isoformat(),
                'ownership_percentage': ownership_percentage,
                'title': self.fake.random.choice(['CEO', 'President', 'Owner', 'Managing Partner', 'Director']),
                'address': {
                    'street': self.fake.street_address(),
                    'city': self.fake.city(),
                    'state': self.fake.state_abbr(),
                    'zip_code': self.fake.zipcode(),
                    'country': 'US'
                },
                'phone': self.fake.phone_number(),
                'email': self.fake.email(),
                'citizenship_status': self.fake.random.choice(['US_CITIZEN', 'PERMANENT_RESIDENT', 'OTHER']),
                'criminal_background': False,  # For simplicity
                'bankruptcy_history': False
            }
            owners.append(owner)
        
        return owners
    
    def _generate_ssn(self) -> str:
        """Generate a properly formatted SSN."""
        # SSN format: XXX-XX-XXXX (avoiding certain invalid ranges)
        area = self.fake.random.randint(100, 799)  # Avoid 000, 666, 900-999
        if area == 666:
            area = 667
        group = self.fake.random.randint(10, 99)
        serial = self.fake.random.randint(1000, 9999)
        return f"{area:03d}-{group:02d}-{serial:04d}"
    
    def _generate_business_metadata(self, business_type: str, revenue: float, net_income: float) -> Dict[str, Any]:
        """Generate business metadata aligned with Prisma BusinessMetadata model."""
        address = {
            'street': self.fake.street_address(),
            'city': self.fake.city(),
            'state': self.fake.state_abbr(),
            'zip_code': self.fake.zipcode(),
            'country': 'US'
        }
        
        return {
            'name': self.fake.company(),
            'type': business_type,
            'entity_type': self.fake.random.choice(['LLC', 'Corporation', 'Partnership', 'Sole Proprietorship']),
            'industry': self._get_industry_for_business_type(business_type),
            'naics_code': self._get_naics_code_for_business_type(business_type),
            'date_established': self.fake.date_between(start_date='-15y', end_date='-2y').isoformat(),
            'number_of_employees': self.fake.random.randint(1, 50),
            'annual_revenue': round(revenue, 2),
            'net_income': round(net_income, 2),
            'address': address,
            'phone': self.fake.phone_number(),
            'email': self.fake.email(),
            'website': f"https://www.{self.fake.domain_name()}",
            'federal_tax_id': self._generate_ein(),
            'state_tax_id': str(self.fake.random.randint(1000000, 9999999)),
            'business_license': str(self.fake.random.randint(100000, 999999)),
            'years_in_business': self.fake.random.randint(2, 15),
            'business_description': f"A {business_type.lower()} business providing quality products and services to customers."
        }
    
    def _get_industry_for_business_type(self, business_type: str) -> str:
        """Map business type to industry classification."""
        industry_map = {
            'Restaurant': 'Food Service',
            'Retail Store': 'Retail Trade',
            'Manufacturing': 'Manufacturing',
            'Construction': 'Construction',
            'Professional Services': 'Professional Services',
            'Technology': 'Information Technology',
            'Healthcare': 'Healthcare'
        }
        return industry_map.get(business_type, 'Other Services')
    
    def _get_naics_code_for_business_type(self, business_type: str) -> str:
        """Get NAICS code for business type."""
        naics_map = {
            'Restaurant': '722511',
            'Retail Store': '453998',
            'Manufacturing': '311999',
            'Construction': '236118',
            'Professional Services': '541990',
            'Technology': '541511',
            'Healthcare': '621999'
        }
        return naics_map.get(business_type, '999999')
    
    def _generate_personal_financial_statement(self, business_revenue: float) -> Dict[str, Any]:
        """Generate comprehensive Personal Financial Statement with 20+ categories."""
        # Generate assets
        assets = self._generate_pfs_assets(business_revenue)
        
        # Generate liabilities
        liabilities = self._generate_pfs_liabilities(business_revenue)
        
        # Calculate totals - handle nested structures properly
        def calculate_total(data_dict):
            total = 0
            for key, value in data_dict.items():
                if isinstance(value, (int, float)):
                    total += value
                elif isinstance(value, dict):
                    # Recursively sum nested dicts
                    total += calculate_total(value)
                elif isinstance(value, list):
                    # Sum values in list of dicts
                    for item in value:
                        if isinstance(item, dict):
                            if 'balance' in item:
                                total += item['balance']
                            elif 'value' in item:
                                total += item['value']
                            elif 'amount' in item:
                                total += item['amount']
            return total
        
        total_assets = calculate_total(assets)
        total_liabilities = calculate_total(liabilities)
        
        net_worth = total_assets - total_liabilities
        
        # Generate income and expenses
        income = self._generate_pfs_income(business_revenue)
        expenses = self._generate_pfs_expenses(business_revenue)
        
        return {
            'assets': assets,
            'liabilities': liabilities,
            'income': income,
            'expenses': expenses,
            'total_assets': round(total_assets, 2),
            'total_liabilities': round(total_liabilities, 2),
            'net_worth': round(net_worth, 2),
            'contingent_liabilities': self._generate_contingent_liabilities(),
            'statement_date': datetime.now().date().isoformat()
        }
    
    def _generate_pfs_assets(self, business_revenue: float) -> Dict[str, Any]:
        """Generate comprehensive PFS assets with 20+ categories."""
        base_amount = business_revenue * 0.3  # Base asset calculation
        
        return {
            'cash_and_cash_equivalents': {
                'cash_on_hand': round(self.fake.random.uniform(1000, 10000), 2),
                'checking_accounts': [
                    {
                        'bank_name': 'Chase Bank',
                        'account_number': '****' + str(self.fake.random.randint(1000, 9999)),
                        'balance': round(self.fake.random.uniform(5000, 50000), 2)
                    },
                    {
                        'bank_name': 'Wells Fargo',
                        'account_number': '****' + str(self.fake.random.randint(1000, 9999)),
                        'balance': round(self.fake.random.uniform(2000, 30000), 2)
                    }
                ],
                'savings_accounts': [
                    {
                        'bank_name': 'Chase Bank',
                        'account_number': '****' + str(self.fake.random.randint(1000, 9999)),
                        'balance': round(self.fake.random.uniform(10000, 100000), 2)
                    }
                ],
                'money_market_accounts': round(self.fake.random.uniform(5000, 50000), 2),
                'certificates_of_deposit': round(self.fake.random.uniform(0, 25000), 2)
            },
            'securities': {
                'publicly_traded_stocks': [
                    {
                        'symbol': 'AAPL',
                        'shares': self.fake.random.randint(50, 500),
                        'market_value': round(self.fake.random.uniform(10000, 80000), 2)
                    },
                    {
                        'symbol': 'MSFT',
                        'shares': self.fake.random.randint(25, 300),
                        'market_value': round(self.fake.random.uniform(5000, 60000), 2)
                    }
                ],
                'bonds': round(self.fake.random.uniform(0, 50000), 2),
                'mutual_funds': round(self.fake.random.uniform(10000, 100000), 2),
                'retirement_accounts_401k': round(base_amount * 0.5, 2),
                'retirement_accounts_ira': round(base_amount * 0.3, 2),
                'other_securities': round(self.fake.random.uniform(0, 25000), 2)
            },
            'real_estate': [
                {
                    'property_type': 'Primary Residence',
                    'address': {
                        'street': self.fake.street_address(),
                        'city': self.fake.city(),
                        'state': self.fake.state_abbr(),
                        'zip_code': self.fake.zipcode()
                    },
                    'market_value': round(self.fake.random.uniform(200000, 800000), 2),
                    'mortgage_balance': round(self.fake.random.uniform(100000, 600000), 2),
                    'monthly_payment': round(self.fake.random.uniform(1200, 4000), 2),
                    'rental_income': 0  # Primary residence
                },
                {
                    'property_type': 'Investment Property',
                    'address': {
                        'street': self.fake.street_address(),
                        'city': self.fake.city(),
                        'state': self.fake.state_abbr(),
                        'zip_code': self.fake.zipcode()
                    },
                    'market_value': round(self.fake.random.uniform(150000, 500000), 2),
                    'mortgage_balance': round(self.fake.random.uniform(80000, 400000), 2),
                    'monthly_payment': round(self.fake.random.uniform(800, 2500), 2),
                    'rental_income': round(self.fake.random.uniform(1200, 3000), 2)
                }
            ],
            'personal_property': {
                'vehicles': [
                    {
                        'year': 2021,
                        'make': 'BMW',
                        'model': 'X5',
                        'market_value': round(self.fake.random.uniform(40000, 70000), 2),
                        'loan_balance': round(self.fake.random.uniform(20000, 50000), 2)
                    },
                    {
                        'year': 2019,
                        'make': 'Honda',
                        'model': 'Accord',
                        'market_value': round(self.fake.random.uniform(20000, 30000), 2),
                        'loan_balance': round(self.fake.random.uniform(5000, 20000), 2)
                    }
                ],
                'jewelry_and_collectibles': round(self.fake.random.uniform(5000, 25000), 2),
                'furniture_and_fixtures': round(self.fake.random.uniform(10000, 40000), 2),
                'art_and_antiques': round(self.fake.random.uniform(0, 50000), 2),
                'other_personal_property': round(self.fake.random.uniform(5000, 20000), 2)
            },
            'business_interests': {
                'ownership_in_business': round(base_amount * 0.8, 2),
                'partnership_interests': round(self.fake.random.uniform(0, 100000), 2),
                'business_equipment': round(self.fake.random.uniform(10000, 100000), 2),
                'accounts_receivable': round(base_amount * 0.1, 2)
            },
            'other_assets': {
                'life_insurance_cash_value': round(self.fake.random.uniform(10000, 50000), 2),
                'notes_receivable': round(self.fake.random.uniform(0, 25000), 2),
                'tax_refunds_due': round(self.fake.random.uniform(0, 5000), 2),
                'prepaid_expenses': round(self.fake.random.uniform(2000, 10000), 2),
                'other_miscellaneous': round(self.fake.random.uniform(0, 15000), 2)
            }
        }
    
    def _generate_pfs_liabilities(self, business_revenue: float) -> Dict[str, Any]:
        """Generate comprehensive PFS liabilities."""
        return {
            'current_liabilities': {
                'accounts_payable': round(business_revenue * 0.05, 2),
                'credit_cards': [
                    {
                        'creditor': 'Chase Sapphire',
                        'balance': round(self.fake.random.uniform(2000, 15000), 2),
                        'monthly_payment': round(self.fake.random.uniform(100, 500), 2),
                        'credit_limit': round(self.fake.random.uniform(15000, 50000), 2)
                    },
                    {
                        'creditor': 'American Express',
                        'balance': round(self.fake.random.uniform(1000, 8000), 2),
                        'monthly_payment': round(self.fake.random.uniform(50, 300), 2),
                        'credit_limit': round(self.fake.random.uniform(10000, 30000), 2)
                    }
                ],
                'short_term_notes_payable': round(self.fake.random.uniform(0, 25000), 2),
                'accrued_expenses': round(self.fake.random.uniform(1000, 10000), 2),
                'taxes_payable': round(self.fake.random.uniform(2000, 20000), 2)
            },
            'long_term_liabilities': {
                'real_estate_mortgages': [
                    {
                        'property': 'Primary Residence',
                        'lender': 'Wells Fargo Mortgage',
                        'original_amount': round(self.fake.random.uniform(300000, 700000), 2),
                        'current_balance': round(self.fake.random.uniform(200000, 600000), 2),
                        'monthly_payment': round(self.fake.random.uniform(1500, 4000), 2),
                        'interest_rate': round(self.fake.random.uniform(2.5, 6.0), 2),
                        'maturity_date': (datetime.now().date() + timedelta(days=365*20)).isoformat()
                    }
                ],
                'vehicle_loans': [
                    {
                        'vehicle': '2021 BMW X5',
                        'lender': 'BMW Financial',
                        'original_amount': round(self.fake.random.uniform(50000, 80000), 2),
                        'current_balance': round(self.fake.random.uniform(25000, 60000), 2),
                        'monthly_payment': round(self.fake.random.uniform(400, 800), 2),
                        'interest_rate': round(self.fake.random.uniform(2.9, 7.5), 2),
                        'maturity_date': (datetime.now().date() + timedelta(days=365*4)).isoformat()
                    }
                ],
                'student_loans': [
                    {
                        'lender': 'Federal Student Aid',
                        'original_amount': round(self.fake.random.uniform(30000, 100000), 2),
                        'current_balance': round(self.fake.random.uniform(15000, 75000), 2),
                        'monthly_payment': round(self.fake.random.uniform(200, 800), 2),
                        'interest_rate': round(self.fake.random.uniform(3.0, 6.5), 2)
                    }
                ],
                'business_loans': [
                    {
                        'lender': 'Chase Business Banking',
                        'original_amount': round(self.fake.random.uniform(50000, 250000), 2),
                        'current_balance': round(self.fake.random.uniform(25000, 200000), 2),
                        'monthly_payment': round(self.fake.random.uniform(500, 2000), 2),
                        'interest_rate': round(self.fake.random.uniform(4.5, 12.0), 2),
                        'collateral': 'Business Equipment and Inventory'
                    }
                ],
                'other_long_term_debt': round(self.fake.random.uniform(0, 50000), 2)
            },
            'contingent_liabilities': {
                'guarantees': round(self.fake.random.uniform(0, 100000), 2),
                'pending_lawsuits': 0,  # For simplicity
                'other_contingent': round(self.fake.random.uniform(0, 25000), 2)
            }
        }
    
    def _generate_pfs_income(self, business_revenue: float) -> Dict[str, Any]:
        """Generate PFS income information."""
        monthly_business_income = business_revenue / 12
        
        return {
            'salary_wages': round(monthly_business_income * 0.6, 2),
            'business_income': round(monthly_business_income * 0.3, 2),
            'rental_income': round(self.fake.random.uniform(1000, 3000), 2),
            'investment_income': round(self.fake.random.uniform(500, 2000), 2),
            'retirement_income': 0,  # Assuming working age
            'social_security': 0,
            'alimony_child_support': 0,
            'other_income': round(self.fake.random.uniform(0, 1000), 2),
            'total_monthly_income': round(monthly_business_income + self.fake.random.uniform(1500, 6000), 2)
        }
    
    def _generate_pfs_expenses(self, business_revenue: float) -> Dict[str, Any]:
        """Generate PFS expense information."""
        monthly_income = business_revenue / 12
        
        return {
            'housing_mortgage_rent': round(monthly_income * 0.25, 2),
            'property_taxes': round(monthly_income * 0.03, 2),
            'utilities': round(self.fake.random.uniform(300, 800), 2),
            'food_groceries': round(self.fake.random.uniform(600, 1200), 2),
            'transportation': round(self.fake.random.uniform(400, 1000), 2),
            'insurance_life_health': round(self.fake.random.uniform(500, 1500), 2),
            'insurance_property': round(self.fake.random.uniform(200, 600), 2),
            'medical_dental': round(self.fake.random.uniform(200, 800), 2),
            'education': round(self.fake.random.uniform(0, 1000), 2),
            'childcare': round(self.fake.random.uniform(0, 2000), 2),
            'clothing': round(self.fake.random.uniform(200, 600), 2),
            'entertainment_recreation': round(self.fake.random.uniform(300, 1000), 2),
            'charitable_contributions': round(self.fake.random.uniform(100, 800), 2),
            'loan_payments': round(self.fake.random.uniform(800, 2500), 2),
            'credit_card_payments': round(self.fake.random.uniform(200, 800), 2),
            'taxes_income': round(monthly_income * 0.18, 2),
            'other_expenses': round(self.fake.random.uniform(300, 1000), 2),
            'total_monthly_expenses': round(monthly_income * 0.75, 2)
        }
    
    def _generate_contingent_liabilities(self) -> Dict[str, Any]:
        """Generate contingent liabilities."""
        return {
            'guarantees_for_others': round(self.fake.random.uniform(0, 50000), 2),
            'pending_legal_claims': 0,
            'tax_liabilities': round(self.fake.random.uniform(0, 10000), 2),
            'other_contingent': round(self.fake.random.uniform(0, 15000), 2)
        }
    
    def _generate_capital_usage(self, loan_amount: float) -> Dict[str, Any]:
        """Generate capital usage breakdown."""
        # Distribute loan amount across different uses
        equipment_pct = self.fake.random.uniform(0.3, 0.5)
        working_capital_pct = self.fake.random.uniform(0.2, 0.4)
        inventory_pct = self.fake.random.uniform(0.1, 0.3)
        
        # Normalize percentages to sum to 1.0
        total_pct = equipment_pct + working_capital_pct + inventory_pct
        equipment_pct /= total_pct
        working_capital_pct /= total_pct
        inventory_pct /= total_pct
        
        # Calculate remaining percentage for other uses
        other_pct = 1.0 - (equipment_pct + working_capital_pct + inventory_pct)
        
        return {
            'equipment_machinery': {
                'amount': round(loan_amount * equipment_pct, 2),
                'percentage': round(equipment_pct * 100, 1),
                'description': 'Purchase of new equipment and machinery for business operations'
            },
            'working_capital': {
                'amount': round(loan_amount * working_capital_pct, 2),
                'percentage': round(working_capital_pct * 100, 1),
                'description': 'General working capital for day-to-day operations'
            },
            'inventory': {
                'amount': round(loan_amount * inventory_pct, 2),
                'percentage': round(inventory_pct * 100, 1),
                'description': 'Purchase of inventory and raw materials'
            },
            'other_uses': {
                'amount': round(loan_amount * other_pct, 2),
                'percentage': round(other_pct * 100, 1),
                'description': 'Marketing, renovations, and other business expenses'
            },
            'total_amount': loan_amount,
            'justification': f'The requested loan will enable business expansion and improve operational efficiency through strategic investments in equipment, inventory, and working capital.'
        }
    
    def _generate_debt_schedule(self, annual_revenue: float) -> List[Dict[str, Any]]:
        """Generate comprehensive debt schedule."""
        debts = []
        
        # Business credit line
        debts.append({
            'creditor_name': 'Chase Business Credit Line',
            'original_amount': round(self.fake.random.uniform(50000, 150000), 2),
            'current_balance': round(self.fake.random.uniform(20000, 100000), 2),
            'monthly_payment': round(self.fake.random.uniform(500, 1500), 2),
            'interest_rate': round(self.fake.random.uniform(6.5, 12.0), 2),
            'maturity_date': (datetime.now().date() + timedelta(days=365*3)).isoformat(),
            'collateral': 'Business Assets',
            'payment_terms': 'Monthly principal and interest',
            'debt_type': 'BUSINESS_CREDIT_LINE',
            'lender_contact': {
                'name': 'Chase Business Banking',
                'phone': '1-800-CHASE24',
                'address': '270 Park Avenue, New York, NY 10017'
            }
        })
        
        # SBA loan (existing)
        debts.append({
            'creditor_name': 'Wells Fargo SBA Loan',
            'original_amount': round(self.fake.random.uniform(100000, 350000), 2),
            'current_balance': round(self.fake.random.uniform(75000, 300000), 2),
            'monthly_payment': round(self.fake.random.uniform(800, 2500), 2),
            'interest_rate': round(self.fake.random.uniform(7.0, 11.5), 2),
            'maturity_date': (datetime.now().date() + timedelta(days=365*7)).isoformat(),
            'collateral': 'Real Estate and Business Equipment',
            'payment_terms': 'Monthly principal and interest',
            'debt_type': 'SBA_LOAN',
            'lender_contact': {
                'name': 'Wells Fargo Business Banking',
                'phone': '1-800-WELLS24',
                'address': '420 Montgomery Street, San Francisco, CA 94163'
            }
        })
        
        # Equipment financing
        debts.append({
            'creditor_name': 'Equipment Finance Solutions',
            'original_amount': round(self.fake.random.uniform(25000, 100000), 2),
            'current_balance': round(self.fake.random.uniform(15000, 80000), 2),
            'monthly_payment': round(self.fake.random.uniform(300, 1200), 2),
            'interest_rate': round(self.fake.random.uniform(5.5, 9.5), 2),
            'maturity_date': (datetime.now().date() + timedelta(days=365*5)).isoformat(),
            'collateral': 'Financed Equipment',
            'payment_terms': 'Monthly principal and interest',
            'debt_type': 'EQUIPMENT_FINANCING',
            'lender_contact': {
                'name': 'Equipment Finance Solutions',
                'phone': '1-888-555-0123',
                'address': '100 Business Park Drive, Atlanta, GA 30309'
            }
        })
        
        # Business credit cards
        debts.append({
            'creditor_name': 'American Express Business Card',
            'original_amount': round(self.fake.random.uniform(15000, 50000), 2),
            'current_balance': round(self.fake.random.uniform(5000, 30000), 2),
            'monthly_payment': round(self.fake.random.uniform(200, 800), 2),
            'interest_rate': round(self.fake.random.uniform(14.5, 24.9), 2),
            'maturity_date': 'Revolving Credit',
            'collateral': 'Unsecured',
            'payment_terms': 'Minimum monthly payment',
            'debt_type': 'BUSINESS_CREDIT_CARD',
            'credit_limit': round(self.fake.random.uniform(25000, 75000), 2),
            'lender_contact': {
                'name': 'American Express Business',
                'phone': '1-800-492-3344',
                'address': '200 Vesey Street, New York, NY 10285'
            }
        })
        
        return debts
    
    def _build_prisma_metadata(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Build metadata structured according to Prisma schema."""
        return {
            'businessMetadata': profile.get('businessMetadata', {}),
            'beneficialOwners': profile.get('beneficial_owners', []),
            'capitalUsageBreakdown': profile.get('capital_usage', {}),
            'debtScheduleItems': profile.get('debt_schedule', []),
            'equipmentQuotes': profile.get('equipment_quotes', []),
            'applicantQuestionnaire': profile.get('applicant_questionnaire', {}),
            'personalFinancialStatements': profile.get('personal_financial_statements', []),
            'loanAmount': profile.get('loan_amount', 0),
            'businessProfile': profile
        }
    
    def _generate_equipment_quotes(self, loan_amount: float) -> List[Dict[str, Any]]:
        """Generate equipment quotes with vendor information."""
        quotes = []
        equipment_budget = loan_amount * 0.4  # 40% of loan for equipment
        
        # Manufacturing equipment
        quotes.append({
            'quote_number': f'Q-{self.fake.random.randint(100000, 999999)}',
            'vendor_name': 'Industrial Equipment Solutions',
            'vendor_contact': {
                'name': 'John Smith',
                'title': 'Sales Manager',
                'phone': '555-123-4567',
                'email': 'j.smith@industrialequip.com',
                'address': '1234 Industrial Blvd, Chicago, IL 60607'
            },
            'equipment_details': {
                'description': 'CNC Machining Center Model X200',
                'manufacturer': 'Precision Manufacturing Corp',
                'model_number': 'PMC-X200-2024',
                'quantity': 1,
                'unit_price': round(equipment_budget * 0.6, 2),
                'specifications': [
                    'Travel: 40" x 20" x 20"',
                    'Spindle speed: 8000 RPM',
                    'Tool capacity: 20 tools',
                    'Control: Fanuc 31i'
                ]
            },
            'pricing': {
                'equipment_cost': round(equipment_budget * 0.6, 2),
                'installation': round(equipment_budget * 0.05, 2),
                'training': round(equipment_budget * 0.02, 2),
                'warranty_1yr': round(equipment_budget * 0.03, 2),
                'total_quote': round(equipment_budget * 0.7, 2)
            },
            'delivery_terms': '8-10 weeks from order',
            'payment_terms': '50% down, balance on delivery',
            'quote_valid_until': (datetime.now().date() + timedelta(days=30)).isoformat(),
            'financing_available': True
        })
        
        # Office equipment
        quotes.append({
            'quote_number': f'Q-{self.fake.random.randint(100000, 999999)}',
            'vendor_name': 'Business Solutions Pro',
            'vendor_contact': {
                'name': 'Sarah Johnson',
                'title': 'Account Executive',
                'phone': '555-987-6543',
                'email': 's.johnson@bizsolpro.com',
                'address': '5678 Commerce Way, Dallas, TX 75201'
            },
            'equipment_details': {
                'description': 'Complete Office Setup Package',
                'items': [
                    {'item': 'Workstations (5)', 'price': round(equipment_budget * 0.08, 2)},
                    {'item': 'Computer Systems (5)', 'price': round(equipment_budget * 0.10, 2)},
                    {'item': 'Network Equipment', 'price': round(equipment_budget * 0.04, 2)},
                    {'item': 'Phone System', 'price': round(equipment_budget * 0.03, 2)},
                    {'item': 'Printer/Copier', 'price': round(equipment_budget * 0.05, 2)}
                ]
            },
            'pricing': {
                'equipment_cost': round(equipment_budget * 0.30, 2),
                'installation_setup': round(equipment_budget * 0.02, 2),
                'total_quote': round(equipment_budget * 0.32, 2)
            },
            'delivery_terms': '2-3 weeks from order',
            'payment_terms': 'Net 30',
            'quote_valid_until': (datetime.now().date() + timedelta(days=45)).isoformat(),
            'warranty': '3 years parts and labor'
        })
        
        return quotes
    
    def _generate_applicant_questionnaire(self) -> Dict[str, Any]:
        """Generate applicant questionnaire responses."""
        return {
            'business_purpose': {
                'primary_business_activity': 'Manufacturing and distribution of specialty products',
                'years_experience_industry': self.fake.random.randint(5, 20),
                'business_plan_summary': 'Expand operations through equipment upgrades and increased working capital to capture growing market demand.',
                'competitive_advantages': [
                    'Established customer relationships',
                    'Proprietary manufacturing processes',
                    'Experienced management team',
                    'Strong brand recognition'
                ]
            },
            'loan_purpose': {
                'specific_use_description': 'Purchase new CNC equipment, increase inventory levels, and strengthen working capital position',
                'how_loan_improves_business': 'Increased production capacity will allow us to serve larger orders and improve profit margins through efficiency gains',
                'repayment_source': 'Increased cash flow from expanded operations',
                'backup_repayment_source': 'Personal guarantees and business asset liquidation if necessary'
            },
            'financial_projections': {
                'revenue_growth_expected': round(self.fake.random.uniform(15, 35), 1),
                'profit_margin_improvement': round(self.fake.random.uniform(2, 8), 1),
                'payback_period_months': self.fake.random.randint(36, 72),
                'break_even_analysis': 'Expect to break even on new investment within 18-24 months based on projected order increases'
            },
            'management_experience': {
                'owner_background': f'Over {self.fake.random.randint(15, 25)} years experience in the industry with strong operational and financial management skills',
                'key_personnel': [
                    {'name': self.fake.name(), 'title': 'Operations Manager', 'years_experience': self.fake.random.randint(8, 15)},
                    {'name': self.fake.name(), 'title': 'Sales Manager', 'years_experience': self.fake.random.randint(10, 18)},
                    {'name': self.fake.name(), 'title': 'Financial Controller', 'years_experience': self.fake.random.randint(12, 20)}
                ],
                'succession_plan': 'Family business with next generation being trained in operations and management'
            },
            'risk_factors': {
                'industry_risks': ['Economic downturn', 'Supply chain disruptions', 'Increased competition'],
                'business_risks': ['Key customer concentration', 'Equipment breakdown', 'Staff turnover'],
                'mitigation_strategies': [
                    'Diversified customer base development',
                    'Equipment maintenance programs',
                    'Cross-training of key personnel',
                    'Business interruption insurance'
                ]
            },
            'compliance_certifications': {
                'business_licenses_current': True,
                'tax_filings_current': True,
                'workers_comp_current': True,
                'environmental_compliance': True,
                'industry_certifications': ['ISO 9001', 'OSHA Compliant']
            }
        }
    
    def _build_expected_values(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Build expected extraction values for testing aligned with Prisma schema."""
        business_metadata = profile['business_metadata']
        primary_owner = profile['beneficial_owners'][0] if profile['beneficial_owners'] else {}
        pfs = profile['personal_financial_statement']
        
        return {
            # Business metadata
            'business_name': business_metadata['name'],
            'ein': business_metadata['federal_tax_id'],
            'business_type': business_metadata['type'],
            'entity_type': business_metadata['entity_type'],
            'naics_code': business_metadata['naics_code'],
            'years_in_business': business_metadata['years_in_business'],
            'number_of_employees': business_metadata['number_of_employees'],
            'annual_revenue': business_metadata['annual_revenue'],
            'net_income': business_metadata['net_income'],
            'business_address': business_metadata['address'],
            'business_phone': business_metadata['phone'],
            'business_email': business_metadata['email'],
            
            # Primary owner information
            'owner_name': primary_owner.get('name'),
            'owner_ssn': primary_owner.get('ssn'),
            'ownership_percentage': primary_owner.get('ownership_percentage'),
            'owner_address': primary_owner.get('address'),
            
            # Loan information
            'loan_amount': profile['loan_amount'],
            
            # Bank information
            'bank_name': profile['bank_name'],
            'account_number': profile['account_number'],
            'routing_number': profile['routing_number'],
            
            # Personal Financial Statement
            'total_assets': pfs['total_assets'],
            'total_liabilities': pfs['total_liabilities'],
            'net_worth': pfs['net_worth'],
            'cash_on_hand': pfs['assets']['cash_and_cash_equivalents']['cash_on_hand'],
            'checking_accounts': pfs['assets']['cash_and_cash_equivalents']['checking_accounts'],
            'savings_accounts': pfs['assets']['cash_and_cash_equivalents']['savings_accounts'],
            'real_estate_owned': pfs['assets']['real_estate'],
            'securities_owned': pfs['assets']['securities'],
            'total_monthly_income': pfs['income']['total_monthly_income'],
            'total_monthly_expenses': pfs['expenses']['total_monthly_expenses']
        }
    
    def _generate_realistic_bank_statements(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate realistic bank statements using the BankStatementGenerator."""
        files = {}
        
        # Select a random bank for consistency
        bank_name = profile['bank_name']
        
        # Generate 12 months of statements
        end_date = datetime.now().date()
        
        for month_offset in range(self.statement_months):
            statement_date = end_date - timedelta(days=30 * month_offset)
            statement_start = statement_date.replace(day=1)
            
            # Calculate next month for end date
            if statement_date.month == 12:
                statement_end = statement_date.replace(year=statement_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                statement_end = statement_date.replace(month=statement_date.month + 1, day=1) - timedelta(days=1)
            
            # Generate transactions for the month
            transactions = self._generate_monthly_transactions(profile, statement_start, statement_end)
            
            # Create realistic PDF bank statement
            filename = f"bank_statement_{bank_name.lower().replace(' ', '_')}_{statement_date.strftime('%Y_%m')}.pdf"
            file_path = app_dir / "bank_statements" / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare account data for realistic generator
            account_data = {
                'account_holder': profile['business_name'],
                'account_number': profile['account_number'],
                'routing_number': profile['routing_number'],
                'beginning_balance': self.fake.random.uniform(5000, 50000),
                'ending_balance': 0,  # Will be calculated
                'business_address': profile.get('business_address', '123 Business St'),
                'city_state_zip': 'Anytown, ST 12345'
            }
            
            # Calculate ending balance
            beginning_balance = account_data['beginning_balance']
            running_balance = beginning_balance
            for txn in transactions:
                if txn['type'] == 'credit':
                    running_balance += txn['amount']
                else:
                    running_balance -= txn['amount']
            account_data['ending_balance'] = running_balance
            
            # Generate realistic bank statement
            self.bank_generator.generate_statement(
                file_path, bank_name, account_data, transactions, 
                (statement_start, statement_end), 'pdf'
            )
            
            files[f'bank_statement_{statement_date.strftime("%Y_%m")}'] = file_path
        
        return files
    
    def _generate_realistic_tax_returns(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate realistic tax returns using the TaxReturnGenerator."""
        files = {}
        
        # Generate returns for the last 3 years
        current_year = datetime.now().year
        
        for year_offset in range(3):
            tax_year = current_year - 1 - year_offset  # Previous years only
            
            # Determine form type based on business entity type
            entity_type = profile['business_metadata'].get('entity_type', 'Corporation')
            if entity_type == 'S Corporation':
                form_type = '1120S'
            elif entity_type in ['LLC', 'Partnership']:
                form_type = '1120S'  # Simplified - would be 1065 in reality
            elif entity_type == 'Sole Proprietorship':
                form_type = '1040_schedule_c'
            else:  # Corporation
                form_type = '1120'
            
            filename = f"tax_return_{form_type}_{tax_year}.pdf"
            file_path = app_dir / "tax_returns" / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare business data for tax generator
            business_data = {
                'name': profile['business_name'],
                'address': profile.get('business_address_dict', {
                    'street': '123 Business St',
                    'city': 'Anytown',
                    'state': 'ST',
                    'zip_code': '12345'
                }),
                'ein': profile.get('ein', self._generate_ein()),
                'annual_revenue': profile['annual_revenue'],
                'net_income': profile['net_income'],
                'type': profile['business_type'],
                'owner_name': profile.get('beneficial_owners', [{}])[0].get('name', 'John Smith'),
                'naics_code': profile['business_metadata'].get('naics_code', '541990'),
                'date_established': profile['business_metadata'].get('date_established', '2015-01-01'),
                'total_assets': profile.get('total_assets', profile['annual_revenue'] * 0.8)
            }
            
            # Generate realistic tax return
            self.tax_generator.generate_tax_return(file_path, form_type, business_data, tax_year)
            
            files[f'tax_return_{tax_year}'] = file_path
        
        return files
    
    def _generate_realistic_financial_statements(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate realistic business financial statements."""
        files = {}
        
        # Prepare business info for financial statement generator
        business_info = {
            'name': profile['business_name'],
            'annual_revenue': profile['annual_revenue']
        }
        
        financial_data = {
            'annual_revenue': profile['annual_revenue'],
            'net_income': profile['net_income']
        }
        
        statement_date = datetime.now().date()
        
        # Generate Balance Sheet
        balance_sheet_file = app_dir / "financial" / "balance_sheet.pdf"
        balance_sheet_file.parent.mkdir(parents=True, exist_ok=True)
        self.business_financial_generator.generate_financial_statement(
            balance_sheet_file, 'balance_sheet', financial_data, business_info, statement_date
        )
        files['balance_sheet'] = balance_sheet_file
        
        # Generate Income Statement (P&L)
        income_statement_file = app_dir / "financial" / "income_statement.pdf"
        self.business_financial_generator.generate_financial_statement(
            income_statement_file, 'income_statement', financial_data, business_info, statement_date
        )
        files['income_statement'] = income_statement_file
        
        # Generate Cash Flow Statement
        cash_flow_file = app_dir / "financial" / "cash_flow_statement.pdf"
        self.business_financial_generator.generate_financial_statement(
            cash_flow_file, 'cash_flow', financial_data, business_info, statement_date
        )
        files['cash_flow_statement'] = cash_flow_file
        
        return files
    
    def _generate_realistic_pfs_documents(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate realistic Personal Financial Statement using SBA Form 413 format."""
        files = {}
        
        pfs_data = profile['personal_financial_statement']
        primary_owner = profile['beneficial_owners'][0] if profile['beneficial_owners'] else {}
        
        # Prepare owner info for PFS generator
        owner_info = {
            'name': primary_owner.get('name', 'John Smith'),
            'ssn': primary_owner.get('ssn', 'XXX-XX-1234'),
            'phone': primary_owner.get('phone', '(555) 123-4567'),
            'business_phone': profile.get('phone_number', '(555) 987-6543'),
            'email': primary_owner.get('email', 'owner@business.com'),
            'address': primary_owner.get('address', {
                'street': '123 Main St',
                'city': 'Anytown',
                'state': 'ST',
                'zip_code': '12345'
            }),
            'date_of_birth': primary_owner.get('date_of_birth', '1980-01-01'),
            'dependents': 2,
            'title': primary_owner.get('title', 'Business Owner'),
            'employer': 'Self-Employed'
        }
        
        statement_date = datetime.now().date()
        
        # Generate SBA Form 413 PFS
        pfs_file = app_dir / "personal_financial" / "sba_form_413_personal_financial_statement.pdf"
        pfs_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.pfs_generator.generate_pfs(pfs_file, pfs_data, owner_info, statement_date)
        
        files['personal_financial_statement'] = pfs_file
        
        return files
    
    def _generate_equipment_quote_documents(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate equipment quote documents."""
        docs = {}
        
        # Generate simple equipment quotes as CSV for now
        equipment_quotes = profile.get('equipment_quotes', [])
        if equipment_quotes:
            import csv
            quotes_file = app_dir / 'equipment_quotes.csv'
            
            fieldnames = ['vendor', 'equipment_description', 'cost', 'is_new', 'contact_person', 'phone', 'email']
            
            with open(quotes_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                for quote in equipment_quotes:
                    # Extract only the fields we need
                    row_data = {field: quote.get(field, '') for field in fieldnames}
                    writer.writerow(row_data)
            
            docs['equipment_quotes'] = quotes_file
        
        return docs
    
    def _generate_realistic_debt_schedule_documents(self, app_dir: Path, profile: Dict[str, Any]) -> Dict[str, Path]:
        """Generate realistic Business Debt Schedule."""
        files = {}
        
        debt_data = profile['debt_schedule']
        business_info = {
            'name': profile['business_name'],
            'annual_revenue': profile['annual_revenue']
        }
        
        statement_date = datetime.now().date()
        
        # Generate Business Debt Schedule
        debt_schedule_file = app_dir / "financial" / "business_debt_schedule.pdf"
        debt_schedule_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.debt_schedule_generator.generate_debt_schedule(
            debt_schedule_file, debt_data, business_info, statement_date
        )
        
        files['business_debt_schedule'] = debt_schedule_file
        
        return files