"""
Unified loan application package model.
Aggregates all document extractions into a complete loan application.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class LoanType(Enum):
    """Types of loans."""
    SBA = "sba"
    COMMERCIAL = "commercial"
    EQUIPMENT = "equipment"
    REAL_ESTATE = "real_estate"
    WORKING_CAPITAL = "working_capital"
    ACQUISITION = "acquisition"


class ApplicationStatus(Enum):
    """Loan application status."""
    INCOMPLETE = "incomplete"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    ADDITIONAL_INFO_NEEDED = "additional_info_needed"
    APPROVED = "approved"
    DECLINED = "declined"


@dataclass
class BorrowerInfo:
    """Primary borrower information."""
    # Personal Information
    first_name: str
    last_name: str
    ssn: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    
    # Contact Information
    email: Optional[str] = None
    phone: Optional[str] = None
    business_phone: Optional[str] = None
    
    # Address
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    
    # Professional
    title: Optional[str] = None
    years_experience: Optional[int] = None
    ownership_percentage: Optional[float] = None
    
    # Spouse Information (if joint application)
    spouse_name: Optional[str] = None
    spouse_ssn: Optional[str] = None
    
    # Credit
    credit_score: Optional[int] = None
    bankruptcies: Optional[int] = None
    
    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class BusinessEntity:
    """Business entity information."""
    # Identification
    business_name: str
    dba: Optional[str] = None
    ein: Optional[str] = None
    
    # Structure
    entity_type: Optional[str] = None  # LLC, Corp, Partnership, etc.
    state_of_incorporation: Optional[str] = None
    date_established: Optional[datetime] = None
    
    # Operations
    industry_code: Optional[str] = None  # NAICS
    number_of_employees: Optional[int] = None
    annual_revenue: Optional[Decimal] = None
    
    # Location
    business_address: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_zip: Optional[str] = None


@dataclass
class FinancialPosition:
    """Aggregated financial position from all sources."""
    # From PFS
    total_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    net_worth: Optional[Decimal] = None
    
    # Asset Breakdown
    cash_on_hand: Optional[Decimal] = None
    accounts_receivable: Optional[Decimal] = None
    inventory: Optional[Decimal] = None
    real_estate_value: Optional[Decimal] = None
    equipment_value: Optional[Decimal] = None
    
    # Liability Breakdown
    accounts_payable: Optional[Decimal] = None
    current_portion_ltd: Optional[Decimal] = None
    long_term_debt: Optional[Decimal] = None
    
    # Income (Annual)
    salary_income: Optional[Decimal] = None
    business_income: Optional[Decimal] = None
    investment_income: Optional[Decimal] = None
    real_estate_income: Optional[Decimal] = None
    total_income: Optional[Decimal] = None
    
    # From Tax Returns
    adjusted_gross_income: Optional[Decimal] = None
    taxable_income: Optional[Decimal] = None
    
    # Business Financials
    gross_revenue: Optional[Decimal] = None
    gross_profit: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    net_income: Optional[Decimal] = None
    
    # Ratios
    current_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_service_coverage: Optional[float] = None
    
    def calculate_ratios(self):
        """Calculate financial ratios."""
        # Current ratio
        if self.cash_on_hand and self.accounts_payable and self.accounts_payable > 0:
            current_assets = self.cash_on_hand + (self.accounts_receivable or 0)
            self.current_ratio = float(current_assets / self.accounts_payable)
        
        # Debt to equity
        if self.total_liabilities and self.net_worth and self.net_worth > 0:
            self.debt_to_equity = float(self.total_liabilities / self.net_worth)


@dataclass
class DebtItem:
    """Individual debt item."""
    creditor_name: str
    account_number: Optional[str] = None
    original_amount: Optional[Decimal] = None
    current_balance: Decimal = Decimal(0)
    monthly_payment: Optional[Decimal] = None
    interest_rate: Optional[float] = None
    maturity_date: Optional[datetime] = None
    collateral: Optional[str] = None
    personal_guarantee: bool = False
    status: str = "current"  # current, past_due, in_default


@dataclass
class DebtSchedule:
    """Complete debt schedule."""
    debts: List[DebtItem] = field(default_factory=list)
    total_debt: Optional[Decimal] = None
    total_monthly_payment: Optional[Decimal] = None
    weighted_avg_rate: Optional[float] = None
    
    def calculate_totals(self):
        """Calculate debt totals and weighted average rate."""
        if self.debts:
            self.total_debt = sum(d.current_balance for d in self.debts)
            self.total_monthly_payment = sum(d.monthly_payment or 0 for d in self.debts)
            
            # Weighted average interest rate
            if self.total_debt > 0:
                weighted_sum = sum(
                    d.current_balance * (d.interest_rate or 0)
                    for d in self.debts
                )
                self.weighted_avg_rate = float(weighted_sum / self.total_debt)


@dataclass
class LoanRequest:
    """Loan request details."""
    loan_type: LoanType
    requested_amount: Decimal
    loan_purpose: str
    term_months: Optional[int] = None
    
    # Use of funds
    working_capital: Optional[Decimal] = None
    equipment_purchase: Optional[Decimal] = None
    real_estate_purchase: Optional[Decimal] = None
    business_acquisition: Optional[Decimal] = None
    debt_refinance: Optional[Decimal] = None
    other_use: Optional[Decimal] = None
    
    # Collateral offered
    collateral_description: Optional[str] = None
    collateral_value: Optional[Decimal] = None
    
    # Projections
    projected_revenue_increase: Optional[float] = None
    jobs_created: Optional[int] = None
    jobs_retained: Optional[int] = None


@dataclass
class DocumentMetadata:
    """Metadata for extracted documents."""
    document_type: str
    file_name: str
    extraction_date: datetime
    extraction_method: str  # regex, llm, manual
    confidence_score: float
    pages_processed: int
    extraction_time: float  # seconds
    errors: List[str] = field(default_factory=list)


@dataclass
class ValidationStatus:
    """Validation status of the application."""
    overall_status: str  # PASS, FAIL, WARNING
    validation_date: datetime
    passed_checks: List[str] = field(default_factory=list)
    failed_checks: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manual_review_required: bool = False
    review_notes: Optional[str] = None


@dataclass
class LoanApplicationPackage:
    """Complete loan application package."""
    # Application Info
    application_id: str
    application_date: datetime
    status: ApplicationStatus
    
    # Parties
    primary_borrower: BorrowerInfo
    
    # Financial Information
    financial_position: FinancialPosition
    debt_schedule: DebtSchedule
    
    # Loan Request
    loan_request: LoanRequest
    
    # Optional fields (with defaults)
    co_borrowers: List[BorrowerInfo] = field(default_factory=list)
    business_entity: Optional[BusinessEntity] = None
    
    # Supporting Documents
    documents_metadata: List[DocumentMetadata] = field(default_factory=list)
    
    # Validation
    validation_status: Optional[ValidationStatus] = None
    
    # Calculations
    loan_to_value: Optional[float] = None
    debt_to_income: Optional[float] = None
    debt_service_coverage: Optional[float] = None
    
    # Risk Assessment
    risk_score: Optional[float] = None
    risk_factors: List[str] = field(default_factory=list)
    
    # Processing
    assigned_to: Optional[str] = None
    last_updated: datetime = field(default_factory=datetime.now)
    notes: List[str] = field(default_factory=list)
    
    def calculate_metrics(self):
        """Calculate key loan metrics."""
        # Loan to Value
        if self.loan_request.collateral_value and self.loan_request.collateral_value > 0:
            self.loan_to_value = float(
                self.loan_request.requested_amount / self.loan_request.collateral_value
            )
        
        # Debt to Income
        if self.financial_position.total_income and self.financial_position.total_income > 0:
            total_debt = self.debt_schedule.total_debt or 0
            new_debt = self.loan_request.requested_amount
            self.debt_to_income = float((total_debt + new_debt) / self.financial_position.total_income)
        
        # Debt Service Coverage Ratio
        if self.debt_schedule.total_monthly_payment:
            annual_debt_service = self.debt_schedule.total_monthly_payment * 12
            
            # Estimate new loan payment (assume 7% rate, if not specified)
            if self.loan_request.term_months:
                rate = 0.07 / 12
                term = self.loan_request.term_months
                new_payment = self.loan_request.requested_amount * (rate * (1 + rate)**term) / ((1 + rate)**term - 1)
                annual_debt_service += new_payment * 12
            
            if annual_debt_service > 0 and self.financial_position.ebitda:
                self.debt_service_coverage = float(self.financial_position.ebitda / annual_debt_service)
    
    def assess_risk(self):
        """Perform risk assessment."""
        self.risk_factors = []
        risk_points = 0
        
        # Check debt service coverage
        if self.debt_service_coverage:
            if self.debt_service_coverage < 1.0:
                self.risk_factors.append("Negative cash flow (DSCR < 1.0)")
                risk_points += 30
            elif self.debt_service_coverage < 1.25:
                self.risk_factors.append("Low debt service coverage")
                risk_points += 15
        
        # Check loan to value
        if self.loan_to_value:
            if self.loan_to_value > 0.9:
                self.risk_factors.append("High loan-to-value ratio")
                risk_points += 20
            elif self.loan_to_value > 0.8:
                self.risk_factors.append("Elevated loan-to-value ratio")
                risk_points += 10
        
        # Check debt to income
        if self.debt_to_income:
            if self.debt_to_income > 5:
                self.risk_factors.append("Very high debt-to-income ratio")
                risk_points += 25
            elif self.debt_to_income > 3:
                self.risk_factors.append("High debt-to-income ratio")
                risk_points += 15
        
        # Check credit score
        if self.primary_borrower.credit_score:
            if self.primary_borrower.credit_score < 650:
                self.risk_factors.append("Low credit score")
                risk_points += 20
            elif self.primary_borrower.credit_score < 700:
                self.risk_factors.append("Fair credit score")
                risk_points += 10
        
        # Check business age
        if self.business_entity and self.business_entity.date_established:
            years_in_business = (datetime.now() - self.business_entity.date_established).days / 365
            if years_in_business < 2:
                self.risk_factors.append("Business less than 2 years old")
                risk_points += 15
        
        # Calculate risk score (0-100, lower is better)
        self.risk_score = min(100, risk_points)
    
    def is_complete(self) -> bool:
        """Check if application has all required information."""
        required_fields = [
            self.primary_borrower.first_name,
            self.primary_borrower.last_name,
            self.financial_position.total_assets,
            self.financial_position.total_liabilities,
            self.loan_request.requested_amount,
            self.loan_request.loan_purpose
        ]
        
        return all(field is not None for field in required_fields)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get application summary."""
        return {
            'application_id': self.application_id,
            'borrower': str(self.primary_borrower),
            'business': self.business_entity.business_name if self.business_entity else None,
            'loan_amount': float(self.loan_request.requested_amount),
            'loan_type': self.loan_request.loan_type.value,
            'net_worth': float(self.financial_position.net_worth) if self.financial_position.net_worth else None,
            'dscr': self.debt_service_coverage,
            'ltv': self.loan_to_value,
            'risk_score': self.risk_score,
            'status': self.status.value,
            'complete': self.is_complete()
        }
    
    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        def serialize_value(v):
            if isinstance(v, Decimal):
                return float(v)
            elif isinstance(v, datetime):
                return v.isoformat()
            elif isinstance(v, Enum):
                return v.value
            elif hasattr(v, '__dict__'):
                return {k: serialize_value(v) for k, v in v.__dict__.items()}
            elif isinstance(v, list):
                return [serialize_value(item) for item in v]
            return v
        
        return {
            k: serialize_value(v) for k, v in self.__dict__.items()
        }