# DynamoDB Single Table Refactoring - Migration Guide

## Overview
This refactoring consolidates DynamoDB usage to use a SINGLE table provided by the Alexa Skill, implementing a modern single-table design pattern.

## Key Changes

### 1. Single Table Design
**Before:**
- 4 separate tables: `LocationCache`, `StationCache`, `UserCache`, `ZoneCache`
- Each table used different key structures

**After:**
- 1 table: Named from environment variable `DYNAMODB_TABLE_NAME` or defaults to ASK SDK format
- Uses composite key structure:
  - `pk` (partition key): `<type>#<id>` (e.g., `location#Miami Florida`, `station#KMIA`, `zone#FLZ072`)
  - `sk` (sort key): `data` for all cache items
- Cache data stored in `cache_data` attribute as a dict

### 2. CacheHandler Class
**New Class:** `CacheHandler`
- Centralizes all cache operations
- Provides atomic operations for shared caches
- Type-safe methods:
  - `get_location(location_id)` / `put_location(location_id, location_data)`
  - `get_station(station_id)` / `put_station(station_id, station_data)`
  - `get_zone(zone_id)` / `put_zone(zone_id, zone_data)`

**Global Instance:** `CACHE_HANDLER`
- Created once at module load
- Passed to all classes that need caching

### 3. User Settings Migration
**Before:**
- `User` class stored settings in `UserCache` table
- Settings: location, pitch, rate, metrics

**After:**
- `User` class **REMOVED**
- Settings stored in Alexa's persistent attributes (managed by ASK SDK)
- Uses `DynamoDbAdapter` from `ask-sdk-dynamodb`
- Settings stored per user automatically by Alexa
- New Skill methods:
  - `_load_user_settings()`: Load from persistent attributes
  - `_save_user_settings()`: Save to persistent attributes
  - Properties: `user_location`, `user_pitch`, `user_rate`, `user_metrics`
  - Methods: `add_metric()`, `remove_metric()`, `reset_metrics()`, `has_metric()`

### 4. Class Updates
All classes that inherit from `Base` now accept `cache_handler` parameter:
- `Base(event, cache_handler=None)`
- `GridPoints(event, tz, cwa, gridpoint, cache_handler=None)`
- `Observations(event, stations, cache_handler=None, limit=3)`
- `Observationsv3(event, stations, cache_handler=None, limit=3)`
- `Alerts(event, zoneid, cache_handler=None)`
- `Location(event, cache_handler=None)`
- `DataLoad(event, cache_handler=None)`
- `Skill(handler_input, cache_handler=None)`

## DynamoDB Table Schema

### Required Table Structure
```
Table Name: <from DYNAMODB_TABLE_NAME env var or ask-<skill-id>>
Primary Key:
  - Partition Key: pk (String)
  - Sort Key: sk (String)
Attributes:
  - cache_data (Map) - Contains the cached data
  - ttl (Number) - Time to live for cache expiration
  - id (String) - User ID for persistent attributes (ASK SDK)
  - attributes (Map) - User persistent attributes (ASK SDK)
```

### Cache Item Examples

#### Location Cache
```json
{
  "pk": "location#Miami Florida",
  "sk": "data",
  "cache_data": {
    "city": "miami",
    "state": "florida",
    "coords": "25.7617,-80.1918",
    "cwa": "MFL",
    "gridPoint": "110,50",
    "timeZone": "America/New_York",
    "forecastZoneId": "FLZ074",
    "forecastZoneName": "Miami-Dade",
    "countyZoneId": "FLC086",
    "countyZoneName": "Miami-Dade",
    "observationStations": ["KMIA", "KTMB", ...]
  },
  "ttl": 1729555200
}
```

#### Station Cache
```json
{
  "pk": "station#KMIA",
  "sk": "data",
  "cache_data": {
    "id": "KMIA",
    "name": "Miami"
  },
  "ttl": 1729555200
}
```

#### Zone Cache
```json
{
  "pk": "zone#FLZ074",
  "sk": "data",
  "cache_data": {
    "id": "FLZ074",
    "type": "forecast",
    "name": "Miami-Dade"
  },
  "ttl": 1729555200
}
```

#### User Persistent Attributes (managed by ASK SDK)
```json
{
  "id": "amzn1.ask.account.XXXXX",
  "attributes": {
    "location": "Miami Florida",
    "pitch": 100,
    "rate": 100,
    "metrics": ["summary", "temperature", "precipitation", "skys", "wind"]
  }
}
```

## Environment Variables

### Required
- `app_id`: Alexa skill application ID
- `mapquest_id`: MapQuest API key

### Optional
- `DYNAMODB_TABLE_NAME`: Name of DynamoDB table (defaults to `ask-<skill-id>`)
- `event_id`: Event ID for logging
- `dataupdate_id`: Data update resource ID

## Migration Steps

### 1. Create New DynamoDB Table
The table will be automatically created by Alexa or can be created manually:

```bash
aws dynamodb create-table \
  --table-name ask-<your-skill-id> \
  --attribute-definitions \
    AttributeName=pk,AttributeType=S \
    AttributeName=sk,AttributeType=S \
  --key-schema \
    AttributeName=pk,KeyType=HASH \
    AttributeName=sk,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --time-to-live-specification \
    Enabled=true,AttributeName=ttl
```

### 2. Update Lambda Environment Variables
Add `DYNAMODB_TABLE_NAME` if using a custom table name.

### 3. Grant Lambda Permissions
Update Lambda IAM role to access the new table:
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query",
    "dynamodb:UpdateItem"
  ],
  "Resource": "arn:aws:dynamodb:us-east-1:*:table/ask-*"
}
```

### 4. Deploy Updated Code
Deploy the refactored lambda_function.py.

### 5. Data Migration (Optional)
User settings will be automatically recreated as users interact with the skill.
Location/station/zone caches will be rebuilt on-demand.

To pre-populate caches, trigger a data load event.

## Benefits

1. **Single Table Design**: Follows AWS best practices, reduces costs
2. **Atomic Operations**: Shared caches protected by DynamoDB's consistency model
3. **Simplified Management**: One table to monitor and maintain
4. **ASK SDK Integration**: User settings managed by Alexa's persistence layer
5. **Better Separation**: Cache handling in dedicated class
6. **Easier Testing**: CacheHandler can be mocked or swapped

## Rollback Plan

If issues arise:
1. Keep old tables temporarily
2. Revert to previous lambda_function.py version
3. Update IAM permissions back to old tables

## Testing

Run the test suite:
```bash
python3 test_cache_handler.py
```

Expected output:
```
✅ ALL TESTS PASSED
```

## Notes

- Cache items have 35-day TTL by default
- User persistent attributes have no TTL (permanent)
- The `id` field for user attributes is managed by ASK SDK
- All cache operations are synchronous (no batch operations needed)
