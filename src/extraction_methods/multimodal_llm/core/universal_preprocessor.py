"""
Universal preprocessing for ANY document format.
No assumptions about layout, structure, or content.
Works with PDFs, Excel, images, handwritten notes, screenshots, etc.
"""

import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import json
import time
from dataclasses import dataclass
from PIL import Image, ImageOps, ImageEnhance
import io
import base64

try:
    from pdf2image import convert_from_path
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Excel processing moved to HybridExcelExtractor
# UniversalPreprocessor now rejects Excel files with clear error message


@dataclass
class ProcessedDocument:
    """Universal document representation after preprocessing."""
    images: List[Image.Image]
    document_type: str
    total_pages: int
    processing_time: float
    metadata: Dict[str, Any]


class UniversalPreprocessor:
    """
    Universal document preprocessor that works with ANY format.
    Only applies universally beneficial improvements.
    """
    
    def __init__(self):
        """Initialize with universal settings only."""
        # Universal quality settings
        self.min_resolution = 1024  # Minimum for text readability
        self.max_resolution = 1900  # Claude's limit for multi-image requests (2000px)
        self.quality_threshold = 0.1  # Auto-contrast cutoff
        
    def preprocess_any_document(self, file_path: Union[str, Path]) -> ProcessedDocument:
        """
        Preprocess any document format for Claude Vision API.
        
        Args:
            file_path: Path to any document (PDF, Excel, image, etc.)
            
        Returns:
            ProcessedDocument with universally optimized images
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        print(f"📄 Processing: {file_path.name}")
        
        # Convert any format to images
        raw_images = self._convert_to_images(file_path)
        
        # Apply universal quality improvements only
        processed_images = []
        for img in raw_images:
            enhanced = self._apply_universal_enhancements(img)
            processed_images.append(enhanced)
        
        processing_time = time.time() - start_time
        
        return ProcessedDocument(
            images=processed_images,
            document_type=file_path.suffix.lower(),
            total_pages=len(processed_images),
            processing_time=processing_time,
            metadata={
                'original_format': file_path.suffix,
                'file_size': file_path.stat().st_size if file_path.exists() else 0,
                'images_created': len(processed_images)
            }
        )
    
    def _convert_to_images(self, file_path: Path) -> List[Image.Image]:
        """Convert any file format to images."""
        
        extension = file_path.suffix.lower()
        
        if extension == '.pdf':
            return self._pdf_to_images(file_path)
        elif extension in ['.xlsx', '.xls']:
            # Excel files should use HybridExcelExtractor, not image conversion
            raise ValueError(
                f"Excel files should be processed with HybridExcelExtractor, not UniversalPreprocessor. "
                f"File: {file_path}"
            )
        elif extension in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            return [Image.open(file_path)]
        else:
            # Unknown format - try as image first
            print(f"Unknown format: {file_path.name} ({extension})")
            try:
                return [Image.open(file_path)]
            except Exception:
                # Create a text representation
                return self._text_file_to_image(file_path)
    
    def _pdf_to_images(self, pdf_path: Path) -> List[Image.Image]:
        """Convert PDF to images with universal settings."""
        
        if not PDF_AVAILABLE:
            raise ImportError("pdf2image required for PDF processing")
        
        # Universal PDF conversion - no format assumptions
        images = convert_from_path(
            str(pdf_path),
            dpi=150,  # Good balance of quality vs. speed
            fmt='PNG',  # Best for text preservation
            thread_count=2,
            first_page=1,
            last_page=10  # Reasonable limit for any document
        )
        
        return images
    
    
    def _text_file_to_image(self, file_path: Path) -> List[Image.Image]:
        """Convert text file to image as fallback."""
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()[:2000]  # Limit to first 2000 chars
            
            return [self._create_text_image(content, f"Content of {file_path.name}")]
            
        except Exception:
            return self._create_error_image(f"Could not process {file_path.name}")
    
    def _create_text_image(self, text: str, title: str = "") -> Image.Image:
        """Create image from text content."""
        
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.axis('off')
        
        if title:
            ax.text(0.5, 0.95, title, transform=ax.transAxes, 
                   fontsize=14, weight='bold', ha='center')
        
        # Wrap text
        import textwrap
        wrapped_text = textwrap.fill(text, width=80)
        
        ax.text(0.05, 0.85, wrapped_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=150, bbox_inches='tight',
                   facecolor='white')
        plt.close()
        
        buffer.seek(0)
        return Image.open(buffer)
    
    def _create_error_image(self, message: str) -> List[Image.Image]:
        """Create error message as image."""
        
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.axis('off')
        
        ax.text(0.5, 0.5, f"⚠️ {message}", transform=ax.transAxes,
               fontsize=12, ha='center', va='center',
               bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.5))
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='PNG', dpi=150, bbox_inches='tight',
                   facecolor='white')
        plt.close()
        
        buffer.seek(0)
        return [Image.open(buffer)]
    
    def _apply_universal_enhancements(self, image: Image.Image) -> Image.Image:
        """Apply only universally beneficial enhancements."""
        
        # Convert RGBA to RGB if needed (many PIL operations don't support RGBA)
        if image.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', image.size, (255, 255, 255))
            # Paste image using alpha channel as mask
            background.paste(image, mask=image.split()[3] if len(image.split()) > 3 else None)
            image = background
        
        # 1. Ensure minimum readable resolution
        if max(image.size) < self.min_resolution:
            scale = self.min_resolution / max(image.size)
            new_size = (int(image.width * scale), int(image.height * scale))
            image = image.resize(new_size, Image.LANCZOS)
        
        # 2. Normalize contrast (helps with any scan quality)
        image = ImageOps.autocontrast(image, cutoff=self.quality_threshold)
        
        # 3. Ensure it's not too large (token efficiency)
        if max(image.size) > self.max_resolution:
            original_dims = (image.width, image.height)
            scale = self.max_resolution / max(image.size)
            new_size = (int(image.width * scale), int(image.height * scale))
            
            print(f"    🔄 Resizing: {original_dims[0]}x{original_dims[1]} → {new_size[0]}x{new_size[1]} (max {self.max_resolution}px)")
            
            image = image.resize(new_size, Image.LANCZOS)
        elif max(image.size) > 1800:
            print(f"    ⚠️  Large image: {image.width}x{image.height} (approaching 2000px limit)")
        
        # 4. Slight sharpening if image looks blurry
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)  # Very mild sharpening
        
        return image
    
    def images_to_base64(self, images: List[Image.Image]) -> List[Dict[str, str]]:
        """Convert images to base64 for Claude API."""
        
        base64_images = []
        
        for i, img in enumerate(images):
            # Choose format based on content
            if self._is_text_heavy(img):
                format_type = 'PNG'
                media_type = 'image/png'
            else:
                format_type = 'JPEG'
                media_type = 'image/jpeg'
                
                # Convert RGBA to RGB for JPEG (JPEG doesn't support transparency)
                if img.mode == 'RGBA':
                    # Create white background
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    # Paste image using alpha channel as mask
                    background.paste(img, mask=img.split()[3] if len(img.split()) > 3 else None)
                    img = background
                elif img.mode not in ['RGB', 'L']:
                    # Convert other modes to RGB for JPEG
                    img = img.convert('RGB')
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format=format_type, quality=95 if format_type == 'JPEG' else None, optimize=True)
            base64_data = base64.b64encode(buffer.getvalue()).decode()
            
            base64_images.append({
                'data': base64_data,
                'media_type': media_type,
                'page_number': i + 1
            })
        
        return base64_images
    
    def _is_text_heavy(self, image: Image.Image) -> bool:
        """Determine if image is text-heavy (use PNG) or not (use JPEG)."""
        
        # Simple heuristic: convert to grayscale and check for sharp edges
        gray = image.convert('L')
        img_array = np.array(gray)
        
        # Calculate variation - text has high local variation
        try:
            # Simple edge detection without scipy
            edges_x = np.abs(np.diff(img_array, axis=1))
            edges_y = np.abs(np.diff(img_array, axis=0))
            edge_variance = np.var(edges_x) + np.var(edges_y)
            
            # Text documents typically have higher edge variance
            return edge_variance > 100
        except:
            # Fallback: assume text-heavy for safety
            return True


class SchemaHintBuilder:
    """
    Build extraction hints for any schema to help Claude map unpredictable documents.
    """
    
    def __init__(self):
        """Initialize with common financial field variations."""
        
        # Universal field name variations
        self.field_variations = {
            'first_name': [
                'first name', 'given name', 'name', 'applicant name', 
                'borrower name', 'customer name', 'account holder',
                'firstname', 'fname', 'forename'
            ],
            'last_name': [
                'last name', 'surname', 'family name', 'lastname', 
                'lname', 'name', 'applicant', 'borrower'
            ],
            'business_name': [
                'business name', 'company name', 'dba', 'doing business as',
                'entity name', 'organization', 'firm name', 'business',
                'company', 'corporation', 'llc', 'inc'
            ],
            'annual_revenue': [
                'annual revenue', 'yearly revenue', 'total revenue', 'gross revenue',
                'annual sales', 'yearly sales', 'gross sales', 'total sales',
                'annual income', 'yearly income', 'gross receipts',
                'revenue', 'sales', 'income'
            ],
            'total_assets': [
                'total assets', 'assets', 'total asset value', 'asset total',
                'net worth', 'total value', 'worth', 'assets total',
                'sum of assets', 'asset sum'
            ],
            'total_liabilities': [
                'total liabilities', 'liabilities', 'total debt', 'debt total',
                'total owed', 'liabilities total', 'sum of liabilities',
                'debt sum', 'total obligations'
            ],
            'net_worth': [
                'net worth', 'worth', 'equity', 'net equity', 'net value',
                'net assets', 'owner equity', 'shareholders equity'
            ],
            'phone': [
                'phone', 'phone number', 'telephone', 'mobile', 'cell',
                'contact number', 'business phone', 'work phone'
            ],
            'email': [
                'email', 'email address', 'e-mail', 'electronic mail',
                'contact email', 'business email'
            ],
            'address': [
                'address', 'street address', 'mailing address', 'business address',
                'location', 'street', 'physical address'
            ]
        }
    
    def build_hints_for_schema(self, schema: Dict[str, Any]) -> Dict[str, List[str]]:
        """Build extraction hints for a given schema."""
        
        hints = {}
        
        if 'properties' in schema:
            for field_name in schema['properties'].keys():
                # Get known variations or create generic ones
                if field_name in self.field_variations:
                    hints[field_name] = self.field_variations[field_name]
                else:
                    # Generate variations from field name
                    hints[field_name] = self._generate_variations(field_name)
        
        return hints
    
    def _generate_variations(self, field_name: str) -> List[str]:
        """Generate likely variations for an unknown field name."""
        
        variations = [field_name]
        
        # Add common transformations
        variations.append(field_name.replace('_', ' '))  # snake_case to spaces
        variations.append(field_name.replace('_', ''))   # remove underscores
        variations.append(field_name.title().replace('_', ' '))  # Title Case
        
        # Add common prefixes/suffixes
        base = field_name.replace('_', ' ')
        variations.extend([
            f'total {base}',
            f'{base} total',
            f'annual {base}',
            f'{base} amount',
            f'{base} value'
        ])
        
        return list(set(variations))  # Remove duplicates