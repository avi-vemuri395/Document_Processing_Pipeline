#!/usr/bin/env python3
"""
Simple test to check DocAI configuration
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_docai_config():
    """Test DocAI configuration directly"""
    print("="*60)
    print("DOCAI CONFIGURATION TEST")
    print("="*60)
    
    # Check environment variables
    print("📊 ENVIRONMENT VARIABLES:")
    print(f"  • GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT', 'Not set')}")
    print(f"  • DOCAI_FORM_PARSER_ID: {os.getenv('DOCAI_FORM_PARSER_ID', 'Not set')}")
    print(f"  • DOCAI_GENERAL_PROCESSOR_ID: {os.getenv('DOCAI_GENERAL_PROCESSOR_ID', 'Not set')}")
    
    # Try to import config module directly
    try:
        from src.config.docai_config import (
            is_form_parser_configured, 
            is_general_processor_configured,
            DOCAI_CONFIG
        )
        
        print(f"\n🔧 CONFIGURATION STATUS:")
        print(f"  • Form Parser configured: {is_form_parser_configured()}")
        print(f"  • General Processor configured: {is_general_processor_configured()}")
        
        print(f"\n📋 DOCAI CONFIG:")
        for processor_type, config in DOCAI_CONFIG["processors"].items():
            print(f"  • {processor_type}:")
            print(f"    - ID: {config.get('id', 'Not set')}")
            print(f"    - Enabled: {config.get('enabled', False)}")
            print(f"    - Max file size: {config.get('max_file_size_mb', 'N/A')} MB")
        
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_docai_config()