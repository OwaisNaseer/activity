"""Pytest configuration and fixtures."""
import pytest
import os
from unittest.mock import patch


@pytest.fixture
def mock_env_vars():
    """Fixture to mock environment variables."""
    with patch.dict(os.environ, {
        'OPENAI_API_KEY': 'test-api-key',
        'OPENAI_MODEL': 'gpt-4o-mini',
        'OPENAI_TEMPERATURE': '0.3'
    }):
        yield

