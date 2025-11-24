#!/usr/bin/env python
"""Quick test script to verify the server can start"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from main import app
    print("[OK] FastAPI app imported successfully")
    
    # Check if routes are registered
    routes = [route.path for route in app.routes]
    print(f"[OK] Found {len(routes)} routes:")
    for route in routes:
        print(f"  - {route}")
    
    print("\n[OK] Server setup is correct!")
    print("You can start the server with:")
    print("  python -m uvicorn main:app --reload")
    print("  or")
    print("  start.bat (Windows)")
    print("  ./start.sh (Linux/Mac)")
    
except Exception as e:
    print(f"[ERROR] Error: {e}")
    sys.exit(1)

