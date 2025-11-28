# Modular Architecture Documentation

## Overview

The activity generation service has been refactored into a fully modular, maintainable architecture following Separation of Concerns (SoC) principles and modern Python standards.

## Architecture

### Core Modules

#### 1. `services/data_models.py`
**Purpose**: Define all structured data schemas for inputs and outputs.

**Content**:
- `ActivityRequest`: Input model for activity generation requests
- `ActivityResponse`: Response wrapper model
- `LessonPlan`: Complete lesson plan structure
- `LessonBundle`: Wrapper for multiple variants
- All nested models (LessonMeta, LessonObjective, Assessment, etc.)

**Standards**:
- Pydantic V2 with full type hints
- Field validation and constraints
- Comprehensive docstrings

#### 2. `services/prompt_builder.py`
**Purpose**: The sole responsibility for serialization and prompt construction.

**Content**:
- `build_toon_prompt()`: Converts ActivityRequest to TOON format and builds complete prompt
- TOON encoding using `utils.toon_utils`
- Prompt template construction

**Key Features**:
- Handles "Other" language option
- Includes standard alignment notes
- Supports multiple variants

#### 3. `services/llm_client.py`
**Purpose**: Low-level wrapper around OpenAI API.

**Content**:
- `LLMClient` class with:
  - API key loading and validation
  - Client initialization
  - `generate()`: Non-streaming with exponential backoff retry
  - `generate_stream()`: Streaming support
  - Error categorization and handling

**Key Features**:
- Exponential backoff retry logic (configurable)
- Comprehensive error categorization
- Streaming support
- Non-retryable error detection

#### 4. `services/llm_generator.py` (Core Service)
**Purpose**: Orchestration layer defining the public interface.

**Content**:
- `ActivityGenerator` class that orchestrates:
  1. Request → Prompt Builder
  2. Prompt → LLM Client
  3. Response → Parser/Validator
  4. Validated Data → Response

**Key Features**:
- Pydantic validation of LLM responses
- TOON parsing with JSON fallback
- Template generation fallback
- Comprehensive error handling
- Streaming support

## Data Flow

```
ActivityRequest (Pydantic)
    ↓
prompt_builder.build_toon_prompt()
    ↓
TOON-formatted prompt string
    ↓
llm_client.generate() or generate_stream()
    ↓
Raw TOON/JSON response
    ↓
llm_generator._parse_and_validate_response()
    ↓
LessonPlan.model_validate() (Pydantic V2)
    ↓
Validated LessonPlan objects
    ↓
Serialized dicts for frontend
```

## Testing

### Test Structure

- `tests/test_data_models.py`: Pydantic model validation tests
- `tests/test_prompt_builder.py`: Prompt construction tests
- `tests/test_llm_client.py`: LLM client tests with mocking
- `tests/test_llm_generator.py`: Orchestration layer tests

### Test Coverage

- ✅ All core logic paths
- ✅ Pydantic validation (valid and invalid data)
- ✅ Error handling scenarios
- ✅ Retry logic
- ✅ Fallback mechanisms
- ✅ Streaming functionality

### Mocking Strategy

All external API calls are mocked using `unittest.mock`:
- No network access required
- Fast, deterministic tests
- No API credits consumed
- Error condition simulation

## Key Improvements

1. **Separation of Concerns**: Each module has a single, well-defined responsibility
2. **Type Safety**: Full type hints throughout
3. **Validation**: Pydantic V2 validation at all boundaries
4. **Error Handling**: Granular error handling with proper categorization
5. **Testability**: Fully testable with comprehensive mocking
6. **Maintainability**: Clear module boundaries and documentation
7. **Extensibility**: Easy to add new features or modify existing ones

## Migration Notes

The router (`routers/activity.py`) has been updated to use the new modular structure:
- Imports from `services.data_models` instead of `models.activity`
- Uses `ActivityGenerator` from `services.llm_generator`
- Passes `ActivityRequest` model directly (no dict conversion)

## Usage Example

```python
from services.data_models import ActivityRequest
from services.llm_generator import ActivityGenerator

# Create request
request = ActivityRequest(
    subject="Science",
    grade_band="5th grade",
    topic_concept="Robotics",
    available_time=45,
    output_language="English",
    num_variants=1
)

# Generate activity
generator = ActivityGenerator()
success, variants, error = generator.generate_activity(request)

if success:
    for variant in variants:
        print(variant["title"])
```

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=services --cov-report=html
```

