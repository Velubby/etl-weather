#!/usr/bin/env python3
"""Quick diagnostic to test if the app can be imported"""

import sys
import os

# Add paths like passenger_wsgi.py does
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

SRC_DIR = os.path.join(APP_DIR, "src")
if os.path.isdir(SRC_DIR):
    sys.path.insert(0, SRC_DIR)
    print(f"✓ Added src to path: {SRC_DIR}")
else:
    print(f"✗ src directory not found: {SRC_DIR}")

print(f"Python: {sys.version}")
print(f"Working dir: {os.getcwd()}")
print(f"Script dir: {APP_DIR}")
print(f"sys.path: {sys.path[:3]}")
print()

# Test 1: Import etl_weather
try:
    from etl_weather.web import app

    print("✓ Successfully imported etl_weather.web.app")
except Exception as e:
    print(f"✗ Failed to import etl_weather.web: {e}")
    sys.exit(1)

# Test 2: Check asgiref
try:
    from asgiref.wsgi import AsgiToWsgi

    print("✓ asgiref.wsgi available")
except Exception as e:
    print(f"✗ asgiref not installed: {e}")
    print("Run: pip install asgiref")
    sys.exit(1)

# Test 3: Wrap it
try:
    application = AsgiToWsgi(app)
    print("✓ ASGI→WSGI wrapper created successfully")
except Exception as e:
    print(f"✗ Failed to create WSGI wrapper: {e}")
    sys.exit(1)

# Test 4: Check .env
if os.path.isfile(".env"):
    print("✓ .env file exists")
    with open(".env") as f:
        lines = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
        if any("GEMINI_API_KEY" in line for line in lines):
            print("✓ GEMINI_API_KEY found in .env")
        else:
            print("✗ GEMINI_API_KEY not found in .env")
else:
    print("⚠ .env file missing (app may fail at runtime)")

print()
print("=== All import tests passed! ===")
print("If you still get 500 errors, the issue is likely:")
print("1. Wrong Application Root in DirectAdmin Python App")
print("2. Passenger can't find passenger_wsgi.py")
print("3. File permissions issue")
