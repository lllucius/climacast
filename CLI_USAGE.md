# Clima Cast CLI Usage

The Clima Cast CLI allows you to test the weather processing logic locally without needing to deploy to AWS Lambda or use the Alexa service.

## Overview

The refactored structure separates the "skill function" (AWS Lambda/Alexa handler) from the "processing code" (weather logic):

- **`weather_processor.py`**: Core weather processing logic (Base, GridPoints, Observations, Alerts, Location, User classes)
- **`lambda_function.py`**: AWS Lambda handler with ASK SDK integration
- **`cli.py`**: Command-line interface for local testing

This separation enables:
- Local testing without AWS Lambda deployment
- Easier debugging and development
- Reusable weather processing logic
- Faster iteration cycles

## Prerequisites

1. **Python 3.8+** installed
2. **Dependencies** installed:
   ```bash
   cd lambda
   pip install -r requirements.txt
   ```

3. **HERE.com API Key** (required for geocoding):
   - Get a free API key from https://developer.here.com/
   - Set the environment variable:
     ```bash
     export here_api_key=YOUR_HERE_API_KEY
     ```

## Basic Usage

```bash
# Navigate to the lambda directory
cd lambda

# Get help
python3 cli.py --help

# Get current conditions
python3 cli.py current "Boulder, Colorado"
python3 cli.py current 80302

# Get forecast
python3 cli.py forecast "Seattle, Washington"
python3 cli.py forecast "Miami, FL" --when tomorrow
python3 cli.py forecast 10001 --when friday

# Get weather alerts
python3 cli.py alerts "New Orleans, Louisiana"
```

## Commands

### Current Conditions

Get current weather observations:

```bash
python3 cli.py current LOCATION [--metrics METRIC1 METRIC2 ...]
```

**Examples:**
```bash
# All default metrics
python3 cli.py current "Chicago, Illinois"

# Specific metrics only
python3 cli.py current "New York, NY" --metrics temperature wind

# Using zip code
python3 cli.py current 90210
```

**Available metrics:**
- `temperature` - Current temperature, wind chill, heat index
- `wind` - Wind speed, direction, and gusts
- `relative humidity` - Humidity percentage
- `dewpoint` - Dewpoint temperature
- `barometric pressure` - Pressure and trend

### Forecast

Get weather forecast:

```bash
python3 cli.py forecast LOCATION [--when PERIOD] [--metrics METRIC1 METRIC2 ...]
```

**Examples:**
```bash
# Today's forecast
python3 cli.py forecast "Portland, Oregon"

# Tomorrow's forecast
python3 cli.py forecast "Austin, Texas" --when tomorrow

# Specific day
python3 cli.py forecast "Denver, CO" --when saturday

# Tonight's forecast
python3 cli.py forecast 55118 --when tonight

# With specific metrics
python3 cli.py forecast "Boston, MA" --when monday --metrics temperature precipitation
```

**Time periods:**
- `today` - Current 12-hour period
- `tonight` - Tonight (6pm-6am)
- `tomorrow` - Tomorrow (6am-6pm)
- Day names: `monday`, `tuesday`, `wednesday`, `thursday`, `friday`, `saturday`, `sunday`

**Available metrics:**
- `summary` - Weather summary/description
- `temperature` - High/low temperature
- `wind` - Wind speed, direction, and gusts
- `precipitation` - Chance of rain/snow and amounts
- `relative humidity` - Humidity levels
- `dewpoint` - Dewpoint temperature
- `barometric pressure` - Pressure levels
- `skys` - Sky conditions (sunny, cloudy, etc.)

### Alerts

Get active weather alerts:

```bash
python3 cli.py alerts LOCATION
```

**Examples:**
```bash
python3 cli.py alerts "Miami, Florida"
python3 cli.py alerts 70112
```

## Location Formats

The CLI accepts locations in multiple formats:

1. **City and State (full names)**:
   ```bash
   "Boulder, Colorado"
   "New York, New York"
   ```

2. **City and State (abbreviations)**:
   ```bash
   "Miami, FL"
   "Seattle, WA"
   ```

3. **ZIP Code**:
   ```bash
   90210
   10001
   ```

4. **ZIP Code (explicit)**:
   ```bash
   "zip code 55118"
   ```

## Examples

### Check conditions before heading out
```bash
$ python3 cli.py current "Denver, CO"

Current conditions for Denver, CO:
  Location: denver, colorado
  Coordinates: 39.7392,-104.9847

  Station: Denver International Airport
  Reported: 02:53 PM MST
  Conditions: Partly Cloudy

  Temperature: 45°F
  Wind: South at 12 mph
    Gusts: 18 mph
  Humidity: 32%
  Pressure: 30.15 in (rising)
```

### Check weekend forecast
```bash
$ python3 cli.py forecast "Portland, OR" --when saturday

Forecast for Portland, OR:
  Location: portland, oregon

  Period: saturday
  Time range: Sat 06:00 AM - Sat 06:00 PM PST

  Summary: light rain
  Temperature: High of 52°F
  Wind: South at 8-12 mph
    Gusts: up to 18 mph
  Precipitation: 80% chance
    Amount: a quarter to a half of an inch
```

### Check for severe weather
```bash
$ python3 cli.py alerts "New Orleans, LA"

Weather alerts for New Orleans, LA:
  Location: new orleans, louisiana
  Zone: Orleans Parish

  Current alerts for Louisiana

  Alert 1:
    Event: flood warning
    Area: orleans parish
    Headline: flood warning issued october 19 at 2:30pm cdt by nws new orleans
```

## Environment Variables

- **`here_api_key`** (required): HERE.com API key for geocoding
- **`app_id`** (optional): Application ID (defaults to test ID)
- **`AWS_DEFAULT_REGION`** (optional): AWS region (defaults to us-east-1)
- **`AWS_ACCESS_KEY_ID`** (optional): AWS access key (only needed if using DynamoDB caching)
- **`AWS_SECRET_ACCESS_KEY`** (optional): AWS secret key (only needed if using DynamoDB caching)

## Troubleshooting

### "here_api_key environment variable is required"

You need to set your HERE.com API key:
```bash
export here_api_key=YOUR_KEY_HERE
```

### "Location could not be found"

- Check your spelling
- Try using the full state name instead of abbreviation
- Try using a ZIP code instead
- Some locations may not be recognized; try a nearby larger city

### No forecast data available

- The NWS API may be temporarily unavailable
- Try a different time period
- Some future dates may not have data yet

### Connection errors

- Check your internet connection
- The NWS API may be experiencing issues
- Try again in a few moments

## Testing

The CLI provides an easy way to test the weather processing logic:

```bash
# Test location parsing
python3 cli.py current "your city, your state"

# Test different metrics
python3 cli.py current "Boulder, CO" --metrics temperature
python3 cli.py current "Boulder, CO" --metrics wind humidity

# Test forecast periods
for day in today tomorrow monday tuesday; do
    echo "=== $day ==="
    python3 cli.py forecast "Denver, CO" --when $day --metrics temperature
done
```

## Development

To modify or extend the CLI:

1. **Core weather logic**: Edit `weather_processor.py`
2. **CLI interface**: Edit `cli.py`
3. **Alexa skill handlers**: Edit `lambda_function.py`

The separation allows you to:
- Test weather logic changes locally before deploying
- Debug issues without AWS Lambda
- Add new features to either the CLI or Alexa skill independently

## Architecture

```
lambda/
├── weather_processor.py    # Core weather processing (Base, Location, GridPoints, etc.)
├── lambda_function.py      # AWS Lambda handler with ASK SDK
├── cli.py                  # Command-line interface
└── requirements.txt        # Python dependencies
```

The `weather_processor.py` module contains:
- `Base`: Base class with utility methods (unit conversions, API calls, caching)
- `GridPoints`: NWS gridpoint forecast data processing
- `Observations`: Current weather observations from NWS stations
- `Alerts`: Weather alerts and warnings
- `Location`: Location lookup and geocoding
- `User`: User profile and preferences (used by Alexa skill)

## Contributing

When making changes:

1. Test locally with the CLI first
2. Verify the changes work with various locations and conditions
3. Ensure backward compatibility with the Alexa skill
4. Update documentation as needed

## License

Released under the GNU Affero GPL. See LICENSE file for details.
