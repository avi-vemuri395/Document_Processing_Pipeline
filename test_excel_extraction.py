#!/usr/bin/env python3
"""
Test script for Excel debt schedule extraction using multi-modal LLM.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extraction_methods.multimodal_llm.providers.claude_extractor import ClaudeExtractor
from src.extraction_methods.multimodal_llm.core.schema_generator import PrismaSchemaGenerator


def print_section(title: str):
    """Print formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


async def extract_debt_schedule():
    """Extract debt schedule from Excel file."""
    
    print_section("Excel Debt Schedule Extraction Test")
    
    # Initialize components
    print("Initializing components...")
    try:
        extractor = ClaudeExtractor()
        schema_generator = PrismaSchemaGenerator()
        print("✅ Components initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Generate schema for debt schedule
    print("\nGenerating debt schedule schema...")
    debt_schema = schema_generator.generate_debt_schedule_schema()
    print(f"✅ Schema generated for debt schedule extraction")
    
    # Path to Excel file
    excel_path = Path("inputs/real/Dave Burlington - Application Packet/Business Debt Schedule/Debt Schedule.xlsx")
    
    if not excel_path.exists():
        print(f"❌ Excel file not found: {excel_path}")
        return
    
    print(f"\n📊 Processing Excel file: {excel_path.name}")
    print("Converting Excel to image and extracting data...")
    print("This may take 10-30 seconds...")
    
    # Perform extraction
    try:
        result = await extractor.extract_with_schema(
            document=excel_path,
            schema=debt_schema,
            document_type="debt_schedule"
        )
        
        if result.error:
            print(f"❌ Extraction failed: {result.error}")
            return
        
        print(f"✅ Extraction completed in {result.processing_time:.2f} seconds")
        
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Display results
    print_section("Extraction Results")
    
    print(f"Model Used: {result.model_used}")
    print(f"Overall Confidence: {result.overall_confidence:.2%}")
    print(f"Fields Extracted: {len(result.fields)}")
    print(f"Needs Review: {'Yes' if result.needs_review else 'No'}")
    
    # Parse debt items
    print_section("Debt Schedule Details")
    
    # Look for debts field
    debts_field = None
    total_debt_field = None
    
    for field in result.fields:
        if field.field_name == "debts":
            debts_field = field
        elif field.field_name == "totalDebt":
            total_debt_field = field
    
    if debts_field and isinstance(debts_field.value, list):
        print(f"Number of debts found: {len(debts_field.value)}")
        print("\nIndividual Debts:")
        print("-" * 60)
        
        total_balance = 0
        for i, debt in enumerate(debts_field.value, 1):
            if isinstance(debt, dict):
                # Extract values, handling both direct values and nested dicts with 'value' key
                creditor = debt.get('creditorName', 'Unknown')
                if isinstance(creditor, dict):
                    creditor = creditor.get('value', 'Unknown')
                    
                balance = debt.get('currentBalance', 0)
                if isinstance(balance, dict):
                    balance = balance.get('value', 0)
                    
                payment = debt.get('monthlyPayment', 0)
                if isinstance(payment, dict):
                    payment = payment.get('value', 0)
                    
                rate = debt.get('interestRate', 0)
                if isinstance(rate, dict):
                    rate = rate.get('value', 0)
                
                if balance:
                    total_balance += balance
                
                print(f"\n{i}. {creditor}")
                print(f"   Balance: ${balance:,.2f}")
                if payment:
                    print(f"   Monthly Payment: ${payment:,.2f}")
                if rate:
                    print(f"   Interest Rate: {rate:.2%}")
    else:
        print("No structured debt items found")
        print("Raw extraction:")
        for field in result.fields[:10]:  # Show first 10 fields
            print(f"  {field.field_name}: {field.value} (confidence: {field.confidence:.2%})")
    
    if total_debt_field:
        print(f"\n📊 Total Debt Extracted: ${total_debt_field.value:,.2f}")
    
    if debts_field and total_balance > 0:
        print(f"📊 Calculated Total: ${total_balance:,.2f}")
    
    # Save results with descriptive naming
    output_dir = Path("outputs/multimodal_llm/debt_schedule")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract meaningful name from path
    doc_name = excel_path.parent.parent.name.lower().replace(" ", "_").replace("-", "_") + "_debt_schedule"
    output_file = output_dir / f"{doc_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_data = {
        "document": str(excel_path),
        "timestamp": datetime.now().isoformat(),
        "model": result.model_used,
        "processing_time": result.processing_time,
        "overall_confidence": result.overall_confidence,
        "fields": {
            f.field_name: {
                "value": f.value,
                "confidence": f.confidence
            }
            for f in result.fields
        }
    }
    
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {output_file}")
    
    # Test the image conversion separately
    print_section("Excel to Image Conversion Test")
    
    try:
        # Just test if the Excel can be converted to image
        from src.extraction_methods.multimodal_llm.providers.claude_extractor import EXCEL_AVAILABLE
        
        if EXCEL_AVAILABLE:
            print("✅ Excel support is available")
            
            # Try to read the Excel file
            import pandas as pd
            df = pd.read_excel(excel_path, nrows=5)
            print(f"✅ Successfully read Excel file")
            print(f"   Columns: {', '.join(df.columns[:5])}")
            print(f"   Rows: {len(df)}")
        else:
            print("❌ Excel support not available")
            
    except Exception as e:
        print(f"❌ Excel reading error: {e}")


if __name__ == "__main__":
    asyncio.run(extract_debt_schedule())