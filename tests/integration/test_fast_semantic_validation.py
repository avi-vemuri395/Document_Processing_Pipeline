#!/usr/bin/env python3
"""
Fast Semantic Validation Test
Tests with 3 PDFs and 2 spreadsheets for quick validation of:
- DocAI processing with quota project fix
- Semantic mapping improvements
- Form coverage metrics

Expected runtime: ~2-3 minutes
"""

import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from src.template_extraction.pipeline_orchestrator import PipelineOrchestrator


class FastSemanticValidationTest:
    """Fast test with minimal documents for semantic mapping validation."""
    
    def __init__(self):
        self.orchestrator = PipelineOrchestrator()
        self.application_id = f"fast_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_results = {
            "processing_time": 0,
            "docai_success": False,
            "semantic_mapping_success": False,
            "coverage_metrics": {},
            "errors": []
        }
        
    async def run_test(self) -> Dict[str, Any]:
        """Run fast validation test with 3 PDFs and 2 spreadsheets."""
        
        print("\n" + "="*70)
        print("  FAST SEMANTIC VALIDATION TEST")
        print("  3 PDFs + 2 Spreadsheets → Semantic Mapping → Form Coverage")
        print("="*70)
        print(f"\n  Application ID: {self.application_id}")
        print(f"  Start Time: {datetime.now().isoformat()}")
        
        start_time = time.time()
        
        # Select test documents (3 PDFs + 2 spreadsheets)
        test_documents = [
            # PDF 1: Personal Financial Statement (3 pages - fast)
            Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
            
            # PDF 2: Business tax return with EIN and business info
            Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf"),
            
            # PDF 3: Another business document for more coverage
            Path("inputs/real/Brigham_dallas/Hello_Sugar_Franchise_LLC_2023.pdf"),
            
            # Spreadsheet 1: P&L statement
            Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx"),
            
            # Spreadsheet 2: Another financial spreadsheet
            Path("inputs/real/Brigham_dallas/Waxxpot Proforma P&L.xlsx")
        ]
        
        # Check which documents exist
        available_docs = []
        for doc in test_documents:
            if doc.exists():
                available_docs.append(doc)
                print(f"  ✅ Found: {doc.name}")
            else:
                print(f"  ⚠️  Missing: {doc.name}")
        
        if len(available_docs) < 3:
            print("\n❌ Not enough test documents available")
            self.test_results["errors"].append("Insufficient test documents")
            return self.test_results
        
        print(f"\n📄 Processing {len(available_docs)} documents...")
        
        try:
            # Process documents through the pipeline
            results = await self.orchestrator.process_application(
                application_id=self.application_id,
                documents=available_docs[:5],  # Use up to 5 documents
                target_banks=["live_oak", "huntington"],  # Just 2 banks for speed
                generate_spreadsheets=False  # Skip spreadsheet generation for speed
            )
            
            # Check if DocAI was used
            self._check_docai_usage(results)
            
            # Analyze semantic mapping coverage
            self._analyze_coverage(results)
            
            # Check for errors
            if results.get("errors"):
                self.test_results["errors"].extend(results["errors"])
            
            self.test_results["processing_time"] = time.time() - start_time
            
        except Exception as e:
            print(f"\n❌ Pipeline error: {e}")
            self.test_results["errors"].append(str(e))
            import traceback
            traceback.print_exc()
        
        # Display results
        self._display_results()
        
        return self.test_results
    
    def _check_docai_usage(self, results: Dict[str, Any]):
        """Check if DocAI was successfully used."""
        
        print("\n" + "─"*50)
        print("  DocAI Processing Check")
        print("─"*50)
        
        # Check master data for DocAI fields
        master_file = Path(f"outputs/applications/{self.application_id}/part1_document_processing/master_data.json")
        
        if master_file.exists():
            with open(master_file, 'r') as f:
                master_data = json.load(f)
            
            docai_count = 0
            for category in master_data.keys():
                if isinstance(master_data[category], dict):
                    for key in master_data[category].keys():
                        if key.startswith('docai_'):
                            if isinstance(master_data[category][key], dict):
                                docai_count += len(master_data[category][key])
            
            if docai_count > 0:
                print(f"  ✅ DocAI fields extracted: {docai_count}")
                self.test_results["docai_success"] = True
                self.test_results["docai_fields"] = docai_count
            else:
                print(f"  ⚠️  No DocAI fields found - may have fallen back to Claude Vision")
        else:
            print(f"  ❌ Master data not found")
    
    def _analyze_coverage(self, results: Dict[str, Any]):
        """Analyze form coverage with semantic mapping."""
        
        print("\n" + "─"*50)
        print("  Semantic Mapping Coverage Analysis")
        print("─"*50)
        
        coverage_data = {}
        
        # Check each form's coverage
        for bank in ["live_oak", "huntington"]:
            bank_forms = results.get("forms", {}).get(bank, {})
            
            for form_name, form_data in bank_forms.items():
                if isinstance(form_data, dict) and "mapped_data" in form_data:
                    mapped = form_data["mapped_data"]
                    filled = len([v for v in mapped.values() if v])
                    total = form_data.get("total_fields", len(mapped))
                    coverage = (filled / total * 100) if total > 0 else 0
                    
                    coverage_data[f"{bank}_{form_name}"] = {
                        "filled": filled,
                        "total": total,
                        "coverage": coverage,
                        "method": form_data.get("extraction_method", "unknown")
                    }
                    
                    print(f"  • {bank} {form_name}: {filled}/{total} ({coverage:.1f}%)")
                    print(f"    Method: {form_data.get('extraction_method', 'unknown')}")
        
        self.test_results["coverage_metrics"] = coverage_data
        
        # Check if semantic mapping was used
        semantic_used = any(
            "semantic" in data.get("method", "").lower() 
            for data in coverage_data.values()
        )
        
        if semantic_used:
            print(f"\n  ✅ Semantic mapping was used")
            self.test_results["semantic_mapping_success"] = True
        else:
            print(f"\n  ⚠️  Semantic mapping may not have been used")
    
    def _display_results(self):
        """Display test results summary."""
        
        print("\n" + "="*70)
        print("  TEST RESULTS SUMMARY")
        print("="*70)
        
        # Processing metrics
        print(f"\n📊 Processing Metrics:")
        print(f"  • Time: {self.test_results['processing_time']:.1f} seconds")
        print(f"  • DocAI Success: {'✅' if self.test_results['docai_success'] else '❌'}")
        if self.test_results.get('docai_fields'):
            print(f"  • DocAI Fields: {self.test_results['docai_fields']}")
        print(f"  • Semantic Mapping: {'✅' if self.test_results['semantic_mapping_success'] else '❌'}")
        
        # Coverage summary
        if self.test_results["coverage_metrics"]:
            print(f"\n📈 Coverage Summary:")
            
            coverages = [data["coverage"] for data in self.test_results["coverage_metrics"].values()]
            if coverages:
                avg_coverage = sum(coverages) / len(coverages)
                print(f"  • Average Coverage: {avg_coverage:.1f}%")
                
                for form, data in self.test_results["coverage_metrics"].items():
                    status = "✅" if data["coverage"] >= 50 else "⚠️"
                    print(f"  {status} {form}: {data['coverage']:.1f}%")
        
        # Errors
        if self.test_results["errors"]:
            print(f"\n❌ Errors:")
            for error in self.test_results["errors"]:
                print(f"  • {error}")
        
        # Overall status
        success = (
            self.test_results["docai_success"] and 
            self.test_results["semantic_mapping_success"] and
            not self.test_results["errors"]
        )
        
        print(f"\n{'='*70}")
        if success:
            print("  ✅ FAST TEST PASSED")
        else:
            print("  ❌ FAST TEST FAILED")
        print(f"{'='*70}")


async def main():
    """Run the fast semantic validation test."""
    test = FastSemanticValidationTest()
    results = await test.run_test()
    return 0 if results.get("semantic_mapping_success") else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)