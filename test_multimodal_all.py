#!/usr/bin/env python3
"""
Comprehensive test script for multi-modal LLM extraction.
Tests all document types and organizes outputs logically.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys
from typing import Dict, Any, Optional
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


def get_output_path(document_path: Path, extraction_method: str, document_type: str) -> Path:
    """
    Generate organized output path based on document and extraction method.
    
    Args:
        document_path: Path to source document
        extraction_method: Method used (e.g., "multimodal_llm", "regex_extraction")
        document_type: Type of document (e.g., "pfs", "debt_schedule", "sba_form")
    
    Returns:
        Path to output file
    """
    # Create base output directory
    output_dir = Path(f"outputs/{extraction_method}/{document_type}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate descriptive filename
    if document_path.parent.name != "real":
        # Include parent folder name for context
        doc_name = f"{document_path.parent.name}_{document_path.stem}"
    else:
        doc_name = document_path.stem
    
    # Clean up filename
    doc_name = doc_name.lower().replace(" ", "_").replace("-", "_")
    
    # Add timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    return output_dir / f"{doc_name}_{timestamp}.json"


async def test_document(
    document_path: Path,
    document_type: str,
    schema_type: str,
    extractor: ClaudeExtractor,
    schema_generator: PrismaSchemaGenerator
) -> Optional[Dict[str, Any]]:
    """
    Test extraction on a single document.
    
    Args:
        document_path: Path to document
        document_type: Type of document for schema selection
        schema_type: Schema to use ("pfs", "debt_schedule", "business", etc.)
        extractor: Claude extractor instance
        schema_generator: Schema generator instance
    
    Returns:
        Extraction results or None if failed
    """
    if not document_path.exists():
        print(f"❌ Document not found: {document_path}")
        return None
    
    print(f"\n📄 Processing: {document_path.name}")
    print(f"   Type: {document_type}")
    print(f"   Format: {document_path.suffix}")
    
    # Generate appropriate schema
    if schema_type == "pfs":
        schema = schema_generator.generate_extraction_schema(
            "PersonalFinancialStatementMetadata",
            include_optional=True
        )
    elif schema_type == "debt_schedule":
        schema = schema_generator.generate_debt_schedule_schema()
    elif schema_type == "business":
        schema = schema_generator.generate_business_schema()
    else:
        print(f"❌ Unknown schema type: {schema_type}")
        return None
    
    # Perform extraction
    try:
        result = await extractor.extract_with_schema(
            document=document_path,
            schema=schema,
            document_type=document_type
        )
        
        if result.error:
            print(f"❌ Extraction failed: {result.error}")
            return None
        
        print(f"✅ Extracted {len(result.fields)} fields")
        print(f"   Confidence: {result.overall_confidence:.2%}")
        print(f"   Time: {result.processing_time:.2f}s")
        
        # Prepare output data
        output_data = {
            "document": str(document_path),
            "document_type": document_type,
            "extraction_method": "multimodal_llm",
            "model": result.model_used,
            "timestamp": datetime.now().isoformat(),
            "processing_time": result.processing_time,
            "overall_confidence": result.overall_confidence,
            "needs_review": result.needs_review,
            "fields_extracted": len(result.fields),
            "fields": {
                f.field_name: {
                    "value": f.value,
                    "confidence": f.confidence
                }
                for f in result.fields
            }
        }
        
        # Save results
        output_path = get_output_path(document_path, "multimodal_llm", schema_type)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        
        print(f"   💾 Saved to: {output_path}")
        
        return output_data
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


async def run_all_tests():
    """Run tests on all available documents."""
    
    print_section("Multi-Modal LLM Extraction - Comprehensive Test")
    
    # Initialize components
    print("Initializing components...")
    try:
        extractor = ClaudeExtractor()
        schema_generator = PrismaSchemaGenerator()
        print("✅ Components initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    # Define test documents
    test_documents = [
        {
            "path": Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
            "type": "personal_financial_statement",
            "schema": "pfs",
            "description": "Brigham Dallas Personal Financial Statement"
        },
        {
            "path": Path("inputs/real/Dave Burlington - Application Packet/Business Debt Schedule/Debt Schedule.xlsx"),
            "type": "debt_schedule", 
            "schema": "debt_schedule",
            "description": "Dave Burlington Debt Schedule (Excel)"
        },
        {
            "path": Path("inputs/real/Dave Burlington - Application Packet/Dave Burlington 413.pdf"),
            "type": "sba_form_413",
            "schema": "pfs",  # SBA 413 contains PFS data
            "description": "Dave Burlington SBA Form 413"
        },
        {
            "path": Path("inputs/real/Brigham_dallas/Tax Returns - 2021 - Brigham, Dallas Allen.pdf"),
            "type": "tax_return",
            "schema": "pfs",  # Extract financial data from tax return
            "description": "Brigham Dallas 2021 Tax Return"
        }
    ]
    
    # Run tests
    results = []
    successful = 0
    failed = 0
    
    print_section("Processing Documents")
    
    for doc_info in test_documents:
        print(f"\n{'='*40}")
        print(f"Testing: {doc_info['description']}")
        print(f"{'='*40}")
        
        result = await test_document(
            document_path=doc_info["path"],
            document_type=doc_info["type"],
            schema_type=doc_info["schema"],
            extractor=extractor,
            schema_generator=schema_generator
        )
        
        if result:
            successful += 1
            results.append(result)
        else:
            failed += 1
    
    # Generate summary report
    print_section("Test Summary")
    
    print(f"Total documents tested: {len(test_documents)}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    
    if results:
        avg_confidence = sum(r["overall_confidence"] for r in results) / len(results)
        avg_time = sum(r["processing_time"] for r in results) / len(results)
        total_fields = sum(r["fields_extracted"] for r in results)
        
        print(f"\nAverage confidence: {avg_confidence:.2%}")
        print(f"Average processing time: {avg_time:.2f}s")
        print(f"Total fields extracted: {total_fields}")
        
        # Save summary
        summary_path = Path("outputs/multimodal_llm/test_summary.json")
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary = {
            "test_run": datetime.now().isoformat(),
            "documents_tested": len(test_documents),
            "successful": successful,
            "failed": failed,
            "average_confidence": avg_confidence,
            "average_processing_time": avg_time,
            "total_fields_extracted": total_fields,
            "results": results
        }
        
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n💾 Summary saved to: {summary_path}")
    
    # Show output structure
    print_section("Output Structure")
    print("outputs/")
    print("├── multimodal_llm/")
    print("│   ├── pfs/              # Personal Financial Statements")
    print("│   ├── debt_schedule/     # Debt Schedules")
    print("│   ├── sba_forms/         # SBA Forms")
    print("│   └── test_summary.json  # Overall test results")
    print("├── regex_extraction/")
    print("│   ├── pfs/              # Regex-based PFS extraction")
    print("│   └── mixed/            # Mixed document types")
    print("└── test_results/         # Comparison and analysis")


if __name__ == "__main__":
    import os
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY not found in .env file")
        print("\nPlease add your API key to the .env file:")
        print("ANTHROPIC_API_KEY=your-actual-key-here")
    else:
        asyncio.run(run_all_tests())