"""
Pipeline Orchestrator - Coordinates the Two-Part Pipeline
Manages the flow from document processing to form generation
"""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .comprehensive_processor import ComprehensiveProcessor
from .form_mapping_service import FormMappingService
from .spreadsheet_mapping_service import SpreadsheetMappingService


class PipelineOrchestrator:
    """
    Orchestrates the correct two-part pipeline:
    1. Part 1: Extract data ONCE from documents (comprehensive extraction)
    2. Part 2: Map extracted data to MANY forms (distribution)
    
    This is the correct architecture: Extract once, map to many.
    NOT: Extract many times with different templates.
    """
    
    def __init__(self):
        """Initialize all pipeline components"""
        self.part1_processor = ComprehensiveProcessor()
        self.part2_mapper = FormMappingService()
        self.spreadsheet_mapper = SpreadsheetMappingService()
        self.output_base = Path("outputs/applications")
    
    async def process_application(
        self,
        application_id: str,
        documents: List[Path],
        target_banks: Optional[List[str]] = None,
        generate_spreadsheets: bool = False
    ) -> Dict[str, Any]:
        """
        Process a complete loan application through both pipeline parts.
        
        Args:
            application_id: Unique identifier for this application
            documents: List of document paths to process
            target_banks: Optional list of banks to generate forms for.
                         If None, generates forms for all banks.
            generate_spreadsheets: Whether to also generate Excel spreadsheets
                         
        Returns:
            Complete results including extracted data and generated forms
        """
        print(f"\n{'='*70}")
        print(f"  TWO-PART PIPELINE ORCHESTRATION")
        print(f"  Application: {application_id}")
        print(f"  Documents: {len(documents)}")
        print(f"  Target Banks: {target_banks or 'All (3 banks)'}")
        print(f"{'='*70}")
        
        # Initialize results
        results = {
            "application_id": application_id,
            "timestamp": datetime.now().isoformat(),
            "documents_processed": [],
            "part1_results": {},
            "part2_results": {},
            "summary": {}
        }
        
        # Part 1: Document Processing (Extract Once)
        print(f"\n{'─'*50}")
        print("  Starting PART 1: Document Processing")
        print(f"{'─'*50}")
        
        master_data = await self.part1_processor.process_documents(
            documents, 
            application_id
        )
        
        results["part1_results"] = {
            "master_data_path": str(
                self.output_base / application_id / "part1_document_processing" / "master_data.json"
            ),
            "total_fields_extracted": sum(
                len(fields) for category, fields in master_data.items()
                if isinstance(fields, dict) and category != "metadata"
            ),
            "categories": list(master_data.keys()),
            "documents_processed": master_data.get("metadata", {}).get("documents_processed", [])
        }
        
        results["documents_processed"] = results["part1_results"]["documents_processed"]
        
        # Part 2: Form Mapping (Map to Many)
        print(f"\n{'─'*50}")
        print("  Starting PART 2: Form Mapping")
        print(f"{'─'*50}")
        
        if target_banks:
            # Process only specified banks
            form_results = {}
            for bank in target_banks:
                if bank in FormMappingService.BANK_FORMS:
                    bank_results = self.part2_mapper.map_bank_forms(
                        application_id,
                        bank
                    )
                    form_results[bank] = bank_results
                else:
                    print(f"  ⚠️  Unknown bank: {bank}")
        else:
            # Process all banks
            form_results = self.part2_mapper.map_all_forms(application_id)
        
        results["part2_results"] = form_results
        
        # Part 2b: Spreadsheet Generation (Optional)
        if generate_spreadsheets:
            print(f"\n{'─'*50}")
            print("  Starting PART 2b: Spreadsheet Generation")
            print(f"{'─'*50}")
            
            spreadsheet_results = self.spreadsheet_mapper.populate_all_spreadsheets(application_id)
            results["spreadsheet_results"] = spreadsheet_results
        else:
            results["spreadsheet_results"] = {}
        
        # Generate summary
        results["summary"] = self._generate_summary(results)
        
        # Save orchestration results
        self._save_results(application_id, results)
        
        # Display final summary
        self._display_summary(results["summary"])
        
        return results
    
    async def process_incremental(
        self,
        application_id: str,
        new_document: Path,
        regenerate_forms: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single new document incrementally.
        
        This method handles the common scenario where documents are
        uploaded one at a time over days/weeks.
        
        Args:
            application_id: Existing application ID
            new_document: Path to newly uploaded document
            regenerate_forms: Whether to regenerate all forms after processing
            
        Returns:
            Updated results after processing new document
        """
        print(f"\n{'='*70}")
        print(f"  INCREMENTAL DOCUMENT PROCESSING")
        print(f"  Application: {application_id}")
        print(f"  New Document: {new_document.name}")
        print(f"{'='*70}")
        
        # Process the new document (Part 1)
        print("\n📄 Processing new document...")
        master_data = await self.part1_processor.process_document(
            new_document,
            application_id
        )
        
        # Check if we should regenerate forms
        if regenerate_forms:
            print("\n🔄 Regenerating forms with updated data...")
            form_results = self.part2_mapper.map_all_forms(application_id)
        else:
            print("\n⏸️  Form regeneration skipped (regenerate_forms=False)")
            form_results = {}
        
        return {
            "application_id": application_id,
            "new_document": str(new_document),
            "timestamp": datetime.now().isoformat(),
            "master_data_updated": True,
            "forms_regenerated": regenerate_forms,
            "form_results": form_results
        }
    
    def get_application_status(self, application_id: str) -> Dict[str, Any]:
        """
        Get the current status of an application.
        
        Args:
            application_id: Application to check
            
        Returns:
            Status information including processing state and coverage
        """
        app_dir = self.output_base / application_id
        
        if not app_dir.exists():
            return {
                "exists": False,
                "application_id": application_id
            }
        
        # Check Part 1 status
        master_path = app_dir / "part1_document_processing" / "master_data.json"
        part1_status = {
            "completed": master_path.exists(),
            "master_data_path": str(master_path) if master_path.exists() else None
        }
        
        if master_path.exists():
            import json
            with open(master_path, 'r') as f:
                master_data = json.load(f)
                part1_status["documents_processed"] = master_data.get("metadata", {}).get("documents_processed", [])
                part1_status["total_fields"] = sum(
                    len(fields) for category, fields in master_data.items()
                    if isinstance(fields, dict) and category != "metadata"
                )
        
        # Check Part 2 status
        mapping_summary_path = app_dir / "part2_form_mapping" / "mapping_summary.json"
        part2_status = {
            "completed": mapping_summary_path.exists(),
            "summary_path": str(mapping_summary_path) if mapping_summary_path.exists() else None
        }
        
        if mapping_summary_path.exists():
            import json
            with open(mapping_summary_path, 'r') as f:
                summary = json.load(f)
                part2_status["banks_processed"] = summary.get("banks_processed", [])
                part2_status["total_forms"] = summary.get("total_forms", 0)
                part2_status["average_coverage"] = summary.get("overall_stats", {}).get("average_coverage", 0)
        
        return {
            "exists": True,
            "application_id": application_id,
            "part1_status": part1_status,
            "part2_status": part2_status,
            "last_modified": datetime.fromtimestamp(app_dir.stat().st_mtime).isoformat()
        }
    
    def _generate_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics from results"""
        summary = {
            "total_documents": len(results["documents_processed"]),
            "total_fields_extracted": results["part1_results"].get("total_fields_extracted", 0),
            "banks_processed": [],
            "total_forms_generated": 0,
            "forms_by_bank": {},
            "overall_coverage": 0,
            "spreadsheets_generated": 0
        }
        
        # Process Part 2 results
        if results["part2_results"]:
            summary["banks_processed"] = list(results["part2_results"].keys())
            
            total_coverage = 0
            form_count = 0
            
            for bank, bank_results in results["part2_results"].items():
                summary["forms_by_bank"][bank] = len(bank_results)
                summary["total_forms_generated"] += len(bank_results)
                
                for form_type, form_data in bank_results.items():
                    if isinstance(form_data, dict):
                        coverage = form_data.get("coverage", 0)
                        total_coverage += coverage
                        form_count += 1
            
            if form_count > 0:
                summary["overall_coverage"] = round(total_coverage / form_count, 1)
        
        # Process spreadsheet results
        if results.get("spreadsheet_results"):
            summary["spreadsheets_generated"] = sum(
                1 for result in results["spreadsheet_results"].values()
                if isinstance(result, dict) and result.get("status") == "success"
            )
        
        return summary
    
    def _save_results(self, application_id: str, results: Dict[str, Any]):
        """Save orchestration results"""
        import json
        
        results_path = self.output_base / application_id / "pipeline_results.json"
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    
    def _display_summary(self, summary: Dict[str, Any]):
        """Display final summary in a nice format"""
        print(f"\n{'='*70}")
        print(f"  PIPELINE COMPLETE - SUMMARY")
        print(f"{'='*70}")
        print(f"\n  📊 Extraction Results:")
        print(f"    • Documents processed: {summary['total_documents']}")
        print(f"    • Total fields extracted: {summary['total_fields_extracted']}")
        
        print(f"\n  📝 Form Generation Results:")
        print(f"    • Banks processed: {', '.join(summary['banks_processed']) or 'None'}")
        print(f"    • Total forms generated: {summary['total_forms_generated']}")
        
        if summary['forms_by_bank']:
            print(f"\n  🏦 Forms by Bank:")
            for bank, count in summary['forms_by_bank'].items():
                print(f"    • {bank.title()}: {count} forms")
        
        if summary['overall_coverage'] > 0:
            print(f"\n  📈 Overall Coverage: {summary['overall_coverage']}%")
        
        if summary['spreadsheets_generated'] > 0:
            print(f"\n  📊 Spreadsheets Generated: {summary['spreadsheets_generated']}")
        
        print(f"\n✅ Pipeline execution complete!")


async def main():
    """Example usage of the pipeline orchestrator"""
    
    # Initialize orchestrator
    orchestrator = PipelineOrchestrator()
    
    # Example: Process a new application
    test_documents = [
        Path("inputs/real/Brigham_dallas/Brigham_PFS_2024.pdf"),
        Path("inputs/real/Brigham_dallas/Brigham_2023_Tax_Return.pdf")
    ]
    
    # Filter to existing documents
    existing_docs = [doc for doc in test_documents if doc.exists()]
    
    if existing_docs:
        results = await orchestrator.process_application(
            application_id="test_correct_pipeline_001",
            documents=existing_docs,
            target_banks=["live_oak", "huntington"]  # Optional: specify banks
        )
        
        print(f"\n📁 Results saved to: outputs/applications/{results['application_id']}/")
    else:
        print("❌ No test documents found")


if __name__ == "__main__":
    asyncio.run(main())