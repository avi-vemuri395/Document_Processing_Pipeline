#!/usr/bin/env python3
"""
Multi-Document Subset Test
Tests a balanced subset of different document types for quick validation.

Purpose: Fills the gap between comprehensive (too slow) and fast (too limited) tests.
Runtime: Target <30 seconds
Documents: 2 PDFs + 2 Excel files covering different data types
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.template_extraction.pipeline_orchestrator import PipelineOrchestrator
from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor


class TestResultManager:
    """Manages test results and output tracking."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path("outputs/test_tracking") / self.timestamp / test_name
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.metrics = {
            "test_name": test_name,
            "timestamp": self.timestamp,
            "start_time": datetime.now().isoformat(),
            "documents_processed": {},
            "extraction_methods": {},
            "field_counts": {},
            "processing_times": {},
            "fusion_metrics": {},
            "errors": []
        }
    
    def log_document_processing(
        self, 
        doc_path: Path, 
        result: Dict[str, Any], 
        processing_time: float
    ):
        """Log processing results for a document."""
        doc_name = doc_path.name
        
        # Count fields extracted
        field_count = self._count_fields_recursive(result)
        
        # Determine extraction method
        extraction_method = "unknown"
        if "extraction_method" in result:
            extraction_method = result["extraction_method"]
        elif "fusion_metadata" in result:
            extraction_method = "fusion"
        elif "docai_success" in result:
            extraction_method = "docai"
        elif result.get("error"):
            extraction_method = "error"
        else:
            extraction_method = "vision"
        
        # Store metrics
        self.metrics["documents_processed"][doc_name] = {
            "path": str(doc_path),
            "file_type": doc_path.suffix,
            "size_mb": doc_path.stat().st_size / (1024 * 1024),
            "processing_time": round(processing_time, 2),
            "extraction_method": extraction_method,
            "field_count": field_count
        }
        
        self.metrics["field_counts"][doc_name] = field_count
        self.metrics["processing_times"][doc_name] = round(processing_time, 2)
        
        # Track extraction methods
        if extraction_method not in self.metrics["extraction_methods"]:
            self.metrics["extraction_methods"][extraction_method] = 0
        self.metrics["extraction_methods"][extraction_method] += 1
        
        # Store fusion metrics if available
        if "fusion_metadata" in result:
            self.metrics["fusion_metrics"][doc_name] = {
                "strategy": result["fusion_metadata"].get("strategy"),
                "quality": result["fusion_metadata"].get("fusion_quality", 0),
                "has_docai": result["fusion_metadata"].get("has_docai"),
                "has_vision": result["fusion_metadata"].get("has_vision")
            }
    
    def _count_fields_recursive(self, data: Any, max_depth: int = 5, current_depth: int = 0) -> int:
        """Count all non-empty fields recursively."""
        if current_depth >= max_depth:
            return 0
        
        count = 0
        if isinstance(data, dict):
            for value in data.values():
                if value not in [None, "", [], {}]:
                    count += 1
                    if isinstance(value, (dict, list)):
                        count += self._count_fields_recursive(value, max_depth, current_depth + 1)
        elif isinstance(data, list):
            for item in data:
                if item not in [None, "", [], {}]:
                    count += 1
                    if isinstance(item, (dict, list)):
                        count += self._count_fields_recursive(item, max_depth, current_depth + 1)
        
        return count
    
    def save_results(self, extracted_data: Dict[str, Any], master_data: Optional[Dict] = None):
        """Save all test results and metrics."""
        self.metrics["end_time"] = datetime.now().isoformat()
        
        # Calculate totals
        self.metrics["totals"] = {
            "documents": len(self.metrics["documents_processed"]),
            "total_fields": sum(self.metrics["field_counts"].values()),
            "total_time": sum(self.metrics["processing_times"].values()),
            "average_fields_per_doc": sum(self.metrics["field_counts"].values()) / len(self.metrics["field_counts"]) if self.metrics["field_counts"] else 0,
            "fusion_used": len(self.metrics["fusion_metrics"]) > 0
        }
        
        # Save metrics
        metrics_path = self.base_dir / "metrics.json"
        with open(metrics_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
        
        # Save extracted data
        data_dir = self.base_dir / "extracted_data"
        data_dir.mkdir(exist_ok=True)
        
        for doc_name, doc_data in extracted_data.items():
            doc_path = data_dir / f"{Path(doc_name).stem}.json"
            with open(doc_path, "w") as f:
                json.dump(doc_data, f, indent=2)
        
        # Save master data if available
        if master_data:
            master_path = self.base_dir / "master_data.json"
            with open(master_path, "w") as f:
                json.dump(master_data, f, indent=2)
        
        # Generate summary report
        self._generate_summary_report()
        
        return self.base_dir
    
    def _generate_summary_report(self):
        """Generate a human-readable summary report."""
        report_path = self.base_dir / "summary.txt"
        
        with open(report_path, "w") as f:
            f.write("=" * 70 + "\n")
            f.write(f"TEST SUMMARY: {self.test_name}\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("DOCUMENTS PROCESSED:\n")
            for doc_name, info in self.metrics["documents_processed"].items():
                f.write(f"  • {doc_name}\n")
                f.write(f"    - Type: {info['file_type']}\n")
                f.write(f"    - Size: {info['size_mb']:.2f} MB\n")
                f.write(f"    - Fields: {info['field_count']}\n")
                f.write(f"    - Time: {info['processing_time']}s\n")
                f.write(f"    - Method: {info['extraction_method']}\n")
            
            f.write(f"\nTOTALS:\n")
            totals = self.metrics.get("totals", {})
            f.write(f"  • Documents: {totals.get('documents', 0)}\n")
            f.write(f"  • Total Fields: {totals.get('total_fields', 0)}\n")
            f.write(f"  • Total Time: {totals.get('total_time', 0):.2f}s\n")
            f.write(f"  • Avg Fields/Doc: {totals.get('average_fields_per_doc', 0):.1f}\n")
            
            if self.metrics["fusion_metrics"]:
                f.write(f"\nFUSION METRICS:\n")
                for doc_name, fusion_info in self.metrics["fusion_metrics"].items():
                    f.write(f"  • {doc_name}\n")
                    f.write(f"    - Strategy: {fusion_info['strategy']}\n")
                    f.write(f"    - Quality: {fusion_info['quality']:.3f}\n")
            
            f.write(f"\nEXTRACTION METHODS:\n")
            for method, count in self.metrics["extraction_methods"].items():
                f.write(f"  • {method}: {count} documents\n")


async def test_multi_document_subset():
    """
    Test with a balanced subset of different document types.
    
    This test provides good coverage while maintaining fast execution time.
    Perfect for development iterations and pre-commit checks.
    """
    
    print("\n" + "=" * 80)
    print("  MULTI-DOCUMENT SUBSET TEST")
    print("  Testing diverse document types in <30 seconds")
    print("=" * 80)
    
    # Initialize result manager
    result_manager = TestResultManager("multi_document_subset")
    
    # Define test documents (2 PDFs + 2 Excel)
    test_documents = [
        # PDF 1: Tax Return (large, complex)
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf"),
        # PDF 2: Personal Financial Statement (form-like)
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        # Excel 1: Profit & Loss Statement
        Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx"),
        # Excel 2: Balance Sheet
        Path("inputs/real/Brigham_dallas/HSF_BS_as_of_20250630.xlsx")
    ]
    
    # Check document availability
    available_docs = []
    print("\n📋 DOCUMENT SELECTION:")
    for doc in test_documents:
        if doc.exists():
            size_mb = doc.stat().st_size / (1024 * 1024)
            doc_type = "PDF" if doc.suffix == ".pdf" else "Excel"
            print(f"  ✅ {doc.name} ({doc_type}, {size_mb:.2f} MB)")
            available_docs.append(doc)
        else:
            print(f"  ❌ {doc.name} (NOT FOUND)")
    
    if len(available_docs) < 2:
        print("\n❌ Insufficient test documents available")
        return False
    
    print(f"\n📊 Testing with {len(available_docs)} documents")
    
    # Initialize extractor
    print("\n🔧 Initializing extraction pipeline...")
    extractor = BenchmarkExtractor()
    
    # Check fusion status
    fusion_enabled = False
    if hasattr(extractor, 'fusion_manager') and extractor.fusion_manager:
        fusion_enabled = True
        print("  ✅ Fusion enabled")
    else:
        print("  ℹ️ Fusion disabled")
    
    # Process documents individually for detailed metrics
    all_results = {}
    total_start = time.time()
    
    print("\n" + "-" * 60)
    print("  DOCUMENT PROCESSING")
    print("-" * 60)
    
    for i, doc_path in enumerate(available_docs, 1):
        print(f"\n📄 Document {i}/{len(available_docs)}: {doc_path.name}")
        
        doc_start = time.time()
        
        try:
            # Extract data
            result = await extractor.extract_all(doc_path)
            
            doc_time = time.time() - doc_start
            
            # Handle result format (may be nested)
            if isinstance(result, dict):
                # Get the actual document result
                doc_result = result.get(str(doc_path), result)
                
                # Log to result manager
                result_manager.log_document_processing(doc_path, doc_result, doc_time)
                
                # Store result
                all_results[str(doc_path)] = doc_result
                
                # Display summary
                field_count = result_manager._count_fields_recursive(doc_result)
                print(f"  ✅ Extracted {field_count} fields in {doc_time:.2f}s")
                
                # Show extraction method
                if "fusion_metadata" in doc_result:
                    fusion_meta = doc_result["fusion_metadata"]
                    print(f"  🔀 Fusion used: {fusion_meta.get('strategy')} (quality: {fusion_meta.get('fusion_quality', 0):.3f})")
                elif "extraction_method" in doc_result:
                    print(f"  📊 Method: {doc_result['extraction_method']}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            result_manager.metrics["errors"].append({
                "document": doc_path.name,
                "error": str(e)
            })
            doc_time = time.time() - doc_start
            all_results[str(doc_path)] = {"error": str(e)}
    
    total_time = time.time() - total_start
    
    # Now test with pipeline orchestrator for comprehensive processing
    print("\n" + "-" * 60)
    print("  PIPELINE ORCHESTRATION TEST")
    print("-" * 60)
    
    orchestrator = PipelineOrchestrator()
    app_id = f"subset_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"\n🔄 Processing through full pipeline...")
    print(f"  Application ID: {app_id}")
    
    pipeline_start = time.time()
    
    # Process with orchestrator (includes form mapping)
    pipeline_results = await orchestrator.process_application(
        application_id=app_id,
        documents=available_docs,
        target_banks=["live_oak"],  # Just one bank for speed
        generate_spreadsheets=False  # Skip for speed
    )
    
    pipeline_time = time.time() - pipeline_start
    
    # Get master data if created
    master_path = Path(f"outputs/applications/{app_id}/part1_document_processing/master_data.json")
    master_data = None
    if master_path.exists():
        with open(master_path) as f:
            master_data = json.load(f)
        print(f"  ✅ Master data created with {len(master_data)} categories")
    
    # Save all results
    output_dir = result_manager.save_results(all_results, master_data)
    
    # Display final summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    print(f"\n📊 METRICS:")
    print(f"  • Documents processed: {len(available_docs)}")
    print(f"  • Total extraction time: {total_time:.2f}s")
    print(f"  • Pipeline processing time: {pipeline_time:.2f}s")
    print(f"  • Average time per doc: {total_time/len(available_docs):.2f}s")
    
    totals = result_manager.metrics.get("totals", {})
    print(f"  • Total fields extracted: {totals.get('total_fields', 0)}")
    print(f"  • Average fields per doc: {totals.get('average_fields_per_doc', 0):.1f}")
    
    if fusion_enabled and result_manager.metrics["fusion_metrics"]:
        avg_quality = sum(m["quality"] for m in result_manager.metrics["fusion_metrics"].values()) / len(result_manager.metrics["fusion_metrics"])
        print(f"  • Fusion quality average: {avg_quality:.3f}")
    
    print(f"\n📁 Results saved to: {output_dir}")
    print(f"  • Metrics: {output_dir}/metrics.json")
    print(f"  • Summary: {output_dir}/summary.txt")
    print(f"  • Extracted data: {output_dir}/extracted_data/")
    
    # Performance check
    if total_time < 30:
        print(f"\n✅ TEST PASSED - Completed in {total_time:.2f}s (target: <30s)")
    else:
        print(f"\n⚠️ TEST SLOW - Completed in {total_time:.2f}s (target: <30s)")
    
    return True


async def compare_test_runs(run1_dir: Path, run2_dir: Path):
    """
    Compare results from two test runs.
    
    Useful for tracking improvements and regressions.
    """
    print("\n" + "=" * 60)
    print("  TEST RUN COMPARISON")
    print("=" * 60)
    
    # Load metrics from both runs
    metrics1_path = run1_dir / "metrics.json"
    metrics2_path = run2_dir / "metrics.json"
    
    if not metrics1_path.exists() or not metrics2_path.exists():
        print("❌ Cannot find metrics files for comparison")
        return
    
    with open(metrics1_path) as f:
        metrics1 = json.load(f)
    
    with open(metrics2_path) as f:
        metrics2 = json.load(f)
    
    print(f"\nRun 1: {metrics1['timestamp']}")
    print(f"Run 2: {metrics2['timestamp']}")
    
    # Compare field counts
    print("\n📊 FIELD EXTRACTION COMPARISON:")
    for doc_name in metrics1["field_counts"]:
        if doc_name in metrics2["field_counts"]:
            count1 = metrics1["field_counts"][doc_name]
            count2 = metrics2["field_counts"][doc_name]
            diff = count2 - count1
            symbol = "✅" if diff >= 0 else "❌"
            print(f"  {symbol} {doc_name}: {count1} → {count2} ({diff:+d})")
    
    # Compare processing times
    print("\n⏱️ PROCESSING TIME COMPARISON:")
    for doc_name in metrics1["processing_times"]:
        if doc_name in metrics2["processing_times"]:
            time1 = metrics1["processing_times"][doc_name]
            time2 = metrics2["processing_times"][doc_name]
            diff = time2 - time1
            symbol = "✅" if diff <= 0 else "⚠️"
            print(f"  {symbol} {doc_name}: {time1:.2f}s → {time2:.2f}s ({diff:+.2f}s)")
    
    # Compare totals
    print("\n📈 TOTALS:")
    totals1 = metrics1.get("totals", {})
    totals2 = metrics2.get("totals", {})
    
    total_fields1 = totals1.get("total_fields", 0)
    total_fields2 = totals2.get("total_fields", 0)
    field_improvement = ((total_fields2 - total_fields1) / total_fields1 * 100) if total_fields1 > 0 else 0
    
    print(f"  • Total fields: {total_fields1} → {total_fields2} ({field_improvement:+.1f}%)")
    
    total_time1 = totals1.get("total_time", 0)
    total_time2 = totals2.get("total_time", 0)
    time_improvement = ((total_time2 - total_time1) / total_time1 * 100) if total_time1 > 0 else 0
    
    print(f"  • Total time: {total_time1:.2f}s → {total_time2:.2f}s ({time_improvement:+.1f}%)")


async def main():
    """Main test runner."""
    import sys
    
    # Check for comparison mode
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        if len(sys.argv) != 4:
            print("Usage: python test_multi_document_subset.py compare <run1_dir> <run2_dir>")
            return
        
        run1 = Path(sys.argv[2])
        run2 = Path(sys.argv[3])
        await compare_test_runs(run1, run2)
    else:
        # Run the test
        success = await test_multi_document_subset()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())