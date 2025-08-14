#!/usr/bin/env python3
"""
Comprehensive Extraction Test - Full Dataset Processing
Tests extraction performance on complete loan application packets.
Outputs detailed JSON and performance metrics.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import hashlib

from src.extraction_methods.multimodal_llm.providers import BenchmarkExtractor


class ComprehensiveExtractionTest:
    """Test extraction pipeline on full loan application datasets."""
    
    def __init__(self):
        self.extractor = BenchmarkExtractor()
        self.results = {
            "test_metadata": {
                "test_date": datetime.now().isoformat(),
                "test_version": "1.0.0",
                "pipeline": "BenchmarkExtractor"
            },
            "datasets": {}
        }
        
        # Rate limit configuration
        self.max_tokens_per_batch = 30000  # Conservative limit for Claude Sonnet
        self.max_images_per_batch = 20  # Limit images to avoid API errors
        self.base_wait_time = 3  # Base seconds between batches
        self.retry_attempts = 3
        self.backoff_factor = 2
    
    def get_file_hash(self, file_path: Path) -> str:
        """Generate hash for file to track processing."""
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:8]
    
    def get_all_files(self, directory: Path) -> List[Path]:
        """Recursively get all files from directory."""
        files = []
        for item in directory.rglob('*'):
            if item.is_file() and not item.name.startswith('.'):
                files.append(item)
        return sorted(files)
    
    def estimate_file_tokens(self, file_path: Path) -> int:
        """
        Estimate tokens for a file based on type and size.
        Optimized based on actual usage patterns.
        """
        ext = file_path.suffix.lower()
        size_mb = file_path.stat().st_size / (1024 * 1024)
        
        # Token estimates based on file type (calibrated from actual usage)
        if ext == '.pdf':
            # PDFs: Actual usage shows ~800 tokens per page for images
            # Rough estimate: 1 page ≈ 50KB
            pages = max(1, size_mb * 20)
            tokens = int(pages * 800)
        elif ext in ['.xlsx', '.xls', '.csv']:
            # Excel files: Reduced estimate based on actual image conversion
            # Small Excel files (<0.1MB) are typically 1-2 images
            if size_mb < 0.1:
                tokens = 2000  # 1-2 images max
            else:
                tokens = int(size_mb * 3000)
        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            # Images: fixed token cost for vision models
            tokens = 1000
        elif ext in ['.doc', '.docx']:
            # Word documents: typically convert to 1-2 images
            tokens = int(max(2000, size_mb * 2000))
        elif ext in ['.txt']:
            # Plain text
            tokens = int(size_mb * 1500)
        else:
            # Default estimate
            tokens = int(size_mb * 2000)
        
        # Smaller buffer (10% instead of 20%)
        return int(tokens * 1.1)
    
    def create_token_aware_batches(self, files: List[Path]) -> List[List[Path]]:
        """
        Group files into batches that respect token AND image count limits.
        Returns list of file batches.
        """
        batches = []
        current_batch = []
        current_tokens = 0
        current_estimated_images = 0
        
        # Sort files by estimated tokens (process smaller files first)
        files_with_tokens = [(f, self.estimate_file_tokens(f)) for f in files]
        files_with_tokens.sort(key=lambda x: x[1])
        
        for file_path, file_tokens in files_with_tokens:
            # Estimate image count for this file
            ext = file_path.suffix.lower()
            if ext == '.pdf':
                # PDFs are limited to 10 pages = ~10 images
                estimated_images = 10
            elif ext in ['.xlsx', '.xls']:
                # Excel files typically produce 1 image per sheet (max 5)
                estimated_images = 1
            else:
                # Other files (images, text) = 1 image
                estimated_images = 1
            
            # Check if adding this file would exceed limits
            would_exceed_tokens = current_tokens + file_tokens > self.max_tokens_per_batch
            would_exceed_images = current_estimated_images + estimated_images > self.max_images_per_batch
            
            if (would_exceed_tokens or would_exceed_images) and current_batch:
                # Save current batch and start new one
                batches.append(current_batch)
                current_batch = [file_path]
                current_tokens = file_tokens
                current_estimated_images = estimated_images
            else:
                # Add to current batch
                current_batch.append(file_path)
                current_tokens += file_tokens
                current_estimated_images += estimated_images
        
        # Add final batch
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    async def extract_dataset(self, dataset_name: str, dataset_path: Path) -> Dict[str, Any]:
        """Extract all documents from a dataset."""
        print(f"\n{'='*70}")
        print(f"📂 EXTRACTING: {dataset_name}")
        print(f"{'='*70}")
        
        # Create output directory with dataset name and timestamp (minute precision)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        dataset_clean = dataset_name.replace(' ', '_')
        run_output_dir = Path(f"outputs/extracted_data/{dataset_clean}_{timestamp}")
        run_output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory: {run_output_dir}")
        
        # Get all files
        all_files = self.get_all_files(dataset_path)
        print(f"\n📊 Dataset Statistics:")
        print(f"   Total files: {len(all_files)}")
        
        # Categorize files
        file_categories = {
            "pdf": [],
            "excel": [],
            "image": [],
            "text": [],
            "other": []
        }
        
        for file in all_files:
            ext = file.suffix.lower()
            if ext == '.pdf':
                file_categories["pdf"].append(file)
            elif ext in ['.xlsx', '.xls', '.csv']:
                file_categories["excel"].append(file)
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
                file_categories["image"].append(file)
            elif ext in ['.txt', '.doc', '.docx']:
                file_categories["text"].append(file)
            else:
                file_categories["other"].append(file)
        
        # Print file breakdown
        print(f"\n📁 File Types:")
        for category, files in file_categories.items():
            if files:
                print(f"   {category.upper()}: {len(files)} files")
                for f in files[:3]:  # Show first 3 files
                    print(f"      • {f.name}")
                if len(files) > 3:
                    print(f"      ... and {len(files)-3} more")
        
        # Create token-aware batches
        batches = self.create_token_aware_batches(all_files)
        all_extractions = []
        failed_files = []
        
        print(f"\n🔄 Processing {len(all_files)} files in {len(batches)} token-aware batches")
        print(f"   Max tokens per batch: {self.max_tokens_per_batch:,}")
        
        for batch_idx, batch in enumerate(batches, 1):
            batch_names = [f.name for f in batch]
            batch_tokens = sum(self.estimate_file_tokens(f) for f in batch)
            
            print(f"\n📦 Batch {batch_idx}/{len(batches)} (~{batch_tokens:,} tokens):")
            for name in batch_names:
                file_path = next(f for f in batch if f.name == name)
                tokens = self.estimate_file_tokens(file_path)
                print(f"   • {name} (~{tokens:,} tokens)")
            
            # Retry logic with exponential backoff
            for attempt in range(self.retry_attempts):
                try:
                    start_time = time.time()
                    
                    # Extract batch
                    batch_result = await self.extractor.extract_all(batch)
                    
                    # Check if extraction actually failed
                    if batch_result.get("_extraction_failed"):
                        print(f"   ⚠️ EXTRACTION FAILED: {batch_result.get('error', 'Unknown error')[:100]}")
                        extraction_status = "failed"
                    else:
                        extraction_status = "success"
                    
                    # Record extraction
                    extraction_record = {
                        "batch_number": batch_idx,
                        "files": batch_names,
                        "file_hashes": {f.name: self.get_file_hash(f) for f in batch},
                        "extraction_time": time.time() - start_time,
                        "estimated_tokens": batch_tokens,
                        "extraction_status": extraction_status,
                        "data": batch_result
                    }
                    all_extractions.append(extraction_record)
                    
                    # Save individual batch extraction (with document count in filename)
                    doc_count = len(batch)
                    batch_output = run_output_dir / f"batch_{batch_idx:02d}_{doc_count}docs.json"
                    with open(batch_output, 'w') as f:
                        json.dump(extraction_record, f, indent=2, default=str)
                    
                    if extraction_status == "success":
                        print(f"   ✅ Extracted in {extraction_record['extraction_time']:.2f}s")
                    else:
                        print(f"   ❌ Failed in {extraction_record['extraction_time']:.2f}s")
                    print(f"   💾 Saved batch to: {batch_output.name}")
                    
                    # Rate limit protection - wait between batches
                    if batch_idx < len(batches):
                        # Adjust wait time based on batch size
                        wait_time = self.base_wait_time + (batch_tokens / 10000)  # Extra second per 10k tokens
                        wait_time = min(wait_time, 10)  # Cap at 10 seconds
                        print(f"   ⏳ Waiting {wait_time:.1f}s before next batch...")
                        await asyncio.sleep(wait_time)
                    
                    break  # Success, exit retry loop
                    
                except Exception as e:
                    error_msg = str(e)
                    is_rate_limit = "429" in error_msg or "rate" in error_msg.lower()
                    
                    if attempt < self.retry_attempts - 1:
                        # Calculate backoff time
                        if is_rate_limit:
                            # For rate limits, use longer backoff
                            wait_time = self.base_wait_time * (self.backoff_factor ** (attempt + 1))
                            print(f"   ⚠️ Rate limit hit (attempt {attempt + 1}/{self.retry_attempts})")
                        else:
                            # For other errors, use shorter backoff
                            wait_time = self.base_wait_time * (self.backoff_factor ** attempt)
                            print(f"   ⚠️ Error: {error_msg[:100]} (attempt {attempt + 1}/{self.retry_attempts})")
                        
                        print(f"   ⏳ Waiting {wait_time:.1f}s before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        # Final attempt failed
                        print(f"   ❌ Batch failed after {self.retry_attempts} attempts: {error_msg[:200]}")
                        failed_files.extend(batch_names)
        
        # Merge all extractions with incremental saves
        print(f"\n🔀 Merging {len(all_extractions)} batch extractions...")
        incremental_dir = run_output_dir / "merges"
        incremental_dir.mkdir(exist_ok=True)
        merged_data = self.merge_extractions(all_extractions, save_incrementals=incremental_dir)
        
        # Save final merged data
        merged_output = run_output_dir / "merged_data.json"
        with open(merged_output, 'w') as f:
            json.dump(merged_data, f, indent=2, default=str)
        print(f"   💾 Saved merged data to: {merged_output.name}")
        print(f"   📂 Incremental merges in: {incremental_dir.name}/")
        
        # Calculate metrics
        total_time = sum(e['extraction_time'] for e in all_extractions)
        total_images = sum(
            e['data'].get('_metadata', {}).get('total_images', 0) 
            for e in all_extractions
        )
        total_tokens = sum(e.get('estimated_tokens', 0) for e in all_extractions)
        
        # Compile results
        dataset_result = {
            "dataset_name": dataset_name,
            "dataset_path": str(dataset_path),
            "statistics": {
                "total_files": len(all_files),
                "processed_files": len(all_files) - len(failed_files),
                "failed_files": failed_files,
                "total_extraction_time": total_time,
                "total_images_processed": total_images,
                "total_estimated_tokens": total_tokens,
                "average_time_per_file": total_time / max(1, len(all_files) - len(failed_files)),
                "average_tokens_per_batch": total_tokens / max(1, len(all_extractions)),
                "total_batches": len(batches),
                "successful_batches": len(all_extractions),
                "file_categories": {k: len(v) for k, v in file_categories.items() if v}
            },
            "extracted_data": merged_data,
            "extraction_history": all_extractions,
            "output_directory": str(run_output_dir)
        }
        
        # Save complete dataset result in the run directory
        final_output = run_output_dir / "complete_result.json"
        with open(final_output, 'w') as f:
            json.dump(dataset_result, f, indent=2, default=str)
        print(f"\n💾 Complete dataset saved to: {final_output}")
        
        return dataset_result
    
    def deep_merge_dict(self, target: Dict, source: Dict) -> Dict:
        """
        Deep merge source dict into target dict.
        Prefers non-null and non-empty values.
        """
        for key, value in source.items():
            if key not in target:
                target[key] = value
            elif isinstance(value, dict) and isinstance(target[key], dict):
                # Recursively merge nested dicts
                target[key] = self.deep_merge_dict(target[key], value)
            elif isinstance(value, list) and isinstance(target[key], list):
                # Combine lists and deduplicate
                combined = target[key] + value
                # Simple deduplication for dicts in lists based on string representation
                seen = set()
                deduped = []
                for item in combined:
                    item_str = str(item)
                    if item_str not in seen:
                        seen.add(item_str)
                        deduped.append(item)
                target[key] = deduped
            elif value is not None and value != "" and value != {}:
                # Prefer non-empty values
                if target[key] is None or target[key] == "" or target[key] == {}:
                    target[key] = value
        return target
    
    def merge_extractions(self, extractions: List[Dict], save_incrementals: Path = None) -> Dict[str, Any]:
        """
        Merge multiple extraction batches into single JSON.
        Uses deep merging to preserve all data.
        Optionally saves incremental merge states.
        """
        merged = {
            "personal": {},
            "business": {},
            "financials": {},
            "documents_metadata": [],
            "extraction_sources": {}  # Track which file provided which data
        }
        
        for idx, extraction in enumerate(extractions, 1):
            data = extraction.get('data', {})
            batch_files = extraction.get('files', [])
            
            # Deep merge personal information
            if 'personal' in data and data['personal']:
                merged['personal'] = self.deep_merge_dict(merged['personal'], data['personal'])
                # Track source
                for file in batch_files:
                    if 'personal' in data['personal'] or 'PFS' in file or 'Personal' in file:
                        merged['extraction_sources']['personal'] = merged['extraction_sources'].get('personal', [])
                        merged['extraction_sources']['personal'].append(file)
            
            # Deep merge business information
            if 'business' in data and data['business']:
                merged['business'] = self.deep_merge_dict(merged['business'], data['business'])
                # Track source
                for file in batch_files:
                    if 'business' in str(data.get('business', {})).lower() or 'LLC' in file or 'Corp' in file:
                        merged['extraction_sources']['business'] = merged['extraction_sources'].get('business', [])
                        merged['extraction_sources']['business'].append(file)
            
            # Deep merge financials (handles new nested structure)
            if 'financials' in data and data['financials']:
                merged['financials'] = self.deep_merge_dict(merged['financials'], data['financials'])
                # Track source for financial data
                for file in batch_files:
                    if any(keyword in file.lower() for keyword in ['financial', 'balance', 'income', 'p&l', 'pfs', 'tax']):
                        merged['extraction_sources']['financials'] = merged['extraction_sources'].get('financials', [])
                        merged['extraction_sources']['financials'].append(file)
            
            # Track document metadata
            merged['documents_metadata'].append({
                "batch": extraction['batch_number'],
                "files": extraction['files'],
                "processing_time": extraction['extraction_time'],
                "estimated_tokens": extraction.get('estimated_tokens', 0)
            })
            
            # Save incremental merge state if requested
            if save_incrementals:
                # This is cumulative data after merging N batches
                incremental_file = save_incrementals / f"cumulative_after_{idx:02d}_batches.json"
                with open(incremental_file, 'w') as f:
                    json.dump(merged, f, indent=2, default=str)
        
        return merged
    
    async def run_comprehensive_test(self):
        """Run extraction test on all datasets."""
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE EXTRACTION TEST")
        print("="*70)
        
        # Dataset paths
        datasets = [
            ("Brigham Dallas", Path("inputs/real/Brigham_dallas")),
            ("Dave Burlington", Path("inputs/real/Dave Burlington - Application Packet"))
        ]
        
        overall_start = time.time()
        
        for dataset_name, dataset_path in datasets:
            if dataset_path.exists():
                try:
                    result = await self.extract_dataset(dataset_name, dataset_path)
                    self.results["datasets"][dataset_name] = result
                    
                    # Dataset result already saved in run directory
                    # Just print the location
                    print(f"\n✅ All outputs saved in: {result['output_directory']}")
                    
                except Exception as e:
                    print(f"\n❌ Failed to process {dataset_name}: {e}")
                    self.results["datasets"][dataset_name] = {"error": str(e)}
            else:
                print(f"\n⚠️ Dataset not found: {dataset_path}")
        
        # Calculate overall metrics
        total_time = time.time() - overall_start
        self.results["test_metadata"]["total_test_time"] = total_time
        
        # Save comprehensive summary with all runs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        summary_file = Path(f"outputs/extracted_data/summary_{timestamp}.json")
        with open(summary_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n📊 Saved run summary to: {summary_file}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("📊 EXTRACTION TEST SUMMARY")
        print("="*70)
        
        for dataset_name, result in self.results["datasets"].items():
            if "error" not in result:
                stats = result["statistics"]
                print(f"\n📁 {dataset_name}:")
                print(f"   Files Processed: {stats['processed_files']}/{stats['total_files']}")
                print(f"   Batches: {stats['successful_batches']}/{stats['total_batches']}")
                print(f"   Total Time: {stats['total_extraction_time']:.2f}s")
                print(f"   Avg Time/File: {stats['average_time_per_file']:.2f}s")
                print(f"   Images Processed: {stats['total_images_processed']}")
                print(f"   Est. Tokens Used: {stats['total_estimated_tokens']:,}")
                print(f"   Avg Tokens/Batch: {stats['average_tokens_per_batch']:,.0f}")
                
                # Show extracted data summary
                extracted = result["extracted_data"]
                if extracted.get("personal"):
                    print(f"   ✓ Personal Info Extracted")
                if extracted.get("business"):
                    print(f"   ✓ Business Info Extracted")
                if extracted.get("financials"):
                    fin = extracted["financials"]
                    if fin.get("assets"):
                        print(f"   ✓ Financial Assets Extracted")
                    if fin.get("liabilities"):
                        print(f"   ✓ Financial Liabilities Extracted")
            else:
                print(f"\n📁 {dataset_name}: ❌ FAILED")
        
        print(f"\n⏱️ Total Test Time: {self.results['test_metadata']['total_test_time']:.2f}s")
        print("\n" + "="*70)
        print("✅ TEST COMPLETE")
        print("="*70)


async def main():
    """Run the comprehensive extraction test."""
    test = ComprehensiveExtractionTest()
    await test.run_comprehensive_test()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║        COMPREHENSIVE EXTRACTION PIPELINE TEST v2.0               ║
║                                                                  ║
║  This test will:                                                ║
║  1. Process ALL files in both loan application datasets         ║
║  2. Use token-aware batching to avoid rate limits              ║
║  3. Extract data using the BenchmarkExtractor                   ║
║  4. Merge results into comprehensive JSON                       ║
║  5. Provide detailed performance and token metrics              ║
║  6. Save results for S3 upload simulation                       ║
║                                                                  ║
║  Datasets:                                                      ║
║  • Brigham Dallas (19 files)                                    ║
║  • Dave Burlington (16 files)                                   ║
║                                                                  ║
║  Rate Limit Protection:                                         ║
║  • Dynamic batching based on token estimates                    ║
║  • Exponential backoff on errors                               ║
║  • Automatic retry with rate limit detection                    ║
║                                                                  ║
║  ⚠️  This will make multiple API calls to Claude                ║
║  ⚠️  Estimated time: 4-6 minutes (with safety delays)           ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    # Run the test
    asyncio.run(main())