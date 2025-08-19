#!/usr/bin/env python3
"""Quick test to check what's in the environment variables"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check the problematic variables
form_parser_id = os.getenv("DOCAI_FORM_PARSER_ID")
general_processor_id = os.getenv("DOCAI_GENERAL_PROCESSOR_ID")

print("=" * 60)
print("ENVIRONMENT VARIABLE VALUES")
print("=" * 60)

print(f"DOCAI_FORM_PARSER_ID:")
print(f"  Raw value: {repr(form_parser_id)}")
print(f"  Length: {len(form_parser_id) if form_parser_id else 0}")
print(f"  Bool: {bool(form_parser_id)}")
print(f"  Stripped: {repr(form_parser_id.strip()) if form_parser_id else None}")

print(f"\nDOCAI_GENERAL_PROCESSOR_ID:")
print(f"  Raw value: {repr(general_processor_id)}")
print(f"  Length: {len(general_processor_id) if general_processor_id else 0}")
print(f"  Bool: {bool(general_processor_id)}")

# Check enabled logic
print("\n" + "=" * 60)
print("ENABLED LOGIC CHECK")
print("=" * 60)

# Simulate the config logic
form_parser_enabled = bool(os.getenv("DOCAI_FORM_PARSER_ID"))
general_enabled = bool(os.getenv("DOCAI_GENERAL_PROCESSOR_ID"))

print(f"Form Parser enabled: {form_parser_enabled}")
print(f"General Processor enabled: {general_enabled}")

# Test with defaults
form_parser_with_default = os.getenv("DOCAI_FORM_PARSER_ID", "")
print(f"\nWith default '':")
print(f"  Form Parser ID: {repr(form_parser_with_default)}")
print(f"  Bool: {bool(form_parser_with_default)}")