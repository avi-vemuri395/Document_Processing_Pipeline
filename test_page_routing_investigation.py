#!/usr/bin/env python3
"""
Investigation script for page routing and batch processing issues.
Tests why DocAI routing is failing for documents with >30 pages.
"""

import os
import sys
from pathlib import Path
import PyPDF2

def count_pdf_pages(file_path):
    """Count pages in PDF using PyPDF2"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return len(pdf_reader.pages)
    except Exception as e:
        return f"Error: {e}"

def analyze_test_document():
    """Analyze the specific document that's causing issues"""
    
    test_file = Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf")
    
    print("="*70)
    print("PAGE ROUTING INVESTIGATION")
    print("="*70)
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return
    
    # File size analysis
    file_size_bytes = test_file.stat().st_size
    file_size_mb = file_size_bytes / 1024 / 1024
    
    print(f"📄 File: {test_file.name}")
    print(f"📏 Size: {file_size_bytes:,} bytes ({file_size_mb:.2f} MB)")
    
    # Page count analysis
    page_count = count_pdf_pages(test_file)
    print(f"📖 Pages: {page_count}")
    
    print("\n" + "="*50)
    print("ROUTING ANALYSIS")
    print("="*50)
    
    # DocAI Form Parser limits
    form_parser_page_limit = 30  # imageless mode
    form_parser_page_limit_standard = 15  # standard mode
    
    # Batch processing thresholds
    batch_size_threshold_mb = 2.0
    batch_page_limit = 200
    
    print(f"📊 DocAI Form Parser Limits:")
    print(f"  • Standard mode: {form_parser_page_limit_standard} pages")
    print(f"  • Imageless mode: {form_parser_page_limit} pages")
    print(f"  • File size limit: No explicit limit (sync processing)")
    
    print(f"\n📊 Batch Processor Limits:")
    print(f"  • Page limit: {batch_page_limit} pages")
    print(f"  • File size threshold: {batch_size_threshold_mb} MB")
    
    print(f"\n🎯 Current Document Analysis:")
    print(f"  • Pages: {page_count} (>{form_parser_page_limit} = exceeds Form Parser)")
    print(f"  • Size: {file_size_mb:.2f} MB (<{batch_size_threshold_mb} = below batch threshold)")
    
    # Routing decisions
    print(f"\n🚦 Routing Decisions:")
    
    can_use_form_parser = isinstance(page_count, int) and page_count <= form_parser_page_limit
    meets_batch_threshold = file_size_mb >= batch_size_threshold_mb
    can_use_batch = isinstance(page_count, int) and page_count <= batch_page_limit
    
    print(f"  • Form Parser: {'✅ CAN USE' if can_use_form_parser else '❌ CANNOT USE'}")
    print(f"    - Page limit check: {page_count} <= {form_parser_page_limit} = {page_count <= form_parser_page_limit if isinstance(page_count, int) else 'Error'}")
    
    print(f"  • Batch Processor (current logic): {'✅ CAN USE' if meets_batch_threshold else '❌ CANNOT USE'}")
    print(f"    - Size threshold: {file_size_mb:.2f} >= {batch_size_threshold_mb} = {meets_batch_threshold}")
    
    print(f"  • Batch Processor (should be): {'✅ CAN USE' if can_use_batch else '❌ CANNOT USE'}")
    print(f"    - Page limit check: {page_count} <= {batch_page_limit} = {page_count <= batch_page_limit if isinstance(page_count, int) else 'Error'}")
    
    print(f"\n🔍 PROBLEM IDENTIFIED:")
    if not can_use_form_parser and not meets_batch_threshold:
        print(f"  ❌ Document cannot use Form Parser (too many pages)")
        print(f"  ❌ Document doesn't meet current batch threshold (too small)")
        print(f"  ➡️  System falls back to Claude Vision (expensive!)")
        
        print(f"\n💡 SOLUTION OPTIONS:")
        print(f"  1. Route to Batch Processor based on PAGE COUNT instead of just file size")
        print(f"  2. Lower batch size threshold to handle high-page, small-file docs")
        print(f"  3. Add hybrid routing: size OR page count triggers batch processing")

def test_docai_initialization():
    """Test if DocAI components are properly initialized"""
    
    print("\n" + "="*50)
    print("DOCAI INITIALIZATION TEST")
    print("="*50)
    
    try:
        from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
        
        # Initialize extractor to test DocAI setup
        extractor = BenchmarkExtractor()
        
        print(f"🤖 BenchmarkExtractor Status:")
        print(f"  • Form Parser: {'✅ Available' if extractor.form_parser else '❌ Not available'}")
        print(f"  • Batch Processor: {'✅ Available' if extractor.batch_processor else '❌ Not available'}")
        print(f"  • General Processor: {'✅ Available' if extractor.general_processor else '❌ Not available'}")
        
        # Check why batch processing might be disabled
        if extractor.batch_processor:
            print(f"\n📊 Batch Processor Details:")
            print(f"  • Processor name: {extractor.batch_processor.processor_name}")
            print(f"  • Temp bucket: {extractor.batch_processor.temp_bucket_name}")
        else:
            print(f"\n❌ Batch Processor Issues:")
            print(f"  • Check if Form Parser is configured")
            print(f"  • Check Google Cloud Storage permissions")
            print(f"  • Check if GCS client can be initialized")
            
    except Exception as e:
        print(f"❌ Failed to initialize BenchmarkExtractor: {e}")

def check_batch_processing_code():
    """Check if batch processing is enabled in the code"""
    
    print("\n" + "="*50)
    print("BATCH PROCESSING CODE STATUS")
    print("="*50)
    
    benchmark_file = Path("src/extraction_methods/multimodal_llm/providers/benchmark_extractor.py")
    
    if not benchmark_file.exists():
        print(f"❌ BenchmarkExtractor file not found")
        return
    
    with open(benchmark_file, 'r') as f:
        content = f.read()
    
    # Check if batch processing code is commented out
    batch_disabled_comment = "# TODO: Batch processing temporarily disabled"
    if batch_disabled_comment in content:
        print(f"❌ FOUND: Batch processing is DISABLED in code")
        print(f"   Comment: '{batch_disabled_comment}'")
        
        # Find the commented section
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if batch_disabled_comment in line:
                print(f"\n📍 Disabled code section starts at line {i+1}:")
                # Show next 10 lines of commented code
                for j in range(i, min(i+15, len(lines))):
                    prefix = "     " if lines[j].strip().startswith('#') else "  >> "
                    print(f"{prefix}{j+1:3}: {lines[j]}")
                break
    else:
        print(f"✅ Batch processing code appears to be active")

if __name__ == "__main__":
    analyze_test_document()
    test_docai_initialization()
    check_batch_processing_code()
    
    print(f"\n" + "="*70)
    print("INVESTIGATION COMPLETE")
    print("="*70)