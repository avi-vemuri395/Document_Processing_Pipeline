#!/usr/bin/env python3
"""
Test Document AI Batch Processing implementation
Tests the new batch processor with large documents that exceed sync limits
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_batch_processing():
    """Test batch processing with known large documents"""
    
    print("="*80)
    print("🧪 DOCUMENT AI BATCH PROCESSING TEST")
    print("="*80)
    
    # Test documents - focus on the large one that currently fails
    test_documents = [
        {
            "path": "inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf",
            "description": "Personal Tax Return (4.9MB, 138 pages)",
            "expected_sync_result": "Would fail Form Parser (>1.5MB limit)",
            "expected_batch_result": "Should succeed with batch processing"
        },
        {
            "path": "inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf", 
            "description": "Personal Financial Statement (500KB, 3 pages)",
            "expected_sync_result": "Would succeed with sync Form Parser",
            "expected_batch_result": "Should not use batch (below 2MB threshold)"
        },
        {
            "path": "inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf",
            "description": "Business Tax Return (219KB, 31 pages)",  
            "expected_sync_result": "Would fail Form Parser (>15 pages)",
            "expected_batch_result": "Should not use batch (below 2MB threshold)"
        }
    ]
    
    # Create output directory
    output_dir = Path("outputs/batch_processing_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📁 Output directory: {output_dir}")
    print(f"📄 Testing {len(test_documents)} documents:")
    for doc in test_documents:
        file_path = Path(doc['path'])
        if file_path.exists():
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  • {file_path.name} ({file_size_mb:.2f}MB) - {doc['description']}")
        else:
            print(f"  ❌ {file_path.name} - FILE NOT FOUND")
    
    try:
        # Import and test batch processor directly
        print(f"\n🔧 DIRECT BATCH PROCESSOR TEST")
        print("="*50)
        
        from src.extraction_methods.docai_batch_processor import BatchDocumentProcessor
        from src.config.docai_config import is_batch_processor_configured, get_batch_config
        
        # Check configuration
        print(f"\n🔍 Configuration Check:")
        is_configured = is_batch_processor_configured()
        print(f"  • Batch processor configured: {is_configured}")
        
        if is_configured:
            batch_config = get_batch_config()
            print(f"  • Batch enabled: {batch_config['enabled']}")
            print(f"  • Threshold: {batch_config['threshold_mb']} MB")
            print(f"  • Timeout: {batch_config['timeout_minutes']} minutes")
        
        if not is_configured:
            print("❌ Batch processor not configured - check .env file")
            return
        
        # Initialize batch processor
        print(f"\n🤖 Initializing Batch Processor...")
        batch_processor = BatchDocumentProcessor()
        
        if not batch_processor.client:
            print("❌ Batch processor client not initialized")
            return
        
        print("✅ Batch processor initialized successfully")
        
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
            print(f"Expected sync: {doc_info['expected_sync_result']}")
            print(f"Expected batch: {doc_info['expected_batch_result']}")
            
            # Calculate file size and determine expected behavior
            file_size_mb = doc_path.stat().st_size / (1024 * 1024)
            print(f"Actual size: {file_size_mb:.2f} MB")
            
            should_use_batch = file_size_mb >= 2.0
            print(f"Should use batch: {should_use_batch}")
            
            # Test batch processing
            print(f"\n🔄 Testing batch processing...")
            start_time = time.time()
            
            try:
                result = await batch_processor.process_large_document(
                    doc_path, 
                    threshold_mb=2.0
                )
                processing_time = time.time() - start_time
                
                print(f"⏱️  Processing time: {processing_time:.2f} seconds")
                
                if result.get("success"):
                    print(f"✅ BATCH PROCESSING SUCCESS!")
                    
                    # Print key metrics
                    pages_processed = result.get("pages", 0)
                    form_fields_count = len(result.get("form_fields", {}))
                    tables_count = len(result.get("tables", []))
                    entities_count = len(result.get("entities", []))
                    confidence = result.get("confidence", 0)
                    
                    print(f"📊 EXTRACTION RESULTS:")
                    print(f"  • Pages processed: {pages_processed}")
                    print(f"  • Form fields: {form_fields_count}")
                    print(f"  • Tables found: {tables_count}")
                    print(f"  • Entities found: {entities_count}")
                    print(f"  • Overall confidence: {confidence:.1%}")
                    
                    # Save complete result to file
                    output_file = output_dir / f"{doc_path.stem}_batch_result.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
                    
                    print(f"💾 Complete output saved to: {output_file}")
                    
                    # Add to summary
                    results_summary.append({
                        "document": doc_path.name,
                        "file_size_mb": file_size_mb,
                        "success": True,
                        "processing_time": processing_time,
                        "pages_processed": pages_processed,
                        "form_fields_count": form_fields_count,
                        "tables_count": tables_count,
                        "entities_count": entities_count,
                        "confidence": confidence,
                        "output_file": str(output_file),
                        "used_batch": should_use_batch,
                        "processor_type": result.get("metadata", {}).get("processor", "unknown")
                    })
                    
                else:
                    error_msg = result.get("error", "Unknown error")
                    print(f"❌ BATCH PROCESSING FAILED: {error_msg}")
                    
                    # Check if this is expected (file below threshold)
                    if "too small for batch processing" in error_msg and not should_use_batch:
                        print(f"✅ Expected result - file below {batch_config['threshold_mb']}MB threshold")
                        
                        results_summary.append({
                            "document": doc_path.name,
                            "file_size_mb": file_size_mb,
                            "success": False,
                            "error": error_msg,
                            "processing_time": processing_time,
                            "expected_failure": True,
                            "reason": "Below batch threshold"
                        })
                    else:
                        results_summary.append({
                            "document": doc_path.name,
                            "file_size_mb": file_size_mb,
                            "success": False,
                            "error": error_msg,
                            "processing_time": processing_time,
                            "expected_failure": False
                        })
                    
            except Exception as e:
                processing_time = time.time() - start_time
                print(f"❌ EXCEPTION: {e}")
                results_summary.append({
                    "document": doc_path.name,
                    "file_size_mb": file_size_mb,
                    "success": False,
                    "error": str(e),
                    "processing_time": processing_time,
                    "expected_failure": False
                })
        
        # Generate summary report
        print(f"\n{'='*80}")
        print("📋 BATCH PROCESSING TEST SUMMARY")
        print(f"{'='*80}")
        
        successful_batch = [r for r in results_summary if r.get("success") and r.get("used_batch")]
        expected_non_batch = [r for r in results_summary if not r.get("success") and r.get("expected_failure")]
        actual_failures = [r for r in results_summary if not r.get("success") and not r.get("expected_failure")]
        
        print(f"✅ Successful batch processing: {len(successful_batch)}")
        print(f"✅ Expected non-batch (below threshold): {len(expected_non_batch)}")
        print(f"❌ Actual failures: {len(actual_failures)}")
        
        if successful_batch:
            print(f"\n💰 BATCH PROCESSING ANALYSIS:")
            total_time = sum(r["processing_time"] for r in successful_batch)
            avg_time = total_time / len(successful_batch)
            avg_confidence = sum(r["confidence"] for r in successful_batch) / len(successful_batch)
            
            print(f"  • Average processing time: {avg_time:.2f} seconds")
            print(f"  • Average confidence: {avg_confidence:.1%}")
            
            print(f"\n📊 DETAILED BATCH RESULTS:")
            for result in successful_batch:
                print(f"  • {result['document']}:")
                print(f"    - Size: {result['file_size_mb']:.2f} MB")
                print(f"    - Pages: {result['pages_processed']}")
                print(f"    - Form fields: {result['form_fields_count']}")
                print(f"    - Tables: {result['tables_count']}")
                print(f"    - Entities: {result['entities_count']}")
                print(f"    - Confidence: {result['confidence']:.1%}")
                print(f"    - Time: {result['processing_time']:.2f}s")
                print(f"    - Output: {Path(result['output_file']).name}")
        
        if expected_non_batch:
            print(f"\n✅ EXPECTED NON-BATCH RESULTS:")
            for result in expected_non_batch:
                print(f"  • {result['document']}: {result['reason']} ({result['file_size_mb']:.2f} MB)")
        
        if actual_failures:
            print(f"\n❌ ACTUAL FAILURES:")
            for result in actual_failures:
                print(f"  • {result['document']}: {result['error']}")
        
        # Save summary
        summary_file = output_dir / "batch_test_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump({
                "test_timestamp": datetime.now().isoformat(),
                "total_documents": len(test_documents),
                "successful_batch": len(successful_batch),
                "expected_non_batch": len(expected_non_batch),
                "actual_failures": len(actual_failures),
                "results": results_summary,
                "batch_config": batch_config
            }, f, indent=2, default=str)
        
        print(f"\n💾 Summary saved to: {summary_file}")
        
        # Test integrated workflow
        print(f"\n🔧 INTEGRATED WORKFLOW TEST")
        print("="*50)
        print("Testing batch processing via BenchmarkExtractor...")
        
        try:
            from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
            
            # Initialize extractor
            extractor = BenchmarkExtractor()
            
            # Test with the large document
            large_doc = "inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf"
            if Path(large_doc).exists():
                print(f"\n🔄 Testing integrated workflow with: {Path(large_doc).name}")
                
                start_time = time.time()
                integrated_result = await extractor.extract_all([large_doc])
                integrated_time = time.time() - start_time
                
                print(f"⏱️  Integrated processing time: {integrated_time:.2f} seconds")
                
                if large_doc in integrated_result and not integrated_result[large_doc].get("error"):
                    print("✅ INTEGRATED WORKFLOW SUCCESS!")
                    
                    # Check which processor was used
                    metadata = integrated_result.get("_metadata", {})
                    processor_type = metadata.get("docai_processor_type", "unknown")
                    print(f"  • Processor used: {processor_type}")
                    
                    # Save integrated result
                    integrated_output = output_dir / f"brigham_ptr_integrated_result.json"
                    with open(integrated_output, 'w', encoding='utf-8') as f:
                        json.dump(integrated_result, f, indent=2, ensure_ascii=False, default=str)
                    
                    print(f"💾 Integrated result saved to: {integrated_output}")
                else:
                    print("❌ INTEGRATED WORKFLOW FAILED")
                    if large_doc in integrated_result:
                        print(f"   Error: {integrated_result[large_doc].get('error', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ Integrated workflow test failed: {e}")
        
        print(f"\n🎯 NEXT STEPS:")
        print(f"  1. Review batch processing results in: {output_dir}")
        print(f"  2. Compare batch vs sync quality for small documents")
        print(f"  3. Validate GCS bucket creation and cleanup")
        print(f"  4. Test with different document types and sizes")
        print(f"  5. Monitor processing costs and performance")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 This suggests DocAI batch integration may have issues")
        print("   Check that google-cloud-storage is installed:")
        print("   pip install google-cloud-storage")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_batch_processing())