#!/usr/bin/env python3
"""
Test OpenAI library availability and basic functionality
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_openai_import():
    print("🔍 Testing OpenAI library availability...")
    
    try:
        import openai
        print("✅ OpenAI library imported successfully")
        print(f"   OpenAI version: {openai.__version__}")
        return True
    except ImportError as e:
        print(f"❌ OpenAI import failed: {e}")
        return False

def test_openai_client():
    print("\n🔧 Testing OpenAI client initialization...")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ OPENAI_API_KEY not set in environment")
        print("   Add your OpenAI API key to .env file:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        return False
    
    if api_key.startswith("sk-your-") or len(api_key) < 20:
        print("⚠️ OPENAI_API_KEY appears to be placeholder")
        print("   Replace with your actual OpenAI API key")
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized successfully")
        print(f"   API key: {api_key[:7]}...{api_key[-4:]} (masked)")
        return True
    except Exception as e:
        print(f"❌ OpenAI client initialization failed: {e}")
        return False

def test_schema_mapper_availability():
    print("\n📋 Testing schema-driven components...")
    
    try:
        from src.schema_driven.openai_form_mapper import OpenAIFormMapper, OPENAI_AVAILABLE
        print(f"✅ OpenAIFormMapper imported successfully")
        print(f"   OPENAI_AVAILABLE flag: {OPENAI_AVAILABLE}")
        return True
    except ImportError as e:
        print(f"❌ Schema-driven components import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 OPENAI AVAILABILITY TEST")
    print("=" * 50)
    
    # Test 1: Library import
    import_ok = test_openai_import()
    
    # Test 2: Client initialization  
    client_ok = test_openai_client()
    
    # Test 3: Schema mapper availability
    schema_ok = test_schema_mapper_availability()
    
    print("\n📊 RESULTS:")
    print("=" * 50)
    print(f"✅ OpenAI Library: {'OK' if import_ok else 'FAILED'}")
    print(f"✅ OpenAI Client: {'OK' if client_ok else 'FAILED'}")
    print(f"✅ Schema Mapper: {'OK' if schema_ok else 'FAILED'}")
    
    if import_ok and client_ok and schema_ok:
        print("\n🎉 Ready for schema-driven testing!")
        print("   Run: ENABLE_SCHEMA_DRIVEN=true python3 test_schema_driven_integration.py")
    else:
        print("\n⚠️ Setup needed before schema-driven testing")
        
    print()