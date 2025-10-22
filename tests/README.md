# Tests

This directory contains all tests for the Climacast Alexa skill.

## Directory Structure

```
tests/
├── unit/                    # Unit tests for individual components
│   ├── test_cache_handler.py
│   ├── test_settings_handler.py
│   └── test_geolocator.py
├── integration/             # Integration tests with external systems
│   ├── test_ask_sdk_integration.py
│   ├── test_geolocator_integration.py
│   ├── test_local_handlers.py
│   └── test_local_handlers_functional.py
├── fixtures/                # Test data and request fixtures
│   ├── requests/            # Sample Alexa request JSON files
│   └── test_launch.json
└── legacy/                  # Legacy test files kept for reference
    └── test_refactored.py
```

## Running Tests

### Unit Tests
```bash
python3 tests/unit/test_cache_handler.py
python3 tests/unit/test_settings_handler.py
python3 tests/unit/test_geolocator.py
```

### Integration Tests
```bash
python3 tests/integration/test_ask_sdk_integration.py
python3 tests/integration/test_local_handlers.py
python3 tests/integration/test_local_handlers_functional.py
```

### With pytest (when installed)
```bash
# All tests
pytest tests/

# Only unit tests
pytest tests/unit/

# Only integration tests
pytest tests/integration/

# With coverage
pytest --cov=. tests/
```

## Test Categories

### Unit Tests
- Test individual components in isolation
- Mock external dependencies (DynamoDB, NWS API, HERE API)
- Fast execution
- Focus on business logic

### Integration Tests
- Test interaction between components
- May use test/mock external services
- Test full request/response cycles
- Verify ASK SDK integration

### Fixtures
- Sample Alexa request JSON files
- Test data for various intents
- Used by integration tests

## Adding New Tests

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Follow naming convention: `test_*.py`
4. Use fixtures from `tests/fixtures/` as needed
5. Set required environment variables before running tests

## Environment Variables for Testing

```bash
export app_id="amzn1.ask.skill.test"
export here_api_key="test_key_here"
export event_id=""
export dataupdate_id="amzn1.ask.data.update"
export AWS_DEFAULT_REGION="us-east-1"
export AWS_ACCESS_KEY_ID="test"
export AWS_SECRET_ACCESS_KEY="test"
export DYNAMODB_TABLE_NAME="test-table"
```
