#!/usr/bin/env python3
"""
Test Document AI with small PDFs that are under the page limits
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from src.extraction_methods.multimodal_llm.providers import BenchmarkExtractor

async def test_docai_processing():
    """Test DocAI with small PDFs under page limits"""
    
    print("\n" + "="*70)
    print("DOCUMENT AI TEST - SMALL FILES")
    print("="*70)
    print("Testing with PDFs under 30 pages to verify DocAI processing")
    
    # Small PDFs for testing (all under 30 pages)
    test_files = [
        ("Brigham_Dallas_PFS.pdf", 3, "Personal Financial Statement"),
        ("Management_Bios.pdf", 5, "Management Biographies"),
        ("Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf", 30, "Tax Return 1065"),
        ("Waxxpot_Org_Chart_2025_.pdf", 1, "Organization Chart"),
    ]
    
    # Create output directory
    output_dir = Path("outputs/docai_tests")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 Output directory: {output_dir}")
    
    # Initialize extractor
    print("\n🚀 Initializing BenchmarkExtractor...")
    extractor = BenchmarkExtractor()
    
    # Check DocAI status
    print(f"\n📊 DocAI Status:")
    print(f"  • Form Parser available: {extractor.form_parser is not None}")
    print(f"  • General Processor available: {extractor.general_processor is not None}")
    
    if not extractor.form_parser and not extractor.general_processor:
        print("\n❌ No DocAI processors available! Check configuration.")
        return
    
    # Process each test file
    results = {}
    
    for filename, expected_pages, description in test_files:
        file_path = Path(f"inputs/real/Brigham_dallas/{filename}")
        
        if not file_path.exists():
            print(f"\n⚠️ File not found: {file_path}")
            continue
        
        print(f"\n{'='*60}")
        print(f"📄 Testing: {filename}")
        print(f"  • Description: {description}")
        print(f"  • Expected pages: {expected_pages}")
        print(f"  • File size: {file_path.stat().st_size / 1024:.1f} KB")
        print(f"{'='*60}")
        
        # Process with DocAI
        try:
            print("\n🔄 Processing with BenchmarkExtractor...")
            result = await extractor.extract_all([str(file_path)])
            
            # Check if DocAI was used
            metadata = result.get('_metadata', {})
            docai_used = metadata.get('docai_processed', 0) > 0
            claude_used = metadata.get('claude_vision_processed', 0) > 0
            
            print(f"\n✅ Processing complete!")
            print(f"  • DocAI used: {'Yes' if docai_used else 'No'}")
            print(f"  • Claude Vision used: {'Yes' if claude_used else 'No'}")
            print(f"  • Processing method: {metadata.get('extraction_methods', {})}")
            
            # Extract key information from result
            if str(file_path) in result:
                doc_result = result[str(file_path)]
                
                # For DocAI results
                if 'form_fields' in doc_result:
                    print(f"\n📊 DocAI Extraction Results:")
                    print(f"  • Form fields: {len(doc_result.get('form_fields', {}))}")
                    print(f"  • Tables: {len(doc_result.get('tables', []))}")
                    print(f"  • Entities: {len(doc_result.get('entities', []))}")
                    print(f"  • Checkboxes: {len(doc_result.get('checkboxes', []))}")
                    print(f"  • Pages processed: {doc_result.get('pages', 0)}")
                    print(f"  • Confidence: {doc_result.get('confidence', 0):.1%}")
                    
                    # Show sample form fields
                    if doc_result.get('form_fields'):
                        print(f"\n  Sample form fields (first 5):")
                        for i, (key, value) in enumerate(list(doc_result['form_fields'].items())[:5]):
                            if isinstance(value, dict):
                                print(f"    {i+1}. {key}: {value.get('value', '')[:50]}...")
                            else:
                                print(f"    {i+1}. {key}: {str(value)[:50]}...")
                
                # Save result to file
                output_file = output_dir / f"{filename.replace('.pdf', '')}_result.json"
                with open(output_file, 'w') as f:
                    json.dump(doc_result, f, indent=2, default=str)
                print(f"\n💾 Saved result to: {output_file.name}")
                
                results[filename] = {
                    "success": True,
                    "docai_used": docai_used,
                    "pages": doc_result.get('pages', 0),
                    "confidence": doc_result.get('confidence', 0),
                    "output_file": str(output_file)
                }
            else:
                print(f"\n⚠️ No result found for {file_path}")
                results[filename] = {"success": False, "error": "No result in output"}
                
        except Exception as e:
            print(f"\n❌ Error processing {filename}: {e}")
            results[filename] = {"success": False, "error": str(e)}
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    success_count = sum(1 for r in results.values() if r.get('success'))
    docai_count = sum(1 for r in results.values() if r.get('docai_used'))
    
    print(f"\n📊 Results:")
    print(f"  • Files processed: {len(results)}")
    print(f"  • Successful: {success_count}")
    print(f"  • Used DocAI: {docai_count}")
    print(f"  • Output directory: {output_dir}")
    
    # Save summary
    summary_file = output_dir / "test_summary.json"
    summary = {
        "test_date": datetime.now().isoformat(),
        "files_tested": len(results),
        "successful": success_count,
        "docai_used": docai_count,
        "results": results
    }
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n💾 Test summary saved to: {summary_file}")
    
    # Show which method was used for each file
    print(f"\n📋 Processing Methods:")
    for filename, result in results.items():
        if result.get('success'):
            method = "DocAI" if result.get('docai_used') else "Claude Vision"
            print(f"  • {filename}: {method}")
        else:
            print(f"  • {filename}: Failed - {result.get('error', 'Unknown error')}")
    
    print(f"\n✅ DocAI test complete! Check {output_dir} for detailed results.")

if __name__ == "__main__":
    asyncio.run(test_docai_processing())