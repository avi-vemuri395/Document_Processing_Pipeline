#!/usr/bin/env python3
"""
PDF Technical Structure Analysis

Analyzes the technical characteristics of PDFs:
- Digital vs Scanned
- Text layer presence
- Image/page ratio
- Form fields (AcroForm/XFA)
- Embedded fonts
- Compression
- Encryption
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    print("⚠️  PyMuPDF not available - install with: pip install PyMuPDF")

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("⚠️  pypdf not available - install with: pip install pypdf")


class PDFTechnicalAnalyzer:
    """Analyze technical structure of PDFs"""
    
    def analyze_pdf_structure(self, pdf_path: Path) -> Dict[str, Any]:
        """Deep technical analysis of PDF structure"""
        
        analysis = {
            "file": pdf_path.name,
            "size_mb": round(pdf_path.stat().st_size / (1024 * 1024), 2),
            "technical_type": "unknown",
            "extraction_difficulty": "unknown"
        }
        
        # PyMuPDF technical analysis
        if PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(str(pdf_path))
                
                # Basic metrics
                analysis["pages"] = doc.page_count
                analysis["pdf_version"] = doc.metadata.get("format", "")
                analysis["producer"] = doc.metadata.get("producer", "")
                analysis["creator"] = doc.metadata.get("creator", "")
                
                # Analyze each page's technical structure
                total_text_chars = 0
                total_images = 0
                total_drawings = 0
                pages_with_text = 0
                pages_with_images = 0
                font_list = set()
                
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    
                    # Text analysis
                    text = page.get_text("text") or ""
                    char_count = len(text.strip())
                    if char_count > 10:
                        pages_with_text += 1
                    total_text_chars += char_count
                    
                    # Image analysis
                    images = page.get_images(full=True)
                    if images:
                        pages_with_images += 1
                        total_images += len(images)
                    
                    # Vector graphics/drawings
                    drawings = page.get_drawings()
                    total_drawings += len(drawings)
                    
                    # Fonts (only check first few pages for speed)
                    if page_num < 3:
                        for font in page.get_fonts():
                            font_list.add(font[3])  # Font name
                
                # Calculate technical characteristics
                avg_text_per_page = total_text_chars / max(1, doc.page_count)
                avg_images_per_page = total_images / max(1, doc.page_count)
                
                analysis["text_characteristics"] = {
                    "total_chars": total_text_chars,
                    "avg_chars_per_page": round(avg_text_per_page),
                    "pages_with_text": pages_with_text,
                    "text_coverage": f"{(pages_with_text/max(1,doc.page_count))*100:.1f}%"
                }
                
                analysis["image_characteristics"] = {
                    "total_images": total_images,
                    "avg_images_per_page": round(avg_images_per_page, 2),
                    "pages_with_images": pages_with_images,
                    "image_coverage": f"{(pages_with_images/max(1,doc.page_count))*100:.1f}%"
                }
                
                analysis["graphics"] = {
                    "vector_drawings": total_drawings,
                    "embedded_fonts": list(font_list)[:5]  # First 5 fonts
                }
                
                # Determine technical type
                if avg_text_per_page < 50 and avg_images_per_page > 0.8:
                    analysis["technical_type"] = "SCANNED"
                    analysis["extraction_difficulty"] = "HIGH (requires OCR)"
                elif avg_text_per_page > 100:
                    analysis["technical_type"] = "DIGITAL_NATIVE"
                    analysis["extraction_difficulty"] = "LOW (direct text extraction)"
                elif total_images > 0 and total_text_chars > 0:
                    analysis["technical_type"] = "HYBRID"
                    analysis["extraction_difficulty"] = "MEDIUM (mixed content)"
                else:
                    analysis["technical_type"] = "UNKNOWN"
                
                doc.close()
                
            except Exception as e:
                analysis["pymupdf_error"] = str(e)
        
        # pypdf technical analysis for forms and security
        if PYPDF_AVAILABLE:
            try:
                reader = pypdf.PdfReader(str(pdf_path))
                
                # Security/Encryption
                analysis["security"] = {
                    "is_encrypted": reader.is_encrypted,
                    "has_user_password": False,
                    "has_owner_password": False
                }
                
                if reader.is_encrypted:
                    try:
                        # Try to decrypt with empty password
                        reader.decrypt("")
                        analysis["security"]["encryption_level"] = "weak"
                    except:
                        analysis["security"]["encryption_level"] = "strong"
                
                # Form fields analysis
                form_info = {
                    "has_acroform": False,
                    "has_xfa": False,
                    "field_count": 0,
                    "field_types": []
                }
                
                if "/Root" in reader.trailer:
                    root = reader.trailer["/Root"]
                    
                    # Check for AcroForm
                    if "/AcroForm" in root:
                        acroform = root["/AcroForm"]
                        form_info["has_acroform"] = True
                        
                        if "/Fields" in acroform:
                            fields = acroform["/Fields"]
                            form_info["field_count"] = len(fields)
                            
                            # Sample field types
                            field_types = set()
                            for field_ref in fields[:10]:  # Check first 10
                                try:
                                    field = field_ref.get_object()
                                    ft = field.get("/FT", "")
                                    if ft:
                                        field_types.add(str(ft))
                                except:
                                    pass
                            form_info["field_types"] = list(field_types)
                        
                        # Check for XFA
                        if "/XFA" in acroform:
                            form_info["has_xfa"] = True
                
                analysis["forms"] = form_info
                
                # Page layout info
                if reader.pages:
                    first_page = reader.pages[0]
                    mediabox = first_page.mediabox
                    analysis["page_dimensions"] = {
                        "width": float(mediabox.width),
                        "height": float(mediabox.height),
                        "orientation": "portrait" if mediabox.height > mediabox.width else "landscape"
                    }
                
            except Exception as e:
                analysis["pypdf_error"] = str(e)
        
        return analysis
    
    def analyze_all_pdfs(self):
        """Analyze all PDFs for technical structure"""
        print("\n" + "="*80)
        print("  PDF TECHNICAL STRUCTURE ANALYSIS")
        print("="*80)
        
        # Find all PDFs
        input_dirs = [
            Path("inputs/real/Brigham_dallas"),
            Path("inputs/real/Dave Burlington")
        ]
        
        all_pdfs = []
        for input_dir in input_dirs:
            if input_dir.exists():
                pdfs = sorted(input_dir.glob("*.pdf"))
                all_pdfs.extend(pdfs)
        
        if not all_pdfs:
            print("\n❌ No PDFs found")
            return []
        
        print(f"\n📊 Analyzing {len(all_pdfs)} PDFs for technical structure...")
        print("-" * 80)
        
        results = []
        technical_types = {}
        extraction_difficulties = {}
        
        for i, pdf_path in enumerate(all_pdfs, 1):
            print(f"\n[{i}/{len(all_pdfs)}] {pdf_path.name}")
            
            analysis = self.analyze_pdf_structure(pdf_path)
            results.append(analysis)
            
            # Print technical details
            print(f"  📦 Size: {analysis['size_mb']} MB, {analysis.get('pages', '?')} pages")
            print(f"  🔧 Type: {analysis['technical_type']}")
            print(f"  📈 Difficulty: {analysis['extraction_difficulty']}")
            
            if "text_characteristics" in analysis:
                tc = analysis["text_characteristics"]
                print(f"  📝 Text: {tc['total_chars']:,} chars, {tc['text_coverage']} page coverage")
            
            if "image_characteristics" in analysis:
                ic = analysis["image_characteristics"]
                print(f"  🖼️  Images: {ic['total_images']} total, {ic['avg_images_per_page']}/page avg")
            
            if "forms" in analysis and analysis["forms"]["has_acroform"]:
                forms = analysis["forms"]
                print(f"  📋 Forms: {forms['field_count']} fields")
                if forms.get("has_xfa"):
                    print(f"     ⚠️  Has XFA forms (complex)")
            
            if "security" in analysis and analysis["security"]["is_encrypted"]:
                print(f"  🔒 Encrypted: {analysis['security']['encryption_level']} encryption")
            
            if "page_dimensions" in analysis:
                pd = analysis["page_dimensions"]
                print(f"  📐 Layout: {pd['width']:.0f}x{pd['height']:.0f} ({pd['orientation']})")
            
            # Track statistics
            tech_type = analysis.get("technical_type", "UNKNOWN")
            technical_types[tech_type] = technical_types.get(tech_type, 0) + 1
            
            difficulty = analysis.get("extraction_difficulty", "UNKNOWN")
            extraction_difficulties[difficulty] = extraction_difficulties.get(difficulty, 0) + 1
        
        # Summary
        print("\n" + "="*80)
        print("  TECHNICAL SUMMARY")
        print("="*80)
        
        print("\n🔧 PDF Technical Types:")
        for tech_type, count in technical_types.items():
            percentage = (count / len(all_pdfs)) * 100
            print(f"  • {tech_type}: {count} ({percentage:.1f}%)")
        
        print("\n📊 Extraction Difficulty:")
        for difficulty, count in extraction_difficulties.items():
            percentage = (count / len(all_pdfs)) * 100
            print(f"  • {difficulty}: {count} ({percentage:.1f}%)")
        
        # Find special cases
        scanned = [r for r in results if r.get("technical_type") == "SCANNED"]
        encrypted = [r for r in results if r.get("security", {}).get("is_encrypted")]
        form_pdfs = [r for r in results if r.get("forms", {}).get("has_acroform")]
        xfa_pdfs = [r for r in results if r.get("forms", {}).get("has_xfa")]
        
        if scanned:
            print(f"\n🔍 Scanned PDFs (need OCR): {len(scanned)}")
            for doc in scanned:
                print(f"  • {doc['file']}")
        
        if encrypted:
            print(f"\n🔒 Encrypted PDFs: {len(encrypted)}")
            for doc in encrypted:
                print(f"  • {doc['file']} ({doc['security']['encryption_level']})")
        
        if form_pdfs:
            print(f"\n📋 PDFs with form fields: {len(form_pdfs)}")
            for doc in form_pdfs:
                print(f"  • {doc['file']} ({doc['forms']['field_count']} fields)")
        
        if xfa_pdfs:
            print(f"\n⚠️  PDFs with XFA forms (complex): {len(xfa_pdfs)}")
            for doc in xfa_pdfs:
                print(f"  • {doc['file']}")
        
        # Save results
        output_path = Path("outputs/pdf_technical_analysis.json")
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed analysis saved to: {output_path}")
        print("\n✅ Technical analysis complete!")
        
        return results


def main():
    """Run technical structure analysis"""
    analyzer = PDFTechnicalAnalyzer()
    results = analyzer.analyze_all_pdfs()
    return 0


if __name__ == "__main__":
    sys.exit(main())