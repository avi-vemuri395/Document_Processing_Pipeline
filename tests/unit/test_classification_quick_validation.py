#!/usr/bin/env python3
"""
Quick validation of the focused test implementation.
Tests classification logic without API calls or file processing.
"""

import sys
from pathlib import Path

def validate_test_documents():
    """Validate test document configuration"""
    print("\n" + "="*50)
    print("VALIDATING TEST DOCUMENT CONFIGURATION")
    print("="*50)
    
    from test_classification_and_extraction_focused import TEST_DOCUMENTS
    
    base_path = Path("inputs/real/Brigham_dallas")
    
    print(f"\n📁 Base path: {base_path}")
    print(f"📄 Configured documents: {len(TEST_DOCUMENTS)}")
    
    available_docs = 0
    total_pages = 0
    
    for doc in TEST_DOCUMENTS:
        file_path = base_path / doc['file']
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        
        print(f"\n{status} {doc['file']}")
        print(f"   Type: {doc['loan_type'] or 'Heuristic only'}")
        print(f"   Expected: {doc['expected_category'].value} → {doc['expected_processor']}")
        print(f"   Pages: {doc['pages']}")
        print(f"   Exists: {exists}")
        
        if exists:
            available_docs += 1
            total_pages += doc['pages']
    
    print(f"\n📊 Summary:")
    print(f"   Available documents: {available_docs}/{len(TEST_DOCUMENTS)}")
    print(f"   Total pages to process: {total_pages}")
    print(f"   Estimated DocAI cost: ${(total_pages/1000)*30:.4f}")
    print(f"   Estimated Claude cost: ${total_pages*0.01:.4f}")
    
    return available_docs == len(TEST_DOCUMENTS)


def validate_imports():
    """Validate all imports work correctly"""
    print("\n" + "="*50)
    print("VALIDATING IMPORTS")
    print("="*50)
    
    try:
        from test_classification_and_extraction_focused import (
            TEST_DOCUMENTS, test_classification, test_extraction, BenchmarkExtractor
        )
        print("✅ Test module imports successful")
        
        from src.extraction_methods.multimodal_llm.utils.document_classifier import (
            DocumentClassifier, DocumentCategory
        )
        print("✅ Document classifier imports successful")
        
        from test_result_manager import TestResultManager
        print("✅ Test result manager imports successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def validate_classification_logic():
    """Validate classification logic without creating extractor"""
    print("\n" + "="*50)  
    print("VALIDATING CLASSIFICATION LOGIC")
    print("="*50)
    
    try:
        from src.extraction_methods.multimodal_llm.utils.document_classifier import (
            DocumentClassifier, DocumentCategory
        )
        from test_classification_and_extraction_focused import TEST_DOCUMENTS
        
        classifier = DocumentClassifier()
        print("✅ Classifier initialized")
        
        correct_mappings = 0
        
        for doc in TEST_DOCUMENTS:
            if doc['loan_type']:
                category, confidence = classifier.map_loan_application_type(doc['loan_type'])
                should_use_docai = classifier.should_use_docai(category, confidence)
                actual_processor = "DocAI" if should_use_docai else "Claude Vision"
                
                correct = (category == doc['expected_category'] and 
                          actual_processor == doc['expected_processor'])
                
                status = "✅" if correct else "❌"
                print(f"{status} {doc['file']}: {category.value} → {actual_processor}")
                
                if correct:
                    correct_mappings += 1
        
        print(f"\n📊 Classification accuracy: {correct_mappings}/{len([d for d in TEST_DOCUMENTS if d['loan_type']])}")
        return correct_mappings > 0
        
    except Exception as e:
        print(f"❌ Classification validation failed: {e}")
        return False


def main():
    """Run all validations"""
    print("\n" + "="*70)
    print("  FOCUSED TEST VALIDATION")
    print("="*70)
    print("Quick validation without API calls or file processing")
    
    # Run all validations
    validations = [
        ("Imports", validate_imports),
        ("Test Documents", validate_test_documents), 
        ("Classification Logic", validate_classification_logic)
    ]
    
    passed = 0
    for name, validator in validations:
        try:
            if validator():
                print(f"\n✅ {name} validation PASSED")
                passed += 1
            else:
                print(f"\n❌ {name} validation FAILED")
        except Exception as e:
            print(f"\n❌ {name} validation ERROR: {e}")
    
    print("\n" + "="*70)
    print("  VALIDATION SUMMARY")
    print("="*70)
    print(f"Passed: {passed}/{len(validations)}")
    
    if passed == len(validations):
        print("✅ All validations passed - focused test is ready to run!")
        print("\nTo run the full test:")
        print("  python3 test_classification_and_extraction_focused.py")
        return 0
    else:
        print("❌ Some validations failed - check issues above")
        return 1


if __name__ == "__main__":
    exit(main())