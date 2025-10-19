# Testing Guide

This guide explains how to test the Clima Cast Alexa skill.

## Local Testing (Without ASK SDK)

The skill requires ASK SDK for Python. For debugging business logic, you can test locally with proper dependencies installed.

### Prerequisites

1. Install Python dependencies:
   ```bash
   cd lambda
   pip install -r requirements.txt
   # Or use the vendored dependencies if pip is not available
   export PYTHONPATH=../aniso8601:../requests:../aws-lambda-lxml/3.6.4/py36:$PYTHONPATH
   ```

2. Set up environment variables:
   ```bash
   export app_id="amzn1.ask.skill.test"
   export here_api_key="YOUR_HERE_API_KEY"
   ```

3. Configure AWS credentials for DynamoDB access:
   ```bash
   aws configure
   ```

### Running Test Cases

The `tests/` directory contains various test scenarios. To run a test:

```bash
cd lambda
python3 lambda_function.py ../tests/test_location
```

Available test files:
- `test_location` - Tests location setting
- `test_metric` - Tests metric queries
- `test_setting_*` - Tests various setting commands
- `test_when_*` - Tests time-based queries
- `test_zipcode` - Tests zipcode-based queries

### Creating Test Cases

Test cases are JSON files in the Alexa request format. Example:

```json
{
  "version": "1.0",
  "session": {
    "new": true,
    "sessionId": "test-session",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "user": {
      "userId": "testuser"
    },
    "attributes": {}
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "test-request",
    "timestamp": "2024-01-01T00:00:00Z",
    "intent": {
      "name": "MetricIntent",
      "slots": {
        "metric": {
          "name": "metric",
          "value": "weather"
        }
      }
    }
  }
}
```

## Testing with ASK SDK

When the ASK SDK is installed, the skill automatically uses the modern handler. This can be tested with the Alexa Simulator in the Developer Console.

### Installation

```bash
cd lambda
pip install -r requirements.txt
```

### Testing the Handler

```python
import lambda_function

# Create a test event (ASK SDK format)
test_event = {
    "version": "1.0",
    "session": {
        "new": True,
        "sessionId": "test-session",
        "application": {
            "applicationId": "amzn1.ask.skill.test"
        },
        "user": {
            "userId": "testuser"
        }
    },
    "request": {
        "type": "LaunchRequest",
        "requestId": "test-request",
        "timestamp": "2024-01-01T00:00:00Z"
    }
}

# Call the handler
response = lambda_function.lambda_handler(test_event, None)
print(response)
```

## Testing in Alexa Developer Console

1. Go to the "Test" tab in your skill
2. Enable testing for "Development"
3. Type or say test phrases:
   - "open clima cast"
   - "ask clima cast for the weather"
   - "ask clima cast to set location to Boulder Colorado"

## Unit Tests

Unit tests should be added to validate individual components. Example test structure:

```python
import unittest
from lambda.lambda_function import Base, Location, GridPoints

class TestLocation(unittest.TestCase):
    def test_location_parsing(self):
        # Test location geocoding
        pass
    
    def test_zipcode_parsing(self):
        # Test zipcode parsing
        pass

class TestGridPoints(unittest.TestCase):
    def test_temperature_conversion(self):
        # Test temperature unit conversion
        pass
```

Run tests with:
```bash
python -m pytest tests/
```

## Integration Tests

Integration tests verify the full skill workflow:

1. **Location Setup Test**
   - Set a default location
   - Verify it's saved to DynamoDB
   - Retrieve weather for that location

2. **Current Conditions Test**
   - Request current weather
   - Verify NWS API is called
   - Verify response format

3. **Forecast Test**
   - Request forecast for tomorrow
   - Verify correct date parsing
   - Verify forecast data retrieval

4. **Alerts Test**
   - Request active alerts
   - Verify zone lookup
   - Verify alerts retrieval

## Performance Testing

Monitor the following metrics:
- Lambda execution time (should be < 3 seconds)
- DynamoDB read/write latency
- NWS API response time
- Memory usage (should fit in 512MB)

## Error Handling Tests

Test error scenarios:
- Invalid location
- Network timeouts
- DynamoDB unavailable
- NWS API errors
- Invalid user input

## Debugging Tips

1. **Enable CloudWatch Logs**
   - Check Lambda logs in CloudWatch
   - Search for error messages
   - Monitor API call patterns

2. **Use Print Statements**
   - Uncomment debug print statements in the code
   - Check for unexpected data formats

3. **Test with Simulators**
   - Use the Alexa Simulator in the Developer Console
   - Test on physical Echo devices
   - Verify voice recognition accuracy

4. **DynamoDB Inspection**
   - Check cache tables for correct data
   - Verify TTL is working correctly
   - Monitor item counts

## Known Issues

- HERE.com geocoding may occasionally return unexpected results for ambiguous location names
- Some NWS stations may have incomplete observation data
- TTL cleanup in DynamoDB can take up to 48 hours
- Voice recognition may mishear similar city names

## Continuous Integration

For CI/CD pipelines, consider:
- Automated syntax checking with `pylint`
- Unit test execution with `pytest`
- Integration tests against staging environment
- Automated deployment with ASK CLI
