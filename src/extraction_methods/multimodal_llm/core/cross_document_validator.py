"""
Cross-document validation engine for loan application packages.
Validates consistency across PFS, tax returns, debt schedules, and financials.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
import re


@dataclass
class ValidationResult:
    """Result of cross-document validation."""
    overall_status: str  # PASS, FAIL, WARNING
    confidence: float
    passed_checks: List[str]
    failed_checks: List[str]
    warnings: List[str]
    discrepancies: List[Dict[str, Any]]
    recommendations: List[str]
    
    @property
    def is_valid(self) -> bool:
        return self.overall_status == "PASS"
    
    @property
    def needs_review(self) -> bool:
        return self.overall_status in ["FAIL", "WARNING"] or len(self.warnings) > 0


class CrossDocumentValidator:
    """Validate consistency across multiple loan documents."""
    
    def __init__(self, tolerance: float = 0.05):
        """
        Initialize validator.
        
        Args:
            tolerance: Acceptable variance percentage (default 5%)
        """
        self.tolerance = tolerance
        self.validation_rules = self._build_validation_rules()
    
    def _build_validation_rules(self) -> Dict[str, Any]:
        """Build validation rules for cross-document checks."""
        return {
            'income_consistency': {
                'description': 'Income should be consistent between PFS and tax returns',
                'tolerance': 0.10,  # 10% tolerance for income
                'critical': True
            },
            'debt_consistency': {
                'description': 'Debt totals should match between PFS and debt schedule',
                'tolerance': 0.02,  # 2% tolerance for debt
                'critical': True
            },
            'asset_consistency': {
                'description': 'Asset values should align across documents',
                'tolerance': 0.15,  # 15% tolerance for assets (more variance expected)
                'critical': False
            },
            'business_income_flow': {
                'description': 'Business income should flow correctly from business returns to personal',
                'tolerance': 0.05,
                'critical': True
            },
            'cash_flow_coverage': {
                'description': 'Cash flow should cover debt service',
                'minimum_dscr': 1.25,
                'critical': True
            },
        }
    
    def validate_loan_package(
        self,
        documents: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate entire loan application package.
        
        Args:
            documents: Dictionary of extracted document data
                {
                    'pfs': {...},
                    'tax_returns': [...],
                    'debt_schedule': {...},
                    'business_financials': {...}
                }
        
        Returns:
            ValidationResult with detailed findings
        """
        passed_checks = []
        failed_checks = []
        warnings = []
        discrepancies = []
        recommendations = []
        
        # Run validation checks
        if 'pfs' in documents and 'tax_returns' in documents:
            self._validate_income_consistency(
                documents['pfs'],
                documents['tax_returns'],
                passed_checks,
                failed_checks,
                discrepancies
            )
        
        if 'pfs' in documents and 'debt_schedule' in documents:
            self._validate_debt_consistency(
                documents['pfs'],
                documents['debt_schedule'],
                passed_checks,
                failed_checks,
                discrepancies
            )
        
        if 'business_financials' in documents and 'tax_returns' in documents:
            self._validate_business_income(
                documents['business_financials'],
                documents['tax_returns'],
                passed_checks,
                failed_checks,
                discrepancies
            )
        
        # Calculate debt service coverage
        if all(k in documents for k in ['pfs', 'debt_schedule']):
            self._validate_debt_service_coverage(
                documents,
                passed_checks,
                failed_checks,
                warnings
            )
        
        # Check for red flags
        red_flags = self._check_red_flags(documents)
        warnings.extend(red_flags)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            failed_checks,
            warnings,
            discrepancies
        )
        
        # Determine overall status
        if failed_checks:
            overall_status = "FAIL"
        elif warnings or discrepancies:
            overall_status = "WARNING"
        else:
            overall_status = "PASS"
        
        # Calculate confidence
        total_checks = len(passed_checks) + len(failed_checks)
        confidence = len(passed_checks) / total_checks if total_checks > 0 else 0.0
        
        return ValidationResult(
            overall_status=overall_status,
            confidence=confidence,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
            discrepancies=discrepancies,
            recommendations=recommendations
        )
    
    def _validate_income_consistency(
        self,
        pfs: Dict,
        tax_returns: List[Dict],
        passed: List,
        failed: List,
        discrepancies: List
    ):
        """Validate income consistency between PFS and tax returns."""
        # Get most recent tax return
        if not tax_returns:
            return
        
        recent_tax = max(tax_returns, key=lambda x: x.get('tax_year', 0))
        
        # Compare salary income
        pfs_salary = self._get_value(pfs, ['salaryIncome', 'salary', 'wages'])
        tax_wages = self._get_value(recent_tax, ['wages_salaries', 'wages', 'w2_income'])
        
        if pfs_salary and tax_wages:
            variance = abs(pfs_salary - tax_wages) / max(pfs_salary, tax_wages)
            
            if variance <= self.validation_rules['income_consistency']['tolerance']:
                passed.append(f"Salary income consistent (variance: {variance:.1%})")
            else:
                failed.append(f"Salary income mismatch: PFS ${pfs_salary:,.0f} vs Tax ${tax_wages:,.0f}")
                discrepancies.append({
                    'type': 'income_mismatch',
                    'field': 'salary',
                    'pfs_value': pfs_salary,
                    'tax_value': tax_wages,
                    'variance': variance
                })
        
        # Compare business income
        pfs_business = self._get_value(pfs, ['businessIncome', 'netInvestmentIncome'])
        tax_business = self._get_value(recent_tax, ['business_income', 'schedule_c_income'])
        
        if pfs_business and tax_business:
            variance = abs(pfs_business - tax_business) / max(pfs_business, tax_business)
            
            if variance <= self.validation_rules['income_consistency']['tolerance']:
                passed.append(f"Business income consistent (variance: {variance:.1%})")
            else:
                failed.append(f"Business income mismatch: PFS ${pfs_business:,.0f} vs Tax ${tax_business:,.0f}")
                discrepancies.append({
                    'type': 'income_mismatch',
                    'field': 'business_income',
                    'pfs_value': pfs_business,
                    'tax_value': tax_business,
                    'variance': variance
                })
    
    def _validate_debt_consistency(
        self,
        pfs: Dict,
        debt_schedule: Dict,
        passed: List,
        failed: List,
        discrepancies: List
    ):
        """Validate debt consistency between PFS and debt schedule."""
        # Get total liabilities from PFS
        pfs_liabilities = self._get_value(pfs, ['totalLiabilities', 'total_liabilities'])
        
        # Get total from debt schedule
        schedule_total = self._get_value(debt_schedule, ['total_debt', 'totalDebt'])
        
        if not schedule_total and 'debts' in debt_schedule:
            # Calculate from individual debts
            schedule_total = sum(
                self._get_value(debt, ['current_balance', 'balance'], 0)
                for debt in debt_schedule['debts']
            )
        
        if pfs_liabilities and schedule_total:
            variance = abs(pfs_liabilities - schedule_total) / max(pfs_liabilities, schedule_total)
            
            if variance <= self.validation_rules['debt_consistency']['tolerance']:
                passed.append(f"Debt totals consistent (variance: {variance:.1%})")
            else:
                failed.append(f"Debt total mismatch: PFS ${pfs_liabilities:,.0f} vs Schedule ${schedule_total:,.0f}")
                discrepancies.append({
                    'type': 'debt_mismatch',
                    'pfs_total': pfs_liabilities,
                    'schedule_total': schedule_total,
                    'variance': variance
                })
        
        # Check for missing debts
        self._check_missing_debts(pfs, debt_schedule, discrepancies)
    
    def _validate_business_income(
        self,
        financials: Dict,
        tax_returns: List[Dict],
        passed: List,
        failed: List,
        discrepancies: List
    ):
        """Validate business income between financials and tax returns."""
        # Find business tax returns
        business_returns = [
            tr for tr in tax_returns
            if tr.get('form_type') in ['1065', '1120S']
        ]
        
        if not business_returns:
            return
        
        recent_business = max(business_returns, key=lambda x: x.get('tax_year', 0))
        
        # Compare gross receipts
        if 'profit_loss' in financials:
            pl_revenue = self._get_value(financials['profit_loss'], ['revenue', 'total_revenue', 'gross_receipts'])
            tax_receipts = self._get_value(recent_business, ['gross_receipts'])
            
            if pl_revenue and tax_receipts:
                variance = abs(pl_revenue - tax_receipts) / max(pl_revenue, tax_receipts)
                
                if variance <= self.validation_rules['business_income_flow']['tolerance']:
                    passed.append(f"Business revenue consistent (variance: {variance:.1%})")
                else:
                    failed.append(f"Business revenue mismatch: P&L ${pl_revenue:,.0f} vs Tax ${tax_receipts:,.0f}")
                    discrepancies.append({
                        'type': 'business_revenue_mismatch',
                        'pl_value': pl_revenue,
                        'tax_value': tax_receipts,
                        'variance': variance
                    })
    
    def _validate_debt_service_coverage(
        self,
        documents: Dict,
        passed: List,
        failed: List,
        warnings: List
    ):
        """Calculate and validate debt service coverage ratio."""
        # Calculate net operating income
        noi = self._calculate_noi(documents)
        
        # Calculate debt service
        debt_service = self._calculate_debt_service(documents)
        
        if noi and debt_service and debt_service > 0:
            dscr = noi / debt_service
            min_dscr = self.validation_rules['cash_flow_coverage']['minimum_dscr']
            
            if dscr >= min_dscr:
                passed.append(f"Debt service coverage adequate: {dscr:.2f}x")
            else:
                failed.append(f"Insufficient debt service coverage: {dscr:.2f}x (minimum: {min_dscr}x)")
            
            if dscr < 1.0:
                warnings.append(f"CRITICAL: Negative cash flow - DSCR {dscr:.2f}x")
        else:
            warnings.append("Unable to calculate debt service coverage ratio")
    
    def _check_red_flags(self, documents: Dict) -> List[str]:
        """Check for red flags in the loan package."""
        red_flags = []
        
        # Check for declining income
        if 'tax_returns' in documents and len(documents['tax_returns']) >= 2:
            returns = sorted(documents['tax_returns'], key=lambda x: x.get('tax_year', 0))
            if len(returns) >= 2:
                recent_income = self._get_value(returns[-1], ['adjusted_gross_income', 'agi'], 0)
                prior_income = self._get_value(returns[-2], ['adjusted_gross_income', 'agi'], 0)
                
                if prior_income > 0 and recent_income < prior_income * 0.8:
                    decline = (prior_income - recent_income) / prior_income
                    red_flags.append(f"Income declined {decline:.1%} year-over-year")
        
        # Check for high debt-to-income
        if 'pfs' in documents:
            income = self._get_value(documents['pfs'], ['totalAnnualIncome', 'total_income'], 0)
            debt = self._get_value(documents['pfs'], ['totalLiabilities', 'total_liabilities'], 0)
            
            if income > 0:
                dti = debt / income
                if dti > 5:  # Debt more than 5x annual income
                    red_flags.append(f"High debt-to-income ratio: {dti:.1f}x")
        
        # Check for negative net worth
        if 'pfs' in documents:
            net_worth = self._get_value(documents['pfs'], ['netWorth', 'net_worth'])
            if net_worth and net_worth < 0:
                red_flags.append(f"Negative net worth: ${net_worth:,.0f}")
        
        # Check for past due debts
        if 'debt_schedule' in documents and 'debts' in documents['debt_schedule']:
            for debt in documents['debt_schedule']['debts']:
                status = self._get_value(debt, ['status', 'payment_status'], '')
                if any(term in str(status).lower() for term in ['past due', 'delinquent', 'default']):
                    creditor = self._get_value(debt, ['creditor_name', 'creditor'], 'Unknown')
                    red_flags.append(f"Past due debt: {creditor}")
        
        # Check for litigation
        if 'pfs' in documents:
            litigation = self._get_value(documents['pfs'], ['legalClaimsContingentLiability', 'legal_claims'], 0)
            if litigation > 0:
                red_flags.append(f"Legal claims/litigation: ${litigation:,.0f}")
        
        return red_flags
    
    def _generate_recommendations(
        self,
        failed_checks: List[str],
        warnings: List[str],
        discrepancies: List[Dict]
    ) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        # Recommendations for failed checks
        if any('income mismatch' in check for check in failed_checks):
            recommendations.append("Request explanation for income discrepancies between PFS and tax returns")
            recommendations.append("Verify all income sources with supporting documentation")
        
        if any('debt' in check.lower() for check in failed_checks):
            recommendations.append("Reconcile debt schedule with recent credit report")
            recommendations.append("Confirm all contingent liabilities are disclosed")
        
        if any('coverage' in check for check in failed_checks):
            recommendations.append("Request detailed cash flow projections")
            recommendations.append("Consider requiring additional collateral or guarantors")
        
        # Recommendations for warnings
        if any('declining income' in warning for warning in warnings):
            recommendations.append("Request explanation for income decline")
            recommendations.append("Evaluate business plan for income recovery")
        
        if any('high debt' in warning for warning in warnings):
            recommendations.append("Analyze debt reduction plan")
            recommendations.append("Consider debt consolidation options")
        
        # General recommendations for discrepancies
        if len(discrepancies) > 3:
            recommendations.append("Schedule clarification call with applicant")
            recommendations.append("Request updated financial statements")
        
        return recommendations
    
    def _calculate_noi(self, documents: Dict) -> Optional[float]:
        """Calculate net operating income from documents."""
        noi = 0
        
        # From PFS
        if 'pfs' in documents:
            salary = self._get_value(documents['pfs'], ['salaryIncome', 'salary'], 0)
            business = self._get_value(documents['pfs'], ['businessIncome'], 0)
            investment = self._get_value(documents['pfs'], ['netInvestmentIncome'], 0)
            real_estate = self._get_value(documents['pfs'], ['realEstateIncome'], 0)
            
            noi = salary + business + investment + real_estate
        
        # From business P&L if available
        if 'business_financials' in documents and 'profit_loss' in documents['business_financials']:
            pl = documents['business_financials']['profit_loss']
            net_income = self._get_value(pl, ['net_income', 'netIncome'], 0)
            
            # Add back interest and depreciation for EBITDA
            interest = self._get_value(pl, ['interest_expense', 'interestExpense'], 0)
            depreciation = self._get_value(pl, ['depreciation'], 0)
            
            ebitda = net_income + interest + depreciation
            if ebitda > noi:  # Use higher of personal or business income
                noi = ebitda
        
        return noi if noi > 0 else None
    
    def _calculate_debt_service(self, documents: Dict) -> Optional[float]:
        """Calculate annual debt service from documents."""
        annual_service = 0
        
        if 'debt_schedule' in documents and 'debts' in documents['debt_schedule']:
            for debt in documents['debt_schedule']['debts']:
                monthly = self._get_value(debt, ['monthly_payment', 'monthlyPayment'], 0)
                annual_service += monthly * 12
        
        # Fallback to PFS if no debt schedule
        if annual_service == 0 and 'pfs' in documents:
            # Estimate from mortgage and other loan payments
            mortgage = self._get_value(documents['pfs'], ['mortgagePayment'], 0) * 12
            other_payments = self._get_value(documents['pfs'], ['installmentPayments'], 0) * 12
            annual_service = mortgage + other_payments
        
        return annual_service if annual_service > 0 else None
    
    def _check_missing_debts(self, pfs: Dict, debt_schedule: Dict, discrepancies: List):
        """Check for debts mentioned in PFS but missing from schedule."""
        # Get contingent liabilities from PFS
        contingent = self._get_value(pfs, ['otherContingentLiabilities', 'contingent_liabilities'], '')
        
        if contingent and isinstance(contingent, str):
            # Look for SBA loans mentioned
            if 'sba' in contingent.lower():
                # Check if SBA loans are in debt schedule
                has_sba = False
                if 'debts' in debt_schedule:
                    for debt in debt_schedule['debts']:
                        creditor = self._get_value(debt, ['creditor_name', 'creditor'], '')
                        if 'sba' in str(creditor).lower():
                            has_sba = True
                            break
                
                if not has_sba:
                    discrepancies.append({
                        'type': 'missing_debt',
                        'description': 'SBA loans mentioned in PFS but not in debt schedule',
                        'source': 'contingent_liabilities'
                    })
    
    def _get_value(
        self,
        data: Dict,
        keys: List[str],
        default: Any = None
    ) -> Any:
        """
        Get value from nested dict trying multiple keys.
        
        Args:
            data: Dictionary to search
            keys: List of possible keys
            default: Default value if not found
            
        Returns:
            Found value or default
        """
        for key in keys:
            if key in data:
                value = data[key]
                
                # Handle nested value/confidence structure
                if isinstance(value, dict) and 'value' in value:
                    return value['value']
                
                # Handle direct value
                if value is not None:
                    return value
        
        return default
    
    def generate_validation_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report."""
        report = f"""
LOAN PACKAGE VALIDATION REPORT
================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

OVERALL STATUS: {result.overall_status}
Confidence: {result.confidence:.1%}

VALIDATION SUMMARY
------------------
✅ Passed Checks: {len(result.passed_checks)}
❌ Failed Checks: {len(result.failed_checks)}
⚠️  Warnings: {len(result.warnings)}
"""
        
        if result.passed_checks:
            report += "\n✅ PASSED CHECKS:\n"
            for check in result.passed_checks:
                report += f"   • {check}\n"
        
        if result.failed_checks:
            report += "\n❌ FAILED CHECKS:\n"
            for check in result.failed_checks:
                report += f"   • {check}\n"
        
        if result.warnings:
            report += "\n⚠️  WARNINGS:\n"
            for warning in result.warnings:
                report += f"   • {warning}\n"
        
        if result.discrepancies:
            report += "\n📊 DISCREPANCIES FOUND:\n"
            for disc in result.discrepancies:
                report += f"   • {disc.get('type', 'Unknown')}: "
                if 'variance' in disc:
                    report += f"{disc['variance']:.1%} variance\n"
                else:
                    report += f"{disc.get('description', '')}\n"
        
        if result.recommendations:
            report += "\n💡 RECOMMENDATIONS:\n"
            for i, rec in enumerate(result.recommendations, 1):
                report += f"   {i}. {rec}\n"
        
        report += f"""

CONCLUSION
----------
{"✅ Loan package validation PASSED" if result.is_valid else "❌ Loan package requires further review"}
Manual review recommended: {"Yes" if result.needs_review else "No"}
"""
        
        return report