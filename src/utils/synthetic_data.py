"""
Helper functions for synthetic data generation.

This module provides utility functions for creating realistic synthetic data
for various document types and business scenarios.
"""

import random
import string
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union
from faker import Faker
import logging

logger = logging.getLogger(__name__)


class SyntheticDataGenerator:
    """Helper class for generating realistic synthetic data."""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize synthetic data generator.
        
        Args:
            seed: Random seed for reproducible generation
        """
        self.fake = Faker()
        if seed:
            Faker.seed(seed)
            random.seed(seed)
    
    def generate_business_name(self, industry: Optional[str] = None) -> str:
        """Generate a realistic business name."""
        if industry:
            # Industry-specific business names
            industry_suffixes = {
                'restaurant': ['Bistro', 'Grill', 'Kitchen', 'Cafe', 'Diner'],
                'retail': ['Store', 'Shop', 'Boutique', 'Market', 'Outlet'],
                'manufacturing': ['Industries', 'Manufacturing', 'Corp', 'Works', 'Factory'],
                'construction': ['Construction', 'Builders', 'Contractors', 'Development'],
                'technology': ['Technologies', 'Systems', 'Solutions', 'Software', 'Tech'],
                'professional_services': ['Associates', 'Partners', 'Group', 'Consulting'],
                'healthcare': ['Medical', 'Health', 'Clinic', 'Services', 'Care']
            }
            
            suffixes = industry_suffixes.get(industry.lower().replace(' ', '_'), ['LLC', 'Inc', 'Corp'])
            base_name = self.fake.company().split()[0]  # Take first word of company name
            suffix = random.choice(suffixes)
            
            return f"{base_name} {suffix}"
        
        return self.fake.company()
    
    def generate_realistic_amounts(
        self, 
        base_amount: float, 
        variance: float = 0.2,
        num_amounts: int = 1
    ) -> Union[float, List[float]]:
        """
        Generate realistic amounts with variance.
        
        Args:
            base_amount: Base amount to vary around
            variance: Percentage variance (0.2 = 20% variance)
            num_amounts: Number of amounts to generate
            
        Returns:
            Single amount or list of amounts
        """
        amounts = []
        for _ in range(num_amounts):
            # Add random variance
            multiplier = 1 + random.uniform(-variance, variance)
            amount = base_amount * multiplier
            
            # Round to realistic precision based on amount size
            if amount < 100:
                amount = round(amount, 2)
            elif amount < 1000:
                amount = round(amount, 0)
            else:
                amount = round(amount, -1)  # Round to nearest 10
            
            amounts.append(amount)
        
        return amounts[0] if num_amounts == 1 else amounts
    
    def generate_date_range(
        self, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        num_days: Optional[int] = None
    ) -> Tuple[date, date]:
        """
        Generate a realistic date range.
        
        Args:
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to today)
            num_days: If specified, generates range of this many days
            
        Returns:
            Tuple of (start_date, end_date)
        """
        if num_days:
            if start_date:
                end_date = start_date + timedelta(days=num_days)
            else:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=num_days)
        else:
            if not end_date:
                end_date = datetime.now().date()
            if not start_date:
                start_date = end_date - timedelta(days=365)
        
        return start_date, end_date
    
    def generate_transaction_descriptions(self, transaction_type: str) -> List[str]:
        """
        Generate realistic transaction descriptions by type.
        
        Args:
            transaction_type: Type of transaction (credit/debit/expense/revenue)
            
        Returns:
            List of realistic transaction descriptions
        """
        descriptions = {
            'credit': [
                'Customer Payment', 'Sales Deposit', 'Credit Card Processing',
                'Wire Transfer In', 'ACH Credit', 'Cash Deposit',
                'Invoice Payment', 'Service Payment', 'Product Sales'
            ],
            'debit': [
                'Rent Payment', 'Utility Bill', 'Payroll Processing',
                'Supplier Payment', 'Equipment Purchase', 'Insurance Premium',
                'Professional Services', 'Marketing Expense', 'Office Supplies'
            ],
            'expense': [
                'Office Rent', 'Electricity Bill', 'Internet Service',
                'Phone Bill', 'Insurance Payment', 'Equipment Lease',
                'Software License', 'Professional Fees', 'Travel Expense',
                'Advertising Cost', 'Maintenance Service'
            ],
            'revenue': [
                'Product Sales', 'Service Revenue', 'Consulting Income',
                'Subscription Revenue', 'License Revenue', 'Commission Income',
                'Interest Income', 'Rental Income'
            ]
        }
        
        return descriptions.get(transaction_type, ['Transaction'])
    
    def generate_account_numbers(self, num_accounts: int = 1) -> Union[str, List[str]]:
        """
        Generate realistic account numbers.
        
        Args:
            num_accounts: Number of account numbers to generate
            
        Returns:
            Single account number or list of account numbers
        """
        accounts = []
        for _ in range(num_accounts):
            # Generate 9-12 digit account number
            length = random.randint(9, 12)
            account = ''.join([str(random.randint(0, 9)) for _ in range(length)])
            accounts.append(account)
        
        return accounts[0] if num_accounts == 1 else accounts
    
    def generate_routing_number(self) -> str:
        """Generate a realistic routing number."""
        # Routing numbers are 9 digits
        return ''.join([str(random.randint(0, 9)) for _ in range(9)])
    
    def generate_ein(self) -> str:
        """Generate a realistic EIN (Employer Identification Number)."""
        # Format: XX-XXXXXXX
        first_two = random.randint(10, 99)
        last_seven = random.randint(1000000, 9999999)
        return f"{first_two}-{last_seven}"
    
    def generate_phone_number(self, format_type: str = 'standard') -> str:
        """
        Generate a realistic phone number.
        
        Args:
            format_type: 'standard', 'dashes', 'dots', 'parentheses'
            
        Returns:
            Formatted phone number
        """
        area_code = random.randint(200, 999)
        exchange = random.randint(200, 999)
        number = random.randint(1000, 9999)
        
        formats = {
            'standard': f'{area_code}{exchange}{number}',
            'dashes': f'{area_code}-{exchange}-{number}',
            'dots': f'{area_code}.{exchange}.{number}',
            'parentheses': f'({area_code}) {exchange}-{number}'
        }
        
        return formats.get(format_type, formats['parentheses'])
    
    def generate_address(self, include_suite: bool = False) -> Dict[str, str]:
        """
        Generate a realistic address.
        
        Args:
            include_suite: Whether to include suite/unit number
            
        Returns:
            Dictionary with address components
        """
        street_number = random.randint(100, 9999)
        street_names = [
            'Main St', 'Oak Ave', 'First St', 'Second Ave', 'Park Rd',
            'Washington St', 'Lincoln Ave', 'Maple Dr', 'Elm St', 'Pine Ave'
        ]
        street = f"{street_number} {random.choice(street_names)}"
        
        if include_suite:
            suite_types = ['Suite', 'Unit', 'Apt', '#']
            suite_num = random.randint(1, 999)
            street += f", {random.choice(suite_types)} {suite_num}"
        
        city = self.fake.city()
        state = self.fake.state_abbr()
        zip_code = f"{random.randint(10000, 99999)}"
        
        return {
            'street': street,
            'city': city,
            'state': state,
            'zip_code': zip_code,
            'full_address': f"{street}, {city}, {state} {zip_code}"
        }
    
    def generate_business_metrics(
        self, 
        annual_revenue: float,
        industry: str = 'general'
    ) -> Dict[str, float]:
        """
        Generate realistic business metrics based on revenue and industry.
        
        Args:
            annual_revenue: Annual revenue amount
            industry: Business industry for realistic ratios
            
        Returns:
            Dictionary of business metrics
        """
        # Industry-specific profit margins
        industry_margins = {
            'restaurant': (0.03, 0.08),
            'retail': (0.02, 0.06),
            'manufacturing': (0.05, 0.15),
            'construction': (0.02, 0.10),
            'technology': (0.15, 0.30),
            'professional_services': (0.10, 0.25),
            'healthcare': (0.08, 0.20),
            'general': (0.05, 0.15)
        }
        
        margin_range = industry_margins.get(industry.lower(), industry_margins['general'])
        profit_margin = random.uniform(*margin_range)
        
        net_income = annual_revenue * profit_margin
        gross_margin = profit_margin + random.uniform(0.1, 0.3)  # Gross margin higher than net
        
        # Calculate expenses
        cogs = annual_revenue * (1 - gross_margin)
        operating_expenses = annual_revenue * gross_margin - net_income
        
        # Employee count based on revenue (rough estimate)
        revenue_per_employee = random.uniform(75000, 150000)
        employees = max(1, int(annual_revenue / revenue_per_employee))
        
        return {
            'annual_revenue': annual_revenue,
            'net_income': net_income,
            'profit_margin': profit_margin,
            'gross_margin': gross_margin,
            'cost_of_goods_sold': cogs,
            'operating_expenses': operating_expenses,
            'employees': employees,
            'revenue_per_employee': annual_revenue / employees
        }
    
    def generate_financial_ratios(self, metrics: Dict[str, float]) -> Dict[str, float]:
        """
        Generate realistic financial ratios based on business metrics.
        
        Args:
            metrics: Business metrics dictionary
            
        Returns:
            Dictionary of financial ratios
        """
        revenue = metrics['annual_revenue']
        
        # Asset ratios
        current_ratio = random.uniform(1.2, 2.5)
        quick_ratio = random.uniform(0.8, 1.5)
        debt_to_equity = random.uniform(0.3, 1.5)
        
        # Activity ratios
        inventory_turnover = random.uniform(4, 12)
        receivables_turnover = random.uniform(6, 15)
        
        # Estimated balance sheet items
        current_assets = revenue * random.uniform(0.2, 0.5)
        current_liabilities = current_assets / current_ratio
        
        return {
            'current_ratio': current_ratio,
            'quick_ratio': quick_ratio,
            'debt_to_equity_ratio': debt_to_equity,
            'inventory_turnover': inventory_turnover,
            'receivables_turnover': receivables_turnover,
            'current_assets': current_assets,
            'current_liabilities': current_liabilities
        }


def generate_coherent_loan_application(
    loan_amount: float,
    business_type: str = 'general',
    seed: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate a coherent loan application with realistic, related data.
    
    Args:
        loan_amount: Requested loan amount
        business_type: Type of business
        seed: Random seed for reproducible generation
        
    Returns:
        Complete loan application data
    """
    generator = SyntheticDataGenerator(seed)
    
    # Generate business profile
    business_name = generator.generate_business_name(business_type)
    address = generator.generate_address(include_suite=True)
    
    # Calculate realistic revenue based on loan amount
    revenue_multiplier = random.uniform(3, 8)  # Revenue should be 3-8x loan amount
    annual_revenue = loan_amount * revenue_multiplier
    
    # Generate business metrics
    metrics = generator.generate_business_metrics(annual_revenue, business_type)
    ratios = generator.generate_financial_ratios(metrics)
    
    # Owner information
    owner_name = generator.fake.name()
    
    return {
        'business_info': {
            'business_name': business_name,
            'business_type': business_type,
            'ein': generator.generate_ein(),
            'address': address,
            'phone': generator.generate_phone_number(),
            'email': generator.fake.email(),
            'years_in_business': random.randint(2, 20),
            'legal_structure': random.choice(['LLC', 'Corporation', 'Partnership', 'Sole Proprietorship'])
        },
        'owner_info': {
            'name': owner_name,
            'ssn': generator.fake.ssn(),
            'ownership_percentage': random.randint(51, 100)
        },
        'loan_info': {
            'requested_amount': loan_amount,
            'purpose': random.choice([
                'Working Capital', 'Equipment Purchase', 'Business Expansion',
                'Inventory Purchase', 'Real Estate', 'Debt Refinancing'
            ]),
            'term_years': random.choice([5, 7, 10, 15, 20])
        },
        'financial_info': {
            **metrics,
            **ratios
        },
        'banking_info': {
            'bank_name': random.choice([
                'Chase Bank', 'Bank of America', 'Wells Fargo', 'Citibank',
                'PNC Bank', 'TD Bank', 'Capital One', 'US Bank'
            ]),
            'account_number': generator.generate_account_numbers(),
            'routing_number': generator.generate_routing_number()
        }
    }


def validate_data_coherence(application_data: Dict[str, Any]) -> List[str]:
    """
    Validate that generated data is coherent and realistic.
    
    Args:
        application_data: Generated application data
        
    Returns:
        List of validation errors
    """
    errors = []
    
    try:
        financial = application_data['financial_info']
        loan = application_data['loan_info']
        
        # Check revenue to loan ratio
        revenue_ratio = financial['annual_revenue'] / loan['requested_amount']
        if revenue_ratio < 2:
            errors.append(f"Revenue to loan ratio too low: {revenue_ratio:.2f}")
        
        # Check profit margin is reasonable
        if financial['profit_margin'] < 0 or financial['profit_margin'] > 0.5:
            errors.append(f"Unrealistic profit margin: {financial['profit_margin']:.2%}")
        
        # Check employee count is reasonable for revenue
        revenue_per_employee = financial['revenue_per_employee']
        if revenue_per_employee < 30000 or revenue_per_employee > 500000:
            errors.append(f"Unrealistic revenue per employee: ${revenue_per_employee:,.0f}")
        
        # Check current ratio is reasonable
        if 'current_ratio' in financial:
            if financial['current_ratio'] < 0.5 or financial['current_ratio'] > 5:
                errors.append(f"Unrealistic current ratio: {financial['current_ratio']:.2f}")
        
    except KeyError as e:
        errors.append(f"Missing required data field: {e}")
    
    return errors