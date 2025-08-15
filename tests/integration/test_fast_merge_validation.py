#!/usr/bin/env python3
"""
Fast end-to-end test with 2 PDFs and 2 spreadsheets to validate merge logic.
This test focuses on verifying that data accumulates properly across documents.

Expected runtime: ~2 minutes (vs 8 minutes for full test)
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.template_extraction import PipelineOrchestrator


class FastMergeValidationTest:
    """Fast test to validate merge logic with minimal documents"""
    
    def __init__(self):
        self.orchestrator = PipelineOrchestrator()
        self.test_id = f"fast_merge_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.results = {}
        
    async def run_test(self) -> dict:
        """Run the fast merge validation test"""
        print("\n" + "="*80)
        print("  FAST MERGE VALIDATION TEST")
        print("  Testing with 2 PDFs + 2 Spreadsheets")
        print("="*80)
        
        try:
            # Phase 1: Process 2 PDFs
            print("\n📄 PHASE 1: Processing 2 PDF documents...")
            pdf_docs = [
                Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),  # Has rich personal/financial data
                Path("inputs/real/Brigham_dallas/Hello_Sugar_Franchise_LLC_2023.pdf")  # Has business/tax data
            ]
            
            phase1_result = await self.orchestrator.process_application(
                application_id=self.test_id,
                documents=pdf_docs,
                target_banks=["live_oak"],  # Just one bank for speed
                generate_spreadsheets=False
            )
            
            # Validate Phase 1
            master_path = Path(f"outputs/applications/{self.test_id}/part1_document_processing/master_data.json")
            with open(master_path, 'r') as f:
                phase1_master = json.load(f)
            
            phase1_fields = self._count_non_null_fields(phase1_master)
            print(f"  ✅ Phase 1 complete: {phase1_fields} non-null fields extracted")
            
            # Capture specific values to test merge
            phase1_values = {
                "personal_name": self._get_nested(phase1_master, "personal_info.personal.primary_applicant.name.first"),
                "business_name": self._get_nested(phase1_master, "business_info.business.primary_business.legal_name"),
                "total_assets": self._get_nested(phase1_master, "financial_data.personal_financial_statement.assets.real_estate"),
                "net_income": self._get_nested(phase1_master, "financial_data.income_statement.net_income")
            }
            print(f"  📊 Key values captured:")
            for key, value in phase1_values.items():
                if value:
                    print(f"     - {key}: {str(value)[:50]}...")
            
            # Phase 2: Add 2 Spreadsheets
            print("\n📊 PHASE 2: Adding 2 Excel spreadsheets...")
            excel_docs = [
                Path("inputs/real/Brigham_dallas/HSF_PL_as_of_20250630.xlsx"),  # P&L statement
                Path("inputs/real/Brigham_dallas/HSF_BS_as_of_20250630.xlsx")   # Balance sheet
            ]
            
            phase2_result = await self.orchestrator.process_application(
                application_id=self.test_id,
                documents=excel_docs,
                target_banks=["live_oak"],
                generate_spreadsheets=True  # Test spreadsheet generation too
            )
            
            # Validate Phase 2
            with open(master_path, 'r') as f:
                phase2_master = json.load(f)
            
            phase2_fields = self._count_non_null_fields(phase2_master)
            print(f"  ✅ Phase 2 complete: {phase2_fields} total non-null fields")
            
            # Check if Phase 1 data was preserved
            phase2_values = {
                "personal_name": self._get_nested(phase2_master, "personal_info.personal.primary_applicant.name.first"),
                "business_name": self._get_nested(phase2_master, "business_info.business.primary_business.legal_name"),
                "total_assets": self._get_nested(phase2_master, "financial_data.personal_financial_statement.assets.real_estate"),
                "net_income": self._get_nested(phase2_master, "financial_data.income_statement.net_income")
            }
            
            # Validate merge worked correctly
            print("\n🔍 MERGE VALIDATION:")
            merge_success = True
            
            for key in phase1_values:
                if phase1_values[key] and not phase2_values[key]:
                    print(f"  ❌ LOST: {key} was present in Phase 1 but missing in Phase 2")
                    merge_success = False
                elif phase1_values[key] and phase2_values[key]:
                    print(f"  ✅ PRESERVED: {key}")
                elif not phase1_values[key] and phase2_values[key]:
                    print(f"  ✅ ADDED: {key} (new in Phase 2)")
            
            # Check field count increased (or at least didn't decrease)
            if phase2_fields >= phase1_fields:
                print(f"\n  ✅ Field count preserved/increased: {phase1_fields} → {phase2_fields}")
            else:
                print(f"\n  ❌ FIELD LOSS: {phase1_fields} → {phase2_fields} (lost {phase1_fields - phase2_fields} fields)")
                merge_success = False
            
            # Check form generation
            print("\n📋 FORM GENERATION CHECK:")
            form_path = Path(f"outputs/applications/{self.test_id}/part2_form_mapping/banks/live_oak")
            if form_path.exists():
                forms = list(form_path.glob("*.json"))
                pdfs = list(form_path.glob("*.pdf"))
                print(f"  ✅ Generated {len(forms)} form mappings, {len(pdfs)} PDFs")
                
                # Check coverage on one form
                if forms:
                    with open(forms[0], 'r') as f:
                        form_data = json.load(f)
                    coverage = form_data.get('coverage', 0)
                    print(f"  📊 Sample form coverage: {coverage:.1f}%")
            
            # Check spreadsheet generation
            print("\n📊 SPREADSHEET CHECK:")
            spreadsheet_path = Path(f"outputs/applications/{self.test_id}/part2_spreadsheets")
            if spreadsheet_path.exists():
                spreadsheets = list(spreadsheet_path.glob("*.xlsx"))
                print(f"  ✅ Generated {len(spreadsheets)} Excel files")
            
            # Final summary
            print("\n" + "="*80)
            print("  TEST SUMMARY")
            print("="*80)
            
            results = {
                "test_id": self.test_id,
                "phase1_fields": phase1_fields,
                "phase2_fields": phase2_fields,
                "field_growth": phase2_fields - phase1_fields,
                "merge_success": merge_success,
                "documents_processed": 4,
                "forms_generated": len(forms) if form_path.exists() else 0,
                "spreadsheets_generated": len(spreadsheets) if spreadsheet_path.exists() else 0
            }
            
            if merge_success and phase2_fields >= phase1_fields:
                print("  🎉 TEST PASSED: Merge logic working correctly!")
                print(f"  📈 Data accumulation: {phase1_fields} → {phase2_fields} fields")
            else:
                print("  ❌ TEST FAILED: Merge logic issues detected")
                if phase2_fields < phase1_fields:
                    print(f"  ⚠️  Data loss: {phase1_fields - phase2_fields} fields lost")
            
            print(f"\n  📁 Outputs saved to: outputs/applications/{self.test_id}/")
            
            return results
            
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "test_id": self.test_id}
    
    def _count_non_null_fields(self, data, prefix=""):
        """Recursively count non-null fields in nested structure"""
        count = 0
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "metadata":  # Skip metadata
                    continue
                if value not in [None, "", [], {}]:
                    if isinstance(value, (dict, list)):
                        count += self._count_non_null_fields(value, f"{prefix}.{key}")
                    else:
                        count += 1
        elif isinstance(data, list):
            for item in data:
                if item not in [None, "", [], {}]:
                    count += self._count_non_null_fields(item, prefix)
        return count
    
    def _get_nested(self, data, path):
        """Get nested value from dict using dot notation"""
        keys = path.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value


async def main():
    """Run the fast merge validation test"""
    test = FastMergeValidationTest()
    results = await test.run_test()
    
    # Return exit code based on test results
    if results.get("merge_success") and not results.get("error"):
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)