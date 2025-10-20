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
./cli.py simulate                        # Simulate a full skill session workflow
./cli.py simulate --location "Boulder Colorado"  # Simulate with location
```

### Location Management
```bash
./cli.py set_location --location "Boulder Colorado"
./cli.py set_location --location "Seattle Washington"
./cli.py get_setting                     # Show current settings
```

### Voice Settings
```bash
./cli.py set_pitch --percent 90          # Set voice pitch (70-130)
./cli.py set_rate --percent 120          # Set voice rate (50-150)
```

### Custom Forecast
```bash
./cli.py get_custom                      # Show custom forecast settings
./cli.py add_custom --metric "temperature"  # Add metric to custom forecast
./cli.py remove_custom --metric "wind"   # Remove metric from custom forecast
./cli.py reset_custom                    # Reset to default metrics
```

### Data Persistence
```bash
./cli.py store_data                      # Save cache data
./cli.py get_data                        # Load and report cache data
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

### AMAZON Intents
```bash
./cli.py yes                             # AMAZON.YesIntent
./cli.py no                              # AMAZON.NoIntent
./cli.py start_over                      # AMAZON.StartOverIntent
./cli.py cancel                          # AMAZON.CancelIntent
./cli.py stop                            # AMAZON.StopIntent
./cli.py session_ended                   # SessionEndedRequest
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
