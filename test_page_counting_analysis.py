#!/usr/bin/env python3
"""
Page counting analysis for all PDFs in the test directory.
Identifies which documents can be processed directly with DocAI.
"""

import PyPDF2
from pathlib import Path
import os

def count_pdf_pages(file_path):
    """Count pages in PDF using PyPDF2"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception as e:
        return f"Error: {e}"

def analyze_all_documents():
    """Analyze all documents in the Brigham Dallas directory"""
    
    test_dir = Path("inputs/real/Brigham_dallas")
    
    print("="*80)
    print("DOCUMENT PAGE ANALYSIS - ROUTING CLASSIFICATION")
    print("="*80)
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    # Get all PDF files
    pdf_files = list(test_dir.glob("*.pdf"))
    excel_files = list(test_dir.glob("*.xlsx"))
    
    print(f"📁 Directory: {test_dir}")
    print(f"📄 Found {len(pdf_files)} PDF files")
    print(f"📊 Found {len(excel_files)} Excel files")
    
    # Classification categories
    docai_sync_suitable = []  # ≤ 30 pages
    docai_batch_suitable = []  # > 30 pages but ≤ 200 pages  
    claude_only = []  # > 200 pages
    processing_errors = []
    
    print(f"\n{'='*80}")
    print("PDF PAGE ANALYSIS")
    print(f"{'='*80}")
    
    for pdf_file in sorted(pdf_files):
        file_size_mb = pdf_file.stat().st_size / 1024 / 1024
        page_count = count_pdf_pages(pdf_file)
        
        print(f"\n📄 {pdf_file.name}")
        print(f"  • Size: {file_size_mb:.2f} MB")
        print(f"  • Pages: {page_count}")
        
        if isinstance(page_count, str):  # Error occurred
            processing_errors.append((pdf_file.name, page_count, file_size_mb))
            print(f"  • Status: ❌ Page counting failed")
        elif page_count <= 30:
            docai_sync_suitable.append((pdf_file.name, page_count, file_size_mb))
            print(f"  • Status: ✅ DocAI Form Parser (sync)")
        elif page_count <= 200:
            docai_batch_suitable.append((pdf_file.name, page_count, file_size_mb))
            print(f"  • Status: 🔄 DocAI Batch Processor")
        else:
            claude_only.append((pdf_file.name, page_count, file_size_mb))
            print(f"  • Status: 🤖 Claude Vision only")
    
    # Summary report
    print(f"\n{'='*80}")
    print("ROUTING SUMMARY")  
    print(f"{'='*80}")
    
    print(f"\n✅ DocAI Form Parser (Sync) - ≤30 pages: {len(docai_sync_suitable)} files")
    for name, pages, size in docai_sync_suitable:
        print(f"  • {name}: {pages} pages, {size:.2f} MB")
    
    print(f"\n🔄 DocAI Batch Processor - 31-200 pages: {len(docai_batch_suitable)} files")
    for name, pages, size in docai_batch_suitable:
        print(f"  • {name}: {pages} pages, {size:.2f} MB")
    
    print(f"\n🤖 Claude Vision Only - >200 pages: {len(claude_only)} files")
    for name, pages, size in claude_only:
        print(f"  • {name}: {pages} pages, {size:.2f} MB")
    
    if processing_errors:
        print(f"\n❌ Processing Errors: {len(processing_errors)} files")
        for name, error, size in processing_errors:
            print(f"  • {name}: {error}")
    
    print(f"\n📊 Excel Files: {len(excel_files)} files")
    for excel_file in sorted(excel_files):
        file_size_mb = excel_file.stat().st_size / 1024 / 1024
        print(f"  • {excel_file.name}: {file_size_mb:.2f} MB")
    
    # Test recommendation
    print(f"\n{'='*80}")
    print("TEST RECOMMENDATIONS")
    print(f"{'='*80}")
    
    if docai_sync_suitable:
        print(f"\n✅ IMMEDIATE TEST: Run DocAI sync processing test")
        print(f"  • Files ready for testing: {len(docai_sync_suitable)}")
        print(f"  • These should route to DocAI Form Parser (not Claude Vision)")
        print(f"  • Test command: python3 test_docai_small_files.py")
    
    if docai_batch_suitable:
        print(f"\n🔄 BATCH TEST: Test batch processing (requires re-enabling)")
        print(f"  • Files needing batch processing: {len(docai_batch_suitable)}")
        print(f"  • These currently fall back to Claude Vision (expensive!)")
        print(f"  • Solution: Enable batch processing or add page-based routing")
    
    total_processable = len(docai_sync_suitable) + len(docai_batch_suitable)
    total_pdfs = len(pdf_files) - len(processing_errors)
    
    if total_pdfs > 0:
        docai_percentage = (total_processable / total_pdfs) * 100
        print(f"\n📈 DocAI Coverage: {docai_percentage:.1f}% ({total_processable}/{total_pdfs} files)")
        if docai_percentage < 80:
            print(f"  ⚠️ Low DocAI coverage - many files will use expensive Claude Vision")
        else:
            print(f"  ✅ Good DocAI coverage - most files can use DocAI")
    
    return {
        'docai_sync_suitable': docai_sync_suitable,
        'docai_batch_suitable': docai_batch_suitable, 
        'claude_only': claude_only,
        'processing_errors': processing_errors,
        'excel_files': [(f.name, f.stat().st_size / 1024 / 1024) for f in excel_files]
    }

if __name__ == "__main__":
    results = analyze_all_documents()
    
    print(f"\n{'='*80}")
    print("NEXT STEPS")
    print(f"{'='*80}")
    
    if results['docai_sync_suitable']:
        print(f"\n1. 🧪 TEST END-TO-END FLOW")
        print(f"   Run: python3 test_docai_small_files.py")
        print(f"   Expected: All {len(results['docai_sync_suitable'])} files should use DocAI (not Claude Vision)")
    
    if results['docai_batch_suitable']:
        print(f"\n2. 🔧 FIX BATCH ROUTING")
        print(f"   Problem: {len(results['docai_batch_suitable'])} files can't use DocAI due to page limits")
        print(f"   Solution: Add page-based routing OR enable chunking")
    
    print(f"\n3. ✅ VERIFY PRODUCTION READINESS")
    print(f"   All documents should route to appropriate processor (DocAI or Claude)")
    print(f"   No documents should fail due to routing issues")