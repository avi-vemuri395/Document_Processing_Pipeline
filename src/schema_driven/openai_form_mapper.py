"""
OpenAI Form Mapper - Schema-driven form mapping using structured outputs
"""
import json
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("❌ OpenAI library not installed. Run: pip install openai")


class OpenAIFormMapper:
    """Schema-driven form mapping using OpenAI structured outputs"""
    
    def __init__(self, schemas_path: Path = None):
        """Initialize with OpenAI client and form schemas"""
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library required. Install with: pip install openai")
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")
        
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Load form schemas
        schemas_path = schemas_path or Path("schemas/openai_form_schemas.json")
        self.schemas = self._load_form_schemas(schemas_path)
        
        print(f"✅ Initialized OpenAI Form Mapper with {len(self.schemas)} schemas")
    
    def _load_form_schemas(self, schemas_path: Path) -> Dict[str, Dict]:
        """Load OpenAI form schemas from file"""
        if not schemas_path.exists():
            raise FileNotFoundError(f"Schemas file not found: {schemas_path}")
        
        with open(schemas_path, 'r') as f:
            return json.load(f)
    
    async def map_to_form_schema(
        self,
        master_data: Dict[str, Any],
        form_schema_key: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Map master data to specific form using OpenAI structured outputs
        
        Args:
            master_data: Comprehensive extraction from Part 1
            form_schema_key: Key for target form schema (e.g., 'live_oak_application_v1')
            max_retries: Maximum retry attempts for API failures
            
        Returns:
            Dictionary mapping form fields to extracted values
        """
        if form_schema_key not in self.schemas:
            raise ValueError(f"Unknown form schema: {form_schema_key}. Available: {list(self.schemas.keys())}")
        
        schema = self.schemas[form_schema_key]
        
        # Create semantic extraction prompt
        system_prompt = self._create_system_prompt(form_schema_key, schema)
        user_prompt = self._create_user_prompt(master_data)
        
        print(f"    🤖 Attempting OpenAI structured extraction for {form_schema_key}...")
        
        # Attempt extraction with retries
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o",  # Use latest model for best accuracy
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": f"{form_schema_key}_extraction",
                            "schema": schema,
                            "strict": True
                        }
                    },
                    temperature=0.1  # Low temperature for consistency
                )
                
                extracted_data = json.loads(response.choices[0].message.content)
                
                # Validate and clean extracted data
                cleaned_data = self._validate_and_clean(extracted_data, schema)
                
                print(f"    ✅ OpenAI extraction successful: {len(cleaned_data)} fields mapped")
                return cleaned_data
                
            except Exception as e:
                print(f"    ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise Exception(f"OpenAI extraction failed after {max_retries} attempts: {e}")
                await asyncio.sleep(1)  # Brief delay before retry
    
    def _create_system_prompt(self, form_key: str, schema: Dict) -> str:
        """Create semantic system prompt for form extraction"""
        
        # Extract bank and form type from key
        bank = "Unknown Bank"
        form_type = "Unknown Form"
        
        if "live_oak" in form_key:
            bank = "Live Oak Bank"
        elif "huntington" in form_key:
            bank = "Huntington Bank" 
        elif "wells_fargo" in form_key:
            bank = "Wells Fargo"
        
        if "application" in form_key:
            form_type = "Loan Application"
        elif "pfs" in form_key:
            form_type = "Personal Financial Statement"
        elif "business" in form_key:
            form_type = "Business Application"
        
        return f"""You are an expert loan application form filling specialist working with {bank} {form_type} forms.

CRITICAL MAPPING RULES:
1. **Personal vs Business Data:**
   - Personal information (SSN, individual names, personal addresses) → Personal/Applicant fields
   - Business information (EIN, company names, business addresses) → Business/Company fields
   - NEVER mix personal and business data

2. **Field Type Accuracy:**
   - Email fields → Valid email addresses ONLY (never physical addresses)
   - Address fields → Physical addresses ONLY (never email addresses)  
   - Phone fields → Phone numbers ONLY
   - Date fields → Properly formatted dates
   - Currency fields → Dollar amounts with proper formatting

3. **Data Extraction Rules:**
   - Use EXACT values from master data - no inference or modification
   - If a field cannot be mapped confidently from master data, return null
   - Prefer structured data over raw text when available
   - For compound fields (e.g., "City, State, & Zip Code": "Tempe, AZ 85281"), parse into components:
     * City field gets "Tempe"
     * State field gets "AZ" 
     * Zip field gets "85281"

4. **Semantic Understanding:**
   - "Business Legal Name" = Official company/entity name (e.g., "Waxxpot Group Holdings LLC")
   - "Applicant Name" = Individual person's name (e.g., "Brigham Dallas")
   - "DBA Name" = "Doing Business As" name if different from legal name
   - Revenue/Income fields = Business financial performance
   - Assets/Liabilities = Personal or business financial position

5. **Quality Standards:**
   - Ensure all extracted data is relevant to the specific field
   - Maintain consistent formatting within field types
   - Validate that dates, SSNs, EINs follow proper patterns
   - Return null for fields that cannot be accurately determined

Form Context: {schema.get('description', f'{bank} {form_type}')}
Output: Fill only the fields you can accurately determine from the master data."""

    def _create_user_prompt(self, master_data: Dict[str, Any]) -> str:
        """Create user prompt with master data"""
        # Limit the data size to avoid token limits
        master_str = json.dumps(master_data, indent=2)
        if len(master_str) > 8000:  # Reasonable token limit
            # Truncate but preserve structure
            master_str = master_str[:8000] + "..."
            
        return f"""Master Data for Form Extraction:

{master_str}

Based on the master data above, extract and map the appropriate values to the form fields defined in the schema. 

Remember:
- Only use data that directly corresponds to each field's semantic meaning
- Return null for fields where you cannot find appropriate data
- Ensure field types match their intended use (email vs address, personal vs business, etc.)
- Parse compound data appropriately (addresses, dates, etc.)
- Use the most specific and accurate data available from the structured master data"""

    def _validate_and_clean(self, extracted_data: Dict, schema: Dict) -> Dict[str, Any]:
        """Validate and clean extracted data against schema"""
        cleaned_data = {}
        
        for field_name, value in extracted_data.items():
            # Skip null/empty values
            if value is None or value == "" or value == []:
                continue
            
            # Basic validation based on field name patterns
            if self._is_valid_field_value(field_name, value):
                cleaned_data[field_name] = value
            else:
                print(f"      ⚠️ Filtered invalid value for {field_name}: {value}")
        
        return cleaned_data
    
    def _is_valid_field_value(self, field_name: str, value: Any) -> bool:
        """Basic validation of field values"""
        if not isinstance(value, str) or not value.strip():
            return False
        
        lower_name = field_name.lower()
        
        # Email validation
        if "email" in lower_name:
            return "@" in value and "." in value and len(value.split("@")) == 2
        
        # Address validation (should not be an email)
        if "address" in lower_name and "email" not in lower_name:
            return "@" not in value
        
        # Basic length validation
        if len(value.strip()) < 2:
            return False
        
        return True


# Test utility
async def test_form_mapping():
    """Test the form mapper with sample data"""
    try:
        mapper = OpenAIFormMapper()
        
        # Sample master data
        sample_data = {
            "personal_info": {
                "primary_applicant": {
                    "name": {"first": "John", "last": "Smith"},
                    "ssn": "XXX-XX-1234",
                    "email": "john.smith@email.com"
                }
            },
            "business_info": {
                "company_name": "Smith Enterprises LLC",
                "ein": "12-3456789",
                "business_address": "123 Business St, City, ST 12345"
            }
        }
        
        # Test mapping to first available schema
        available_schemas = list(mapper.schemas.keys())
        if available_schemas:
            test_schema = available_schemas[0]
            result = await mapper.map_to_form_schema(sample_data, test_schema)
            print(f"✅ Test mapping successful: {len(result)} fields mapped")
            return result
        else:
            print("❌ No schemas available for testing")
            return None
        
    except Exception as e:
        print(f"❌ Test mapping failed: {e}")
        return None


if __name__ == "__main__":
    asyncio.run(test_form_mapping())