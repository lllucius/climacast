# Lambda Function

This directory contains the Lambda function code for the Clima Cast Alexa skill.

## Structure

- `lambda_function.py` - Main Lambda handler using ASK SDK for Python
- `cache_adapter.py` - Cache abstraction layer for DynamoDB and JSON files
- `processing.py` - Core weather processing logic
- `cli.py` - Command-line interface for local testing
- `requirements.txt` - Python dependencies
- `CLI_README.md` - Detailed documentation for the CLI

## Local Testing

The skill can now be tested locally using the CLI without deploying to Lambda:

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI commands
./cli.py launch
./cli.py help
./cli.py set_location --location "Boulder Colorado"
./cli.py metric --metric temperature

# See CLI_README.md for more examples
```

The CLI uses JSON file caching instead of DynamoDB, allowing you to test all processing logic locally.

## Architecture

The code is now structured into three layers:

1. **Cache Abstraction** (`cache_adapter.py`) - Provides pluggable caching backends
   - `DynamoDBCacheAdapter` for Lambda (AWS DynamoDB)
   - `JSONFileCacheAdapter` for CLI (local JSON files)

2. **Processing Logic** (`processing.py`) - Core weather processing
   - Independent of Lambda/Alexa infrastructure
   - Uses cache adapter for storage
   - Testable via CLI

3. **Lambda Handler** (`lambda_function.py`) - Alexa Skill integration
   - ASK SDK request handlers
   - Uses cache abstraction layer
   - Unchanged public interface

## Dependencies

The skill uses the following main dependencies:
- `ask-sdk-core` - Alexa Skills Kit SDK for Python
- `boto3` - AWS SDK for DynamoDB access
- `requests` - HTTP library for NWS API calls
- `lxml` - XML processing for observation data
- `python-dateutil` - Date/time utilities
- `aniso8601` - ISO 8601 duration parsing

## Deployment

For Alexa-hosted skills, this directory is automatically deployed when you push changes.

For self-hosted Lambda:
1. Install dependencies: `pip install -r requirements.txt -t .`
2. Create deployment package: `zip -r function.zip .`
3. Upload to Lambda or use ASK CLI: `ask deploy`

## NWS API

The skill uses the National Weather Service API v3:
- Base URL: `https://api.weather.gov`
- No API key required
- User-Agent header required: `ClimacastAlexaSkill/2.0 (climacast@homerow.net)`

Main endpoints used:
- `/points/{lat},{lon}` - Get grid data for coordinates
- `/gridpoints/{office}/{gridX},{gridY}` - Get forecast gridpoint data
- `/stations/{stationId}/observations` - Get current observations
- `/alerts/active?zone={zoneId}` - Get active weather alerts
- `/zones/{type}/{zoneId}` - Get zone information

## Environment Variables

- `event_id` - SNS topic ARN for notifications (optional)
- `app_id` - Alexa application ID for validation
- `here_api_key` - HERE.com API key for geocoding (required)
- `dataupdate_id` - Data update event identifier (optional)
