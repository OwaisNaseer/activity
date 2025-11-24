# Free API Setup Guide

The HuggingFace Inference API (`api-inference.huggingface.co`) is **deprecated** and returns 410 errors.

## Recommended: Use Groq API (Free & Fast)

1. **Get a free API key:**
   - Go to: https://console.groq.com/
   - Sign up (free account)
   - Go to "API Keys" section
   - Click "Create API Key"
   - Copy your key (starts with `gsk_`)

2. **Add to `.env` file:**
   ```
   GROQ_API_KEY=your_groq_key_here
   ```

3. **Restart the server**

## Alternative: Together AI (Free Tier)

1. **Get a free API key:**
   - Go to: https://api.together.xyz/
   - Sign up (free tier available)
   - Get your API key

2. **Add to `.env` file:**
   ```
   TOGETHER_API_KEY=your_together_key_here
   ```

3. **Restart the server**

## Priority Order

The system will try APIs in this order:
1. Groq API (if `GROQ_API_KEY` is set)
2. Together AI (if `TOGETHER_API_KEY` is set)
3. Template response (if no API keys)

## Why HuggingFace Doesn't Work

The old HuggingFace Inference API endpoint is deprecated (returns 410 error). 
Your HuggingFace token won't work with the old endpoint anymore.

**Solution:** Use Groq API (recommended) - it's free, fast, and reliable!

