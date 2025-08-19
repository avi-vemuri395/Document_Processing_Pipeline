"""
Optimal Two-Tool Document Processor
Uses only Google Document AI and Claude Vision for high-accuracy extraction
with intelligent routing, rate limiting, and chunking support.
"""

import asyncio
import random
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

# Core imports
from .multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
from .docai_form_parser import FormParserExtractor
from .multimodal_llm.core.universal_preprocessor import UniversalPreprocessor
from ..config.docai_config import is_form_parser_configured

# PDF handling
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("Warning: pypdf not available. PDF page counting will be limited.")


@dataclass
class ProcessingResult:
    """Container for document processing results"""
    data: Dict[str, Any]
    processor_used: str
    processing_time: float
    page_count: int
    confidence: float
    metadata: Dict[str, Any]


class RateLimitHandler:
    """
    Handles rate limiting for both DocAI and Claude APIs
    with exponential backoff and jitter
    """
    
    def __init__(self):
        self.docai_last_request = 0
        self.claude_last_request = 0
        
        # Minimum time between requests (in seconds)
        self.docai_min_interval = 0.1  # 10 requests per second max
        self.claude_min_interval = 0.2  # 5 requests per second max
        
        # Backoff configuration
        self.max_retries = 5
        self.base_delay = 1.0
        self.max_delay = 60.0
        
    async def wait_if_needed(self, api_type: str):
        """Wait if we're sending requests too quickly"""
        current_time = time.time()
        
        if api_type == "docai":
            time_since_last = current_time - self.docai_last_request
            if time_since_last < self.docai_min_interval:
                await asyncio.sleep(self.docai_min_interval - time_since_last)
            self.docai_last_request = time.time()
            
        elif api_type == "claude":
            time_since_last = current_time - self.claude_last_request
            if time_since_last < self.claude_min_interval:
                await asyncio.sleep(self.claude_min_interval - time_since_last)
            self.claude_last_request = time.time()
    
    async def execute_with_backoff(self, func, *args, api_type: str = "claude", **kwargs):
        """
        Execute function with exponential backoff on rate limit errors
        """
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                await self.wait_if_needed(api_type)
                
                # Execute the function
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                is_rate_limit = (
                    "rate" in error_str or 
                    "429" in error_str or 
                    "too many requests" in error_str
                )
                
                if not is_rate_limit or attempt == self.max_retries - 1:
                    raise
                
                # Calculate backoff with jitter
                delay = min(
                    self.base_delay * (2 ** attempt),
                    self.max_delay
                )
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                
                print(f"  ⚠️ Rate limited on attempt {attempt + 1}/{self.max_retries}. "
                      f"Waiting {total_delay:.1f}s before retry...")
                
                await asyncio.sleep(total_delay)
        
        raise Exception(f"Max retries ({self.max_retries}) exceeded")


class SmartChunker:
    """
    Intelligent document chunking for both DocAI and Claude
    """
    
    def __init__(self):
        self.docai_page_limit = 30  # With imageless mode
        self.docai_safe_limit = 15  # Without imageless mode
        self.claude_token_estimate_per_page = 2000  # Conservative estimate
        self.claude_max_tokens = 100000  # Claude's context window
        
    def get_pdf_page_count(self, file_path: Path) -> int:
        """Get the number of pages in a PDF"""
        if not PYPDF_AVAILABLE:
            print(f"  ⚠️ Cannot count pages without pypdf. Assuming 10 pages.")
            return 10
            
        try:
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                return len(reader.pages)
        except Exception as e:
            print(f"  ⚠️ Error counting PDF pages: {e}. Assuming 10 pages.")
            return 10
    
    def should_chunk_for_docai(self, file_path: Path, use_imageless: bool = True) -> bool:
        """Determine if document needs chunking for DocAI"""
        if not str(file_path).lower().endswith('.pdf'):
            return False
            
        page_count = self.get_pdf_page_count(file_path)
        limit = self.docai_page_limit if use_imageless else self.docai_safe_limit
        return page_count > limit
    
    def chunk_for_docai(self, file_path: Path, use_imageless: bool = True) -> List[Dict[str, Any]]:
        """
        Create intelligent chunks for DocAI processing
        Preserves document structure when possible
        """
        page_count = self.get_pdf_page_count(file_path)
        limit = self.docai_page_limit if use_imageless else self.docai_safe_limit
        
        if page_count <= limit:
            return [{
                "file_path": file_path,
                "pages": f"1-{page_count}",
                "start_page": 1,
                "end_page": page_count,
                "chunk_index": 0,
                "total_chunks": 1
            }]
        
        chunks = []
        overlap = 2  # Pages of overlap
        chunk_size = limit - overlap
        
        # Detect document type for intelligent chunking
        file_name_lower = str(file_path).lower()
        
        if "tax" in file_name_lower or "1040" in file_name_lower or "1065" in file_name_lower:
            # Tax return - preserve form boundaries
            chunks = self._chunk_tax_return(page_count, limit)
        elif "financial" in file_name_lower or "statement" in file_name_lower:
            # Financial statement - preserve statement sections
            chunks = self._chunk_financial_statement(page_count, limit)
        else:
            # Default chunking with overlap
            for i in range(0, page_count, chunk_size):
                end = min(i + limit, page_count)
                chunks.append({
                    "file_path": file_path,
                    "pages": f"{i+1}-{end}",
                    "start_page": i + 1,
                    "end_page": end,
                    "chunk_index": len(chunks),
                    "total_chunks": -1  # Will update after
                })
        
        # Update total chunks
        for chunk in chunks:
            chunk["total_chunks"] = len(chunks)
            
        return chunks
    
    def _chunk_tax_return(self, page_count: int, limit: int) -> List[Dict[str, Any]]:
        """Special chunking for tax returns to preserve form boundaries"""
        chunks = []
        
        # Common tax return structure
        sections = [
            (1, min(10, page_count), "main_return"),
            (11, min(25, page_count), "schedules"),
            (26, min(40, page_count), "k1_forms"),
            (41, page_count, "attachments")
        ]
        
        for start, end, section_name in sections:
            if start <= page_count:
                actual_end = min(end, page_count)
                if actual_end >= start:
                    chunks.append({
                        "pages": f"{start}-{actual_end}",
                        "start_page": start,
                        "end_page": actual_end,
                        "section": section_name,
                        "chunk_index": len(chunks)
                    })
        
        return chunks if chunks else self._default_chunking(page_count, limit)
    
    def _chunk_financial_statement(self, page_count: int, limit: int) -> List[Dict[str, Any]]:
        """Special chunking for financial statements"""
        chunks = []
        
        # Common financial statement structure
        sections = [
            (1, min(5, page_count), "summary"),
            (6, min(15, page_count), "balance_sheet"),
            (16, min(25, page_count), "income_statement"),
            (26, page_count, "notes_and_appendix")
        ]
        
        for start, end, section_name in sections:
            if start <= page_count:
                actual_end = min(end, page_count)
                if actual_end >= start:
                    chunks.append({
                        "pages": f"{start}-{actual_end}",
                        "start_page": start,
                        "end_page": actual_end,
                        "section": section_name,
                        "chunk_index": len(chunks)
                    })
        
        return chunks if chunks else self._default_chunking(page_count, limit)
    
    def _default_chunking(self, page_count: int, limit: int) -> List[Dict[str, Any]]:
        """Default chunking with overlap"""
        chunks = []
        overlap = 2
        chunk_size = limit - overlap
        
        for i in range(0, page_count, chunk_size):
            end = min(i + limit, page_count)
            chunks.append({
                "pages": f"{i+1}-{end}",
                "start_page": i + 1,
                "end_page": end,
                "chunk_index": len(chunks)
            })
        
        return chunks
    
    def estimate_claude_tokens(self, file_path: Path) -> int:
        """Estimate tokens for Claude processing"""
        if str(file_path).lower().endswith('.pdf'):
            page_count = self.get_pdf_page_count(file_path)
            return page_count * self.claude_token_estimate_per_page
        else:
            # For other files, use file size as rough estimate
            file_size_kb = file_path.stat().st_size / 1024
            return int(file_size_kb * 100)  # Rough estimate


class DocumentRouter:
    """
    Routes documents to the optimal processor based on characteristics
    """
    
    def __init__(self):
        self.chunker = SmartChunker()
        
        # Document type patterns
        self.tax_patterns = ["tax", "1040", "1065", "1120", "schedule", "k-1", "w-2", "1099"]
        self.loan_patterns = ["application", "loan", "sba", "credit"]
        self.statement_patterns = ["statement", "financial", "balance", "income", "p&l"]
        
    def classify_document(self, file_path: Path) -> str:
        """Classify document type based on filename and content"""
        file_name_lower = str(file_path.name).lower()
        
        # Check for tax documents
        if any(pattern in file_name_lower for pattern in self.tax_patterns):
            return "tax_return"
        
        # Check for loan applications
        if any(pattern in file_name_lower for pattern in self.loan_patterns):
            return "loan_application"
        
        # Check for financial statements
        if any(pattern in file_name_lower for pattern in self.statement_patterns):
            return "financial_statement"
        
        # Check file extension
        if file_name_lower.endswith(('.xlsx', '.xls')):
            return "spreadsheet"
        
        # Default
        return "general_document"
    
    async def route_document(self, file_path: Path) -> Tuple[str, Dict[str, Any]]:
        """
        Determine optimal processor and processing strategy
        
        Returns:
            Tuple of (processor_name, processing_config)
        """
        doc_type = self.classify_document(file_path)
        page_count = self.chunker.get_pdf_page_count(file_path) if str(file_path).endswith('.pdf') else 0
        
        config = {
            "document_type": doc_type,
            "page_count": page_count,
            "needs_chunking": False,
            "use_batch_api": False
        }
        
        # Spreadsheets always use pandas (via BenchmarkExtractor)
        if doc_type == "spreadsheet":
            return "excel", config
        
        # Structured documents prefer DocAI
        if doc_type in ["tax_return", "loan_application", "financial_statement"]:
            if page_count <= 30:
                return "docai", config
            elif page_count <= 100:
                config["needs_chunking"] = True
                return "docai", config
            else:
                # Very large documents use Claude batch
                config["use_batch_api"] = True
                return "claude", config
        
        # General documents
        if page_count <= 15:
            return "docai", config
        elif page_count <= 50:
            return "claude", config
        else:
            config["use_batch_api"] = True
            return "claude", config


class ResultMerger:
    """
    Merges results from multiple chunks or processors
    """
    
    def merge_chunked_results(self, chunk_results: List[Dict[str, Any]], overlap_pages: int = 2) -> Dict[str, Any]:
        """Merge results from document chunks, handling overlaps"""
        if not chunk_results:
            return {}
        
        if len(chunk_results) == 1:
            return chunk_results[0]
        
        merged = {
            "extracted_data": {},
            "metadata": {
                "chunks_processed": len(chunk_results),
                "merge_strategy": "intelligent_deduplication"
            }
        }
        
        # Track field sources for deduplication
        field_sources = {}
        
        for i, chunk_result in enumerate(chunk_results):
            chunk_data = chunk_result.get("extracted_data", chunk_result)
            
            for key, value in chunk_data.items():
                if key.startswith("_"):  # Skip metadata fields
                    continue
                    
                if key not in merged["extracted_data"]:
                    # First occurrence of this field
                    merged["extracted_data"][key] = value
                    field_sources[key] = i
                else:
                    # Field already exists - use confidence or length to decide
                    if self._is_better_extraction(value, merged["extracted_data"][key]):
                        merged["extracted_data"][key] = value
                        field_sources[key] = i
        
        # Add chunk source metadata
        merged["metadata"]["field_sources"] = field_sources
        
        return merged
    
    def _is_better_extraction(self, new_value: Any, existing_value: Any) -> bool:
        """Determine if new extraction is better than existing"""
        # Handle None values
        if new_value is None:
            return False
        if existing_value is None:
            return True
        
        # Prefer longer, more complete extractions
        if isinstance(new_value, str) and isinstance(existing_value, str):
            # Remove whitespace for comparison
            new_clean = new_value.strip()
            existing_clean = existing_value.strip()
            
            # Prefer non-empty over empty
            if new_clean and not existing_clean:
                return True
            if not new_clean and existing_clean:
                return False
            
            # Prefer longer content (likely more complete)
            return len(new_clean) > len(existing_clean)
        
        # For other types, keep existing
        return False
    
    def merge_hybrid_results(self, docai_result: Optional[Dict], claude_result: Optional[Dict]) -> Dict[str, Any]:
        """
        Merge results from both DocAI and Claude processors
        DocAI is preferred for structured data, Claude for narrative
        """
        merged = {
            "structured_data": {},
            "narrative_data": {},
            "tables": [],
            "metadata": {
                "processors_used": []
            }
        }
        
        # Process DocAI results (better for structured data)
        if docai_result:
            merged["processors_used"].append("docai")
            
            # Extract structured fields
            if "form_fields" in docai_result:
                merged["structured_data"].update(docai_result["form_fields"])
            
            # Extract tables
            if "tables" in docai_result:
                merged["tables"].extend(docai_result["tables"])
            
            # Keep any entities
            if "entities" in docai_result:
                merged["entities"] = docai_result["entities"]
        
        # Process Claude results (better for narrative and complex understanding)
        if claude_result:
            merged["processors_used"].append("claude")
            
            # Extract narrative sections
            for key, value in claude_result.items():
                if key.startswith("_"):
                    continue
                    
                # Add to narrative data
                if key not in merged["structured_data"]:
                    merged["narrative_data"][key] = value
                # Fill gaps in structured data
                elif not merged["structured_data"].get(key):
                    merged["structured_data"][key] = value
        
        # Flatten into single result
        final_result = merged["structured_data"].copy()
        final_result.update(merged["narrative_data"])
        
        if merged["tables"]:
            final_result["_tables"] = merged["tables"]
        
        final_result["_metadata"] = merged["metadata"]
        
        return final_result


class OptimalDocumentProcessor:
    """
    Main processor that orchestrates the two-tool approach
    """
    
    def __init__(self):
        print("\n" + "="*70)
        print("Initializing Optimal Two-Tool Document Processor")
        print("="*70)
        
        # Initialize components
        self.rate_limiter = RateLimitHandler()
        self.chunker = SmartChunker()
        self.router = DocumentRouter()
        self.merger = ResultMerger()
        
        # Initialize processors
        self.benchmark_extractor = BenchmarkExtractor()
        
        # Check DocAI availability
        self.form_parser = None
        if is_form_parser_configured():
            try:
                self.form_parser = FormParserExtractor()
                print("  ✅ DocAI Form Parser initialized")
            except Exception as e:
                print(f"  ⚠️ Could not initialize Form Parser: {e}")
        else:
            print("  ℹ️ DocAI Form Parser not configured")
        
        print("  ✅ Claude Vision available via BenchmarkExtractor")
        print("="*70 + "\n")
    
    async def process_document(self, file_path: Path) -> ProcessingResult:
        """
        Process a single document with optimal routing
        """
        start_time = time.time()
        
        # Route document to optimal processor
        processor, config = await self.router.route_document(file_path)
        
        print(f"\n📄 Processing: {file_path.name}")
        print(f"  • Document type: {config['document_type']}")
        print(f"  • Page count: {config['page_count']}")
        print(f"  • Selected processor: {processor}")
        print(f"  • Needs chunking: {config['needs_chunking']}")
        
        # Process based on routing decision
        if processor == "excel":
            result = await self._process_excel(file_path)
        elif processor == "docai":
            if config["needs_chunking"]:
                result = await self._process_chunked_docai(file_path)
            else:
                result = await self._process_single_docai(file_path)
        elif processor == "claude":
            if config["use_batch_api"]:
                result = await self._process_batch_claude(file_path)
            else:
                result = await self._process_single_claude(file_path)
        else:
            # Fallback
            result = await self._process_single_claude(file_path)
        
        # Create processing result
        processing_time = time.time() - start_time
        
        return ProcessingResult(
            data=result,
            processor_used=processor,
            processing_time=processing_time,
            page_count=config["page_count"],
            confidence=0.9,  # Default high confidence
            metadata=config
        )
    
    async def _process_excel(self, file_path: Path) -> Dict[str, Any]:
        """Process Excel file using pandas extractor"""
        print("  🔄 Processing with Excel extractor (pandas)...")
        
        # Excel processing doesn't need rate limiting
        result = await self.benchmark_extractor.extract_all([str(file_path)])
        
        # Extract the file result
        if str(file_path) in result:
            return result[str(file_path)]
        
        return result
    
    async def _process_single_docai(self, file_path: Path) -> Dict[str, Any]:
        """Process single document with DocAI"""
        if not self.form_parser:
            print("  ⚠️ DocAI not available, falling back to Claude")
            return await self._process_single_claude(file_path)
        
        print("  🔄 Processing with DocAI Form Parser...")
        
        try:
            result = await self.rate_limiter.execute_with_backoff(
                self.form_parser.extract,
                file_path,
                api_type="docai"
            )
            return result
        except Exception as e:
            print(f"  ⚠️ DocAI failed: {e}, falling back to Claude")
            return await self._process_single_claude(file_path)
    
    async def _process_chunked_docai(self, file_path: Path) -> Dict[str, Any]:
        """Process large document with DocAI chunking"""
        if not self.form_parser:
            print("  ⚠️ DocAI not available, falling back to Claude")
            return await self._process_single_claude(file_path)
        
        print("  🔄 Processing with DocAI (chunked)...")
        
        # Create chunks
        chunks = self.chunker.chunk_for_docai(file_path)
        print(f"  📦 Created {len(chunks)} chunks for processing")
        
        chunk_results = []
        
        for i, chunk_info in enumerate(chunks):
            print(f"  • Processing chunk {i+1}/{len(chunks)}: pages {chunk_info['pages']}")
            
            # For now, process the full file with page limits
            # In production, you'd split the PDF here
            try:
                result = await self.rate_limiter.execute_with_backoff(
                    self.form_parser.extract,
                    chunk_info["file_path"],
                    api_type="docai"
                )
                chunk_results.append(result)
                
                # Small delay between chunks
                if i < len(chunks) - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"  ⚠️ Chunk {i+1} failed: {e}")
                # Continue with other chunks
        
        if not chunk_results:
            print("  ⚠️ All chunks failed, falling back to Claude")
            return await self._process_single_claude(file_path)
        
        # Merge chunk results
        return self.merger.merge_chunked_results(chunk_results)
    
    async def _process_single_claude(self, file_path: Path) -> Dict[str, Any]:
        """Process document with Claude Vision"""
        print("  🔄 Processing with Claude Vision...")
        
        result = await self.rate_limiter.execute_with_backoff(
            self.benchmark_extractor.extract_all,
            [str(file_path)],
            api_type="claude"
        )
        
        # Extract the file result
        if str(file_path) in result:
            return result[str(file_path)]
        
        return result
    
    async def _process_batch_claude(self, file_path: Path) -> Dict[str, Any]:
        """Process very large document with Claude Batch API"""
        print("  🔄 Processing with Claude Batch API (for cost savings)...")
        print("  ℹ️ Note: Batch processing typically takes 1-2 hours")
        
        # For now, fall back to regular processing
        # In production, you'd implement batch submission here
        print("  ⚠️ Batch API not yet implemented, using synchronous processing")
        return await self._process_single_claude(file_path)
    
    async def process_application(self, 
                                  documents: List[Path],
                                  application_id: str = None) -> Dict[str, Any]:
        """
        Process a complete loan application with multiple documents
        """
        if not application_id:
            application_id = f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n{'='*70}")
        print(f"Processing Application: {application_id}")
        print(f"Documents: {len(documents)}")
        print(f"{'='*70}")
        
        all_results = {}
        processing_stats = {
            "total_documents": len(documents),
            "docai_processed": 0,
            "claude_processed": 0,
            "excel_processed": 0,
            "total_pages": 0,
            "total_time": 0
        }
        
        for doc_path in documents:
            if not doc_path.exists():
                print(f"  ⚠️ File not found: {doc_path}")
                continue
            
            # Process document
            result = await self.process_document(doc_path)
            
            # Store result
            all_results[str(doc_path)] = result.data
            
            # Update statistics
            processing_stats["total_pages"] += result.page_count
            processing_stats["total_time"] += result.processing_time
            
            if result.processor_used == "docai":
                processing_stats["docai_processed"] += 1
            elif result.processor_used == "claude":
                processing_stats["claude_processed"] += 1
            elif result.processor_used == "excel":
                processing_stats["excel_processed"] += 1
        
        # Create final result
        final_result = {
            "application_id": application_id,
            "documents_processed": len(all_results),
            "extracted_data": self._merge_all_results(all_results),
            "processing_stats": processing_stats,
            "_metadata": {
                "processing_date": datetime.now().isoformat(),
                "processor_version": "optimal_two_tool_v1"
            }
        }
        
        print(f"\n{'='*70}")
        print(f"✅ Application Processing Complete")
        print(f"  • Documents processed: {processing_stats['total_documents']}")
        print(f"  • Total pages: {processing_stats['total_pages']}")
        print(f"  • DocAI used: {processing_stats['docai_processed']} times")
        print(f"  • Claude used: {processing_stats['claude_processed']} times")
        print(f"  • Excel processor used: {processing_stats['excel_processed']} times")
        print(f"  • Total time: {processing_stats['total_time']:.1f}s")
        print(f"{'='*70}\n")
        
        return final_result
    
    def _merge_all_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Merge results from all documents into a single dataset"""
        merged = {}
        
        for file_path, data in results.items():
            if isinstance(data, dict):
                for key, value in data.items():
                    if not key.startswith("_"):  # Skip metadata
                        if key not in merged or value:  # Prefer non-empty values
                            merged[key] = value
        
        return merged


# Convenience function for testing
async def test_optimal_processor():
    """Test the optimal processor with sample documents"""
    processor = OptimalDocumentProcessor()
    
    # Test with sample documents
    test_docs = [
        Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf"),
        Path("inputs/real/Brigham_dallas/Waxxpot_Group_Holdings_LLC_2022_Form_1065_Tax_Return.pdf")
    ]
    
    # Filter to existing files
    existing_docs = [doc for doc in test_docs if doc.exists()]
    
    if existing_docs:
        result = await processor.process_application(existing_docs, "test_001")
        
        # Save result
        output_path = Path("outputs/optimal_processor_test.json")
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {output_path}")
    else:
        print("No test documents found. Please add documents to test.")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_optimal_processor())