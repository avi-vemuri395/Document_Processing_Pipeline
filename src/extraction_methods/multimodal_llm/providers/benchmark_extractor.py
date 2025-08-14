"""
Ultra-simple benchmark extractor for unstructured JSON extraction.
No schema validation, no confidence scoring, just raw extraction.
"""

import os
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Union, Optional

try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
except ImportError:
    pass  # dotenv not required

from ..core.universal_preprocessor import UniversalPreprocessor


class BenchmarkExtractor:
    """
    Dead simple extractor for benchmarking.
    Takes documents → converts to images → extracts all data as unstructured JSON.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with minimal setup."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")
        
        # Use provided key, then env var, then .env file
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError(
                "No API key found. Please either:\n"
                "1. Pass api_key parameter\n"
                "2. Set ANTHROPIC_API_KEY environment variable\n"
                "3. Add ANTHROPIC_API_KEY to .env file"
            )
        
        self.client = AsyncAnthropic(api_key=api_key)
        self.preprocessor = UniversalPreprocessor()
        self.model = "claude-3-5-sonnet-20241022"
    
    async def extract_all(
        self, 
        file_paths: Union[str, Path, List[Union[str, Path]]]
    ) -> Dict[str, Any]:
        """
        Extract all information from documents as structured JSON.
        
        Args:
            file_paths: Single document or list of documents
            
        Returns:
            Dict with all extracted data in structured format
        """
        start_time = time.time()
        
        # Normalize input
        if not isinstance(file_paths, list):
            file_paths = [file_paths]
        
        # Convert all documents to images
        all_images = []
        for file_path in file_paths:
            try:
                processed = self.preprocessor.preprocess_any_document(file_path)
                all_images.extend(processed.images)
                print(f"  ✅ Processed {Path(file_path).name}: {len(processed.images)} images")
            except Exception as e:
                print(f"  ❌ Failed to process {Path(file_path).name}: {e}")
        
        if not all_images:
            return {"error": "No documents could be processed"}
        
        # Extract data with structured prompt
        result = await self._extract_from_images(all_images)
        
        # Add metadata
        result['_metadata'] = {
            'processing_time': time.time() - start_time,
            'documents_processed': len(file_paths),
            'total_images': len(all_images),
            'model': self.model
        }
        
        return result
    
    async def _extract_from_images(self, images: List) -> Dict[str, Any]:
        """Extract data from images with ultra-simple prompt."""
        
        # Convert images to base64
        image_data = self.preprocessor.images_to_base64(images)
        
        # Enhanced prompt for better extraction coverage
#         prompt = """Extract ALL information from these loan application documents as JSON.

# FOCUS AREAS:
# 1. Personal Information:
#    - Full name, SSN, date of birth
#    - Phone numbers (mobile, business, home)
#    - Email addresses
#    - Residential and business addresses
#    - Marital status, citizenship status

# 2. Business Information:
#    - Business/company names (ALL entities mentioned)
#    - Ownership percentages
#    - Business structure (LLC, Corp, etc.)
#    - Management titles and roles
#    - Years in business

# 3. Financial Data:
#    - Assets (cash, investments, real estate, etc.)
#    - Liabilities (loans, mortgages, credit cards)
#    - Income (salary, business, investment)
#    - Net worth
#    - Tax information (AGI, refunds, payments)

# 4. Real Estate:
#    - Property addresses
#    - Property types and values
#    - Mortgage details

# 5. Other Entities:
#    - Any other businesses owned
#    - Partnerships or investments

# INSTRUCTIONS:
# - Extract EVERYTHING you can see
# - Preserve exact values (keep $, commas, etc.)
# - For checkboxes: note if checked (Yes/No)
# - Create logical nested structure
# - Use descriptive keys

# Return ONLY a JSON object with all extracted data."""

        # Optimized extraction prompt for maximum accuracy
        prompt = """Extract ALL information from these loan application documents. Focus on ACCURACY and COMPLETENESS.

## EXTRACTION STRATEGY:
1. Read EVERY piece of text carefully - numbers, names, addresses, percentages
2. Look for patterns: tables, checkboxes, form fields, signatures
3. Pay special attention to financial values, SSN, business relationships
4. Extract both line items AND totals for validation
5. Note any calculated fields (net worth = assets - liabilities)
6. Capture ownership percentages and business entity relationships

## OUTPUT STRUCTURE:
{
  "metadata": {
    "document_type": "identify what type of document this is",
    "document_date": "date on document if visible",
    "total_pages": number,
    "extraction_confidence": 0.0-1.0
  },
  
  "personal": {
    "primary_applicant": {
      "name": {"first": "", "middle": "", "last": "", "suffix": ""},
      "ssn": "xxx-xx-xxxx format",
      "dob": "YYYY-MM-DD",
      "phones": {"mobile": "", "home": "", "business": ""},
      "email": "",
      "marital_status": "",
      "citizenship": {"is_us_citizen": boolean, "country": ""},
      "government_employment": {"employed": boolean, "agency": ""},
      "ownership_percentage": number
    },
    "co_applicants": [/* same structure */]
  },
  
  "addresses": {
    "current_residence": {
      "street": "", "city": "", "state": "", "zip": "",
      "years_at_address": number,
      "own_or_rent": ""
    },
    "previous_residences": [],
    "business_address": {/* same structure */},
    "mailing_address": {/* same structure */}
  },
  
  "business": {
    "primary_business": {
      "legal_name": "",
      "dba_names": [],
      "ein": "xx-xxxxxxx",
      "entity_type": "LLC|Corp|Partnership|Sole Prop",
      "date_established": "YYYY-MM-DD",
      "naics_code": "",
      "employees": {"full_time": number, "part_time": number},
      "annual_revenue": number,
      "ownership": [
        {"name": "", "percentage": number, "role": ""}
      ]
    },
    "affiliated_businesses": [/* same structure */]
  },
  
  "financials": {
    "assets": {
      "liquid": {
        "cash_on_hand": number,
        "checking_accounts": [{"bank": "", "balance": number}],
        "savings_accounts": [{"bank": "", "balance": number}],
        "money_market": number,
        "cds": number
      },
      "investments": {
        "stocks_bonds": [{"description": "", "value": number}],
        "retirement_accounts": [{"type": "401k|IRA", "value": number}],
        "life_insurance_cash_value": number
      },
      "real_estate": [
        {
          "address": {"street": "", "city": "", "state": "", "zip": ""},
          "property_type": "Primary|Rental|Commercial|Land",
          "current_value": number,
          "purchase_price": number,
          "purchase_date": "YYYY-MM-DD",
          "mortgage": {
            "lender": "",
            "original_amount": number,
            "current_balance": number,
            "monthly_payment": number,
            "interest_rate": number
          }
        }
      ],
      "personal_property": {
        "vehicles": [{"year": "", "make": "", "model": "", "value": number}],
        "other": [{"description": "", "value": number}]
      },
      "business_assets": {
        "equipment": number,
        "inventory": number,
        "accounts_receivable": number
      }
    },
    
    "liabilities": {
      "real_estate_loans": [/* see real_estate.mortgage structure */],
      "other_debts": [
        {
          "creditor": "",
          "account_number": "",
          "debt_type": "auto|credit_card|business|personal|student",
          "original_amount": number,
          "current_balance": number,
          "monthly_payment": number,
          "interest_rate": number,
          "maturity_date": "YYYY-MM-DD",
          "collateral": "",
          "past_due": boolean
        }
      ]
    },
    
    "income": {
      "employment": {
        "salary": number,
        "bonuses": number,
        "commissions": number
      },
      "business": {
        "net_income": number,
        "k1_distributions": number
      },
      "investments": {
        "dividends": number,
        "interest": number,
        "capital_gains": number
      },
      "real_estate": {
        "rental_income": number
      },
      "other": [{"source": "", "amount": number}]
    },
    
    "tax_info": {
      "year": number,
      "filing_status": "",
      "adjusted_gross_income": number,
      "taxable_income": number,
      "tax_owed_or_refund": number
    }
  },
  
  "checkboxes_and_questions": {
    "has_declared_bankruptcy": boolean,
    "bankruptcy_details": {"date": "", "chapter": "", "discharged": boolean},
    "pending_lawsuits": boolean,
    "lawsuit_details": "",
    "delinquent_on_taxes": boolean,
    "delinquent_on_child_support": boolean,
    "borrowed_down_payment": boolean,
    "co_signer_on_other_debts": boolean,
    "us_citizen": boolean
  },
  
  "extracted_values": {
    /* Any other data that doesn't fit above categories */
  },
  
  "quality_indicators": {
    "unclear_fields": [
      {"field": "", "reason": "illegible|cut_off|ambiguous", "best_guess": ""}
    ],
    "missing_expected_fields": ["list fields that seem like they should be there"],
    "calculation_checks": {
      "assets_total_matches": boolean,
      "liabilities_total_matches": boolean,
      "net_worth_calculation": "assets - liabilities = stated_net_worth?"
    }
  }
}

## CRITICAL ACCURACY REQUIREMENTS:
1. Numbers: Convert to numbers (remove $ and commas): "$1,500,000" → 1500000
2. Dates: Use YYYY-MM-DD format consistently  
3. SSN/EIN: Preserve format with dashes: "123-45-6789"
4. Percentages: Store as numbers: "75%" → 75
5. Business Names: Extract ALL business entities mentioned
6. Addresses: Include street, city, state, zip separately
7. Ownership: Capture all ownership percentages and relationships
8. Checkboxes: true/false based on marks or X's
9. Tables: Extract each row AND verify totals match
10. Missing data: Use null, never guess or make up values

## VALIDATION CHECKS:
- Verify asset totals = sum of individual assets
- Verify liability totals = sum of individual liabilities  
- Calculate net worth = total assets - total liabilities
- Check that percentages add up to 100% where applicable
- Ensure all business entities are captured with ownership %

Return ONLY valid JSON. Be extremely precise with numbers and business relationships.""" 

        # Build message content
        content = [{"type": "text", "text": prompt}]
        for img_data in image_data:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img_data['media_type'],
                    "data": img_data['data']
                }
            })
        
        # Single API call
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0,
                messages=[{"role": "user", "content": content}]
            )
            
            # Parse response
            raw_text = response.content[0].text.strip()
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            
            return json.loads(raw_text)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON: {e}")
            return {"raw_text": raw_text, "error": str(e)}
        except Exception as e:
            print(f"API call failed: {e}")
            return {"error": str(e)}
    


class SimpleFormFiller:
    """
    Optional: Maps unstructured JSON to form fields.
    Uses simple fuzzy matching without complex logic.
    """
    
    def __init__(self):
        self.extractor = BenchmarkExtractor()
    
    async def extract_and_fill(
        self,
        documents: List[Union[str, Path]],
        form_template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract data and map to form template.
        
        Args:
            documents: List of document paths
            form_template: Template with field names as keys
            
        Returns:
            Filled form with extracted values
        """
        # Extract unstructured data
        extracted = await self.extractor.extract_all(documents)
        
        # Simple mapping to form fields
        filled_form = {}
        for field_name in form_template:
            value = self._find_value_in_json(field_name, extracted)
            filled_form[field_name] = value
        
        return filled_form
    
    def _find_value_in_json(self, field_name: str, data: Dict, depth: int = 0) -> Any:
        """
        Recursively search for field in unstructured JSON.
        Simple fuzzy matching based on key similarity.
        """
        if depth > 5:  # Prevent infinite recursion
            return None
        
        # Direct match
        if field_name in data:
            return data[field_name]
        
        # Case-insensitive match
        field_lower = field_name.lower()
        for key, value in data.items():
            if key.lower() == field_lower:
                return value
        
        # Partial match
        for key, value in data.items():
            if field_lower in key.lower() or key.lower() in field_lower:
                return value
        
        # Recursive search in nested objects
        for value in data.values():
            if isinstance(value, dict):
                result = self._find_value_in_json(field_name, value, depth + 1)
                if result is not None:
                    return result
        
        return None