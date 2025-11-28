# Unit Tests

This directory contains comprehensive unit tests for the activity generation service.

## Test Structure

- `test_data_models.py`: Tests for Pydantic model validation
- `test_prompt_builder.py`: Tests for TOON prompt construction
- `test_llm_client.py`: Tests for LLM client with mocking
- `test_llm_generator.py`: Tests for orchestration layer

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=services --cov-report=html

# Run specific test file
pytest tests/test_data_models.py

# Run with verbose output
pytest tests/ -v
```

## Test Requirements

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock
```

## Mocking Strategy

All external API calls (OpenAI) are mocked using `unittest.mock` to ensure:
- Tests run without network access
- Tests are fast and deterministic
- Tests don't consume API credits
- Tests can simulate various error conditions

