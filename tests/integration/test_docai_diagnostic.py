#!/usr/bin/env python3
"""
Quick diagnostic test for DocAI connectivity and configuration.
Tests basic DocAI connection without full processing.
"""

import os
from pathlib import Path
from google.cloud import documentai
from google.api_core.client_options import ClientOptions
from dotenv import load_dotenv

load_dotenv()

def test_docai_connection():
    """Test basic DocAI connection and configuration"""
    print("\n" + "="*50)
    print("DOCAI DIAGNOSTIC TEST")
    print("="*50)
    
    # Check environment variables
    print("\n1. Checking environment variables...")
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
    processor_id = os.getenv("DOCAI_FORM_PARSER_ID", "")
    
    print(f"   PROJECT_ID: {'✅ Set' if project_id else '❌ Not set'}")
    print(f"   LOCATION: {location}")
    print(f"   PROCESSOR_ID: {'✅ Set' if processor_id else '❌ Not set'} ({processor_id[:10]}...)" if processor_id else "")
    
    if not project_id or not processor_id:
        print("\n❌ Missing required environment variables!")
        return False
    
    # Check credentials
    print("\n2. Checking Google Cloud credentials...")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    if creds_path:
        print(f"   Credentials file: {creds_path}")
        if Path(creds_path).exists():
            print(f"   ✅ Credentials file exists")
        else:
            print(f"   ❌ Credentials file not found!")
            return False
    else:
        print("   ⚠️ Using default credentials (gcloud auth)")
    
    # Try to create client
    print("\n3. Creating DocAI client...")
    try:
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        print("   ✅ Client created successfully")
    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")
        return False
    
    # Build processor name
    processor_name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"
    print(f"\n4. Processor path: {processor_name}")
    
    # Try a minimal request (just to test connectivity)
    print("\n5. Testing API connectivity...")
    try:
        # Create a minimal test document (1 byte)
        test_content = b"test"
        raw_document = documentai.RawDocument(
            content=test_content,
            mime_type="text/plain"
        )
        
        # Build minimal request
        request = documentai.ProcessRequest(
            name=processor_name,
            raw_document=raw_document,
            skip_human_review=True
        )
        
        print("   Sending minimal test request...")
        # Use very short timeout for diagnostic
        result = client.process_document(request=request, timeout=10.0)
        
        if result:
            print("   ✅ API connection successful!")
            print(f"   Response received: {type(result)}")
            return True
        else:
            print("   ⚠️ Empty response from API")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ API error: {error_msg[:200]}")
        
        # Diagnose common issues
        if "403" in error_msg:
            print("\n   🔍 DIAGNOSIS: Permission denied")
            print("      • Check if DocAI API is enabled in GCP")
            print("      • Verify service account permissions")
        elif "404" in error_msg:
            print("\n   🔍 DIAGNOSIS: Processor not found")
            print("      • Verify processor ID is correct")
            print("      • Check if processor exists in the project")
        elif "429" in error_msg:
            print("\n   🔍 DIAGNOSIS: Rate limit exceeded")
            print("      • Check DocAI quotas in GCP Console")
        elif "timeout" in error_msg.lower():
            print("\n   🔍 DIAGNOSIS: Connection timeout")
            print("      • Check network connectivity")
            print("      • Verify firewall rules")
        
        return False


if __name__ == "__main__":
    success = test_docai_connection()
    
    print("\n" + "="*50)
    if success:
        print("✅ DocAI connection test PASSED")
        print("The API is reachable and responding")
    else:
        print("❌ DocAI connection test FAILED")
        print("Fix the issues above before running extraction tests")
    print("="*50)