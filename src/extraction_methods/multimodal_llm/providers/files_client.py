"""
Minimal Files API client for testing Anthropic's Files API.
THIS IS A TEST IMPLEMENTATION - TO BE REFINED FOR PRODUCTION
"""

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import base64

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class FilesAPIClient:
    """
    Minimal client for Anthropic Files API - TEST VERSION
    Handles file uploads, caching, and retrieval with deduplication.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Files API client with minimal setup."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package required: pip install anthropic")
        
        # Use provided key, then env var, then .env file
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError("No API key found")
        
        self.client = Anthropic(api_key=api_key)
        
        # Initialize cache
        self.cache_file = Path("outputs/file_cache.json")
        self.cache = self._load_cache()
        
        # Beta header for Files API
        self.headers = {
            "anthropic-beta": "files-api-2025-04-14"
        }
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load file cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_cache(self):
        """Save file cache to disk."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def upload_file(self, file_path: Path, force: bool = False) -> Optional[str]:
        """
        Upload file to Anthropic Files API with caching.
        Returns file_id or None if failed.
        
        THIS IS A SIMPLIFIED VERSION FOR TESTING
        TODO: Add proper retry logic, error handling for production
        """
        file_path = Path(file_path)
        if not file_path.exists():
            print(f"  ❌ File not found: {file_path}")
            return None
        
        # Compute hash for deduplication
        file_hash = self._compute_file_hash(file_path)
        
        # Check cache unless forced
        if not force and file_hash in self.cache:
            cached = self.cache[file_hash]
            print(f"  ♻️  Using cached file_id for {file_path.name}")
            return cached['file_id']
        
        # Determine MIME type
        ext = file_path.suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.txt': 'text/plain',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.xls': 'application/vnd.ms-excel'
        }
        mime_type = mime_types.get(ext, 'application/octet-stream')
        
        try:
            print(f"  📤 Uploading {file_path.name} ({file_path.stat().st_size / 1024:.1f}KB)...")
            
            # The Files API expects a file-like object or tuple (filename, content, mime_type)
            # Let's try passing it with proper metadata
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create a tuple with filename and content
            file_data = (file_path.name, file_content, mime_type)
            
            # Upload file using the actual Files API with beta header
            response = self.client.beta.files.upload(
                file=file_data,
                extra_headers=self.headers  # Includes anthropic-beta header
            )
            
            file_id = response.id
            
            # Cache the result
            self.cache[file_hash] = {
                'file_id': file_id,
                'name': file_path.name,
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'mime_type': mime_type,
                'hash': file_hash,
                'uploaded_at': time.time()
            }
            self._save_cache()
            
            print(f"  ✅ Uploaded successfully: {file_id}")
            return file_id
            
        except Exception as e:
            print(f"  ❌ Upload failed: {e}")
            # TODO: Add retry logic here for production
            return None
    
    def get_file_id_for_path(self, file_path: Path) -> Optional[str]:
        """Get cached file_id for a path without uploading."""
        file_hash = self._compute_file_hash(file_path)
        if file_hash in self.cache:
            return self.cache[file_hash]['file_id']
        return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete file from Anthropic storage.
        """
        try:
            # Use actual Files API delete with beta header
            self.client.beta.files.delete(
                file_id,
                extra_headers=self.headers
            )
            # Remove from cache
            for hash_key, cached in list(self.cache.items()):
                if cached['file_id'] == file_id:
                    del self.cache[hash_key]
            self._save_cache()
            return True
        except Exception as e:
            print(f"  ❌ Delete failed: {e}")
            return False
    
    def clear_old_files(self, days: int = 7):
        """
        Clear files older than specified days.
        TODO: Implement for production
        """
        current_time = time.time()
        cutoff_time = current_time - (days * 24 * 60 * 60)
        
        for hash_key, cached in list(self.cache.items()):
            if cached.get('uploaded_at', 0) < cutoff_time:
                if self.delete_file(cached['file_id']):
                    print(f"  🗑️  Deleted old file: {cached['name']}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the file cache."""
        total_size = sum(c.get('size', 0) for c in self.cache.values())
        return {
            'total_files': len(self.cache),
            'total_size_mb': total_size / (1024 * 1024),
            'cache_file': str(self.cache_file)
        }