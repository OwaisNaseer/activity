"""Unit tests for LLM client."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from services.llm_client import LLMClient


class TestLLMClient:
    """Test LLM client functionality."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_client_initialization(self):
        """Test client initialization."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            
            assert client.api_key == "test-key"
            assert client.model == "gpt-4o-mini"
            assert client.temperature == 0.3
    
    @patch.dict('os.environ', {}, clear=True)
    def test_client_initialization_no_key(self):
        """Test client initialization without API key."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            
            assert client.api_key == ""
            assert client.is_configured() is False
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_is_configured(self):
        """Test is_configured method."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_client_instance = MagicMock()
            mock_openai.OpenAI.return_value = mock_client_instance
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            
            assert client.is_configured() is True
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_generate_success(self):
        """Test successful generation."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_client_instance = MagicMock()
            
            # Mock response
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Test response"
            mock_response.choices = [mock_choice]
            mock_client_instance.chat.completions.create.return_value = mock_response
            
            mock_openai.OpenAI.return_value = mock_client_instance
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            success, text, error = client.generate("Test prompt")
            
            assert success is True
            assert text == "Test response"
            assert error is None
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_generate_with_retry(self):
        """Test generation with retry on failure."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_client_instance = MagicMock()
            
            # First call fails, second succeeds
            mock_response = MagicMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "Success after retry"
            mock_response.choices = [mock_choice]
            
            mock_client_instance.chat.completions.create.side_effect = [
                Exception("Temporary error"),
                mock_response
            ]
            
            mock_openai.OpenAI.return_value = mock_client_instance
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            
            with patch('time.sleep'):  # Speed up test
                success, text, error = client.generate("Test prompt", max_retries=2)
            
            assert success is True
            assert text == "Success after retry"
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_generate_stream(self):
        """Test streaming generation."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_client_instance = MagicMock()
            
            # Mock streaming response
            mock_chunk1 = MagicMock()
            mock_chunk1.choices = [MagicMock()]
            mock_chunk1.choices[0].delta.content = "Hello "
            
            mock_chunk2 = MagicMock()
            mock_chunk2.choices = [MagicMock()]
            mock_chunk2.choices[0].delta.content = "World"
            
            mock_client_instance.chat.completions.create.return_value = [
                mock_chunk1,
                mock_chunk2
            ]
            
            mock_openai.OpenAI.return_value = mock_client_instance
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            chunks = list(client.generate_stream("Test prompt"))
            
            assert "Hello " in chunks
            assert "World" in chunks
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_error_categorization(self):
        """Test error categorization."""
        with patch('services.llm_client._get_openai') as mock_get_openai:
            mock_openai = MagicMock()
            mock_openai.OpenAI.return_value = MagicMock()
            mock_get_openai.return_value = mock_openai
            
            client = LLMClient()
            
            # Test authentication error
            error = client._categorize_error("Authentication failed", "AuthenticationError")
            assert "authentication" in error.lower() or "api key" in error.lower()
            
            # Test rate limit error
            error = client._categorize_error("Rate limit exceeded", "RateLimitError")
            assert "rate limit" in error.lower()
            
            # Test model error
            error = client._categorize_error("Model not found", "ModelError")
            assert "model" in error.lower()

