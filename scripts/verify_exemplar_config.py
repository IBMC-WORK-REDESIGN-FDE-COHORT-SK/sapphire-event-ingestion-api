# #!/usr/bin/env python3
# """
# Quick script to verify that the exemplar filter is being set correctly.
# Run this to check if the configuration is working.
# """

# import os
# import sys

# # Add parent directory to path
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# print("=" * 80)
# print("Verifying Exemplar Configuration")
# print("=" * 80)

# # Check .env file
# print("\n1. Checking .env file...")
# try:
#     with open('.env', 'r') as f:
#         env_content = f.read()
#         if 'OTEL_METRICS_EXEMPLAR_FILTER' in env_content:
#             for line in env_content.split('\n'):
#                 if 'OTEL_METRICS_EXEMPLAR_FILTER' in line and not line.strip().startswith('#'):
#                     print(f"   ✅ Found in .env: {line.strip()}")
#                     break
#         else:
#             print("   ❌ OTEL_METRICS_EXEMPLAR_FILTER not found in .env")
# except FileNotFoundError:
#     print("   ❌ .env file not found")

# # Check if it's loaded by settings
# print("\n2. Checking if loaded by Pydantic settings...")
# try:
#     from app.config import settings
#     print(f"   ✅ settings.OTEL_METRICS_EXEMPLAR_FILTER = {settings.OTEL_METRICS_EXEMPLAR_FILTER}")
# except Exception as e:
#     print(f"   ❌ Error loading settings: {e}")

# # Check if environment variable is set
# print("\n3. Checking environment variable...")
# exemplar_filter = os.environ.get('OTEL_METRICS_EXEMPLAR_FILTER')
# if exemplar_filter:
#     print(f"   ✅ OTEL_METRICS_EXEMPLAR_FILTER = {exemplar_filter}")
# else:
#     print("   ❌ OTEL_METRICS_EXEMPLAR_FILTER not set in environment")

# # Import metrics module to trigger the env var setting
# print("\n4. Importing metrics module (should set env var)...")
# try:
#     from app.core import metrics
#     exemplar_filter_after = os.environ.get('OTEL_METRICS_EXEMPLAR_FILTER')
#     if exemplar_filter_after:
#         print(f"   ✅ After import: OTEL_METRICS_EXEMPLAR_FILTER = {exemplar_filter_after}")
#     else:
#         print("   ❌ Still not set after importing metrics module")
# except Exception as e:
#     print(f"   ❌ Error importing metrics: {e}")

# # Check OpenTelemetry SDK version
# print("\n5. Checking OpenTelemetry SDK version...")
# try:
#     import opentelemetry
#     print(f"   ℹ️  OpenTelemetry version: {opentelemetry.__version__}")
# except Exception as e:
#     print(f"   ❌ Error checking version: {e}")

# print("\n" + "=" * 80)
# print("Verification Complete")
# print("=" * 80)

# # Summary
# print("\n📋 Summary:")
# if exemplar_filter_after == 'always_on':
#     print("   ✅ Configuration looks correct!")
#     print("   ✅ Exemplar filter is set to 'always_on'")
#     print("   ✅ Restart your FastAPI app to apply changes")
# else:
#     print("   ⚠️  Configuration issue detected")
#     print("   Please ensure:")
#     print("   1. .env file contains: OTEL_METRICS_EXEMPLAR_FILTER=always_on")
#     print("   2. Restart the FastAPI application")

# # Made with Bob
