#!/usr/bin/env python3
"""
Quick validation test to check if chunking is needed.
This test doesn't actually process documents, just validates the setup.
"""

import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Check for large PDFs
def check_chunking_requirements():
    """Check which documents would need chunking"""
    
    try:
        from pypdf import PdfReader
        pdf_lib = "pypdf"
    except ImportError:
        from PyPDF2 import PdfReader
        pdf_lib = "PyPDF2"
    
    print("\n" + "="*70)
    print("📚 PDF CHUNKING REQUIREMENTS CHECK")
    print("="*70)
    
    # Use absolute path from project root
    project_root = Path(__file__).parent.parent.parent
    test_dir = project_root / "inputs/real/Brigham_dallas"
    
    if not test_dir.exists():
        print(f"❌ Test directory not found: {test_dir}")
        return
    
    # Analyze PDFs
    all_pdfs = list(test_dir.glob("*.pdf"))
    print(f"\n📊 Found {len(all_pdfs)} PDF files")
    
    needs_chunking = []
    no_chunking = []
    
    for pdf_file in all_pdfs:
        try:
            reader = PdfReader(pdf_file)
            pages = len(reader.pages)
            
            if pages > 30:
                chunks_needed = calculate_chunks(pages)
                needs_chunking.append((pdf_file.name, pages, chunks_needed))
            else:
                no_chunking.append((pdf_file.name, pages))
                
        except Exception as e:
            print(f"  ⚠️ Error reading {pdf_file.name}: {e}")
    
    # Print results
    print(f"\n✅ Documents that DON'T need chunking ({len(no_chunking)}):")
    for name, pages in sorted(no_chunking, key=lambda x: x[1]):
        print(f"  • {name:50} {pages:3} pages")
    
    print(f"\n⚠️ Documents that NEED chunking ({len(needs_chunking)}):")
    for name, pages, chunks in sorted(needs_chunking, key=lambda x: x[1], reverse=True):
        print(f"  • {name:50} {pages:3} pages → {chunks} chunks")
    
    # Summary
    total_pages_needing_chunks = sum(p for _, p, _ in needs_chunking)
    total_chunks = sum(c for _, _, c in needs_chunking)
    
    print(f"\n📈 Summary:")
    print(f"  • Documents needing chunking: {len(needs_chunking)}/{len(all_pdfs)} ({len(needs_chunking)*100//len(all_pdfs)}%)")
    print(f"  • Total pages to chunk: {total_pages_needing_chunks}")
    print(f"  • Total chunks needed: {total_chunks}")
    print(f"  • Average chunks per large doc: {total_chunks/len(needs_chunking):.1f}" if needs_chunking else "")
    
    # Implementation status
    print(f"\n🔍 Current Implementation Status:")
    
    # Check if chunking is implemented
    chunker_file = project_root / "src/extraction_methods/pdf_chunker.py"
    
    if chunker_file.exists():
        print(f"  ✅ PDF chunker module exists")
        
        # Check if it's integrated
        docai_file = project_root / "src/extraction_methods/docai_general_processor.py"
        if docai_file.exists():
            with open(docai_file) as f:
                content = f.read()
                if "chunk" in content.lower():
                    print(f"  ✅ Chunking integrated in DocAI processor")
                else:
                    print(f"  ❌ Chunking NOT integrated in DocAI processor")
    else:
        print(f"  ❌ PDF chunker module NOT implemented")
        print(f"     Need to create: {chunker_file}")
    
    print("\n" + "="*70)
    
    return needs_chunking

def calculate_chunks(pages: int, max_pages: int = 30, overlap: int = 1) -> int:
    """Calculate number of chunks needed"""
    if pages <= max_pages:
        return 1
    
    # With overlap
    effective_pages = max_pages - overlap
    remaining = pages - max_pages
    additional = (remaining + effective_pages - 1) // effective_pages
    return 1 + additional

if __name__ == "__main__":
    needs_chunking = check_chunking_requirements()
    
    if needs_chunking:
        print("\n💡 Next Steps:")
        print("  1. Implement pdf_chunker.py module")
        print("  2. Update docai_general_processor.py to use chunking")
        print("  3. Run test_docai_chunking.py to validate")
    else:
        print("\n✅ No documents need chunking!")