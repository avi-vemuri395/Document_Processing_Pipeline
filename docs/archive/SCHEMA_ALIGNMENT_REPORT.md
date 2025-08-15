# Schema Alignment Report: Current Extraction vs Prisma Schema

## Executive Summary

This report analyzes the alignment between the current PFS extraction capabilities and the target Prisma schema for loan application data processing.

**Overall Alignment: PARTIAL (≈40%)**
- Core financial fields are well-covered
- Personal/business information needs expansion
- Missing several relationship structures

## 1. PersonalFinancialStatementMetadata Alignment

### ✅ **WELL ALIGNED** - Assets (90% coverage)

| Prisma Field | Current Extraction | Status | Notes |
|-------------|-------------------|---------|-------|
| cashOnHand | cash_on_hand | ✅ Aligned | Extracts correctly |
| savingsAccount | savings_accounts | ✅ Aligned | Field name difference |
| retirementAccount | ira_retirement_accounts | ✅ Aligned | Maps to retirement |
| accountAndNotesReceivable | accounts_notes_receivable | ✅ Aligned | Good match |
| lifeInsuranceCashValue | life_insurance_cash_value | ✅ Aligned | Extracts well |
| stockAndBonds | stocks_bonds | ✅ Aligned | Combined field |
| realEstate | real_estate_owned | ✅ Aligned | Good extraction |
| automobileValue | automobile_present_value | ✅ Aligned | Field name difference |
| otherPersonalProperty | other_personal_property | ✅ Aligned | Matches |
| otherAssets | other_assets | ✅ Aligned | Extracts |

### ⚠️ **PARTIALLY ALIGNED** - Liabilities (60% coverage)

| Prisma Field | Current Extraction | Status | Notes |
|-------------|-------------------|---------|-------|
| accountsPayable | accounts_payable | ✅ Aligned | |
| notesPayableToBanks | notes_payable_to_banks | ✅ Aligned | |
| installmentAccountAutoLoan | ❌ Missing | ❌ Gap | Not extracted |
| installmentAccountAutoMonthlyPayment | ❌ Missing | ❌ Gap | Not extracted |
| installmentAccountOtherLoan | installment_debts | ⚠️ Partial | Combined field |
| installmentAccountOtherLoanMonthlyPayment | ❌ Missing | ❌ Gap | Not extracted |
| loanOnLifeInsurance | loan_on_life_insurance | ✅ Aligned | |
| mortgageOnRealEstate | mortgages_on_real_estate | ✅ Aligned | Low confidence |
| unpaidTaxes | unpaid_taxes | ✅ Aligned | |
| otherLiabilities | other_liabilities | ✅ Aligned | |
| totalLiabilities | total_liabilities | ✅ Aligned | |

### ✅ **ALIGNED** - Income Fields (100% coverage)

| Prisma Field | Current Extraction | Status |
|-------------|-------------------|---------|
| salaryIncome | salary | ✅ Aligned |
| netInvestmentIncome | net_investment_income | ✅ Aligned |
| realEstateIncome | real_estate_income | ✅ Aligned |
| otherIncome | other_income | ✅ Aligned |

### ❌ **MISSING** - Contingent Liabilities (0% coverage)

All contingent liability fields are missing:
- asEndorsedContingentLiability
- legalClaimsContingentLiability
- provisionForFederalTaxesContingentLiability
- otherContingentLiabilities

### ❌ **MISSING** - Description Fields (0% coverage)

All description fields are missing:
- descriptionOfOtherIncome
- descriptionOfOtherPersonalProperty
- descriptionOfUnpaidTaxes
- descriptionOfOtherLiabilities
- descriptionOfLifeInsurance

## 2. BeneficialOwnerMetadata Alignment

### ⚠️ **WEAK ALIGNMENT** - Personal Information (20% coverage)

| Prisma Field | Current Extraction | Status | Notes |
|-------------|-------------------|---------|-------|
| firstName | name (combined) | ⚠️ Partial | Need to split name |
| lastName | name (combined) | ⚠️ Partial | Need to split name |
| ssn | social_security_number | ✅ Aligned | Pattern exists |
| email | ❌ Missing | ❌ Gap | Not extracted |
| dateOfBirth | date_of_birth | ✅ Aligned | Pattern exists |
| title | ❌ Missing | ❌ Gap | |
| yearsOfExperience | ❌ Missing | ❌ Gap | |
| ownershipPercentage | ❌ Missing | ❌ Gap | |

### ❌ **NOT COVERED** - Status Information (0% coverage)

All status fields missing:
- maritalStatus
- hasAlimony
- delinquentOnChildSupport
- employedByUSGovernment
- usGovernmentAgency
- isUSCitizen
- driversLicenseNumber

## 3. Additional Schema Elements Not Covered

### ❌ **BusinessMetadata** - Not extracted
- Business name, DBA, EIN
- Number of employees
- Entity type, annual sales
- SBA debt information

### ❌ **DebtScheduleItem** - Not extracted
- Individual debt details
- Payment schedules
- Interest rates
- Account numbers

### ❌ **Real Estate Assets Detail** - Limited extraction
Currently only extracts total value, missing:
- Individual property details
- Mortgage information
- Property addresses
- Purchase dates

## 4. Data Type Mismatches

| Issue | Current | Required | Impact |
|-------|---------|----------|--------|
| Numeric fields | String/Decimal | Int | Need conversion |
| Addresses | Single string | Structured Address model | Need parsing |
| Names | Combined string | firstName/lastName | Need splitting |

## 5. Current Extraction Success Metrics

Based on Brigham Dallas PFS test:
- **Fields Extracted**: 21 fields
- **Average Confidence**: 67.62%
- **High Confidence Fields** (>80%): 8 fields
- **Low Confidence Fields** (<50%): 2 fields

## 6. Priority Gaps to Address

### 🔴 **HIGH PRIORITY** (Core loan application data)
1. **Name Parsing**: Split into firstName/lastName
2. **Email Extraction**: Add email pattern matching
3. **Business Information**: Extract business name, EIN
4. **Debt Schedule**: Extract individual debts with details

### 🟡 **MEDIUM PRIORITY** (Important but not critical)
1. **Address Parsing**: Structure into street/city/state/zip
2. **Contingent Liabilities**: Add pattern matching
3. **Real Estate Details**: Extract individual properties
4. **Monthly Payment Fields**: Extract payment amounts

### 🟢 **LOW PRIORITY** (Nice to have)
1. **Description Fields**: Extract text descriptions
2. **Status Information**: Marital status, citizenship
3. **Securities Details**: Individual stock/bond holdings

## 7. Recommendations

### Immediate Actions
1. **Update PFS Extractor** to split name field into firstName/lastName
2. **Add Email Pattern** to extract email addresses
3. **Convert Data Types** from String/Decimal to Int where needed
4. **Enhance Business Extraction** to capture business name and EIN

### Next Phase
1. **Create Debt Schedule Extractor** for detailed debt information
2. **Implement Address Parser** to structure address data
3. **Add Real Estate Detail Extractor** for property-level data
4. **Develop Business Metadata Extractor** for company information

### Data Quality Improvements
1. **Improve Name Extraction**: Currently extracts "Brigham Dallas Business Phone" instead of just "Brigham Dallas"
2. **Enhance Confidence**: Many fields at 55-65% confidence need improvement
3. **Add Validation**: Ensure SSN, EIN formats are valid
4. **Handle Missing Data**: Better defaults and null handling

## 8. Coverage Summary

| Schema Model | Fields Coverage | Status |
|--------------|----------------|---------|
| PersonalFinancialStatementMetadata | 60% | ⚠️ Partial |
| BeneficialOwnerMetadata | 20% | ❌ Weak |
| BusinessMetadata | 0% | ❌ Missing |
| DebtScheduleItem | 0% | ❌ Missing |
| Real Estate Assets | 10% | ❌ Minimal |
| CapitalUsageBreakdown | 0% | ❌ Missing |
| ApplicantQuestionnaire | 0% | ❌ Missing |

## Conclusion

The current extraction system provides a solid foundation for PFS financial data (assets, liabilities, income) but needs significant expansion to fully support the loan application schema. Priority should be given to:

1. Improving personal information extraction (name splitting, email)
2. Adding business information extraction
3. Implementing debt schedule extraction
4. Structuring address data properly

With these improvements, the system could achieve 80%+ schema alignment for core loan application processing.