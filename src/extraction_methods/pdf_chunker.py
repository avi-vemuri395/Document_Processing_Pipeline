"""
Minimal PDF chunker for Document AI processing
Splits PDFs > 15 pages into processable chunks
"""

import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from pypdf import PdfReader, PdfWriter


class PDFChunker:
    """Simple PDF chunker for DocAI sync processing"""
    
    def __init__(self, max_pages: int = 15):
        """
        Initialize chunker with page limit
        
        Args:
            max_pages: Maximum pages per chunk (15 for DocAI sync)
        """
        self.max_pages = max_pages
    
    def get_page_count(self, file_path: Path) -> int:
        """Get number of pages in PDF"""
        try:
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                return len(reader.pages)
        except Exception as e:
            print(f"  ⚠️ Error counting pages: {e}")
            return 0
    
    def needs_chunking(self, file_path: Path) -> bool:
        """Check if PDF needs chunking"""
        if not str(file_path).lower().endswith('.pdf'):
            return False
        
        page_count = self.get_page_count(file_path)
        return page_count > self.max_pages
    
    def split_pdf(self, file_path: Path, temp_dir: str) -> List[Dict[str, Any]]:
        """
        Split PDF into chunks and save to temp directory
        
        Args:
            file_path: Path to PDF file
            temp_dir: Temporary directory to save chunks
            
        Returns:
            List of chunk info with file paths
        """
        page_count = self.get_page_count(file_path)
        
        if page_count <= self.max_pages:
            # No chunking needed
            return [{
                "chunk_path": file_path,
                "chunk_index": 0,
                "total_chunks": 1,
                "start_page": 1,
                "end_page": page_count,
                "pages": f"1-{page_count}"
            }]
        
        chunks = []
        
        try:
            with open(file_path, 'rb') as f:
                reader = PdfReader(f)
                
                # Calculate chunks
                num_chunks = (page_count + self.max_pages - 1) // self.max_pages
                
                for chunk_idx in range(num_chunks):
                    start_page = chunk_idx * self.max_pages
                    end_page = min(start_page + self.max_pages, page_count)
                    
                    # Create chunk PDF
                    writer = PdfWriter()
                    for page_num in range(start_page, end_page):
                        writer.add_page(reader.pages[page_num])
                    
                    # Save chunk to temp file
                    chunk_filename = f"{file_path.stem}_chunk_{chunk_idx + 1}.pdf"
                    chunk_path = Path(temp_dir) / chunk_filename
                    
                    with open(chunk_path, 'wb') as chunk_file:
                        writer.write(chunk_file)
                    
                    chunks.append({
                        "chunk_path": chunk_path,
                        "chunk_index": chunk_idx,
                        "total_chunks": num_chunks,
                        "start_page": start_page + 1,  # 1-indexed for display
                        "end_page": end_page,
                        "pages": f"{start_page + 1}-{end_page}"
                    })
                    
                    print(f"     • Created chunk {chunk_idx + 1}/{num_chunks}: pages {start_page + 1}-{end_page}")
                    
        except Exception as e:
            print(f"  ❌ Error splitting PDF: {e}")
            # Return original file as single chunk on error
            return [{
                "chunk_path": file_path,
                "chunk_index": 0,
                "total_chunks": 1,
                "start_page": 1,
                "end_page": page_count,
                "pages": f"1-{page_count}"
            }]
        
        return chunks
    
    def merge_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge results from multiple chunks
        Simple concatenation for bare minimum implementation
        
        Args:
            chunk_results: List of extraction results from each chunk
            
        Returns:
            Merged result dictionary
        """
        if not chunk_results:
            return {}
        
        if len(chunk_results) == 1:
            return chunk_results[0]
        
        # Simple merge - combine all fields
        merged = {
            "success": True,
            "text": "",
            "form_fields": {},
            "tables": [],
            "entities": [],
            "pages": 0,
            "confidence": 0.0,
            "_metadata": {
                "chunks_processed": len(chunk_results),
                "processor": "docai_form_parser_chunked"
            }
        }
        
        total_confidence = 0.0
        
        for chunk_result in chunk_results:
            if not chunk_result.get("success", False):
                continue
            
            # Concatenate text
            merged["text"] += chunk_result.get("text", "")
            
            # Merge form fields (later chunks override earlier ones for duplicates)
            merged["form_fields"].update(chunk_result.get("form_fields", {}))
            
            # Append tables and entities
            merged["tables"].extend(chunk_result.get("tables", []))
            merged["entities"].extend(chunk_result.get("entities", []))
            
            # Sum pages
            merged["pages"] += chunk_result.get("pages", 0)
            
            # Average confidence
            total_confidence += chunk_result.get("confidence", 0.0)
        
        # Calculate average confidence
        if len(chunk_results) > 0:
            merged["confidence"] = total_confidence / len(chunk_results)
        
        return merged