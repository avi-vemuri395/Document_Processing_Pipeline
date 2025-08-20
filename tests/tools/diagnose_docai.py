#!/usr/bin/env python3
"""Diagnose why DocAI isn't working in comprehensive test"""

import sys
import os
from pathlib import Path

print("="*70)
print("DOCAI DIAGNOSTIC")
print("="*70)

# 1. Check Python path
print("\n1. Python Path:")
print(f"   Working directory: {os.getcwd()}")
print(f"   Python executable: {sys.executable}")
print(f"   Python version: {sys.version}")

# 2. Check if Google Cloud libraries are available
print("\n2. Google Cloud Libraries:")
try:
    import google.cloud.documentai
    print(f"   ✅ google.cloud.documentai version: {google.cloud.documentai.__version__}")
except ImportError as e:
    print(f"   ❌ google.cloud.documentai not available: {e}")

try:
    import google.auth
    print(f"   ✅ google.auth available")
except ImportError as e:
    print(f"   ❌ google.auth not available: {e}")

# 3. Check environment variables
print("\n3. Environment Variables:")
from dotenv import load_dotenv
load_dotenv()

print(f"   GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'NOT SET')}")
print(f"   DOCAI_FORM_PARSER_ID: {os.getenv('DOCAI_FORM_PARSER_ID', 'NOT SET')}")

# 4. Try DocAI imports
print("\n4. DocAI Module Imports:")
try:
    from src.config.docai_config import is_form_parser_configured
    print(f"   ✅ docai_config imported successfully")
    print(f"   Form parser configured: {is_form_parser_configured()}")
except ImportError as e:
    print(f"   ❌ Failed to import docai_config: {e}")

try:
    from src.extraction_methods.docai_form_parser import FormParserExtractor
    print(f"   ✅ FormParserExtractor imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import FormParserExtractor: {e}")

# 5. Try creating FormParserExtractor
print("\n5. FormParserExtractor Initialization:")
try:
    from src.extraction_methods.docai_form_parser import FormParserExtractor
    extractor = FormParserExtractor()
    print(f"   ✅ FormParserExtractor created successfully")
    print(f"   Client initialized: {extractor.client is not None}")
    print(f"   Processor name: {extractor.processor_name}")
except Exception as e:
    print(f"   ❌ Failed to create FormParserExtractor: {e}")
    import traceback
    traceback.print_exc()

# 6. Try creating BenchmarkExtractor
print("\n6. BenchmarkExtractor Initialization:")
try:
    from src.extraction_methods.multimodal_llm.providers import BenchmarkExtractor
    extractor = BenchmarkExtractor()
    print(f"   ✅ BenchmarkExtractor created successfully")
    print(f"   Form parser: {extractor.form_parser is not None}")
    print(f"   General processor: {extractor.general_processor is not None}")
except Exception as e:
    print(f"   ❌ Failed to create BenchmarkExtractor: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)