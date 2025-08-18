#!/usr/bin/env python3
import asyncio
import json
from pathlib import Path

async def compare_formats():
    # Test Document AI format
    print("=== Document AI Format ===")
    try:
        from src.extraction_methods.docai_general_processor import GeneralProcessorExtractor
        docai_extractor = GeneralProcessorExtractor()
        test_file = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
        
        if test_file.exists():
            result = await docai_extractor.extract(test_file)
            print("Keys:", list(result.keys()))
            print("Success:", result.get('success'))
            print("Text length:", len(result.get('text', '')))
            print("Entities count:", len(result.get('entities', [])))
            print("Tables count:", len(result.get('tables', [])))
        else:
            print("Test file not found")
    except Exception as e:
        print(f"DocAI error: {e}")
    
    print("\n=== BenchmarkExtractor Format ===")
    try:
        from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
        benchmark_extractor = BenchmarkExtractor()
        
        if test_file.exists():
            result = await benchmark_extractor.extract_all([str(test_file)])
            print("Keys:", list(result.keys()))
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, dict):
                        print(f"{key}: {list(value.keys())}")
                    else:
                        print(f"{key}: {type(value)} - {len(str(value))} chars")
        else:
            print("Test file not found")
    except Exception as e:
        print(f"BenchmarkExtractor error: {e}")

if __name__ == "__main__":
    asyncio.run(compare_formats())
