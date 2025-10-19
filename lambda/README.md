# Lambda Function

This directory contains the Lambda function code for the Clima Cast Alexa skill.

## Structure

- `lambda_function.py` - Main Lambda handler using ASK SDK for Python
- `requirements.txt` - Python dependencies

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
