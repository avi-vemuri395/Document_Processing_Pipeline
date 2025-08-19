#!/usr/bin/env python3
"""Test Google Document AI Authentication Flow"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_authentication():
    """Test authentication status and flow"""
    
    print("=" * 70)
    print("GOOGLE DOCUMENT AI AUTHENTICATION FLOW TEST")
    print("=" * 70)
    
    # 1. Check environment variables
    print("\n1. ENVIRONMENT VARIABLES:")
    print("-" * 40)
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    form_parser_id = os.getenv("DOCAI_FORM_PARSER_ID")
    general_processor_id = os.getenv("DOCAI_GENERAL_PROCESSOR_ID")
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"  GOOGLE_CLOUD_PROJECT: {project_id or 'NOT SET'}")
    print(f"  GOOGLE_CLOUD_LOCATION: {location or 'NOT SET'}")
    print(f"  DOCAI_FORM_PARSER_ID: {form_parser_id or 'NOT SET'}")
    print(f"  DOCAI_GENERAL_PROCESSOR_ID: {general_processor_id or 'NOT SET'}")
    print(f"  GOOGLE_APPLICATION_CREDENTIALS: {creds_path or 'NOT SET (using ADC)'}")
    
    # 2. Check Application Default Credentials
    print("\n2. APPLICATION DEFAULT CREDENTIALS (ADC):")
    print("-" * 40)
    
    try:
        import google.auth
        from google.auth import default
        from google.auth.exceptions import DefaultCredentialsError
        
        # Try to get default credentials
        credentials, project = default()
        
        print(f"  ✅ Default credentials found!")
        print(f"  Credentials type: {type(credentials).__name__}")
        print(f"  Project from credentials: {project}")
        
        # Check if it's a service account
        if hasattr(credentials, 'service_account_email'):
            print(f"  Service account email: {credentials.service_account_email}")
        
        # Check if it's user credentials
        if hasattr(credentials, 'refresh_token'):
            print(f"  User credentials (from gcloud auth)")
            
    except Exception as e:
        if 'DefaultCredentialsError' in str(type(e)):
            print(f"  ❌ No default credentials found: {e}")
            print("\n  To fix this, run ONE of the following:")
            print("  Option 1: gcloud auth application-default login")
            print("  Option 2: Set GOOGLE_APPLICATION_CREDENTIALS to service account key file")
        elif 'ModuleNotFoundError' in str(type(e)):
            print("  ❌ google-auth library not installed")
            print("  Run: pip install google-auth")
        else:
            print(f"  ❌ Error checking credentials: {e}")
        
    # 3. Check if Document AI client can be initialized
    print("\n3. DOCUMENT AI CLIENT INITIALIZATION:")
    print("-" * 40)
    
    try:
        from google.cloud import documentai
        from google.api_core.client_options import ClientOptions
        
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us")
        opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
        
        # Try to create client (this will use ADC)
        client = documentai.DocumentProcessorServiceClient(client_options=opts)
        
        print(f"  ✅ Document AI client created successfully!")
        
        # Try to build processor path
        if project_id and form_parser_id:
            processor_name = client.processor_path(
                project_id,
                location,
                form_parser_id
            )
            print(f"  Processor path: {processor_name}")
            
            # Try to get processor info (this will actually make an API call)
            try:
                processor = client.get_processor(name=processor_name)
                print(f"  ✅ Processor verified: {processor.display_name}")
                print(f"  Type: {processor.type_}")
                print(f"  State: {processor.state}")
            except Exception as e:
                print(f"  ⚠️ Could not verify processor: {e}")
                
    except Exception as e:
        print(f"  ❌ Failed to initialize client: {e}")
        
    # 4. Check for service account key file
    print("\n4. SERVICE ACCOUNT KEY FILE CHECK:")
    print("-" * 40)
    
    if creds_path:
        if Path(creds_path).exists():
            print(f"  ✅ Service account key file exists: {creds_path}")
        else:
            print(f"  ❌ Service account key file NOT found: {creds_path}")
    else:
        print("  ℹ️ No service account key file configured (using ADC)")
        
        # Check if credentials directory exists
        creds_dir = Path("./credentials")
        if creds_dir.exists():
            json_files = list(creds_dir.glob("*.json"))
            if json_files:
                print(f"  Found {len(json_files)} JSON file(s) in credentials/:")
                for f in json_files:
                    print(f"    - {f.name}")
            else:
                print("  No JSON files found in credentials/ directory")
                
    print("\n" + "=" * 70)
    print("AUTHENTICATION FLOW SUMMARY:")
    print("=" * 70)
    
    # Summary
    auth_methods = []
    if creds_path and Path(creds_path).exists():
        auth_methods.append("Service Account Key (GOOGLE_APPLICATION_CREDENTIALS)")
    
    try:
        from google.auth import default
        credentials, _ = default()
        if hasattr(credentials, 'refresh_token'):
            auth_methods.append("User Credentials (gcloud auth)")
        elif hasattr(credentials, 'service_account_email'):
            auth_methods.append("Service Account (from environment)")
    except:
        pass
        
    if auth_methods:
        print(f"✅ Authentication available via: {', '.join(auth_methods)}")
    else:
        print("❌ No authentication configured!")
        print("\nTo fix, run ONE of the following:")
        print("1. gcloud auth application-default login  (easiest for local dev)")
        print("2. Download service account key and set GOOGLE_APPLICATION_CREDENTIALS")

if __name__ == "__main__":
    test_authentication()