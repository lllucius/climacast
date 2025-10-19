# Clima Cast CLI

Command-line interface for testing Clima Cast weather processing locally without deploying to AWS Lambda.

## Overview

The CLI allows you to test the weather processing logic locally by:
- Emulating Alexa Skill JSON input
- Using JSON file caching instead of DynamoDB
- Providing a command-line interface to simulate skill interactions

## Architecture

The refactored code separates concerns into three layers:

1. **Cache Abstraction Layer** (`cache_adapter.py`):
   - `CacheAdapter` - Abstract base class for caching
   - `DynamoDBCacheAdapter` - DynamoDB-backed cache for Lambda
   - `JSONFileCacheAdapter` - JSON file cache for CLI

2. **Processing Logic** (`processing.py`):
   - `WeatherProcessor` - Wraps weather processing logic from `lambda_function.py`
   - Provides simplified interface for CLI testing
   - Uses classes from `lambda_function.py` with cache adapter

3. **Lambda Function** (`lambda_function.py`):
   - Updated to use cache abstraction layer
   - Maintains backward compatibility
   - Initializes skill builder only when DynamoDB is configured

## Installation

1. Install dependencies:
```bash
cd lambda
pip install -r requirements.txt
```

2. (Optional) Create a `.env` file with your HERE API key:
```bash
echo "here_api_key=YOUR_API_KEY_HERE" > .env
```

## Usage

### Basic Commands

**Launch request:**
```bash
./cli.py launch
```

**Get help:**
```bash
./cli.py help
```

**Set location:**
```bash
./cli.py set_location --location "Boulder Colorado"
```

**Query weather metric:**
```bash
./cli.py metric --metric temperature
./cli.py metric --metric temperature --location "Seattle Washington"
./cli.py metric --metric wind --when tomorrow
```

**Get settings:**
```bash
./cli.py get_setting
```

### Advanced Options

**Specify cache directory:**
```bash
./cli.py --cache-dir /tmp/climacast_cache metric --metric temperature
```

**Use JSON input file:**
```bash
./cli.py --json-input request.json
```

**Save response to JSON file:**
```bash
./cli.py --json-output response.json metric --metric temperature
```

**Specify user ID:**
```bash
./cli.py --user-id test-user-123 metric --metric temperature
```

**Set default location for user:**
```bash
./cli.py --user-location "Denver Colorado" metric --metric temperature
```

## JSON Input Format

You can provide request data as JSON for more complex testing:

```json
{
  "request_type": "IntentRequest",
  "intent_name": "MetricIntent",
  "user_id": "test-user",
  "slots": {
    "metric": {"value": "temperature"},
    "location": {"value": "Boulder Colorado"}
  }
}
```

Then run:
```bash
./cli.py --json-input request.json
```

## Cache Storage

Caches are stored in the `.climacast_cache` directory (or the directory specified with `--cache-dir`):

- `LocationCache.json` - Cached location data
- `StationCache.json` - Cached weather station data
- `ZoneCache.json` - Cached zone information
- `UserCache.json` - User profiles and preferences

Caches are created automatically and respect TTL (time to live) settings.

## Examples

### Test a complete workflow

```bash
# Set location
./cli.py set_location --location "Boulder Colorado"

# Get current conditions
./cli.py metric --metric temperature

# Get forecast
./cli.py metric --metric forecast --when tomorrow

# Get alerts
./cli.py metric --metric alerts
```

### Debug with verbose output

```bash
# Run with Python's verbose mode
python3 -v cli.py metric --metric temperature
```

### Clear cache

```bash
# Remove all cached data
rm -rf .climacast_cache
```

## Differences from Lambda

- **Caching**: Uses JSON files instead of DynamoDB
- **Authentication**: No Alexa user authentication
- **Network**: May have limited network access depending on environment
- **HERE API**: Requires `here_api_key` in environment for location geocoding

## Testing in Lambda

The Lambda function remains unchanged in functionality. The cache adapter abstraction is transparent:

1. When deployed to Lambda with DynamoDB configured, it uses `DynamoDBCacheAdapter`
2. The skill builder and handlers work exactly as before
3. All existing functionality is preserved

## Development

### Adding new intents

1. Add handler logic in `processing.py`
2. Add command-line interface in `cli.py`
3. Test locally before deploying

### Modifying caching behavior

1. Update `CacheAdapter` interface if needed
2. Implement in both adapters (DynamoDB and JSON)
3. Test with both CLI and Lambda

## Troubleshooting

**Error: "here_api_key not found"**
- Set the `here_api_key` environment variable or add to `.env` file
- Geocoding will fail without this key

**Error: "No address associated with hostname"**
- Network access is required for API calls
- Check your internet connection
- Some domains may be blocked in certain environments

**Error: "DynamoDB not configured"**
- This is normal in CLI mode
- The CLI uses JSON file caching, not DynamoDB

**Cache not updating**
- Clear the cache directory: `rm -rf .climacast_cache`
- Check TTL values in cache files

## Contributing

When making changes that affect processing logic:
1. Test with CLI first
2. Verify Lambda still works
3. Ensure both cache adapters work correctly
