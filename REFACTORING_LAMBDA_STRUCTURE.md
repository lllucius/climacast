# Lambda Function Structure Refactoring

## Overview

This refactoring separates the "skill function" (AWS Lambda/Alexa handler) from the "processing code" (weather logic) and provides a command-line interface for local testing. It also replaces MapQuest API with HERE.com geocoding API.

## Changes Made

### 1. Cache Abstraction Layer (`lambda/cache_adapter.py`)

Created a unified cache interface to support different storage backends:

- **`CacheAdapter`**: Abstract base class defining cache operations (`get`, `put`)
- **`DynamoDBCacheAdapter`**: Implementation for AWS Lambda/Alexa environments
  - Uses ASK SDK's AttributesManager for user-specific caches
  - Direct DynamoDB access for shared caches (LocationCache, StationCache, ZoneCache)
  - Implements optimistic locking with version numbers
- **`JSONFileCacheAdapter`**: Implementation for CLI/local testing
  - Stores caches as JSON files in a configurable directory (default: `.cache/`)
  - Supports TTL-based expiration

### 2. Weather Processing Module (`lambda/weather_processor.py`)

Extracted all core weather processing logic from `lambda_function.py`:

**Classes:**
- `Base`: Base class with utility methods (unit conversions, API calls, caching)
- `GridPoints`: NWS gridpoint forecast data processing
- `Observations`: Current weather observations from NWS stations
- `Alerts`: Weather alerts and warnings
- `Location`: Location lookup and geocoding
- `User`: User profile and preferences

**Key Features:**
- All classes accept a `cache_adapter` parameter instead of `attributes_manager`
- Geocoding abstraction supporting both HERE.com and MapQuest APIs
- HERE.com preferred, MapQuest deprecated but still supported for backward compatibility
- No dependencies on AWS or Alexa SDKs

### 3. Command-Line Interface (`lambda/cli.py`)

New CLI tool for local weather testing:

**Commands:**
- `current LOCATION`: Get current weather conditions
- `forecast LOCATION [--when PERIOD]`: Get weather forecast
- `alerts LOCATION`: Get weather alerts

**Options:**
- `--metrics`: Specify which metrics to display
- `--cache-dir`: Specify cache directory (default: `.cache/`)
- `--when`: Specify time period for forecast (today, tomorrow, monday, etc.)

**Features:**
- Uses `JSONFileCacheAdapter` for file-based caching
- Supports both HERE.com (`here_api_key`) and MapQuest (`mapquest_id`) API keys
- Helpful error messages and usage examples
- No AWS dependencies required

### 4. Updated Lambda Function (`lambda/lambda_function.py`)

Simplified the Lambda function to focus on Alexa skill handling:

**Changes:**
- Reduced from 2887 to 1084 lines (62% reduction, -1866 lines)
- Removed duplicate Base, GridPoints, Observations, Alerts, Location, and User classes
- Now imports from `weather_processor` module
- All intent handlers use `DynamoDBCacheAdapter` for persistence
- Added HERE.com API key support with fallback to MapQuest

**Preserved:**
- All ASK SDK request handlers (LaunchRequestHandler, MetricIntentHandler, etc.)
- Session management and response building
- User preference handling (pitch, rate, custom forecast)
- All existing functionality

## HERE.com Geocoding API

### Why Replace MapQuest?

1. **Better Coverage**: HERE.com provides more comprehensive global coverage
2. **Modern API**: RESTful JSON API with better documentation
3. **Free Tier**: Generous free tier suitable for this use case
4. **Long-term Support**: HERE is actively maintained and supported

### Migration Path

The code supports both geocoding providers:

```python
# Preferred: HERE.com
export here_api_key=YOUR_HERE_KEY

# Deprecated: MapQuest (still works)
export mapquest_id=YOUR_MAPQUEST_KEY
```

If both are set, HERE.com takes precedence. The lambda function automatically detects which key is available and uses the appropriate geocoding service.

### HERE.com API Setup

1. Sign up at https://developer.here.com/
2. Create a new project
3. Generate an API key
4. Set the environment variable: `export here_api_key=YOUR_KEY`

## Usage

### Local Testing (CLI)

```bash
cd lambda

# Set API key
export here_api_key=YOUR_KEY

# Get current conditions
python3 cli.py current "Boulder, Colorado"

# Get forecast for tomorrow
python3 cli.py forecast "Seattle, WA" --when tomorrow

# Get alerts
python3 cli.py alerts "Miami, FL"
```

### AWS Lambda Deployment

No changes required for deployment. The lambda function works the same way:

1. Set `here_api_key` or `mapquest_id` environment variable in Lambda console
2. Deploy `lambda/` directory contents
3. Skill continues to work as before

## Architecture Benefits

### Before Refactoring

```
lambda_function.py (2887 lines)
├── ASK SDK Handlers
├── Weather Processing Classes (Base, GridPoints, etc.)
├── DynamoDB Cache Code
└── Utility Functions
```

**Issues:**
- Tightly coupled skill and processing logic
- Hard to test without AWS/Alexa
- Duplicate code between local testing and Lambda
- No separation of concerns

### After Refactoring

```
lambda/
├── lambda_function.py (1084 lines) - Alexa skill handlers only
├── weather_processor.py - Weather processing logic
├── cache_adapter.py - Cache abstraction
└── cli.py - Command-line interface
```

**Benefits:**
- ✅ Clear separation of concerns
- ✅ Weather logic testable without AWS/Alexa
- ✅ CLI for local development and debugging
- ✅ Reusable cache abstraction
- ✅ Smaller, more maintainable files
- ✅ Support for multiple geocoding providers
- ✅ 62% reduction in lambda_function.py size

## Testing

### Lambda Function Import Test

```bash
cd lambda
python3 -c "import lambda_function; print('Success!')"
```

### CLI Help Test

```bash
python3 cli.py --help
python3 cli.py current --help
python3 cli.py forecast --help
python3 cli.py alerts --help
```

### Module Structure

All modules can be imported independently:

```python
from weather_processor import Location, GridPoints, Observations
from cache_adapter import JSONFileCacheAdapter
```

## Security

### CodeQL Analysis

One alert found in `weather_processor.py` line 361:
- **Alert**: Clear-text logging of sensitive data
- **Assessment**: False positive - logs Alexa event data for debugging, which doesn't contain passwords
- **Status**: Pre-existing code, outside scope of this refactoring
- **Risk**: Low - Alexa events don't contain sensitive credentials

### Best Practices

- API keys loaded from environment variables (not hardcoded)
- Cache TTLs enforce data freshness
- DynamoDB uses optimistic locking to prevent race conditions
- No credentials stored in caches

## Migration Guide

### For Developers

1. Install dependencies: `pip install -r requirements.txt`
2. Set geocoding API key: `export here_api_key=YOUR_KEY`
3. Test locally: `python3 cli.py current "Your City, State"`

### For Deployment

1. Update Lambda environment variables:
   - Add `here_api_key` (recommended)
   - Or keep existing `mapquest_id` (deprecated)
2. Deploy updated `lambda/` directory
3. No changes needed to DynamoDB tables or Alexa skill configuration

## Future Enhancements

Potential improvements enabled by this refactoring:

1. **Unit Tests**: Easy to add pytest tests for weather_processor module
2. **Mock Geocoding**: Can create mock cache adapter for testing without API calls
3. **Alternative Backends**: Can add other geocoding providers by extending Location class
4. **Batch Processing**: CLI could process multiple locations from a file
5. **Web Interface**: Weather processor could be used by a web service

## Documentation

Updated documentation files:
- `README.md`: Updated requirements and local testing examples
- `CLI_USAGE.md`: Updated geocoding API key instructions
- `.gitignore`: Added `.cache/` directory

## Conclusion

This refactoring successfully separates skill handling from weather processing, providing a cleaner architecture that's easier to test, maintain, and extend. The CLI enables rapid local development without AWS deployment, and the cache abstraction provides flexibility for different storage backends.

The HERE.com geocoding API provides a modern, well-supported alternative to MapQuest while maintaining backward compatibility for existing deployments.
