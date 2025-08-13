#!/usr/bin/env python3
"""
Quick script to check if .env file is properly configured.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

def check_env():
    """Check environment configuration."""
    print("🔍 Checking Environment Configuration\n")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path(".env")
    if env_file.exists():
        print("✅ .env file found")
    else:
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        return False
    
    # Check API keys
    print("\n📝 API Keys:")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic_key and anthropic_key != "" and "your-" not in anthropic_key.lower():
        print(f"✅ ANTHROPIC_API_KEY configured (ends with ...{anthropic_key[-4:]})")
    else:
        print("❌ ANTHROPIC_API_KEY not configured")
        print("   Add your key to .env file")
    
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key and openai_key != "" and "your-" not in openai_key.lower():
        print(f"✅ OPENAI_API_KEY configured (ends with ...{openai_key[-4:]})")
    else:
        print("⚠️  OPENAI_API_KEY not configured (optional)")
    
    # Check other settings
    print("\n⚙️  Configuration Settings:")
    
    settings = {
        "CLAUDE_MODEL": os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
        "CONFIDENCE_THRESHOLD": os.getenv("CONFIDENCE_THRESHOLD", "0.85"),
        "MAX_RETRIES": os.getenv("MAX_RETRIES", "3"),
        "REQUEST_TIMEOUT": os.getenv("REQUEST_TIMEOUT", "120"),
    }
    
    for key, value in settings.items():
        print(f"   {key}: {value}")
    
    # Test import
    print("\n📦 Package Dependencies:")
    
    try:
        import anthropic
        print("✅ anthropic package installed")
    except ImportError:
        print("❌ anthropic package not installed")
        print("   Run: pip install anthropic")
    
    try:
        import pydantic
        print("✅ pydantic package installed")
    except ImportError:
        print("❌ pydantic package not installed")
        print("   Run: pip install pydantic")
    
    try:
        import dotenv
        print("✅ python-dotenv package installed")
    except ImportError:
        print("❌ python-dotenv package not installed")
        print("   Run: pip install python-dotenv")
    
    print("\n" + "=" * 50)
    
    # Overall status
    if anthropic_key and anthropic_key != "" and "your-" not in anthropic_key.lower():
        print("\n✅ Environment is configured and ready!")
        print("   You can now run: python3 test_multimodal_extraction.py")
        return True
    else:
        print("\n⚠️  Environment needs configuration")
        print("   Please add your ANTHROPIC_API_KEY to the .env file")
        return False

if __name__ == "__main__":
    check_env()