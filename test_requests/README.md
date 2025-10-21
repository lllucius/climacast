# Test Request Files

This directory contains predefined JSON request files that can be used to test the Clima Cast skill locally without needing to interact with an Alexa device.

## How to Use

The skill already has a built-in test mechanism. Simply run:

```bash
python lambda_function.py test_requests/launch.json
```

Or use the default test.json:
```bash
python lambda_function.py
```

## Environment Setup

Before running tests, set these environment variables:

```bash
export app_id="amzn1.ask.skill.test"
export mapquest_id="your_mapquest_api_key"
```

## Available Test Files

### Basic Intents
- `launch.json` - Launch the skill
- `help.json` - Request help
- `stop.json` - Stop the skill
- `cancel.json` - Cancel the current interaction

### Weather Queries
- `current_temp.json` - Ask for current temperature (uses default location)
- `current_temp_with_location.json` - Ask for temperature in a specific location
- `current_weather.json` - Ask for current conditions
- `forecast_tomorrow.json` - Get tomorrow's forecast
- `forecast_monday.json` - Get Monday's forecast
- `will_it_rain.json` - Check if it will rain

### Location Management
- `set_location.json` - Set default location
- `get_location.json` - Get current default location

### Settings Management
- `set_pitch.json` - Set voice pitch
- `set_rate.json` - Set speech rate
- `get_settings.json` - Get all settings

### Alerts
- `get_alerts.json` - Check for weather alerts

## Creating New Test Files

To create a new test file, copy an existing one and modify the request section. The basic structure is:

```json
{
  "version": "1.0",
  "session": {
    "new": false,
    "sessionId": "amzn1.echo-api.session.test",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "attributes": {},
    "user": {
      "userId": "amzn1.ask.account.test"
    }
  },
  "context": {
    "System": {
      "application": {
        "applicationId": "amzn1.ask.skill.test"
      },
      "user": {
        "userId": "amzn1.ask.account.test"
      }
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.test",
    "timestamp": "2024-01-01T00:00:00Z",
    "locale": "en-US",
    "intent": {
      "name": "MetricIntent",
      "confirmationStatus": "NONE",
      "slots": {
        "metric": {
          "name": "metric",
          "value": "temperature"
        }
      }
    }
  }
}
```

## Notes

- The skill will make real API calls to NWS and MapQuest
- DynamoDB operations will use the configured table
- HTTP responses are cached in `.webcache` directory to speed up repeated tests
- User settings are stored in DynamoDB under the test user ID

## Testing Flow

1. Start with `launch.json` to initialize the skill
2. Test setting a location with `set_location.json`
3. Query weather with various metric files
4. Test different time periods and locations
5. Check alert functionality

## Debugging

The test function prints the full response JSON, including:
- Speech output (SSML format)
- Session attributes
- Should end session flag
- Card information (if any)

You can redirect output to a file for easier analysis:
```bash
python lambda_function.py test_requests/forecast_tomorrow.json > output.json
```
