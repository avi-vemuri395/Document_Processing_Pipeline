#!/usr/bin/env python3
"""
Comprehensive test for Document AI PDF chunking functionality.
Tests processing of documents > 30 pages with automatic chunking.
"""

import asyncio
import json
import time
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Color codes for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


class DocAIChunkingTest:
    """Test suite for PDF chunking with Document AI"""
    
    def __init__(self):
        self.test_results = {
            "passed": [],
            "failed": [],
            "chunked_files": [],
            "performance": {}
        }
        
    async def test_large_document_processing(self) -> Dict[str, Any]:
        """Test processing of documents that exceed 30-page limit"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}📚 DOCUMENT AI CHUNKING TEST{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        
        # Find test documents > 30 pages  
        project_root = Path(__file__).parent.parent.parent
        test_dir = project_root / "inputs/real/Brigham_dallas"
        large_docs = self._find_large_documents(test_dir)
        
        if not large_docs:
            print(f"{YELLOW}⚠️ No documents > 30 pages found for testing{RESET}")
            return self.test_results
            
        print(f"\n📊 Found {len(large_docs)} documents exceeding 30 pages:")
        for doc, pages in large_docs:
            print(f"  • {doc.name}: {pages} pages")
        
        # Test each large document
        for doc_path, page_count in large_docs:
            await self._test_document_chunking(doc_path, page_count)
        
        # Print summary
        self._print_summary()
        
        return self.test_results
    
    def _find_large_documents(self, directory: Path) -> List[Tuple[Path, int]]:
        """Find all PDFs > 30 pages"""
        try:
            from pypdf import PdfReader
        except ImportError:
            from PyPDF2 import PdfReader
        
        large_docs = []
        
        if not directory.exists():
            print(f"{RED}❌ Test directory not found: {directory}{RESET}")
            return large_docs
        
        for pdf_file in directory.glob("*.pdf"):
            try:
                reader = PdfReader(pdf_file)
                page_count = len(reader.pages)
                if page_count > 30:
                    large_docs.append((pdf_file, page_count))
            except Exception as e:
                print(f"{YELLOW}⚠️ Could not read {pdf_file.name}: {e}{RESET}")
        
        return sorted(large_docs, key=lambda x: x[1], reverse=True)
    
    async def _test_document_chunking(self, doc_path: Path, page_count: int):
        """Test chunking and processing of a single large document"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"Testing: {doc_path.name} ({page_count} pages)")
        print(f"{BLUE}{'='*60}{RESET}")
        
        from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
        
        try:
            # Initialize extractor
            extractor = BenchmarkExtractor()
            
            # Check if DocAI is configured
            if not extractor.general_processor:
                print(f"{YELLOW}⚠️ DocAI not configured - skipping{RESET}")
                self.test_results["failed"].append({
                    "file": doc_path.name,
                    "reason": "DocAI not configured"
                })
                return
            
            # Calculate expected chunks
            expected_chunks = self._calculate_expected_chunks(page_count)
            print(f"\n📋 Chunking Strategy:")
            print(f"  • Document pages: {page_count}")
            print(f"  • Max pages per chunk: 30")
            print(f"  • Overlap: 1 page")
            print(f"  • Expected chunks: {expected_chunks}")
            
            # Process document
            print(f"\n🔄 Processing document...")
            start_time = time.time()
            
            result = await extractor.extract_all(doc_path)
            
            processing_time = time.time() - start_time
            
            # Analyze results
            self._analyze_results(doc_path, result, page_count, processing_time)
            
        except Exception as e:
            print(f"{RED}❌ Test failed: {e}{RESET}")
            self.test_results["failed"].append({
                "file": doc_path.name,
                "error": str(e)
            })
    
    def _calculate_expected_chunks(self, page_count: int, max_pages: int = 30, overlap: int = 1) -> int:
        """Calculate expected number of chunks"""
        if page_count <= max_pages:
            return 1
        
        # First chunk: pages 0-29 (30 pages)
        # Second chunk: pages 29-58 (30 pages, 1 overlap)
        # etc.
        effective_pages_per_chunk = max_pages - overlap
        remaining_pages = page_count - max_pages
        additional_chunks = (remaining_pages + effective_pages_per_chunk - 1) // effective_pages_per_chunk
        
        return 1 + additional_chunks
    
    def _analyze_results(self, doc_path: Path, result: Dict[str, Any], page_count: int, processing_time: float):
        """Analyze and validate chunking results"""
        
        # Check if DocAI was used
        metadata = result.get("_metadata", {})
        docai_processed = metadata.get("docai_processed", 0)
        extraction_methods = metadata.get("extraction_methods", {})
        
        print(f"\n📊 Results Analysis:")
        print(f"  • Processing time: {processing_time:.2f} seconds")
        print(f"  • Processing rate: {page_count/processing_time:.1f} pages/second")
        
        # Check if chunking was used
        if docai_processed > 0:
            print(f"{GREEN}✅ Document processed with DocAI{RESET}")
            
            # Validate data extraction
            if isinstance(result, dict) and doc_path.name in str(result):
                doc_result = result.get(str(doc_path), result)
                
                if doc_result.get("success"):
                    text_len = len(doc_result.get("text", ""))
                    entities = len(doc_result.get("entities", []))
                    tables = len(doc_result.get("tables", []))
                    
                    print(f"  • Text extracted: {text_len:,} characters")
                    print(f"  • Entities found: {entities}")
                    print(f"  • Tables found: {tables}")
                    
                    self.test_results["passed"].append({
                        "file": doc_path.name,
                        "pages": page_count,
                        "processing_time": processing_time,
                        "text_length": text_len,
                        "entities": entities,
                        "tables": tables
                    })
                    
                    self.test_results["chunked_files"].append(doc_path.name)
                else:
                    error_msg = doc_result.get("error", "Unknown error")
                    
                    # Check if it's a page limit error that should have been chunked
                    if "PAGE_LIMIT_EXCEEDED" in error_msg:
                        print(f"{RED}❌ CHUNKING FAILED - Page limit error not handled{RESET}")
                        print(f"  Error: {error_msg}")
                        self.test_results["failed"].append({
                            "file": doc_path.name,
                            "reason": "Chunking not implemented - page limit error"
                        })
                    else:
                        print(f"{YELLOW}⚠️ Processing failed: {error_msg}{RESET}")
                        self.test_results["failed"].append({
                            "file": doc_path.name,
                            "reason": error_msg
                        })
            else:
                print(f"{GREEN}✅ Document processed successfully{RESET}")
                self.test_results["passed"].append({
                    "file": doc_path.name,
                    "pages": page_count,
                    "processing_time": processing_time
                })
                
        elif "claude_vision" in str(extraction_methods):
            print(f"{YELLOW}⚠️ Fell back to Claude Vision (chunking not working){RESET}")
            self.test_results["failed"].append({
                "file": doc_path.name,
                "reason": "Fell back to Claude Vision instead of chunking"
            })
        else:
            print(f"{RED}❌ Unknown processing method{RESET}")
            self.test_results["failed"].append({
                "file": doc_path.name,
                "reason": "Unknown processing method"
            })
    
    def _print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}📈 TEST SUMMARY{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")
        
        total_tests = len(self.test_results["passed"]) + len(self.test_results["failed"])
        
        if total_tests == 0:
            print(f"{YELLOW}No tests were run{RESET}")
            return
        
        passed = len(self.test_results["passed"])
        failed = len(self.test_results["failed"])
        
        print(f"\n📊 Results:")
        print(f"  • Total tests: {total_tests}")
        print(f"  • {GREEN}Passed: {passed}{RESET}")
        print(f"  • {RED}Failed: {failed}{RESET}")
        
        if self.test_results["passed"]:
            print(f"\n{GREEN}✅ Successful Processing:{RESET}")
            for test in self.test_results["passed"]:
                print(f"  • {test['file']}: {test['pages']} pages in {test['processing_time']:.1f}s")
                if 'text_length' in test:
                    print(f"    - Extracted: {test['text_length']:,} chars, {test['entities']} entities, {test['tables']} tables")
        
        if self.test_results["failed"]:
            print(f"\n{RED}❌ Failed Tests:{RESET}")
            for test in self.test_results["failed"]:
                print(f"  • {test['file']}: {test['reason']}")
        
        # Performance metrics
        if self.test_results["passed"]:
            avg_time = sum(t["processing_time"] for t in self.test_results["passed"]) / len(self.test_results["passed"])
            avg_pages = sum(t["pages"] for t in self.test_results["passed"]) / len(self.test_results["passed"])
            print(f"\n⚡ Performance:")
            print(f"  • Average processing time: {avg_time:.2f} seconds")
            print(f"  • Average document size: {avg_pages:.0f} pages")
            print(f"  • Average rate: {avg_pages/avg_time:.1f} pages/second")
        
        # Chunking status
        if self.test_results["chunked_files"]:
            print(f"\n{GREEN}✅ Chunking Implementation Status: WORKING{RESET}")
            print(f"  Files successfully chunked: {', '.join(self.test_results['chunked_files'])}")
        else:
            print(f"\n{RED}❌ Chunking Implementation Status: NOT WORKING{RESET}")
            print(f"  All large documents either failed or fell back to Claude Vision")


async def main():
    """Run the comprehensive chunking test"""
    tester = DocAIChunkingTest()
    results = await tester.test_large_document_processing()
    
    # Save results to file
    project_root = Path(__file__).parent.parent.parent
    output_file = project_root / "outputs/test_chunking_results.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    # Return exit code based on results
    if results["failed"]:
        return 1  # Tests failed
    elif not results["passed"]:
        return 2  # No tests ran
    else:
        return 0  # All tests passed


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)