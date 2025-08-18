#!/usr/bin/env python3
import asyncio
import json
from pathlib import Path

async def test_outputs():
    test_file = Path("inputs/real/Brigham_dallas/Brigham_Dallas_PFS.pdf")
    
    if not test_file.exists():
        print("Test file not found")
        return
    
    # Test Document AI
    print("=== Document AI Output ===")
    try:
        from src.extraction_methods.docai_general_processor import GeneralProcessorExtractor
        docai_extractor = GeneralProcessorExtractor()
        result = await docai_extractor.extract(test_file)
        print(json.dumps(result, indent=2, default=str)[:500] + "...")
    except Exception as e:
        print(f"DocAI error: {e}")
    
    # Test BenchmarkExtractor with just single file
    print("\n=== BenchmarkExtractor Output (single file) ===")
    try:
        from src.extraction_methods.multimodal_llm.providers.benchmark_extractor import BenchmarkExtractor
        benchmark_extractor = BenchmarkExtractor()
        result = await benchmark_extractor.extract_all(str(test_file))
        print("Type:", type(result))
        if isinstance(result, dict):
            print("Keys:", list(result.keys()))
            if "error" in result:
                print("Error:", result["error"])
            else:
                print(json.dumps(result, indent=2, default=str)[:500] + "...")
    except Exception as e:
        print(f"BenchmarkExtractor error: {e}")

if __name__ == "__main__":
    asyncio.run(test_outputs())
