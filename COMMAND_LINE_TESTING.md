# Command Line Testing for Clima Cast

This document describes how to test the Clima Cast Alexa skill from the command line.

## Overview

The `lambda_function.py` script now supports command-line testing, allowing you to invoke intents and test the skill without deploying to AWS or using the Alexa Developer Console.

## Usage

### Basic Syntax

```bash
python lambda_function.py <IntentName> [slot1=value1] [slot2=value2] ...
```

### Examples

#### Test a Launch Request
```bash
python lambda_function.py LaunchRequest
```

#### Test Help Intent
```bash
python lambda_function.py AMAZON.HelpIntent
```

#### Test an Intent with Slots
```bash
python lambda_function.py SetPitchIntent percent=90
```

#### Test with Multiple Slots
```bash
python lambda_function.py MetricIntent metric=temperature location="Seattle, Washington"
```

#### Test with Complex Slot Values
When slot values contain spaces or special characters, use quotes:
```bash
python lambda_function.py SetLocationIntent location="Boulder, Colorado"
```

### Batch Testing from a File

You can read multiple test cases from a file:

```bash
python lambda_function.py --file test_cases.txt
```

#### File Format

The file should contain one test case per line in the format:
```
IntentName [slot1=value1] [slot2=value2] ...
```

Lines starting with `#` are treated as comments and empty lines are ignored.

Example `test_cases.txt`:
```
# Basic requests
LaunchRequest
AMAZON.HelpIntent
AMAZON.StopIntent

# Location setting
SetLocationIntent location="Seattle, Washington"
SetLocationIntent zipcode=98101

# Voice settings
SetPitchIntent percent=90
SetRateIntent percent=110

# Metric queries
MetricIntent metric=temperature
MetricIntent metric=wind location="Portland, Oregon"
```

### Legacy JSON Mode

For backward compatibility, you can still use JSON files:

```bash
python lambda_function.py --json test.json
```

## Environment Variables

Before running tests, make sure to set these environment variables:

```bash
export AWS_DEFAULT_REGION=us-east-1
export here_api_key=test  # Use actual API key for real geocoding
```

For testing without AWS services, the skill will automatically use local handlers when `SKILLTEST=true` is set (which the command-line interface does automatically).

## Output

The script outputs the full JSON response from the skill, which includes:
- `response.outputSpeech.ssml`: The spoken response
- `response.reprompt`: The reprompt if session continues
- `response.shouldEndSession`: Whether the session should end
- `sessionAttributes`: Any session state being maintained

### Extracting Speech Text

You can use `jq` to extract just the speech text:

```bash
python lambda_function.py LaunchRequest 2>/dev/null | jq -r '.response.outputSpeech.ssml'
```

Or remove the SSML tags to get clean text:

```bash
python lambda_function.py LaunchRequest 2>/dev/null | jq -r '.response.outputSpeech.ssml' | sed 's/<[^>]*>//g'
```

## Available Intents

Common intents you can test:

- `LaunchRequest` - Skill launch
- `AMAZON.HelpIntent` - Help information
- `AMAZON.StopIntent` - Stop the skill
- `AMAZON.CancelIntent` - Cancel the current action
- `MetricIntent` - Weather metrics (temperature, wind, etc.)
- `SetLocationIntent` - Set default location
- `SetPitchIntent` - Set voice pitch
- `SetRateIntent` - Set voice rate
- `GetSettingIntent` - Get current settings
- `AddCustomIntent` - Add metric to custom forecast
- `RemCustomIntent` - Remove metric from custom forecast
- `RstCustomIntent` - Reset custom forecast

## Available Slots

Common slots used in intents:

- `location` - City and state (e.g., "Seattle, Washington")
- `zipcode` - Zip code (e.g., "98101")
- `metric` - Weather metric (temperature, wind, humidity, etc.)
- `percent` - Percentage value for voice settings
- `when_abs` - Absolute time reference (tomorrow, monday, etc.)
- `when_any` - Any time reference
- `when_pos` - Positional time reference
- `day` - Day of month
- `month` - Month name
- `setting` - Setting name (location, pitch, rate, forecast)

## Testing Tips

1. **Test Mode**: The command-line interface automatically enables test mode, which uses local file-based handlers instead of DynamoDB.

2. **Geocoding**: Geocoding requires a valid HERE API key. For testing without internet access, some location-based features may not work.

3. **Iterative Testing**: Use a test file to run multiple test cases in sequence and verify the skill's behavior.

4. **Debugging**: Use `2>&1` to see log output alongside JSON results, or `2>/dev/null` to suppress logs and only see JSON.

## Integration with CI/CD

The command-line interface can be integrated into automated testing pipelines:

```bash
# Run batch tests
python lambda_function.py --file test_cases.txt > results.json

# Test specific scenarios
python lambda_function.py LaunchRequest | jq -e '.response.shouldEndSession == false'
```

## See Also

- [README.md](../README.md) - Main project documentation
- [tests/integration/test_command_line.py](tests/integration/test_command_line.py) - Automated tests for command-line interface
