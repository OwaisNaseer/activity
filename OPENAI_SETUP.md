# OpenAI Setup and Troubleshooting Guide

## Issue Found: OpenAI Package Not Installed

The diagnostic script has identified that the `openai` Python package is **not installed** in your environment.

### Why You're Seeing Template Responses

When the OpenAI API call fails, the system automatically falls back to a template-based response. This is why you see:
```
*Note: This is a template-based response generated because OpenAI API call failed.*
```

## Solution: Install OpenAI Package

### Step 1: Install the openai package

```bash
cd backend
pip install openai
```

Or if you're using a virtual environment:
```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Verify Installation

Run the diagnostic script:
```bash
python check_openai.py
```

This will check:
- ✅ If `openai` package is installed
- ✅ If `OPENAI_API_KEY` is set in your `.env` file
- ✅ If the API key format is correct
- ✅ If the OpenAI client can be initialized
- ✅ If a test API call works

### Step 3: Configure API Key

Make sure you have a `.env` file in the `backend` directory with:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Step 4: Restart Backend Server

After installing and configuring, restart your backend server:
```bash
cd backend
python main.py
# or
uvicorn main:app --reload
```

## Common Issues and Solutions

### Issue 1: "No module named 'openai'"
**Solution:** Run `pip install openai`

### Issue 2: "OPENAI_API_KEY not configured"
**Solution:** 
1. Create a `.env` file in the `backend` directory
2. Add `OPENAI_API_KEY=sk-your-key-here`
3. Get your API key from https://platform.openai.com/api-keys

### Issue 3: "Authentication failed" or "401 error"
**Solution:** 
- Check if your API key is valid
- Make sure the key starts with `sk-`
- Verify the key hasn't expired
- Check your OpenAI account has credits

### Issue 4: "Rate limit exceeded" or "429 error"
**Solution:**
- Wait a few minutes and try again
- Upgrade your OpenAI plan if you need higher rate limits

### Issue 5: "Model not found" or "404 error"
**Solution:**
- Check if the model name in `.env` is correct
- Verify the model is available in your API plan
- Default model is `gpt-4o-mini`

### Issue 6: Network/Connection errors
**Solution:**
- Check your internet connection
- Verify firewall settings
- Check if `OPENAI_BASE_URL` is correct (default: `https://api.openai.com/v1`)

## Enhanced Error Logging

The system now includes detailed error logging. Check your backend server logs to see:
- Exact error messages from OpenAI API
- Error types (authentication, rate limit, model, network, etc.)
- Detailed diagnostic information

## Testing

After setup, test the generation:
1. Start the backend server
2. Open the frontend
3. Fill in the form and click "Generate"
4. Check the backend logs for detailed error messages if it fails

## Diagnostic Script

Run `python backend/check_openai.py` anytime to diagnose OpenAI configuration issues.

