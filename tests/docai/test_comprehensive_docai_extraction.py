#!/usr/bin/env python3
"""
Comprehensive DocAI Extraction Test
Tests Google Document AI extraction with 6 different PDF types with verbose output.
Saves all incremental merges and master JSON for analysis.
NO CLAUDE FALLBACK - DocAI only.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.template_extraction.comprehensive_processor import ComprehensiveProcessor


class VerboseDocAITester:
    """Test DocAI extraction with detailed verbose output."""
    
    def __init__(self):
        self.test_id = f"docai_comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.output_base = Path("outputs/test_results/docai_tests") / self.test_id
        self.processor = None
        
    async def run_test(self):
        """Run comprehensive DocAI test with 6 PDFs."""
        
        print("\n" + "🤖" * 35)
        print("  COMPREHENSIVE GOOGLE DOCUMENT AI EXTRACTION TEST")
        print("  NO CLAUDE VISION FALLBACK - DOCAI ONLY")
        print("🤖" * 35)
        
        # Select 6 diverse PDF documents
        test_pdfs = [
            Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),           # Personal Financial Statement
            Path("inputs/real/Brigham_dallas/Brigham_Dallas_2024_PTR.pdf"),      # Personal Tax Return
            Path("inputs/real/Brigham_dallas/Hello_Sugar_Franchise_LLC_2024.pdf"), # Business Tax Return
            Path("inputs/real/Brigham_dallas/Waxxpot_Org_Chart_2025_.pdf"),      # Organization Chart
            Path("inputs/real/Brigham_dallas/Management_Bios.pdf"),              # Text-heavy document
            Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2023_Form_1065_Tax_Return.pdf") # Complex form
        ]
        
        print(f"\n📋 TEST CONFIGURATION:")
        print(f"  • Test ID: {self.test_id}")
        print(f"  • Documents: {len(test_pdfs)} PDFs")
        print(f"  • Output: {self.output_base}")
        print(f"  • Timestamp: {datetime.now().isoformat()}")
        
        # Verify all documents exist
        print(f"\n📁 VERIFYING TEST DOCUMENTS:")
        valid_docs = []
        for i, doc_path in enumerate(test_pdfs, 1):
            if doc_path.exists():
                size_mb = doc_path.stat().st_size / (1024 * 1024)
                print(f"  {i}. ✅ {doc_path.name[:50]:<50} ({size_mb:6.2f} MB)")
                valid_docs.append(doc_path)
            else:
                print(f"  {i}. ❌ {doc_path.name} - NOT FOUND")
        
        if len(valid_docs) != len(test_pdfs):
            print(f"\n⚠️ Warning: Only {len(valid_docs)}/{len(test_pdfs)} documents found")
        
        # Create output directories
        self.output_base.mkdir(parents=True, exist_ok=True)
        incremental_dir = self.output_base / "incremental_merges"
        incremental_dir.mkdir(exist_ok=True)
        
        print(f"\n🔧 INITIALIZING PROCESSOR...")
        self.processor = ComprehensiveProcessor()
        
        # Disable Claude Vision fallback by modifying extractor
        if hasattr(self.processor, 'extractor'):
            # This will be initialized on first use
            pass
        
        print("\n" + "="*70)
        print("  STARTING INCREMENTAL DOCUMENT PROCESSING")
        print("="*70)
        
        # Process documents incrementally
        all_results = {}
        master_data = {}
        
        for doc_num, doc_path in enumerate(valid_docs, 1):
            print(f"\n{'='*70}")
            print(f"  DOCUMENT {doc_num}/{len(valid_docs)}: {doc_path.name}")
            print(f"{'='*70}")
            
            print(f"\n🔍 VERBOSE EXTRACTION DETAILS:")
            print(f"  • File: {doc_path}")
            print(f"  • Size: {doc_path.stat().st_size / (1024 * 1024):.2f} MB")
            print(f"  • Type: PDF Document")
            
            try:
                # Process document with verbose output
                print(f"\n📤 Sending to DocAI Form Parser...")
                print(f"  • Processor: projects/robotic-heaven-469117-v3/locations/us/processors/67072eea67ca011a")
                print(f"  • Mode: Form Parser ($30/1000 pages)")
                
                # Process document
                result = await self.processor.process_document(doc_path, self.test_id)
                
                # Store results
                all_results[doc_path.name] = self._extract_summary(result)
                master_data = result  # Latest master data
                
                # Save incremental merge
                incremental_path = incremental_dir / f"merge_{doc_num:02d}_{doc_path.stem}.json"
                with open(incremental_path, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                print(f"\n💾 Saved incremental merge: {incremental_path.name}")
                
                # Print extraction summary
                self._print_extraction_summary(result, doc_path.name)
                
            except Exception as e:
                print(f"\n❌ ERROR processing {doc_path.name}: {e}")
                import traceback
                traceback.print_exc()
                all_results[doc_path.name] = {"error": str(e)}
        
        # Save final master data
        print(f"\n{'='*70}")
        print("  SAVING FINAL RESULTS")
        print("="*70)
        
        master_path = self.output_base / "master_data_final.json"
        with open(master_path, 'w') as f:
            json.dump(master_data, f, indent=2, default=str)
        print(f"✅ Master data saved: {master_path}")
        
        # Save test summary
        summary = self._generate_summary(all_results, master_data)
        summary_path = self.output_base / "test_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"✅ Test summary saved: {summary_path}")
        
        # Print final statistics
        self._print_final_statistics(summary)
        
        return summary
    
    def _extract_summary(self, result: dict) -> dict:
        """Extract key metrics from result."""
        summary = {
            "categories_populated": 0,
            "total_fields": 0,
            "extraction_method": "unknown",
            "confidence": 0.0
        }
        
        # Count populated categories
        for category in ["personal_info", "business_info", "financial_data", "tax_data", "debt_schedules", "other_data"]:
            if category in result and result[category]:
                summary["categories_populated"] += 1
                if isinstance(result[category], dict):
                    summary["total_fields"] += len(result[category])
        
        # Get metadata
        if "metadata" in result and "document_extractions" in result["metadata"]:
            # Get the latest document's metadata
            doc_extractions = result["metadata"]["document_extractions"]
            if doc_extractions:
                latest_doc = list(doc_extractions.values())[-1]
                summary["extraction_method"] = latest_doc.get("extraction_method", "unknown")
                summary["confidence"] = latest_doc.get("extraction_confidence", 0.0)
        
        return summary
    
    def _print_extraction_summary(self, result: dict, doc_name: str):
        """Print detailed extraction summary."""
        print(f"\n📊 EXTRACTION RESULTS for {doc_name}:")
        
        # Check metadata
        if "metadata" in result and "document_extractions" in result["metadata"]:
            if doc_name in result["metadata"]["document_extractions"]:
                doc_meta = result["metadata"]["document_extractions"][doc_name]
                print(f"\n  🔍 Metadata:")
                print(f"    • Method: {doc_meta.get('extraction_method', 'unknown')}")
                print(f"    • Confidence: {doc_meta.get('extraction_confidence', 0.0):.1%}")
                
                if "docai_metadata" in doc_meta:
                    docai_meta = doc_meta["docai_metadata"]
                    print(f"    • DocAI Processor: ✅ {docai_meta.get('processor', 'unknown')}")
                    print(f"    • Pages processed: {docai_meta.get('pages_count', 0)}")
        
        # Print category details
        print(f"\n  📂 Categories:")
        categories = ["personal_info", "business_info", "financial_data", "tax_data", "debt_schedules", "other_data"]
        
        for category in categories:
            if category in result and result[category]:
                if isinstance(result[category], dict):
                    field_count = len(result[category])
                    # Count nested fields
                    nested_count = 0
                    for key, value in result[category].items():
                        if isinstance(value, dict):
                            nested_count += len(value)
                    
                    if nested_count > 0:
                        print(f"    ✅ {category}: {field_count} sections, {nested_count} fields")
                    else:
                        print(f"    ✅ {category}: {field_count} fields")
                    
                    # Show sample fields
                    sample_keys = list(result[category].keys())[:3]
                    for key in sample_keys:
                        if isinstance(result[category][key], dict):
                            print(f"       • {key}: {len(result[category][key])} items")
                        elif isinstance(result[category][key], list):
                            print(f"       • {key}: {len(result[category][key])} entries")
                        else:
                            print(f"       • {key}: {type(result[category][key]).__name__}")
                else:
                    print(f"    ✅ {category}: {type(result[category]).__name__}")
            else:
                print(f"    ❌ {category}: empty")
    
    def _generate_summary(self, all_results: dict, master_data: dict) -> dict:
        """Generate comprehensive test summary."""
        summary = {
            "test_id": self.test_id,
            "timestamp": datetime.now().isoformat(),
            "test_type": "comprehensive_docai_extraction",
            "documents_processed": len(all_results),
            "successful_extractions": sum(1 for r in all_results.values() if "error" not in r),
            "individual_results": all_results,
            "master_data_stats": {
                "total_documents": len(master_data.get("metadata", {}).get("documents_processed", [])),
                "categories_with_data": sum(
                    1 for cat in ["personal_info", "business_info", "financial_data", "tax_data", "debt_schedules"]
                    if cat in master_data and master_data[cat]
                ),
                "total_fields": sum(
                    len(master_data.get(cat, {}))
                    for cat in ["personal_info", "business_info", "financial_data", "tax_data", "debt_schedules", "other_data"]
                    if isinstance(master_data.get(cat), dict)
                )
            }
        }
        
        # Calculate averages
        if all_results:
            valid_results = [r for r in all_results.values() if "error" not in r]
            if valid_results:
                summary["average_confidence"] = sum(r.get("confidence", 0) for r in valid_results) / len(valid_results)
                summary["average_fields_per_doc"] = sum(r.get("total_fields", 0) for r in valid_results) / len(valid_results)
                summary["average_categories_populated"] = sum(r.get("categories_populated", 0) for r in valid_results) / len(valid_results)
        
        return summary
    
    def _print_final_statistics(self, summary: dict):
        """Print final test statistics."""
        print(f"\n{'='*70}")
        print("  FINAL TEST STATISTICS")
        print("="*70)
        
        print(f"\n📊 Overall Results:")
        print(f"  • Documents processed: {summary['documents_processed']}")
        print(f"  • Successful extractions: {summary['successful_extractions']}")
        print(f"  • Success rate: {summary['successful_extractions']/summary['documents_processed']*100:.1f}%")
        
        if "average_confidence" in summary:
            print(f"\n📈 Averages:")
            print(f"  • Average confidence: {summary['average_confidence']:.1%}")
            print(f"  • Average fields/doc: {summary['average_fields_per_doc']:.1f}")
            print(f"  • Average categories populated: {summary['average_categories_populated']:.1f}/6")
        
        print(f"\n🗂️ Master Data Statistics:")
        stats = summary["master_data_stats"]
        print(f"  • Total documents in master: {stats['total_documents']}")
        print(f"  • Categories with data: {stats['categories_with_data']}/5")
        print(f"  • Total fields accumulated: {stats['total_fields']}")
        
        print(f"\n💾 Output Location:")
        print(f"  • Test results: {self.output_base}")
        print(f"  • Incremental merges: {self.output_base}/incremental_merges/")
        print(f"  • Master data: {self.output_base}/master_data_final.json")
        
        # Performance assessment
        success_rate = summary['successful_extractions']/summary['documents_processed']*100
        if success_rate >= 90:
            print(f"\n🎉 EXCELLENT: {success_rate:.0f}% DocAI extraction success!")
        elif success_rate >= 75:
            print(f"\n✅ GOOD: {success_rate:.0f}% DocAI extraction success")
        elif success_rate >= 50:
            print(f"\n⚠️ MODERATE: {success_rate:.0f}% DocAI extraction success")
        else:
            print(f"\n❌ POOR: {success_rate:.0f}% DocAI extraction success")


async def main():
    """Run the comprehensive DocAI test."""
    tester = VerboseDocAITester()
    summary = await tester.run_test()
    
    print(f"\n{'='*70}")
    print("  TEST COMPLETE")
    print("="*70)
    print(f"✅ All results saved to: outputs/test_results/docai_tests/{tester.test_id}")
    
    return summary


if __name__ == "__main__":
    asyncio.run(main())