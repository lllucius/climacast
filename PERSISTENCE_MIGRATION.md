# Persistence Migration Guide

## Overview

The Clima Cast skill has been refactored to use Alexa-hosted DynamoDB persistent attributes instead of directly accessing separate DynamoDB tables. This change simplifies deployment and follows Alexa best practices.

## What Changed

### Before (Separate DynamoDB Tables)

The skill used four separate DynamoDB tables:
- `LocationCache`: Geocoded location information (shared across users)
- `StationCache`: Weather station metadata (shared across users)
- `ZoneCache`: NWS zone information (shared across users)
- `UserCache`: User preferences and settings (per-user)

Each table required manual creation and IAM permissions.

### After (Persistent Attributes)

The skill now uses a single DynamoDB table managed by the Alexa SDK:
- `climacast_persistence`: Single table storing all persistent attributes
  - Shared caches use partition key: `SHARED_CACHE`
  - User caches use partition key: `<user_id>`

## Key Benefits

1. **Simplified Deployment**: No need to manually create multiple tables
2. **Alexa Best Practices**: Uses standard ASK SDK persistence patterns
3. **Single Table Design**: Reduced DynamoDB costs and simpler management
4. **Built-in User Isolation**: User data automatically partitioned by user ID

## Implementation Details

### Cache Storage Structure

#### Shared Caches (LocationCache, StationCache, ZoneCache)
Stored in a single DynamoDB item with partition key `SHARED_CACHE`:
```json
{
  "id": "SHARED_CACHE",
  "attributes": {
    "LocationCache": {
      "boulder_colorado": { ... },
      "seattle_washington": { ... }
    },
    "StationCache": {
      "KBDU": { ... },
      "KSEA": { ... }
    },
    "ZoneCache": {
      "COZ039": { ... },
      "WAZ558": { ... }
    }
  }
}
```

#### User Cache
Stored per-user with partition key `<user_id>`:
```json
{
  "id": "amzn1.ask.account.XXX",
  "attributes": {
    "UserCache": {
      "amzn1.ask.account.XXX": {
        "userid": "amzn1.ask.account.XXX",
        "location": "Boulder Colorado",
        "rate": 100,
        "pitch": 100,
        "metrics": ["summary", "temperature", ...]
      }
    }
  }
}
```

### New Intent Handlers

Two new intent handlers were added for data management:

#### StoreDataIntent
Explicitly saves persistent attributes to DynamoDB.
```
Usage: "Alexa, ask Clima Cast to store data"
```

#### GetDataIntent
Reports the current state of all caches.
```
Usage: "Alexa, ask Clima Cast to get data"
Response: "Data has been loaded. LocationCache has 10 items, StationCache has 5 items..."
```

## Code Changes

### Base Class Methods

#### `cache_get(cache_name, key)`
- Now uses persistent attributes instead of direct DynamoDB access
- Handles both shared and user-specific caches
- Automatically manages TTL expiration

#### `cache_put(cache_name, key, ttl=35)`
- Stores data in persistent attributes
- Shared caches written to `SHARED_CACHE` partition
- User caches written to user's partition

### Helper Methods

#### `_get_cache_attributes(cache_name)`
Returns attributes dict for a cache:
- Shared caches: Read from `SHARED_CACHE` item
- User caches: Read from user's persistent attributes

#### `_save_cache_attributes(cache_name, attrs)`
Saves attributes dict for a cache:
- Shared caches: Write to `SHARED_CACHE` item
- User caches: Write to user's persistent attributes

## Migration Steps

### For New Deployments

1. Deploy the skill normally - no manual table creation needed
2. The persistence table is created automatically by Alexa
3. Caches will populate on first use

### For Existing Deployments

If you have existing data in the old table structure:

1. **Option A: Fresh Start** (Recommended)
   - Deploy the new code
   - Old caches will repopulate naturally as users interact

2. **Option B: Migrate Data** (If you want to preserve caches)
   - Export data from old tables
   - Transform to new structure
   - Import to new persistence table
   - Script provided below

## Data Migration Script

```python
import boto3
import json

# Initialize clients
old_dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
new_dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

# Old tables
old_location = old_dynamodb.Table('LocationCache')
old_station = old_dynamodb.Table('StationCache')
old_zone = old_dynamodb.Table('ZoneCache')
old_user = old_dynamodb.Table('UserCache')

# New persistence table
persistence = new_dynamodb.Table('climacast_persistence')

# Migrate shared caches
shared_attrs = {
    "LocationCache": {},
    "StationCache": {},
    "ZoneCache": {}
}

# Scan and migrate LocationCache
response = old_location.scan()
for item in response['Items']:
    key = item['location']
    shared_attrs['LocationCache'][key] = item

# Scan and migrate StationCache
response = old_station.scan()
for item in response['Items']:
    key = item['id']
    shared_attrs['StationCache'][key] = item

# Scan and migrate ZoneCache
response = old_zone.scan()
for item in response['Items']:
    key = item['id']
    shared_attrs['ZoneCache'][key] = item

# Write shared caches to new table
persistence.put_item(Item={
    'id': 'SHARED_CACHE',
    'attributes': shared_attrs
})

# Migrate user caches
response = old_user.scan()
for item in response['Items']:
    user_id = item['userid']
    user_attrs = {
        "UserCache": {
            user_id: item
        }
    }
    persistence.put_item(Item={
        'id': user_id,
        'attributes': user_attrs
    })

print("Migration complete!")
```

## Testing

A test script is provided to verify the refactoring:

```bash
python3 test_cache_refactoring.py
```

This tests:
- Cache get/put operations
- User profile management
- Intent handler registration
- Skill builder configuration

## Troubleshooting

### Issue: Cache Not Persisting

**Symptom**: User settings or location data not saved between sessions

**Solution**: 
- Verify persistence adapter is configured in skill builder
- Check CloudWatch logs for DynamoDB errors
- Ensure Lambda has DynamoDB permissions

### Issue: Shared Cache Not Accessible

**Symptom**: Multiple users can't access same cached location data

**Solution**:
- Verify `SHARED_CACHE` partition key exists in table
- Check that `_get_cache_attributes` is using correct logic
- Review CloudWatch logs for access errors

### Issue: Old Tables Still Referenced

**Symptom**: Errors about missing LocationCache, StationCache, etc.

**Solution**:
- Ensure all code is updated to use cache names (strings) not table objects
- Remove any remaining references to `LOCATIONCACHE`, `STATIONCACHE`, etc.
- Redeploy the Lambda function

## Performance Considerations

### Shared Cache Access
- Shared caches are read/written as a single DynamoDB item
- Large shared caches (>100 items) may impact performance
- Consider implementing pagination or splitting if needed

### User Cache Access
- User caches benefit from ASK SDK's built-in caching
- Attributes loaded once per session
- No performance impact

## Future Enhancements

Potential improvements for consideration:

1. **Cache Size Management**
   - Implement max size limits for shared caches
   - Add automatic cleanup of old/unused entries
   - Monitor DynamoDB item sizes

2. **Cache Warming**
   - Pre-populate common locations
   - Background job to refresh stale data

3. **Analytics**
   - Track cache hit/miss rates
   - Monitor cache growth over time
   - Identify popular locations/stations

## Support

For issues or questions:
- Check CloudWatch Logs for detailed error messages
- Review this migration guide
- Open an issue on GitHub: https://github.com/lllucius/climacast

## References

- [ASK SDK Persistence Adapter Documentation](https://developer.amazon.com/docs/alexa-skills-kit-sdk-for-python/manage-attributes.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Alexa-Hosted Skills](https://developer.amazon.com/docs/hosted-skills/build-a-skill-end-to-end-using-an-alexa-hosted-skill.html)
