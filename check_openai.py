#!/usr/bin/env python3
"""
Diagnostic script to check OpenAI configuration and identify issues
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("OpenAI Configuration Diagnostic")
print("=" * 60)

# Check if openai package is installed
print("\n1. Checking if 'openai' package is installed...")
try:
    import openai
    print("   OK openai package is installed")
    print(f"   Version: {openai.__version__ if hasattr(openai, '__version__') else 'Unknown'}")
except ImportError as e:
    print(f"   X openai package is NOT installed: {e}")
    print("   Solution: Run 'pip install openai'")
    sys.exit(1)

# Check API key
print("\n2. Checking OPENAI_API_KEY...")
api_key = os.getenv("OPENAI_API_KEY", "")
if api_key:
    print(f"   OK API Key is set (length: {len(api_key)} characters)")
    print(f"   Key prefix: {api_key[:10]}...")
    if api_key.startswith("sk-"):
        print("   OK Key format looks correct (starts with 'sk-')")
    else:
        print("   WARNING: Key doesn't start with 'sk-'. It might be invalid.")
else:
    print("   X OPENAI_API_KEY is NOT set!")
    print("   Solution: Set OPENAI_API_KEY in your .env file or environment variables")
    sys.exit(1)

# Check model
print("\n3. Checking OPENAI_MODEL...")
model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
print(f"   Model: {model}")

# Check base URL
print("\n4. Checking OPENAI_BASE_URL...")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
print(f"   Base URL: {base_url}")

# Check temperature
print("\n5. Checking OPENAI_TEMPERATURE...")
try:
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    print(f"   Temperature: {temperature}")
except ValueError:
    print("   ⚠ Warning: Invalid temperature value")

# Try to initialize client
print("\n6. Testing OpenAI client initialization...")
try:
    client = openai.OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    print("   OK Client initialized successfully")
except Exception as e:
    print(f"   X Failed to initialize client: {e}")
    sys.exit(1)

# Try a simple API call
print("\n7. Testing OpenAI API call...")
try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Say 'test' if you can read this."}
        ],
        max_tokens=10
    )
    
    if response and response.choices:
        print("   OK API call successful!")
        print(f"   Response: {response.choices[0].message.content}")
    else:
        print("   X API call returned no results")
        sys.exit(1)
        
except Exception as e:
    error_type = type(e).__name__
    error_msg = str(e)
    print(f"   X API call failed!")
    print(f"   Error Type: {error_type}")
    print(f"   Error Message: {error_msg}")
    
    # Provide specific guidance
    if "authentication" in error_msg.lower() or "api key" in error_msg.lower() or "401" in error_msg:
        print("\n   → Issue: Authentication failed")
        print("   → Solution: Check if your API key is valid and has not expired")
    elif "rate limit" in error_msg.lower() or "429" in error_msg:
        print("\n   → Issue: Rate limit exceeded")
        print("   → Solution: Wait a few minutes and try again, or upgrade your OpenAI plan")
    elif "model" in error_msg.lower() or "404" in error_msg:
        print(f"\n   → Issue: Model '{model}' not found")
        print("   → Solution: Check if the model name is correct and available in your API plan")
    elif "network" in error_msg.lower() or "connection" in error_msg.lower():
        print("\n   → Issue: Network/connection error")
        print("   → Solution: Check your internet connection and firewall settings")
    else:
        print("\n   → Issue: Unknown error")
        print("   → Solution: Check the error message above and OpenAI API documentation")
    
    sys.exit(1)

print("\n" + "=" * 60)
print("OK All checks passed! OpenAI is configured correctly.")
print("=" * 60)

