"""
Generates JSON Schemas from Prisma models for LLM-based extraction.
Maps database schema requirements to extraction constraints.
"""

from typing import Dict, Any, List, Optional
from enum import Enum


class PrismaFieldType(Enum):
    """Prisma field types that we handle."""
    STRING = "String"
    INT = "Int"
    FLOAT = "Float"
    BOOLEAN = "Boolean"
    DATETIME = "DateTime"
    DECIMAL = "Decimal"


class PrismaSchemaGenerator:
    """Converts Prisma models to JSON Schemas for structured extraction."""
    
    def __init__(self):
        """Initialize the schema generator with field mappings."""
        self.type_mappings = {
            PrismaFieldType.STRING: "string",
            PrismaFieldType.INT: "integer",
            PrismaFieldType.FLOAT: "number",
            PrismaFieldType.BOOLEAN: "boolean",
            PrismaFieldType.DATETIME: "string",  # with format: date-time
            PrismaFieldType.DECIMAL: "number"
        }
        
        # Define our Prisma models (in lieu of parsing actual .prisma file)
        self.models = self._define_models()
    
    def _define_models(self) -> Dict[str, Dict[str, Any]]:
        """Define Prisma models and their fields."""
        return {
            "PersonalFinancialStatementMetadata": {
                "fields": {
                    # Personal Information
                    "firstName": {"type": PrismaFieldType.STRING, "required": True, "description": "Applicant's first name"},
                    "lastName": {"type": PrismaFieldType.STRING, "required": True, "description": "Applicant's last name"},
                    "email": {"type": PrismaFieldType.STRING, "required": False, "format": "email", "description": "Email address"},
                    "phone": {"type": PrismaFieldType.STRING, "required": False, "description": "Phone number"},
                    "businessPhone": {"type": PrismaFieldType.STRING, "required": False, "description": "Business phone number"},
                    
                    # Assets
                    "cashOnHand": {"type": PrismaFieldType.INT, "required": False, "description": "Cash on hand in dollars (as integer)"},
                    "savingsAccount": {"type": PrismaFieldType.INT, "required": False, "description": "Savings account balance in dollars (as integer)"},
                    "retirementAccount": {"type": PrismaFieldType.INT, "required": False, "description": "IRA/retirement account value in dollars (as integer)"},
                    "accountAndNotesReceivable": {"type": PrismaFieldType.INT, "required": False, "description": "Accounts/notes receivable in dollars (as integer)"},
                    "lifeInsuranceCashValue": {"type": PrismaFieldType.INT, "required": False, "description": "Life insurance cash surrender value in dollars (as integer)"},
                    "stockAndBonds": {"type": PrismaFieldType.INT, "required": False, "description": "Stocks and bonds value in dollars (as integer)"},
                    "realEstate": {"type": PrismaFieldType.INT, "required": False, "description": "Real estate owned value in dollars (as integer)"},
                    "automobileValue": {"type": PrismaFieldType.INT, "required": False, "description": "Automobile present value in dollars (as integer)"},
                    "otherPersonalProperty": {"type": PrismaFieldType.INT, "required": False, "description": "Other personal property value in dollars (as integer)"},
                    "otherAssets": {"type": PrismaFieldType.INT, "required": False, "description": "Other assets value in dollars (as integer)"},
                    "totalAssets": {"type": PrismaFieldType.INT, "required": True, "description": "Total assets in dollars (as integer)"},
                    
                    # Liabilities
                    "accountsPayable": {"type": PrismaFieldType.INT, "required": False, "description": "Accounts payable in dollars (as integer)"},
                    "notesPayableToBanks": {"type": PrismaFieldType.INT, "required": False, "description": "Notes payable to banks in dollars (as integer)"},
                    "installmentAccountAutoLoan": {"type": PrismaFieldType.INT, "required": False, "description": "Auto loan balance in dollars (as integer)"},
                    "installmentAccountAutoMonthlyPayment": {"type": PrismaFieldType.INT, "required": False, "description": "Auto loan monthly payment in dollars (as integer)"},
                    "installmentAccountOtherLoan": {"type": PrismaFieldType.INT, "required": False, "description": "Other installment loan balance in dollars (as integer)"},
                    "installmentAccountOtherLoanMonthlyPayment": {"type": PrismaFieldType.INT, "required": False, "description": "Other loan monthly payment in dollars (as integer)"},
                    "loanOnLifeInsurance": {"type": PrismaFieldType.INT, "required": False, "description": "Loan on life insurance in dollars (as integer)"},
                    "mortgageOnRealEstate": {"type": PrismaFieldType.INT, "required": False, "description": "Mortgages on real estate in dollars (as integer)"},
                    "unpaidTaxes": {"type": PrismaFieldType.INT, "required": False, "description": "Unpaid taxes in dollars (as integer)"},
                    "otherLiabilities": {"type": PrismaFieldType.INT, "required": False, "description": "Other liabilities in dollars (as integer)"},
                    "totalLiabilities": {"type": PrismaFieldType.INT, "required": True, "description": "Total liabilities in dollars (as integer)"},
                    
                    # Income
                    "salaryIncome": {"type": PrismaFieldType.INT, "required": False, "description": "Annual salary in dollars (as integer)"},
                    "netInvestmentIncome": {"type": PrismaFieldType.INT, "required": False, "description": "Net investment income in dollars (as integer)"},
                    "realEstateIncome": {"type": PrismaFieldType.INT, "required": False, "description": "Real estate income in dollars (as integer)"},
                    "otherIncome": {"type": PrismaFieldType.INT, "required": False, "description": "Other income in dollars (as integer)"},
                    
                    # Contingent Liabilities
                    "asEndorsedContingentLiability": {"type": PrismaFieldType.INT, "required": False, "description": "As endorser or co-maker in dollars (as integer)"},
                    "legalClaimsContingentLiability": {"type": PrismaFieldType.INT, "required": False, "description": "Legal claims/judgments in dollars (as integer)"},
                    "provisionForFederalTaxesContingentLiability": {"type": PrismaFieldType.INT, "required": False, "description": "Provision for federal taxes in dollars (as integer)"},
                    "otherContingentLiabilities": {"type": PrismaFieldType.INT, "required": False, "description": "Other special debt in dollars (as integer)"},
                    
                    # Calculated Fields
                    "netWorth": {"type": PrismaFieldType.INT, "required": False, "description": "Net worth (assets - liabilities) in dollars (as integer)"},
                    "totalAnnualIncome": {"type": PrismaFieldType.INT, "required": False, "description": "Total annual income in dollars (as integer)"}
                }
            },
            
            "BeneficialOwnerMetadata": {
                "fields": {
                    "firstName": {"type": PrismaFieldType.STRING, "required": True, "description": "Owner's first name"},
                    "lastName": {"type": PrismaFieldType.STRING, "required": True, "description": "Owner's last name"},
                    "ssn": {"type": PrismaFieldType.STRING, "required": False, "pattern": "^\\d{3}-\\d{2}-\\d{4}$", "description": "Social Security Number"},
                    "email": {"type": PrismaFieldType.STRING, "required": False, "format": "email", "description": "Email address"},
                    "dateOfBirth": {"type": PrismaFieldType.DATETIME, "required": False, "description": "Date of birth"},
                    "title": {"type": PrismaFieldType.STRING, "required": False, "description": "Job title"},
                    "yearsOfExperience": {"type": PrismaFieldType.INT, "required": False, "description": "Years of business experience"},
                    "ownershipPercentage": {"type": PrismaFieldType.FLOAT, "required": False, "description": "Ownership percentage (0-100)"},
                    "maritalStatus": {"type": PrismaFieldType.STRING, "required": False, "enum": ["single", "married", "divorced", "widowed"], "description": "Marital status"},
                    "isUSCitizen": {"type": PrismaFieldType.BOOLEAN, "required": False, "description": "US citizenship status"},
                    "driversLicenseNumber": {"type": PrismaFieldType.STRING, "required": False, "description": "Driver's license number"}
                }
            },
            
            "BusinessMetadata": {
                "fields": {
                    "businessName": {"type": PrismaFieldType.STRING, "required": True, "description": "Legal business name"},
                    "dba": {"type": PrismaFieldType.STRING, "required": False, "description": "Doing Business As name"},
                    "ein": {"type": PrismaFieldType.STRING, "required": False, "pattern": "^\\d{2}-\\d{7}$", "description": "Employer Identification Number"},
                    "numberOfEmployees": {"type": PrismaFieldType.INT, "required": False, "description": "Number of employees"},
                    "entityType": {"type": PrismaFieldType.STRING, "required": False, "enum": ["LLC", "Corporation", "Partnership", "Sole Proprietorship"], "description": "Business entity type"},
                    "annualSales": {"type": PrismaFieldType.INT, "required": False, "description": "Annual sales/revenue in dollars (as integer)"},
                    "dateEstablished": {"type": PrismaFieldType.DATETIME, "required": False, "description": "Business establishment date"},
                    "outstandingSBADebt": {"type": PrismaFieldType.INT, "required": False, "description": "Outstanding SBA debt in dollars (as integer)"}
                }
            },
            
            "DebtScheduleItem": {
                "fields": {
                    "creditorName": {"type": PrismaFieldType.STRING, "required": True, "description": "Name of creditor"},
                    "accountNumber": {"type": PrismaFieldType.STRING, "required": False, "description": "Account number"},
                    "originalAmount": {"type": PrismaFieldType.INT, "required": False, "description": "Original loan amount in dollars (as integer)"},
                    "currentBalance": {"type": PrismaFieldType.INT, "required": True, "description": "Current balance in dollars (as integer)"},
                    "monthlyPayment": {"type": PrismaFieldType.INT, "required": False, "description": "Monthly payment amount in dollars (as integer)"},
                    "interestRate": {"type": PrismaFieldType.FLOAT, "required": False, "description": "Interest rate percentage"},
                    "maturityDate": {"type": PrismaFieldType.DATETIME, "required": False, "description": "Loan maturity date"},
                    "collateral": {"type": PrismaFieldType.STRING, "required": False, "description": "Collateral description"},
                    "status": {"type": PrismaFieldType.STRING, "required": False, "enum": ["current", "past_due", "paid_off"], "description": "Payment status"}
                }
            }
        }
    
    def generate_extraction_schema(
        self,
        model_name: str,
        include_optional: bool = True,
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON Schema for a Prisma model.
        
        Args:
            model_name: Name of the Prisma model
            include_optional: Whether to include optional fields
            custom_instructions: Additional extraction instructions
            
        Returns:
            JSON Schema for LLM extraction
        """
        if model_name not in self.models:
            raise ValueError(f"Unknown model: {model_name}")
        
        model = self.models[model_name]
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": f"{model_name} Extraction Schema",
            "description": f"Schema for extracting {model_name} from documents",
            "properties": {},
            "required": []
        }
        
        # Add custom instructions if provided
        if custom_instructions:
            schema["description"] += f". {custom_instructions}"
        
        # Process each field
        for field_name, field_def in model["fields"].items():
            if not include_optional and not field_def.get("required", False):
                continue
            
            # Build field schema
            field_schema = {
                "type": self.type_mappings[field_def["type"]],
                "description": field_def.get("description", "")
            }
            
            # Add format if specified
            if "format" in field_def:
                field_schema["format"] = field_def["format"]
            
            # Add pattern if specified
            if "pattern" in field_def:
                field_schema["pattern"] = field_def["pattern"]
            
            # Add enum if specified
            if "enum" in field_def:
                field_schema["enum"] = field_def["enum"]
            
            # Special handling for datetime
            if field_def["type"] == PrismaFieldType.DATETIME:
                field_schema["format"] = "date-time"
            
            # Add to schema
            schema["properties"][field_name] = field_schema
            
            # Add to required if needed
            if field_def.get("required", False):
                schema["required"].append(field_name)
        
        return schema
    
    def generate_debt_schedule_schema(self) -> Dict[str, Any]:
        """Generate schema specifically for debt schedule extraction."""
        item_schema = self.generate_extraction_schema("DebtScheduleItem")
        
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Debt Schedule Extraction",
            "properties": {
                "debts": {
                    "type": "array",
                    "description": "List of all debts/liabilities",
                    "items": item_schema["properties"]
                },
                "totalDebt": {
                    "type": "integer",
                    "description": "Sum of all current balances in dollars (as integer)"
                }
            },
            "required": ["debts"]
        }
    
    def generate_combined_schema(self, model_names: List[str]) -> Dict[str, Any]:
        """
        Generate a combined schema for extracting multiple models.
        
        Args:
            model_names: List of model names to combine
            
        Returns:
            Combined JSON Schema
        """
        combined = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "title": "Combined Extraction Schema",
            "properties": {},
            "required": []
        }
        
        for model_name in model_names:
            model_schema = self.generate_extraction_schema(model_name)
            # Add as nested object
            combined["properties"][model_name.lower()] = {
                "type": "object",
                "properties": model_schema["properties"],
                "required": model_schema.get("required", [])
            }
        
        return combined