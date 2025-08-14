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
from .files_client import FilesAPIClient  # TEST: Files API integration


class BenchmarkExtractor:
    """
    Dead simple extractor for benchmarking.
    Takes documents → converts to images → extracts all data as unstructured JSON.
    """
    
    def __init__(self, api_key: Optional[str] = None, use_files_api: bool = False):
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
        self.model = "claude-sonnet-4-20250514"
        
        # TEST: Files API integration
        self.use_files_api = use_files_api or os.getenv("USE_FILES_API", "false").lower() == "true"
        self.files_client = FilesAPIClient(api_key=api_key) if self.use_files_api else None
    
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
        
        print("\n" + "="*70)
        print("📊 EXTRACTION STARTED")
        print("="*70)
        
        # Normalize input
        if not isinstance(file_paths, list):
            file_paths = [file_paths]
        
        print(f"\n📁 Documents to process: {len(file_paths)}")
        total_file_size = sum(Path(f).stat().st_size for f in file_paths if Path(f).exists())
        print(f"📏 Total file size: {total_file_size / 1024 / 1024:.2f} MB")
        
        # Convert all documents to images
        all_images = []
        total_pages = 0
        for file_path in file_paths:
            try:
                file_size = Path(file_path).stat().st_size / 1024 / 1024  # MB
                print(f"\n  📄 Processing: {Path(file_path).name} ({file_size:.2f} MB)")
                
                processed = self.preprocessor.preprocess_any_document(file_path)
                all_images.extend(processed.images)
                
                # Track dimensions
                for idx, img in enumerate(processed.images):
                    print(f"     • Image {idx+1}: {img.width}x{img.height} pixels")
                    if img.width > 2000 or img.height > 2000:
                        print(f"     ⚠️  WARNING: Image exceeds 2000px limit!")
                
                print(f"  ✅ Generated {len(processed.images)} images")
                total_pages += len(processed.images)
                
            except Exception as e:
                print(f"  ❌ Failed to process {Path(file_path).name}: {e}")
        
        print(f"\n📊 PREPROCESSING SUMMARY:")
        print(f"  • Total images created: {len(all_images)}")
        print(f"  • Average images per document: {len(all_images)/len(file_paths):.1f}")
        
        if not all_images:
            return {"error": "No documents could be processed"}
        
        # Choose extraction method
        print(f"\n🔧 EXTRACTION METHOD:")
        if self.use_files_api:
            print("  • Mode: Files API (Native PDF)")
            print("  • Expected behavior: Higher accuracy, MORE tokens")
            result = await self._extract_with_files_api(file_paths)
        else:
            print("  • Mode: Image-based (Base64)")
            print("  • Expected behavior: Good accuracy, FEWER tokens")
            estimated_tokens = len(all_images) * 1500  # Rough estimate
            print(f"  • Estimated tokens: ~{estimated_tokens:,}")
            result = await self._extract_from_images(all_images)
        
        # Add metadata
        processing_time = time.time() - start_time
        result['_metadata'] = {
            'processing_time': processing_time,
            'documents_processed': len(file_paths),
            'total_images': len(all_images),
            'model': self.model,
            'files_api_used': self.use_files_api,
            'total_file_size_mb': total_file_size / 1024 / 1024
        }
        
        print(f"\n✅ EXTRACTION COMPLETE:")
        print(f"  • Processing time: {processing_time:.2f} seconds")
        print(f"  • Rate: {len(file_paths)/processing_time:.2f} docs/second")
        print("="*70 + "\n")
        
        return result
    
    async def _extract_from_images(self, images: List) -> Dict[str, Any]:
        """Extract data from images with ultra-simple prompt."""
        
        print(f"\n🔄 STARTING IMAGE-BASED EXTRACTION")
        print(f"  • Converting {len(images)} images to base64...")
        
        # Convert images to base64
        image_data = self.preprocessor.images_to_base64(images)
        
        # Calculate approximate token usage
        total_base64_size = sum(len(img['data']) for img in image_data) 
        estimated_tokens = total_base64_size // 3  # Rough token estimate
        print(f"  • Base64 data size: {total_base64_size / 1024 / 1024:.2f} MB")
        print(f"  • Estimated tokens: ~{estimated_tokens:,}")
        
        if estimated_tokens > 30000:
            print(f"  ⚠️  WARNING: May exceed rate limit (30k tokens/min)")
            print(f"     Consider processing fewer documents at once")
        
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

## FINANCIAL DATA EXTRACTION (CRITICAL):
For Balance Sheets, P&L Statements, and Financial Tables:
- Extract ALL line items with their values
- Look for: Current Assets, Fixed Assets, Total Assets
- Look for: Current Liabilities, Long-term Debt, Total Liabilities
- Look for: Revenue, Expenses, Net Income, EBITDA
- Look for: Cash, Accounts Receivable, Inventory
- Extract both current year AND prior year columns if present

For Tax Returns:
- Line 1: Gross receipts or sales
- Line 11: Total income
- Line 21: Total expenses
- Line 31: Net income
- Schedule K: Partner's distributive share items
- Form 1065: Partnership income details
- Form 1120S: S-Corp income details
- Personal returns: AGI, taxable income, refund/amount owed

For Excel/Spreadsheet Data:
- Extract ALL cells with values
- Preserve row/column relationships
- Look for totals, subtotals, and formulas
- Capture sheet names and tabs

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
    "balance_sheet": {
      "assets": {
        "current_assets": {
          "cash": number,
          "accounts_receivable": number,
          "inventory": number,
          "prepaid_expenses": number,
          "other_current": number,
          "total_current_assets": number
        },
        "fixed_assets": {
          "property_plant_equipment": number,
          "accumulated_depreciation": number,
          "net_fixed_assets": number
        },
        "other_assets": {
          "intangibles": number,
          "investments": number,
          "other": number
        },
        "total_assets": number
      },
      "liabilities": {
        "current_liabilities": {
          "accounts_payable": number,
          "accrued_expenses": number,
          "current_portion_ltd": number,
          "other_current": number,
          "total_current_liabilities": number
        },
        "long_term_debt": number,
        "other_liabilities": number,
        "total_liabilities": number
      },
      "equity": {
        "paid_in_capital": number,
        "retained_earnings": number,
        "total_equity": number
      }
    },
    "income_statement": {
      "revenue": {
        "gross_sales": number,
        "returns_allowances": number,
        "net_sales": number
      },
      "cost_of_goods_sold": number,
      "gross_profit": number,
      "operating_expenses": {
        "salaries_wages": number,
        "rent": number,
        "utilities": number,
        "depreciation": number,
        "other": number,
        "total_operating_expenses": number
      },
      "operating_income": number,
      "other_income_expenses": number,
      "net_income": number
    },
    "personal_financial_statement": {
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
            print(f"\n🚀 Making API call to {self.model}...")
            api_start = time.time()
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0,
                messages=[{"role": "user", "content": content}]
            )
            
            api_time = time.time() - api_start
            print(f"✅ API response received in {api_time:.2f} seconds")
            
            # Track token usage if available
            if hasattr(response, 'usage'):
                print(f"\n📊 TOKEN USAGE REPORT:")
                print(f"  • Input tokens: {response.usage.input_tokens:,}")
                print(f"  • Output tokens: {response.usage.output_tokens:,}")
                total = response.usage.input_tokens + response.usage.output_tokens
                print(f"  • Total tokens: {total:,}")
                print(f"  • Tokens per second: {total/api_time:.0f}")
                
                # Rate limit warnings
                if total > 20000:
                    print(f"\n  ⚠️  HIGH TOKEN USAGE WARNING:")
                    print(f"     At {total:,} tokens, approaching 30k/min limit")
                    print(f"     Consider: Fewer documents or smaller images")
            
            # Parse response
            raw_text = response.content[0].text.strip()
            print(f"\n📤 Response length: {len(raw_text)} characters")
            
            # Try to extract JSON from the response
            if "```json" in raw_text:
                # Extract content between ```json and ```
                start = raw_text.find("```json") + 7
                end = raw_text.find("```", start)
                if end > start:
                    raw_text = raw_text[start:end].strip()
            elif "```" in raw_text:
                # Extract content between ``` markers
                parts = raw_text.split("```")
                if len(parts) >= 2:
                    raw_text = parts[1].strip()
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:].strip()
            
            return json.loads(raw_text)
            
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON PARSING FAILED:")
            print(f"  Error: {e}")
            print(f"  Raw response preview: {raw_text[:500] if raw_text else 'Empty response'}")
            return {"_extraction_failed": True, "raw_text": raw_text, "error": f"JSON parse error: {str(e)}"}
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ API CALL FAILED:")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Message: {error_msg}")
            
            # Detailed error analysis
            if "2000 pixels" in error_msg or "2000px" in error_msg:
                print(f"\n  🗖️ IMAGE SIZE ERROR:")
                print(f"     Images exceed 2000px limit for multi-image requests")
                print(f"     Solution: Reduce DPI or resize images to max 1900px")
            elif "rate" in error_msg.lower() or "429" in error_msg:
                print(f"\n  🚫 RATE LIMIT ERROR:")
                print(f"     Hit API rate limit (30k tokens/minute)")
                print(f"     Solution: Process fewer documents or add delays")
            elif "413" in error_msg:
                print(f"\n  📦 PAYLOAD TOO LARGE:")
                print(f"     Request size exceeds limits")
                print(f"     Solution: Reduce number of images per request")
            elif "timeout" in error_msg.lower():
                print(f"\n  ⏱️ TIMEOUT ERROR:")
                print(f"     API call took too long")
                print(f"     Solution: Process fewer documents at once")
            
            return {"_extraction_failed": True, "error": error_msg, "error_type": type(e).__name__}
    
    async def _extract_with_files_api(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """
        Extract using Files API with batching and rate limit protection.
        
        Features:
        - Processes documents in small batches (1-2 at a time)
        - Adds delays between API calls
        - Uses document blocks for PDFs
        - Merges results from multiple batches
        """
        
        # Configuration for batching
        MAX_DOCS_PER_BATCH = 1  # Process max 1 document at a time (safer for rate limits)
        DELAY_BETWEEN_BATCHES = 10  # Seconds to wait between API calls (longer delay)
        
        # Split files into smaller batches
        file_paths = [Path(f) for f in file_paths]
        batches = []
        for i in range(0, len(file_paths), MAX_DOCS_PER_BATCH):
            batches.append(file_paths[i:i + MAX_DOCS_PER_BATCH])
        
        print(f"  📦 Processing {len(file_paths)} files in {len(batches)} batches")
        
        # Process each batch and collect results
        all_results = []
        
        for batch_idx, batch_files in enumerate(batches, 1):
            print(f"\n  🔄 Batch {batch_idx}/{len(batches)} ({len(batch_files)} files):")
            for f in batch_files:
                print(f"    • {f.name}")
            
            # Process this batch
            batch_result = await self._process_files_batch(batch_files)
            
            if batch_result.get("_extraction_failed"):
                print(f"    ❌ Batch {batch_idx} failed: {batch_result.get('error', 'Unknown')[:100]}")
                # Continue with other batches even if one fails
            else:
                print(f"    ✅ Batch {batch_idx} extracted successfully")
                all_results.append(batch_result)
            
            # Wait between batches to avoid rate limits (except for last batch)
            if batch_idx < len(batches):
                print(f"    ⏳ Waiting {DELAY_BETWEEN_BATCHES}s before next batch...")
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)
        
        # Merge results from all successful batches
        if not all_results:
            return {"_extraction_failed": True, "error": "All batches failed"}
        
        merged_result = self._merge_batch_results(all_results)
        
        # Add metadata about the batching process
        merged_result['_files_api_metadata'] = {
            'total_batches': len(batches),
            'successful_batches': len(all_results),
            'files_processed': len(file_paths),
            'cache_stats': self.files_client.get_cache_stats()
        }
        
        return merged_result
    
    async def _process_files_batch(self, batch_files: List[Path]) -> Dict[str, Any]:
        """Process a single batch of files using Files API."""
        
        # Upload PDFs and prepare content blocks
        file_ids = []
        pdf_file_ids = []
        
        for file_path in batch_files:
            # Only upload PDFs directly - they can be used as document blocks
            if file_path.suffix.lower() == '.pdf':
                file_id = self.files_client.upload_file(file_path)
                if file_id:
                    file_ids.append({
                        'file_id': file_id,
                        'name': file_path.name,
                        'is_pdf': True,
                        'original_path': file_path
                    })
                    pdf_file_ids.append(file_id)
        
        # Build content blocks
        content = []
        
        # Add text prompt
        content.append({
            "type": "text",
            "text": self._get_extraction_prompt()
        })
        
        # Add PDF document blocks
        for file_info in file_ids:
            if file_info['is_pdf']:
                content.append({
                    "type": "document",
                    "source": {
                        "type": "file",
                        "file_id": file_info['file_id']
                    },
                    "title": file_info['name']
                })
        
        # Process non-PDF files to images
        non_pdf_files = [f for f in batch_files if f.suffix.lower() != '.pdf']
        for file_path in non_pdf_files:
            processed = self.preprocessor.preprocess_any_document(file_path)
            
            # Upload each image and add as image block
            for img in processed.images:
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    img.save(tmp.name, 'PNG')
                    img_file_id = self.files_client.upload_file(Path(tmp.name))
                    os.unlink(tmp.name)
                    
                    if img_file_id:
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "file",
                                "file_id": img_file_id
                            }
                        })
        
        # Make API call
        try:
            print(f"\n🚀 Making Files API call...")
            print(f"  • Content blocks: {len(content)}")
            print(f"  • PDF documents: {len([c for c in content if c.get('type') == 'document'])}")
            print(f"  • Images: {len([c for c in content if c.get('type') == 'image'])}")
            
            api_start = time.time()
            extra_headers = {"anthropic-beta": "files-api-2025-04-14"}
            
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0,
                messages=[{"role": "user", "content": content}],
                extra_headers=extra_headers
            )
            
            api_time = time.time() - api_start
            print(f"✅ Files API response in {api_time:.2f}s")
            
            # Track token usage if available
            if hasattr(response, 'usage'):
                print(f"\n📊 FILES API TOKEN USAGE:")
                print(f"  • Input tokens: {response.usage.input_tokens:,}")
                print(f"  • Output tokens: {response.usage.output_tokens:,}")
                total = response.usage.input_tokens + response.usage.output_tokens
                print(f"  • Total tokens: {total:,}")
                
                # Files API token warning
                if total > 20000:
                    print(f"\n  🔴 HIGH TOKEN USAGE WITH FILES API:")
                    print(f"     {total:,} tokens - confirms Files API uses MORE tokens")
                    print(f"     Native PDF sends full text, not just reference!")
            
            # Parse response
            raw_text = response.content[0].text.strip()
            print(f"  • Response length: {len(raw_text)} characters")
            
            # Try to extract JSON from the response
            if "```json" in raw_text:
                # Extract content between ```json and ```
                start = raw_text.find("```json") + 7
                end = raw_text.find("```", start)
                if end > start:
                    raw_text = raw_text[start:end].strip()
            elif "```" in raw_text:
                # Extract content between ``` markers
                parts = raw_text.split("```")
                if len(parts) >= 2:
                    raw_text = parts[1].strip()
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:].strip()
            
            return json.loads(raw_text)
            
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON PARSING FAILED (Files API):")
            print(f"  Error: {e}")
            print(f"  Raw response preview: {raw_text[:500] if raw_text else 'Empty response'}")
            return {"_extraction_failed": True, "raw_text": raw_text, "error": f"JSON parse error: {str(e)}"}
        except Exception as e:
            error_msg = str(e)
            print(f"\n❌ FILES API CALL FAILED:")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Message: {error_msg}")
            
            # Files API specific error analysis
            if "413" in error_msg or "too large" in error_msg.lower():
                print(f"\n  📦 PAYLOAD TOO LARGE (Files API):")
                print(f"     PDF sent as full text block exceeded limits")
                print(f"     This confirms Files API sends MORE data than images!")
            elif "rate" in error_msg.lower() or "429" in error_msg:
                print(f"\n  🚫 RATE LIMIT (Files API):")
                print(f"     Hit 30k tokens/minute limit")
                print(f"     Files API paradox: Uses MORE tokens than image method")
            
            return {"_extraction_failed": True, "error": error_msg, "error_type": type(e).__name__}
    
    def _merge_batch_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple batches."""
        
        merged = {}
        
        for result in results:
            for key, value in result.items():
                if key.startswith('_'):  # Skip metadata keys
                    continue
                
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    # Deep merge dictionaries
                    merged[key] = self._deep_merge(merged[key], value)
                elif value and not merged[key]:
                    # Prefer non-empty values
                    merged[key] = value
        
        return merged
    
    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            elif value:  # Prefer non-empty values
                result[key] = value
        
        return result
    
    def _get_extraction_prompt(self) -> str:
        """
        Get the extraction prompt (extracted from _extract_from_images for reuse).
        SIMPLIFIED version to avoid token limits.
        """
        # Much shorter prompt to stay under token limits
        return """Extract loan application data from these documents.

Focus on:
1. Personal info: Name, SSN, DOB, contact details, ownership %
2. Business info: Company names, EIN, entity types, ownership structure
3. Financial data: Assets, liabilities, income, net worth
4. Tax info: AGI, taxable income, refunds

Return JSON with this structure:
{
  "personal": {
    "primary_applicant": {
      "name": {"first": "", "last": ""},
      "ssn": "",
      "ownership_percentage": number
    }
  },
  "business": {
    "primary_business": {
      "legal_name": "",
      "ein": "",
      "entity_type": "",
      "annual_revenue": number
    }
  },
  "financials": {
    "assets": {"total_assets": number},
    "liabilities": {"total_liabilities": number},
    "net_worth": number
  }
}

Be precise with numbers. Remove $ and commas. Return only valid JSON."""
    
