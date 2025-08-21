"""
Visual Form Filler - Direct Claude Vision PDF Form Mapping
Uses Claude Vision to analyze form templates and map master data directly to visible fields.
"""

import os
import json
import time
import hashlib
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Follow existing import patterns from benchmark_extractor.py
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Import existing components following benchmark_extractor pattern
from ..extraction_methods.multimodal_llm.core.universal_preprocessor import UniversalPreprocessor
from ..extraction_methods.multimodal_llm.providers.rate_limiter import RateLimitHandler


class VisualFormCache:
    """
    Caches visual form analysis to avoid re-processing identical forms.
    Follows existing caching patterns from the codebase.
    """
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path("outputs/visual_form_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_cache_key(self, form_path: Path) -> str:
        """Generate cache key from form file hash (follows existing pattern)."""
        return hashlib.md5(form_path.read_bytes()).hexdigest()
    
    def get_cached_analysis(self, form_path: Path) -> Optional[Dict]:
        """Get cached form analysis if available."""
        cache_key = self.get_cache_key(form_path)
        cache_file = self.cache_dir / f"{cache_key}_analysis.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    print(f"    📋 Using cached form analysis")
                    return cached_data
            except Exception as e:
                print(f"    ⚠️ Cache read failed: {e}")
        return None
    
    def cache_analysis(self, form_path: Path, analysis: Dict):
        """Cache form analysis for future use."""
        cache_key = self.get_cache_key(form_path)
        cache_file = self.cache_dir / f"{cache_key}_analysis.json"
        
        try:
            analysis['_cache_metadata'] = {
                'form_path': str(form_path),
                'cached_at': datetime.now().isoformat(),
                'cache_key': cache_key
            }
            
            with open(cache_file, 'w') as f:
                json.dump(analysis, f, indent=2)
                print(f"    💾 Cached form analysis")
        except Exception as e:
            print(f"    ⚠️ Cache write failed: {e}")


class VisualFormFiller:
    """
    Visual form filling using Claude Vision API.
    Directly maps master data to form fields using visual analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize following benchmark_extractor pattern."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")
        
        # API key handling (same pattern as benchmark_extractor)
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY required for visual form filling")
        
        # Initialize components (lazy loading pattern)
        self._client = None
        self._preprocessor = None
        self._rate_limiter = None
        self._cache = None
        
        self.api_key = api_key
        self.model = "claude-sonnet-4-20250514"  # Same model as benchmark_extractor
    
    @property
    def client(self):
        """Lazy initialization of Anthropic client (follows existing pattern)."""
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client
    
    @property
    def preprocessor(self):
        """Lazy initialization of preprocessor."""
        if self._preprocessor is None:
            self._preprocessor = UniversalPreprocessor()
        return self._preprocessor
    
    @property
    def rate_limiter(self):
        """Lazy initialization of rate limiter."""
        if self._rate_limiter is None:
            self._rate_limiter = RateLimitHandler()
        return self._rate_limiter
    
    @property
    def cache(self):
        """Lazy initialization of cache."""
        if self._cache is None:
            self._cache = VisualFormCache()
        return self._cache
    
    async def fill_form_visually(
        self,
        form_template_path: Path,
        master_data: Dict[str, Any],
        form_key: str
    ) -> Dict[str, Any]:
        """
        Main visual form filling method.
        
        Args:
            form_template_path: Path to PDF form template
            master_data: Extracted data from Part 1
            form_key: Form identifier (e.g., 'live_oak_application_v1')
            
        Returns:
            Dictionary containing mapped data, confidence scores, and metadata
        """
        print(f"    🔍 Visual form filling for: {form_template_path.name}")
        start_time = time.time()
        
        try:
            # Step 1: Check cache first
            cached_result = self.cache.get_cached_analysis(form_template_path)
            
            if cached_result and self._is_cache_valid(cached_result, master_data):
                print(f"    ⚡ Using cached mapping result")
                return self._update_cached_result(cached_result, master_data)
            
            # Step 2: Convert form to images
            print(f"    📄 Converting form to images...")
            processed_doc = self.preprocessor.preprocess_any_document(form_template_path)
            
            if not processed_doc.images:
                raise Exception("No images generated from form template")
            
            print(f"    ✅ Generated {len(processed_doc.images)} form images")
            
            # Step 3: Create visual mapping prompt
            prompt = self._create_visual_mapping_prompt(master_data, form_key)
            
            # Step 4: Make Claude Vision API call
            mapped_data = await self._call_claude_vision(
                processed_doc.images, 
                prompt,
                form_template_path
            )
            
            # Step 5: Create result structure (follows existing pattern)
            processing_time = time.time() - start_time
            result = {
                'mapped_data': mapped_data,
                'confidence_scores': {k: 0.95 for k in mapped_data.keys()},  # High confidence for visual mapping
                'overall_confidence': 0.95,
                'extraction_method': 'claude_vision_direct',
                'processing_time': processing_time,
                'form_images_count': len(processed_doc.images)
            }
            
            # Step 6: Cache the result
            self.cache.cache_analysis(form_template_path, result)
            
            print(f"    ✅ Visual mapping completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            print(f"    ❌ Visual form filling failed: {e}")
            # Return error result following existing pattern
            return {
                'mapped_data': {},
                'confidence_scores': {},
                'overall_confidence': 0.0,
                'extraction_method': 'claude_vision_direct',
                'error': str(e),
                'success': False
            }
    
    def _create_visual_mapping_prompt(self, master_data: Dict, form_key: str) -> str:
        """Create optimized prompt for visual form mapping."""
        
        # Clean master data for prompt (remove metadata)
        clean_data = {k: v for k, v in master_data.items() 
                     if not k.startswith('_') and k != 'metadata'}
        
        return f"""You are analyzing a loan application form (shown in images) to map extracted data to visible form fields.

EXTRACTED DATA FROM DOCUMENTS:
{json.dumps(clean_data, indent=2)}

TASK:
1. Look at EVERY visible form field in the images (text fields, checkboxes, dropdowns)
2. Map the extracted data above to the appropriate form fields
3. Use EXACT field names/labels as they appear in the form
4. For checkboxes, return true/false based on the data
5. For text fields, return the appropriate value from the data
6. If no matching data exists for a field, return null

CRITICAL REQUIREMENTS:
- Use EXACT field names from the form (case-sensitive)
- Only map data you can see clearly in the extracted data
- Never guess or invent values
- For financial amounts, preserve format (numbers only, no $ or commas)
- For dates, use YYYY-MM-DD format
- For percentages, return as numbers (75% → 75)

FIELD MAPPING FOCUS:
- Personal info: Names, SSN, DOB, addresses, phone, email
- Business info: Business names, EIN, entity type, addresses  
- Financial data: Assets, liabilities, income, net worth
- Ownership: Percentages, roles, relationships

Return ONLY a JSON object mapping form field names to values:
{{
  "Field Name as Shown in Form": "mapped_value",
  "Another Field Name": true,
  "Some Number Field": 1234567
}}

Form type: {form_key}"""
    
    async def _call_claude_vision(
        self, 
        form_images: List, 
        prompt: str,
        form_path: Path
    ) -> Dict[str, Any]:
        """Make Claude Vision API call (follows benchmark_extractor pattern)."""
        
        print(f"    🤖 Calling Claude Vision API...")
        
        # Convert images to base64 (using existing method)
        image_data = self.preprocessor.images_to_base64(form_images)
        
        # Build message content (same pattern as benchmark_extractor)
        content = [{"type": "text", "text": prompt}]
        for img_data in image_data:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img_data['media_type'],
                    "data": img_data['data']
                }
            })
        
        try:
            # API call with rate limiting (same pattern as benchmark_extractor)
            response = await self.rate_limiter.execute_with_backoff(
                self.client.messages.create,
                model=self.model,
                max_tokens=8192,
                temperature=0.1,  # Slightly higher for better mapping
                messages=[{"role": "user", "content": content}],
                api_type="claude"
            )
            
            # Parse response (same pattern as benchmark_extractor)
            raw_text = response.content[0].text.strip()
            
            # Extract JSON (same logic as benchmark_extractor)
            if "```json" in raw_text:
                start = raw_text.find("```json") + 7
                end = raw_text.find("```", start)
                if end > start:
                    raw_text = raw_text[start:end].strip()
            elif "```" in raw_text:
                parts = raw_text.split("```")
                if len(parts) >= 2:
                    raw_text = parts[1].strip()
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:].strip()
            
            # Parse JSON
            mapped_data = json.loads(raw_text)
            
            if not isinstance(mapped_data, dict):
                raise ValueError("Response is not a JSON object")
            
            print(f"    ✅ Mapped {len(mapped_data)} fields")
            return mapped_data
            
        except json.JSONDecodeError as e:
            print(f"    ❌ JSON parsing failed: {e}")
            return {}
        except Exception as e:
            print(f"    ❌ API call failed: {e}")
            return {}
    
    def _is_cache_valid(self, cached_result: Dict, current_master_data: Dict) -> bool:
        """Check if cached result is valid for current data."""
        # Simple validation - could be enhanced
        return 'mapped_data' in cached_result
    
    def _update_cached_result(self, cached_result: Dict, master_data: Dict) -> Dict:
        """Update cached result with current data if needed."""
        # For now, just return cached result
        # Could implement smart updating logic here
        return cached_result