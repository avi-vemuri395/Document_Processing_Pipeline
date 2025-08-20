#!/usr/bin/env python3
"""
Quick test to understand current processor initialization and routing
"""

import asyncio
from pathlib import Path
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_processor_initialization():
    """Test current processor initialization logic"""
    print("="*60)
    print("PROCESSOR INITIALIZATION TEST")
    print("="*60)
    
    try:
        # Import the BenchmarkExtractor
        from extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
        
        # Initialize with our API key
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ No API key found")
            return
            
        print("🔄 Initializing BenchmarkExtractor...")
        extractor = BenchmarkExtractor(api_key=api_key)
        
        # Check processor availability
        print(f"\n📊 PROCESSOR STATUS:")
        print(f"  • Form Parser available: {extractor.form_parser is not None}")
        print(f"  • General Processor available: {extractor.general_processor is not None}")
        
        if extractor.form_parser:
            print("  • Form Parser config:", extractor.form_parser.config)
        if extractor.general_processor:
            print("  • General Processor config:", extractor.general_processor.config)
            
        # Test file size analysis with a known large file
        test_file = Path("inputs/real/Brigham_dallas/Brigham_Dallas_2023_PTR.pdf")
        if test_file.exists():
            file_size_mb = test_file.stat().st_size / (1024 * 1024)
            print(f"\n📄 TEST FILE ANALYSIS:")
            print(f"  • File: {test_file.name}")
            print(f"  • Size: {file_size_mb:.2f} MB")
            
            # Estimate pages
            estimated_pages = int(file_size_mb * 10)  # Conservative estimate
            print(f"  • Estimated pages: {estimated_pages}")
            
            # Check which processor would be used
            print(f"\n🤖 ROUTING DECISION:")
            if extractor.form_parser:
                if file_size_mb <= 1.5:  # Form Parser limit
                    print("  • Would use: Form Parser")
                else:
                    print("  • Form Parser would reject (>1.5MB)")
            
            if extractor.general_processor:
                if file_size_mb <= 20:  # General Processor limit  
                    print("  • Could use: General Processor (but not initialized if Form Parser works)")
                else:
                    print("  • General Processor would reject (>20MB)")
                    
            print("  • Fallback: Claude Vision (expensive)")
            
        else:
            print(f"\n⚠️ Test file not found: {test_file}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_processor_initialization())