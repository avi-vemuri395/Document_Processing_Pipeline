#!/usr/bin/env python3
"""
Test current document routing and processing flow
"""

import asyncio
from pathlib import Path
from src.extraction_methods.multimodal_llm.core.enhanced_document_classifier import EnhancedDocumentClassifier, DocumentType

async def test_document_classification():
    """Test how documents are currently classified"""
    
    classifier = EnhancedDocumentClassifier()
    
    # Test documents
    test_files = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf"),
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf"),
        Path("inputs/real/Brigham_dallas/Management_Bios.pdf"),
        Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf"),
        Path("inputs/real/Brigham_dallas/HSF_BS_as_of_20250630.xlsx"),
        Path("inputs/real/Brigham_dallas/HSF_AR_Aging_as_of_20250630.xlsx"),
    ]
    
    print("\n" + "="*70)
    print("DOCUMENT CLASSIFICATION TEST")
    print("="*70)
    
    for file_path in test_files:
        if file_path.exists():
            result = classifier.classify_document(document_path=file_path)
            
            print(f"\n📄 {file_path.name}")
            print(f"   Type: {result.primary_type.value}")
            print(f"   Confidence: {result.confidence:.1%}")
            
            # Determine if structured or narrative
            structured_types = [
                DocumentType.PERSONAL_FINANCIAL_STATEMENT,
                DocumentType.TAX_RETURN_1040,
                DocumentType.TAX_RETURN_1065,
                DocumentType.TAX_RETURN_1120S,
                DocumentType.BALANCE_SHEET,
                DocumentType.PROFIT_LOSS,
                DocumentType.AR_AGING,
                DocumentType.AP_AGING,
                DocumentType.DEBT_SCHEDULE,
            ]
            
            narrative_types = [
                DocumentType.MANAGEMENT_BIOS,
                DocumentType.BUSINESS_PLAN,
                DocumentType.ORG_CHART,
            ]
            
            if result.primary_type in structured_types:
                print(f"   → Would use: Form Parser")
            elif result.primary_type in narrative_types:
                print(f"   → Would use: Claude Vision")
            else:
                print(f"   → Would use: Form Parser (default)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(test_document_classification())