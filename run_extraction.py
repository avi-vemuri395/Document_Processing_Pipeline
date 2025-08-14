#!/usr/bin/env python3
"""
Main extraction runner for document processing pipeline.

Uses enhanced AI-powered extraction pipeline for processing loan documents.
Generates both JSON data files and markdown summary reports.
"""

import json
import asyncio
import argparse
import os
from pathlib import Path
from datetime import datetime
import sys

from src.extractors.enhanced_extraction_pipeline import (
    EnhancedExtractionPipeline,
    EnhancedPipelineConfig,
    ExtractionMethod
)

def create_results_directory(doc_type: str = "mixed"):
    """Create results directory with proper structure.
    
    Args:
        doc_type: Type of documents being processed (pfs, debt_schedule, mixed, etc.)
    
    Returns:
        Path: Path to newly created results directory.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Use multimodal_llm output structure
    if doc_type in ["pfs", "debt_schedule", "sba_forms", "tax_returns"]:
        results_dir = Path(f"outputs/multimodal_llm/{doc_type}")
    else:
        results_dir = Path("outputs/multimodal_llm/mixed")
    
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


async def process_with_enhanced_pipeline(input_paths: list, extraction_method: ExtractionMethod = ExtractionMethod.HYBRID):
    """Process documents using the enhanced extraction pipeline.
    
    Args:
        input_paths: List of document paths to process.
        extraction_method: Method to use (HYBRID, LLM, or NATIVE)
        
    Returns:
        tuple: (results_directory, pipeline_result)
    """
    print("🚀 Using Enhanced AI Extraction Pipeline")
    print("-"*40)
    
    # Determine document type based on input files
    doc_type = "mixed"
    for path in input_paths:
        path_str = str(path).lower()
        if "pfs" in path_str or "personal_financial" in path_str:
            doc_type = "pfs"
            break
        elif "debt" in path_str and "schedule" in path_str:
            doc_type = "debt_schedule"
            break
        elif "sba" in path_str:
            doc_type = "sba_forms"
            break
        elif "tax" in path_str or "return" in path_str:
            doc_type = "tax_returns"
            break
    
    # Create results directory
    results_dir = create_results_directory(doc_type)
    
    # Configure pipeline
    config = EnhancedPipelineConfig(
        extraction_method=extraction_method,
        prefer_native_excel=True,
        enable_cross_validation=True,
        save_intermediate_results=True,
        output_directory=results_dir
    )
    
    # Initialize pipeline
    pipeline = EnhancedExtractionPipeline(config)
    
    # Convert paths to Path objects
    document_paths = [Path(p) for p in input_paths]
    
    # Process as loan package
    result = await pipeline.process_loan_package(
        document_paths,
        application_id=f"EXTRACTION-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    
    # Display results
    print(f"\n📊 Pipeline Results:")
    print(f"  Total Processing Time: {result.total_processing_time:.2f} seconds")
    print(f"  Documents Processed: {len(result.documents_processed)}")
    
    if result.loan_application:
        app = result.loan_application
        print(f"\n💰 Loan Application Summary:")
        if app.primary_borrower and app.primary_borrower.first_name:
            print(f"  Borrower: {app.primary_borrower.first_name} {app.primary_borrower.last_name}")
        if app.financial_position.net_worth:
            print(f"  Net Worth: ${app.financial_position.net_worth:,.2f}")
        if app.risk_score is not None:
            print(f"  Risk Score: {app.risk_score}/100")
    
    if result.validation_result:
        print(f"\n✅ Validation Results:")
        print(f"  Status: {result.validation_result.overall_status}")
        print(f"  Confidence: {result.validation_result.confidence:.2%}")
    
    # Generate output filename based on document owner or type
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Try to determine document owner from paths
    doc_owner = "unknown"
    for path in input_paths:
        path_str = str(path).lower()
        if "brigham" in path_str:
            doc_owner = "brigham_dallas"
            break
        elif "dave" in path_str or "burlington" in path_str:
            doc_owner = "dave_burlington"
            break
    
    # Save JSON results with proper naming
    if result.loan_application and result.loan_application.primary_borrower:
        borrower = result.loan_application.primary_borrower
        if borrower.first_name and borrower.last_name:
            doc_owner = f"{borrower.first_name}_{borrower.last_name}".lower().replace(" ", "_")
    
    # Save extraction results
    json_file = results_dir / f"{doc_owner}_{doc_type}_{timestamp}.json"
    if result.loan_application:
        with open(json_file, 'w') as f:
            # Convert loan application to dict
            app_dict = {
                'application_id': result.loan_application.application_id,
                'timestamp': timestamp,
                'primary_borrower': {
                    'first_name': result.loan_application.primary_borrower.first_name if result.loan_application.primary_borrower else None,
                    'last_name': result.loan_application.primary_borrower.last_name if result.loan_application.primary_borrower else None,
                },
                'financial_position': {
                    'total_assets': float(result.loan_application.financial_position.total_assets) if result.loan_application.financial_position.total_assets else None,
                    'total_liabilities': float(result.loan_application.financial_position.total_liabilities) if result.loan_application.financial_position.total_liabilities else None,
                    'net_worth': float(result.loan_application.financial_position.net_worth) if result.loan_application.financial_position.net_worth else None,
                },
                'documents_processed': len(result.documents_processed),
                'average_confidence': sum(d.confidence_score for d in result.documents_processed) / len(result.documents_processed) if result.documents_processed else 0
            }
            json.dump(app_dict, f, indent=2)
        print(f"📄 JSON saved to: {json_file.name}")
    
    # Create summary report
    report_file = results_dir / f"{doc_owner}_{doc_type}_summary_{timestamp}.md"
    with open(report_file, 'w') as f:
        f.write("# Document Extraction Results\n\n")
        f.write(f"**Timestamp**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Processing Time**: {result.total_processing_time:.2f}s\n")
        f.write(f"**Method**: {extraction_method.value}\n\n")
        
        f.write("## Documents Processed\n\n")
        for doc in result.documents_processed:
            f.write(f"### {doc.file_path.name}\n")
            f.write(f"- Type: {doc.classification.primary_type.value}\n")
            f.write(f"- Method: {doc.extraction_method}\n")
            f.write(f"- Confidence: {doc.confidence_score:.2%}\n\n")
        
        if result.summary_statistics:
            f.write("## Statistics\n\n")
            for key, value in result.summary_statistics.items():
                if isinstance(value, float):
                    f.write(f"- {key}: {value:.2%}\n")
                else:
                    f.write(f"- {key}: {value}\n")
    
    print(f"\n📄 Report saved to: {report_file.name}")
    print(f"📁 All results saved to: {results_dir}")
    
    return results_dir, result


def main():
    """Main entry point for extraction pipeline.
    
    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Document Extraction Pipeline - AI-powered loan document processing"
    )
    
    # Add command-line arguments
    parser.add_argument(
        '--method',
        choices=['hybrid', 'llm', 'native'],
        default='hybrid',
        help='Extraction method: hybrid (default), llm-only, or native-excel'
    )
    
    parser.add_argument(
        '--documents',
        nargs='+',
        help='Specific documents to process (space-separated paths)'
    )
    
    parser.add_argument(
        '--directory',
        help='Process all documents in a directory'
    )
    
    parser.add_argument(
        '--brigham',
        action='store_true',
        help='Process Brigham Dallas loan package'
    )
    
    parser.add_argument(
        '--dave',
        action='store_true',
        help='Process Dave Burlington loan package'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all available documents'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("DOCUMENT EXTRACTION PIPELINE")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Method: {args.method.upper()}")
    print("="*60)
    
    # Map method string to enum
    method_map = {
        'hybrid': ExtractionMethod.HYBRID,
        'llm': ExtractionMethod.LLM,
        'native': ExtractionMethod.NATIVE
    }
    extraction_method = method_map[args.method]
    
    # Determine which documents to process
    documents = []
    
    if args.documents:
        documents = args.documents
    elif args.directory:
        documents = list(Path(args.directory).rglob("*.pdf"))
        documents.extend(list(Path(args.directory).rglob("*.xlsx")))
        documents.extend(list(Path(args.directory).rglob("*.xls")))
        documents = [str(d) for d in documents]
    elif args.brigham:
        # Brigham Dallas package
        documents = [
            "inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf",
            "inputs/real/Brigham_dallas/Brigham_Dallas_2024_PTR.pdf",
            "inputs/real/Brigham_dallas/Hello_Sugar_Franchise_LLC_2024.pdf",
            "inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf",
            "inputs/real/Brigham_dallas/HSF_BS_as_of_20250630.xlsx",
            "inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx",
        ]
    elif args.dave:
        # Dave Burlington package
        documents = [
            "inputs/real/Dave Burlington - Application Packet/Personal Financial Statement/Dave Burlington Personal Financial Statement.pdf",
            "inputs/real/Dave Burlington - Application Packet/Personal Tax Returns (3 years)/David and Janette Burlington 2024 Tax Return.pdf",
            "inputs/real/Dave Burlington - Application Packet/Business Tax Returns (3 years)/Beyond Bassin LLC 2024 Tax Return.pdf",
            "inputs/real/Dave Burlington - Application Packet/Business Debt Schedule/Debt Schedule.xlsx",
        ]
    elif args.all:
        # All documents
        documents = list(Path("inputs/real").rglob("*.pdf"))
        documents.extend(list(Path("inputs/real").rglob("*.xlsx")))
        documents.extend(list(Path("inputs/real").rglob("*.xls")))
        documents = [str(d) for d in documents]
    else:
        # Default documents
        documents = [
            "inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf",
            "inputs/real/Dave Burlington - Application Packet/Personal Financial Statement/Dave Burlington Personal Financial Statement.pdf",
        ]
    
    # Filter to existing files only
    existing_docs = [d for d in documents if Path(d).exists()]
    
    print(f"\n📋 Documents to process: {len(existing_docs)}")
    for doc in existing_docs:
        print(f"  - {Path(doc).name}")
    
    if not existing_docs:
        print("\n❌ No documents found to process")
        return 1
    
    # Check for API key if using LLM
    if extraction_method in [ExtractionMethod.LLM, ExtractionMethod.HYBRID]:
        if not os.getenv("ANTHROPIC_API_KEY"):
            print("\n⚠️ ANTHROPIC_API_KEY not found in environment")
            print("Add to .env file to enable LLM extraction")
            print("Continuing with available methods...")
    
    # Run enhanced pipeline
    results_dir, result = asyncio.run(process_with_enhanced_pipeline(existing_docs, extraction_method))
    
    print(f"\n✨ Extraction complete! Results saved to:")
    print(f"   {results_dir}")
    
    # Print final summary
    if result.documents_processed:
        successful = len([d for d in result.documents_processed if d.confidence_score > 0.5])
        print(f"\n📈 Final Results:")
        print(f"  - Processed: {len(result.documents_processed)} documents")
        print(f"  - Successful: {successful}/{len(result.documents_processed)}")
        print(f"  - Success Rate: {successful/len(result.documents_processed)*100:.1f}%")
        
        return 0 if successful > 0 else 1
    
    return 1


if __name__ == "__main__":
    sys.exit(main())