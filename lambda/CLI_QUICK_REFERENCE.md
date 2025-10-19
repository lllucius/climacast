# Clima Cast CLI - Quick Reference

## Installation

```bash
cd lambda
pip install -r requirements.txt
```

## Common Commands

### Getting Started
```bash
./cli.py launch                          # Welcome message
./cli.py help                            # Get help information
```

### Location Management
```bash
./cli.py set_location --location "Boulder Colorado"
./cli.py set_location --location "Seattle Washington"
./cli.py get_setting                     # Show current settings
```

### Weather Queries
```bash
# Current conditions
./cli.py metric --metric temperature
./cli.py metric --metric humidity
./cli.py metric --metric wind
./cli.py metric --metric "barometric pressure"

# With specific location
./cli.py metric --metric temperature --location "Denver Colorado"

# Forecasts
./cli.py metric --metric forecast --when tomorrow
./cli.py metric --metric forecast --when "monday afternoon"

# Alerts
./cli.py metric --metric alerts
```

### Advanced Options
```bash
# Specify cache directory
./cli.py --cache-dir /tmp/climacast metric --metric temperature

# Use JSON input
./cli.py --json-input request.json

# Save to JSON file
./cli.py --json-output response.json metric --metric wind

# Specify user
./cli.py --user-id alice metric --metric temperature
./cli.py --user-location "Phoenix Arizona" metric --metric temperature
```

## Cache Management

View cached data:
```bash
ls -lh .climacast_cache/
cat .climacast_cache/UserCache.json
```

Clear cache:
```bash
rm -rf .climacast_cache
```

## Environment Setup

Create `.env` file:
```bash
echo "here_api_key=YOUR_API_KEY_HERE" > .env
```

## JSON Input Example

Create `request.json`:
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

Run:
```bash
./cli.py --json-input request.json
```

## Troubleshooting

**Network errors**: Check internet connection and HERE API key
**Cache issues**: Clear cache with `rm -rf .climacast_cache`
**DynamoDB errors**: Normal in CLI mode - uses JSON files instead

## More Information

- Full documentation: `CLI_README.md`
- Technical details: `REFACTORING_SUMMARY.md`
- Lambda README: `README.md`
