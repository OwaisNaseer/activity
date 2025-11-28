"""Low-level OpenAI API client wrapper.

This module provides a clean interface to the OpenAI API with:
- Authentication handling
- Exponential backoff retry logic
- Streaming support
- Error handling and categorization
"""
import os
import time
import logging
from typing import Optional, Iterator, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Lazy import of openai to avoid import errors if package is not installed
_openai = None


def _get_openai():
    """Lazy import of openai module.
    
    Returns:
        The openai module
        
    Raises:
        ImportError: If openai package is not installed
    """
    global _openai
    if _openai is None:
        try:
            import openai
            _openai = openai
        except ImportError as e:
            logger.error(f"Failed to import openai: {str(e)}")
            raise ImportError(
                "openai package is not installed. Please install it with: pip install openai"
            )
    return _openai


class LLMClient:
    """Low-level wrapper around OpenAI API.
    
    This class handles:
    - API key loading and validation
    - Client initialization
    - API calls with retry logic
    - Streaming responses
    - Error categorization
    
    Attributes:
        api_key: OpenAI API key
        model: Model name to use (default: "gpt-4o-mini")
        temperature: Temperature setting (default: 0.3)
        base_url: Base URL for API (default: OpenAI official URL)
        client: Initialized OpenAI client instance
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        base_url: Optional[str] = None
    ) -> None:
        """Initialize LLM client.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to OPENAI_MODEL env var or "gpt-4o-mini")
            temperature: Temperature setting (defaults to OPENAI_TEMPERATURE env var or 0.3)
            base_url: Base URL (defaults to OPENAI_BASE_URL env var or official URL)
        """
        # Try to import openai
        try:
            openai = _get_openai()
        except ImportError as e:
            logger.error(f"OpenAI import failed: {str(e)}")
            self.api_key = None
            self.model = None
            self.temperature = None
            self.base_url = None
            self.client = None
            return
        
        # Load configuration from environment or use provided values
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(temperature) if temperature is not None else float(
            os.getenv("OPENAI_TEMPERATURE", "0.3")
        )
        self.base_url = base_url or os.getenv(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )
        
        # Validate API key
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables!")
        else:
            logger.info(f"OpenAI API - Key loaded: {self.api_key[:10]}...")
            logger.info(f"OpenAI Model: {self.model}")
            logger.info(f"OpenAI Temperature: {self.temperature}")
            logger.info(f"OpenAI Base URL: {self.base_url}")
        
        # Initialize OpenAI client
        try:
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("✓ OpenAI client initialized")
        except Exception as e:
            logger.error(f"Error initializing OpenAI client: {str(e)}")
            self.client = None
    
    def is_configured(self) -> bool:
        """Check if client is properly configured.
        
        Returns:
            True if API key and client are available, False otherwise
        """
        return bool(self.api_key and self.client)
    
    def generate(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 3000,  # Reduced from 4000 for faster generation (still sufficient)
        max_retries: int = 3,
        initial_backoff: float = 1.0
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Generate text using OpenAI API with exponential backoff retry.
        
        Args:
            prompt: User prompt to send
            system_message: Optional system message (defaults to TOON instruction)
            temperature: Optional temperature override
            max_tokens: Maximum tokens to generate
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff delay in seconds
            
        Returns:
            Tuple of (success: bool, text: Optional[str], error: Optional[str])
            - success: True if generation succeeded
            - text: Generated text if successful, None otherwise
            - error: Error message if failed, None otherwise
        """
        if not self.is_configured():
            error_msg = "OpenAI client is not configured (missing API key or client)"
            logger.error(error_msg)
            return False, None, error_msg
        
        # Default system message
        if system_message is None:
            system_message = (
                "You are an expert instructional designer who outputs only valid "
                "TOON (Token-Oriented Object Notation) format following the provided schema. "
                "No JSON, no markdown, only TOON."
            )
        
        use_temperature = temperature if temperature is not None else self.temperature
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        # Retry logic with exponential backoff
        last_error: Optional[str] = None
        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Calling OpenAI API (attempt {attempt + 1}/{max_retries}) - "
                    f"model: {self.model}, temperature: {use_temperature}"
                )
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=use_temperature,
                    max_tokens=max_tokens
                )
                
                # Extract generated text
                if response and response.choices and len(response.choices) > 0:
                    generated_text = response.choices[0].message.content
                    if generated_text:
                        generated_text = generated_text.strip()
                        logger.info(f"✓ Generated {len(generated_text)} characters")
                        return True, generated_text, None
                    else:
                        error_msg = "OpenAI returned empty text"
                        logger.warning(error_msg)
                        return False, None, error_msg
                else:
                    error_msg = "OpenAI returned no results (empty choices)"
                    logger.warning(error_msg)
                    return False, None, error_msg
                    
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                last_error = self._categorize_error(error_msg, error_type)
                
                logger.warning(
                    f"OpenAI API call failed (attempt {attempt + 1}/{max_retries}): {error_type} - {error_msg}"
                )
                
                # Don't retry on certain errors (authentication, invalid model)
                if self._should_not_retry(error_msg, error_type):
                    logger.error(f"Non-retryable error: {last_error}")
                    return False, None, last_error
                
                # Exponential backoff before retry
                if attempt < max_retries - 1:
                    backoff_time = initial_backoff * (2 ** attempt)
                    logger.info(f"Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
        
        # All retries exhausted
        logger.error(f"All {max_retries} retry attempts failed. Last error: {last_error}")
        return False, None, last_error or "OpenAI API call failed after retries"
    
    def generate_stream(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 3000  # Reduced from 4000 for faster generation (still sufficient)
    ) -> Iterator[str]:
        """Generate text using OpenAI API with streaming.
        
        Args:
            prompt: User prompt to send
            system_message: Optional system message (defaults to TOON instruction)
            temperature: Optional temperature override
            max_tokens: Maximum tokens to generate
            
        Yields:
            str: Chunks of generated text as they arrive
            "ERROR: <message>": Error message if generation fails
        """
        if not self.is_configured():
            yield "ERROR: OpenAI client is not configured (missing API key or client)"
            return
        
        # Default system message
        if system_message is None:
            system_message = (
                "You are an expert instructional designer who outputs only valid "
                "TOON (Token-Oriented Object Notation) format following the provided schema. "
                "No JSON, no markdown, only TOON."
            )
        
        use_temperature = temperature if temperature is not None else self.temperature
        
        try:
            logger.info(
                f"Streaming from OpenAI API - model: {self.model}, temperature: {use_temperature}"
            )
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=use_temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            accumulated_text = ""
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        content = delta.content
                        accumulated_text += content
                        yield content
            
            logger.info(f"✓ Streamed {len(accumulated_text)} characters")
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            categorized_error = self._categorize_error(error_msg, error_type)
            logger.error(f"OpenAI Streaming Error - Type: {error_type}, Message: {error_msg}")
            yield f"ERROR: {categorized_error}"
    
    def _categorize_error(self, error_msg: str, error_type: str) -> str:
        """Categorize and format error message for better user feedback.
        
        Args:
            error_msg: Raw error message
            error_type: Error type name
            
        Returns:
            Formatted, user-friendly error message
        """
        error_lower = error_msg.lower()
        
        if "authentication" in error_lower or "api key" in error_lower or "401" in error_msg:
            return (
                f"OpenAI API authentication failed. Please check your API key. "
                f"Error: {error_msg}"
            )
        elif "rate limit" in error_lower or "429" in error_msg:
            return (
                f"OpenAI API rate limit exceeded. Please try again later. "
                f"Error: {error_msg}"
            )
        elif "model" in error_lower or "404" in error_msg:
            return (
                f"OpenAI model not found. Check if model '{self.model}' is available. "
                f"Error: {error_msg}"
            )
        elif "network" in error_lower or "connection" in error_lower:
            return (
                f"Network error connecting to OpenAI API. Check your internet connection "
                f"and base_url. Error: {error_msg}"
            )
        else:
            return f"OpenAI API error ({error_type}): {error_msg}"
    
    def _should_not_retry(self, error_msg: str, error_type: str) -> bool:
        """Determine if an error should not be retried.
        
        Args:
            error_msg: Error message
            error_type: Error type name
            
        Returns:
            True if error should not be retried, False otherwise
        """
        error_lower = error_msg.lower()
        
        # Don't retry authentication errors, invalid model errors, or validation errors
        non_retryable_indicators = [
            "authentication",
            "api key",
            "401",
            "model",
            "404",
            "invalid",
            "validation"
        ]
        
        return any(indicator in error_lower for indicator in non_retryable_indicators)

