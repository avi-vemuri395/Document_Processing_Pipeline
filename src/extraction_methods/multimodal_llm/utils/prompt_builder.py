"""
Builds optimized prompts for LLM extraction based on document type and schema.
Includes few-shot examples and extraction guidelines.
"""

import json
from typing import Dict, Any, List, Optional
from enum import Enum


class DocumentType(Enum):
    """Supported document types for extraction."""
    PERSONAL_FINANCIAL_STATEMENT = "personal_financial_statement"
    DEBT_SCHEDULE = "debt_schedule"
    BUSINESS_FINANCIAL = "business_financial"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    EQUIPMENT_QUOTE = "equipment_quote"


class PromptBuilder:
    """Builds schema-aware prompts for document extraction."""
    
    def __init__(self):
        """Initialize with extraction guidelines and examples."""
        self.extraction_guidelines = self._get_extraction_guidelines()
        self.few_shot_examples = self._get_few_shot_examples()
    
    def _get_extraction_guidelines(self) -> str:
        """Get general extraction guidelines."""
        return """
EXTRACTION GUIDELINES:
1. Extract ONLY information clearly visible in the document
2. Return null for fields that are not present or unclear
3. Extract monetary values exactly as shown (do NOT multiply by 100)
4. Preserve exact text for names and addresses
5. Use standard date format (YYYY-MM-DD) for dates
6. Include confidence score (0-1) for each extracted field
7. For calculated fields (like net worth), verify the math if possible
8. When multiple values could match a field, choose the most specific one
9. Pay attention to document sections and headers for context
10. Distinguish between similar fields (e.g., business phone vs personal phone)
"""
    
    def _get_few_shot_examples(self) -> Dict[DocumentType, List[Dict]]:
        """Get few-shot examples for different document types."""
        return {
            DocumentType.PERSONAL_FINANCIAL_STATEMENT: [
                {
                    "input": "Name: John Smith, Total Assets: $500,000",
                    "output": {
                        "firstName": {"value": "John", "confidence": 0.95},
                        "lastName": {"value": "Smith", "confidence": 0.95},
                        "totalAssets": {"value": 500000, "confidence": 0.90}
                    }
                }
            ],
            DocumentType.DEBT_SCHEDULE: [
                {
                    "input": "Wells Fargo Auto Loan, Balance: $25,000, Payment: $450/mo",
                    "output": {
                        "creditorName": {"value": "Wells Fargo", "confidence": 0.95},
                        "currentBalance": {"value": 25000, "confidence": 0.90},
                        "monthlyPayment": {"value": 450, "confidence": 0.90}
                    }
                }
            ]
        }
    
    def build_extraction_prompt(
        self,
        schema: Dict[str, Any],
        document_type: Optional[DocumentType] = None,
        custom_instructions: Optional[str] = None,
        include_examples: bool = True
    ) -> str:
        """
        Build extraction prompt for LLM.
        
        Args:
            schema: JSON Schema for extraction
            document_type: Type of document being processed
            custom_instructions: Additional custom instructions
            include_examples: Whether to include few-shot examples
            
        Returns:
            Complete prompt for LLM extraction
        """
        prompt_parts = []
        
        # Task description
        prompt_parts.append(
            "You are a financial document extraction specialist. "
            "Extract structured data from the provided document image according to the schema below."
        )
        
        # Add extraction guidelines
        prompt_parts.append(self.extraction_guidelines)
        
        # Add few-shot examples if requested
        if include_examples and document_type and document_type in self.few_shot_examples:
            prompt_parts.append("\nEXAMPLES:")
            for example in self.few_shot_examples[document_type]:
                prompt_parts.append(f"Input: {example['input']}")
                prompt_parts.append(f"Output: {json.dumps(example['output'], indent=2)}")
        
        # Add schema
        prompt_parts.append("\nEXTRACTION SCHEMA:")
        prompt_parts.append(json.dumps(schema, indent=2))
        
        # Add custom instructions if provided
        if custom_instructions:
            prompt_parts.append(f"\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}")
        
        # Add output format instructions
        prompt_parts.append("""
OUTPUT FORMAT:
Return a JSON object that matches the schema above. For each field, include:
- "value": The extracted value (or null if not found)
- "confidence": Confidence score between 0 and 1
- "raw_text": The original text where the value was found (optional)
- "page_number": Page number where value was found (optional)

IMPORTANT: 
- Extract monetary values as integers (remove $ and commas, keep the number as-is)
- Use null for missing fields rather than empty strings or 0
- Include confidence scores for ALL extracted fields
""")
        
        return "\n".join(prompt_parts)
    
    def build_classification_prompt(self) -> str:
        """Build prompt for document classification."""
        return """
Classify this document into one of the following categories:

1. PERSONAL_FINANCIAL_STATEMENT - Personal Financial Statement (PFS), SBA Form 413, or similar
2. DEBT_SCHEDULE - List of debts, liabilities, or loan schedule
3. BUSINESS_FINANCIAL - Business financial statements, P&L, balance sheet
4. TAX_RETURN - Personal or business tax returns
5. BANK_STATEMENT - Bank account statements
6. EQUIPMENT_QUOTE - Equipment purchase quotes or invoices
7. OTHER - Any other document type

Analyze the document structure, headers, and content to determine the type.
Return a JSON object with:
{
    "document_type": "<type>",
    "confidence": <0-1>,
    "reasoning": "<brief explanation>"
}
"""
    
    def build_validation_prompt(
        self,
        extracted_data: Dict[str, Any],
        document_type: DocumentType
    ) -> str:
        """
        Build prompt for validating extracted data.
        
        Args:
            extracted_data: Previously extracted data
            document_type: Type of document
            
        Returns:
            Validation prompt
        """
        return f"""
Please validate the following extracted data from a {document_type.value}:

{json.dumps(extracted_data, indent=2)}

Check for:
1. Mathematical consistency (e.g., assets - liabilities = net worth)
2. Reasonable values (e.g., phone numbers have correct format)
3. Field relationships (e.g., total assets should equal sum of individual assets)
4. Missing critical fields that should be present
5. Potential extraction errors

Return a JSON object with:
{{
    "is_valid": true/false,
    "issues": ["list of issues found"],
    "suggestions": ["list of suggested corrections"],
    "confidence": <0-1>
}}
"""
    
    def build_enhancement_prompt(
        self,
        partial_data: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> str:
        """
        Build prompt to enhance partial extraction.
        
        Args:
            partial_data: Partially extracted data
            schema: Full schema for extraction
            
        Returns:
            Enhancement prompt
        """
        # Find missing required fields
        required_fields = schema.get("required", [])
        extracted_fields = set(partial_data.keys())
        missing_fields = set(required_fields) - extracted_fields
        
        return f"""
The following data was partially extracted from the document:

{json.dumps(partial_data, indent=2)}

Please look for the following MISSING REQUIRED fields:
{json.dumps(list(missing_fields), indent=2)}

Also look for any other fields defined in this schema that might be present:
{json.dumps(schema, indent=2)}

Focus especially on:
- Fields that might be in different sections of the document
- Fields with alternative labels (e.g., "Name" vs "Applicant Name")
- Calculated fields that can be derived from other values
- Fields in tables or structured sections

Return any additional fields found in the same format as above.
"""
    
    def build_table_extraction_prompt(self) -> str:
        """Build specialized prompt for table extraction."""
        return """
Extract all tables from this document. For each table:

1. Identify the table type (debt schedule, asset list, income statement, etc.)
2. Extract headers and understand column meanings
3. Extract all rows with proper alignment to columns
4. Handle merged cells and subtotals correctly
5. Preserve numeric formatting and units

Return a JSON object with:
{
    "tables": [
        {
            "table_type": "<type>",
            "headers": ["col1", "col2", ...],
            "rows": [
                {"col1": value1, "col2": value2, ...},
                ...
            ],
            "confidence": <0-1>,
            "page_number": <page>
        }
    ]
}

IMPORTANT:
- Extract monetary values as integers (remove $ and commas)
- Preserve exact text for non-numeric fields
- Include confidence scores for complex extractions
"""