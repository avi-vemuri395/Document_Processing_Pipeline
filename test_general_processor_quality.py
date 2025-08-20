#!/usr/bin/env python3
"""
Test General Processor (OCR) quality on 3 representative PDFs
Saves complete outputs for manual quality analysis
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_general_processor_quality():
    """Test General Processor on 3 representative documents"""
    
    print("="*80)
    print("🔬 GENERAL PROCESSOR QUALITY ASSESSMENT")
    print("="*80)
    
    # Test documents - representative range
    test_documents = [
        {
            "path": "inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf",
            "description": "Personal Financial Statement (500K, structured form)",
            "expected_form_parser": "Would use Form Parser (optimal case)",
            "file_size": "500K"
        },
        {
            "path": "inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf", 
            "description": "Personal Tax Return (4.9M, large document)",
            "expected_form_parser": "Form Parser would reject (>1.5MB limit)",
            "file_size": "4.9M"
        },
        {
            "path": "inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf",
            "description": "Business Tax Return (219K, structured form)",
            "expected_form_parser": "Would use Form Parser",
            "file_size": "219K"
        }
    ]
    
    # Create output directory
    output_dir = Path("outputs/general_processor_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Output directory: {output_dir}")
    print(f"📄 Testing {len(test_documents)} documents:")
    for doc in test_documents:
        print(f"  • {Path(doc['path']).name} ({doc['file_size']}) - {doc['description']}")
    
    try:
        # Import General Processor directly
        from src.extraction_methods.docai_general_processor import GeneralProcessorExtractor
        from src.config.docai_config import is_general_processor_configured
        
        print(f"\n🔧 CONFIGURATION CHECK:")
        if not is_general_processor_configured():
            print("❌ General Processor not configured!")
            return
        print("✅ General Processor is configured")
        
        # Initialize General Processor
        print(f"\n🤖 Initializing General Processor...")
        processor = GeneralProcessorExtractor()
        
        if not processor.client:
            print("❌ General Processor client not initialized!")
            return
        print("✅ General Processor client ready")
        
        # Test each document
        results_summary = []
        
        for i, doc_info in enumerate(test_documents, 1):
            doc_path = Path(doc_info["path"])
            if not doc_path.exists():
                print(f"\n❌ Document not found: {doc_path}")
                continue
                
            print(f"\n{'='*60}")
            print(f"📄 TEST {i}/3: {doc_path.name}")
            print(f"{'='*60}")
            print(f"Description: {doc_info['description']}")
            print(f"File size: {doc_info['file_size']}")
            print(f"Form Parser expectation: {doc_info['expected_form_parser']}")
            
            # Calculate actual file size and estimated pages
            actual_size_mb = doc_path.stat().st_size / (1024 * 1024)
            estimated_pages = int(actual_size_mb * 10)  # Conservative estimate
            estimated_cost = (estimated_pages / 1000) * 1.50  # $1.50/1000 pages
            
            print(f"Actual size: {actual_size_mb:.2f} MB")
            print(f"Estimated pages: {estimated_pages}")
            print(f"Estimated cost: ${estimated_cost:.4f}")
            
            # Process with General Processor
            print(f"\n🔄 Processing with General Processor...")
            start_time = time.time()
            
            try:
                result = await processor.extract(doc_path)
                processing_time = time.time() - start_time
                
                print(f"⏱️  Processing time: {processing_time:.2f} seconds")
                
                if result.get("success"):
                    print(f"✅ SUCCESS!")
                    
                    # Print key metrics
                    text_length = len(result.get("text", ""))
                    entities_count = len(result.get("entities", []))
                    tables_count = len(result.get("tables", []))
                    form_fields_count = len(result.get("form_fields", {}))
                    pages_processed = result.get("pages", 0)
                    confidence = result.get("confidence", 0)
                    
                    print(f"📊 EXTRACTION RESULTS:")
                    print(f"  • Pages processed: {pages_processed}")
                    print(f"  • Text extracted: {text_length:,} characters")
                    print(f"  • Entities found: {entities_count}")
                    print(f"  • Tables found: {tables_count}")
                    print(f"  • Form fields: {form_fields_count}")
                    print(f"  • Overall confidence: {confidence:.1%}")
                    
                    # Save complete result to file
                    output_file = output_dir / f"{doc_path.stem}_general_processor_output.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
                    
                    print(f"💾 Complete output saved to: {output_file}")
                    
                    # Add to summary
                    results_summary.append({
                        "document": doc_path.name,
                        "success": True,
                        "processing_time": processing_time,
                        "pages_processed": pages_processed,
                        "text_length": text_length,
                        "entities_count": entities_count,
                        "tables_count": tables_count,
                        "form_fields_count": form_fields_count,
                        "confidence": confidence,
                        "estimated_cost": estimated_cost,
                        "cost_per_second": estimated_cost / processing_time if processing_time > 0 else 0,
                        "output_file": str(output_file)
                    })
                    
                else:
                    print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                    results_summary.append({
                        "document": doc_path.name,
                        "success": False,
                        "error": result.get('error', 'Unknown error'),
                        "processing_time": processing_time
                    })
                    
            except Exception as e:
                processing_time = time.time() - start_time
                print(f"❌ EXCEPTION: {e}")
                results_summary.append({
                    "document": doc_path.name,
                    "success": False,
                    "error": str(e),
                    "processing_time": processing_time
                })
        
        # Generate summary report
        print(f"\n{'='*80}")
        print("📋 QUALITY ASSESSMENT SUMMARY")
        print(f"{'='*80}")
        
        successful_tests = [r for r in results_summary if r.get("success")]
        failed_tests = [r for r in results_summary if not r.get("success")]
        
        print(f"✅ Successful: {len(successful_tests)}/{len(results_summary)}")
        print(f"❌ Failed: {len(failed_tests)}/{len(results_summary)}")
        
        if successful_tests:
            total_cost = sum(r["estimated_cost"] for r in successful_tests)
            avg_confidence = sum(r["confidence"] for r in successful_tests) / len(successful_tests)
            avg_processing_time = sum(r["processing_time"] for r in successful_tests) / len(successful_tests)
            
            print(f"\n💰 COST ANALYSIS:")
            print(f"  • Total estimated cost: ${total_cost:.4f}")
            print(f"  • Average processing time: {avg_processing_time:.2f} seconds")
            print(f"  • Average confidence: {avg_confidence:.1%}")
            
            print(f"\n📊 DETAILED RESULTS:")
            for result in successful_tests:
                print(f"  • {result['document']}:")
                print(f"    - Pages: {result['pages_processed']}")
                print(f"    - Text: {result['text_length']:,} chars")
                print(f"    - Entities: {result['entities_count']}")
                print(f"    - Tables: {result['tables_count']}")
                print(f"    - Form fields: {result['form_fields_count']}")
                print(f"    - Confidence: {result['confidence']:.1%}")
                print(f"    - Cost: ${result['estimated_cost']:.4f}")
                print(f"    - Time: {result['processing_time']:.2f}s")
                print(f"    - Output: {Path(result['output_file']).name}")
        
        if failed_tests:
            print(f"\n❌ FAILED DOCUMENTS:")
            for result in failed_tests:
                print(f"  • {result['document']}: {result['error']}")
        
        # Save summary
        summary_file = output_dir / "test_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_timestamp": datetime.now().isoformat(),
                "total_documents": len(test_documents),
                "successful": len(successful_tests),
                "failed": len(failed_tests),
                "results": results_summary
            }, f, indent=2, default=str)
        
        print(f"\n💾 Summary saved to: {summary_file}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"  1. Review the output files in: {output_dir}")
        print(f"  2. Compare General Processor vs Form Parser quality")
        print(f"  3. Assess if cost savings justify any quality differences")
        print(f"  4. Make data-driven decision on implementation approach")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 This suggests DocAI integration may have issues")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_general_processor_quality())