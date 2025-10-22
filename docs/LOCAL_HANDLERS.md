# Local JSON Handlers for Testing

This document describes the local JSON-based handlers for testing the Clima Cast skill without requiring AWS credentials or DynamoDB access.

## Overview

The skill includes two local handler implementations that use JSON files instead of DynamoDB:

1. **LocalJsonCacheHandler** - Stores weather data cache in local JSON files
2. **LocalJsonSettingsHandler** - Stores user settings in local JSON files

These handlers are automatically used when running tests via the `test_one()` function (i.e., `python lambda_function.py test_requests/launch.json`).

## Benefits

- ✅ Test without AWS credentials
- ✅ Test without DynamoDB setup
- ✅ Fast local development
- ✅ Easy to inspect cached data
- ✅ Isolated test environments per user
- ✅ Simple JSON file format

## Usage

### Running Tests

Simply run the lambda_function with a test file:

```bash
# Set required environment variables (MapQuest API key optional for basic tests)
export app_id="amzn1.ask.skill.test"
export mapquest_id="your_mapquest_api_key"

# Run a test
python lambda_function.py test_requests/launch.json
```

The handlers are automatically activated in test mode. No additional configuration needed!

### Storage Locations

Test data is stored in the following directories:

```
.test_cache/          # Weather data cache
  location/           # Location geocoding results
  station/            # Weather station data
  zone/               # Weather zone data

.test_settings/       # User settings
  <user_id>.json      # One file per user
```

### Viewing Cached Data

Since data is stored as JSON files, you can easily inspect what's cached:

```bash
# View cached location data
cat .test_cache/location/seattle_washington.json

# View user settings
cat .test_settings/testuser.json
```

### Clearing Test Data

Simply delete the directories:

```bash
rm -rf .test_cache .test_settings
```

The directories will be recreated automatically on the next test run.

## LocalJsonCacheHandler

### Interface

The `LocalJsonCacheHandler` implements the same interface as `CacheHandler`:

```python
# Generic methods
cache_handler.get(cache_type, cache_id) -> dict or None
cache_handler.put(cache_type, cache_id, cache_data, ttl_days=35)

# Convenience methods
cache_handler.get_location(location_id) -> dict or None
cache_handler.put_location(location_id, location_data, ttl_days=35)
cache_handler.get_station(station_id) -> dict or None
cache_handler.put_station(station_id, station_data, ttl_days=35)
cache_handler.get_zone(zone_id) -> dict or None
cache_handler.put_zone(zone_id, zone_data, ttl_days=35)
```

### Features

- **File-based storage**: Each cache item is a separate JSON file
- **TTL support**: Cached items automatically expire after the specified number of days
- **Safe filenames**: Special characters in cache IDs are sanitized for filesystem compatibility
- **Hierarchical structure**: Cache types are organized in subdirectories

### File Format

```json
{
  "cache_data": {
    "lat": 47.6062,
    "lon": -122.3321,
    "city": "Seattle"
  },
  "ttl": 1234567890
}
```

## LocalJsonSettingsHandler

### Interface

The `LocalJsonSettingsHandler` implements the same interface as `SettingsHandler`:

```python
# Settings access
settings_handler.get_location() -> str or None
settings_handler.set_location(location)
settings_handler.get_rate() -> int (default: 100)
settings_handler.set_rate(rate)
settings_handler.get_pitch() -> int (default: 100)
settings_handler.set_pitch(pitch)
settings_handler.get_metrics() -> list
settings_handler.set_metrics(metrics)
```

### Features

- **Per-user storage**: Each user has their own JSON file
- **Automatic persistence**: Settings are saved immediately when changed
- **Default values**: New users automatically get sensible defaults
- **Isolated users**: Multiple test users don't interfere with each other

### File Format

```json
{
  "location": "Seattle, WA",
  "rate": 110,
  "pitch": 95,
  "metrics": ["temperature", "humidity", "wind"]
}
```

## Testing

Three test suites are provided:

### 1. Structure Tests

Tests that the handlers have the correct structure and interface:

```bash
python test_local_handlers.py
```

### 2. Functional Tests

Tests that the handlers actually work correctly:

```bash
python test_local_handlers_functional.py
```

### 3. Integration Tests

All original tests still pass with the new handlers:

```bash
python test_cache_handler.py
python test_settings_handler.py
```

## Production vs. Test Mode

The skill automatically detects when running in test mode:

| Mode | Cache Handler | Settings Handler |
|------|---------------|------------------|
| **Production** (Lambda) | `CacheHandler` (DynamoDB) | `AlexaSettingsHandler` (DynamoDB) |
| **Test** (local) | `LocalJsonCacheHandler` (JSON files) | `LocalJsonSettingsHandler` (JSON files) |

Test mode is activated when:
1. Running via `test_one()` function
2. The `TEST_MODE` global is set to `True`

## Architecture

The implementation follows these principles:

1. **Interface compatibility**: Local handlers implement the same interface as production handlers
2. **Dependency injection**: Handlers are injected into the Skill class, not hardcoded
3. **Mode detection**: Test mode is automatically detected, no manual configuration needed
4. **Clean separation**: Test code doesn't affect production code paths

## Troubleshooting

### Issue: "Permission denied" when creating directories

The handlers need write access to create `.test_cache/` and `.test_settings/` directories. Run from a directory where you have write permissions.

### Issue: Stale cache data

Cache files have a TTL (Time To Live) of 35 days by default. To force fresh data, delete the cache:

```bash
rm -rf .test_cache
```

### Issue: Settings not persisting

Check that `.test_settings/` directory exists and the user ID matches between test runs. The user ID is extracted from the test JSON file:

```json
{
  "session": {
    "user": {
      "userId": "testuser"  // This determines the settings file name
    }
  }
}
```

## Examples

### Testing Location Setting

```bash
# Set a default location
python lambda_function.py test_requests/set_location.json

# View the saved setting
cat .test_settings/amzn1.ask.account.test.json

# Query weather using the default location
python lambda_function.py test_requests/current_temp.json
```

### Testing Cache Behavior

```bash
# First call - hits real API and caches result
python lambda_function.py test_requests/current_temp_with_location.json

# View cached location data
cat .test_cache/location/seattle_washington.json

# Second call - uses cached data (faster)
python lambda_function.py test_requests/current_temp_with_location.json

# Clear cache to force fresh API call
rm -rf .test_cache
python lambda_function.py test_requests/current_temp_with_location.json
```

### Testing Multiple Users

Different user IDs get isolated settings:

```bash
# Edit test file to use user1
sed 's/testuser/user1/g' test_requests/set_location.json > /tmp/user1_set_location.json
python lambda_function.py /tmp/user1_set_location.json

# Edit test file to use user2
sed 's/testuser/user2/g' test_requests/set_location.json > /tmp/user2_set_location.json
python lambda_function.py /tmp/user2_set_location.json

# Each user has their own settings file
ls -la .test_settings/
```

## Summary

The local JSON handlers provide a simple, file-based alternative to DynamoDB for testing. They require no AWS credentials, are easy to inspect and debug, and maintain full compatibility with the production code.
