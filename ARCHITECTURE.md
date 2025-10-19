# Architecture Overview

## System Architecture

### Before: Separate DynamoDB Tables

```
┌─────────────────────────────────────────────────────┐
│                 Lambda Function                      │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Location │  │ Observ.  │  │  User    │         │
│  │  Class   │  │  Class   │  │  Class   │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       │             │             │                 │
└───────┼─────────────┼─────────────┼─────────────────┘
        │             │             │
        ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐
│ Location  │  │ Station   │  │   User    │
│  Cache    │  │  Cache    │  │   Cache   │
│  Table    │  │  Table    │  │   Table   │
└───────────┘  └───────────┘  └───────────┘
     DDB           DDB              DDB
┌───────────┐
│   Zone    │
│  Cache    │
│  Table    │
└───────────┘
     DDB

4 separate tables, each requiring:
- Manual creation
- IAM permissions
- TTL configuration
- Separate monitoring
```

### After: Alexa-Hosted Persistent Attributes

```
┌─────────────────────────────────────────────────────────┐
│                 Lambda Function                          │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Location │  │ Observ.  │  │  User    │             │
│  │  Class   │  │  Class   │  │  Class   │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │                     │
│       │   ┌─────────▼─────────────▼──────────┐         │
│       │   │  Attributes Manager (ASK SDK)    │         │
│       │   └──────────────┬───────────────────┘         │
│       │                  │                              │
│       │   ┌──────────────▼───────────────────┐         │
│       │   │  DynamoDB Persistence Adapter    │         │
│       │   └──────────────┬───────────────────┘         │
│       │                  │                              │
└───────┼──────────────────┼──────────────────────────────┘
        │                  │
        │ (Direct access   │ (ASK SDK)
        │  for shared)     │
        │                  │
        ▼                  ▼
┌─────────────────────────────────────┐
│   climacast_persistence (DDB)       │
│                                     │
│  ┌────────────────────────────┐    │
│  │ id: "SHARED_CACHE"         │    │
│  │ attributes: {              │    │
│  │   LocationCache: {...},    │    │
│  │   StationCache: {...},     │    │
│  │   ZoneCache: {...}         │    │
│  │ }                          │    │
│  └────────────────────────────┘    │
│                                     │
│  ┌────────────────────────────┐    │
│  │ id: "user-123"             │    │
│  │ attributes: {              │    │
│  │   UserCache: {             │    │
│  │     userid: "user-123",    │    │
│  │     location: "Boulder",   │    │
│  │     rate: 100,             │    │
│  │     ...                    │    │
│  │   }                        │    │
│  │ }                          │    │
│  └────────────────────────────┘    │
│                                     │
│  ... (one item per user)           │
└─────────────────────────────────────┘

Single table with:
- Automatic creation
- Built-in permissions (Alexa-hosted)
- Simplified management
- Unified monitoring
```

## Data Flow

### Reading Cached Location (Shared Cache)

```
User Request
    │
    ▼
┌─────────────────────┐
│ MetricIntentHandler │
│                     │
│ get_forecast()      │
└──────────┬──────────┘
           │
           ▼
    ┌──────────┐
    │ Location │
    │  Class   │
    └────┬─────┘
         │
         │ cache_get("LocationCache", {"location": "boulder colorado"})
         │
         ▼
    ┌──────────────────────────┐
    │ Base._get_cache_attrs()  │
    │ (detects shared cache)   │
    └────┬─────────────────────┘
         │
         │ DDB.get_item(Key={"id": "SHARED_CACHE"})
         │
         ▼
    ┌──────────────┐
    │  DynamoDB    │
    │  Table       │
    └────┬─────────┘
         │
         │ Return attributes["LocationCache"]["boulder_colorado"]
         │
         ▼
    ┌──────────┐
    │ Location │
    │  Object  │
    └──────────┘
```

### Reading User Preferences (User Cache)

```
User Request
    │
    ▼
┌─────────────────────┐
│   Intent Handler    │
└──────────┬──────────┘
           │
           ▼
      ┌────────┐
      │  User  │
      │ Class  │
      └───┬────┘
          │
          │ cache_get("UserCache", {"userid": "user-123"})
          │
          ▼
    ┌──────────────────────────┐
    │ Base._get_cache_attrs()  │
    │ (detects user cache)     │
    └────┬─────────────────────┘
         │
         │ attributes_manager.persistent_attributes
         │
         ▼
    ┌──────────────────────┐
    │ ASK SDK (automatic)  │
    │ DDB.get_item(        │
    │   Key={"id":         │
    │        "user-123"}   │
    │ )                    │
    └────┬─────────────────┘
         │
         │ Return attributes["UserCache"]["user-123"]
         │
         ▼
      ┌────────┐
      │  User  │
      │ Object │
      └────────┘
```

### Writing Cached Data

```
Location.set()
    │
    ▼
cache_put("LocationCache", location_data)
    │
    ▼
┌──────────────────────────────┐
│ Base._get_cache_attrs()      │
│ (read existing shared cache) │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ Update cache dict:           │
│ cache["boulder_colorado"]    │
│   = location_data            │
└────┬─────────────────────────┘
     │
     ▼
┌──────────────────────────────┐
│ Base._save_cache_attrs()     │
│ (write back to DDB)          │
└────┬─────────────────────────┘
     │
     ▼
DDB.put_item(
  Item={
    "id": "SHARED_CACHE",
    "attributes": updated_cache
  }
)
```

## Cache Structure

### Shared Cache Item

```json
{
  "id": "SHARED_CACHE",
  "attributes": {
    "LocationCache": {
      "boulder_colorado": {
        "location": "boulder colorado",
        "city": "boulder",
        "state": "colorado",
        "coords": "40.0150,-105.2705",
        "cwa": "BOU",
        "gridPoint": "52,73",
        "timeZone": "America/Denver",
        "forecastZoneId": "COZ039",
        "countyZoneId": "COC013",
        "observationStations": ["KBDU", "KBJC", ...],
        "ttl": 1729382400
      },
      "seattle_washington": { ... },
      ...
    },
    "StationCache": {
      "KBDU": {
        "id": "KBDU",
        "name": "Boulder",
        "ttl": 1729382400
      },
      ...
    },
    "ZoneCache": {
      "COZ039": {
        "id": "COZ039",
        "type": "forecast",
        "name": "Boulder and Jefferson Counties Below 6000 Feet",
        "ttl": 1729382400
      },
      ...
    }
  }
}
```

### User Cache Item

```json
{
  "id": "amzn1.ask.account.AEXAMPLEID123",
  "attributes": {
    "UserCache": {
      "amzn1.ask.account.AEXAMPLEID123": {
        "userid": "amzn1.ask.account.AEXAMPLEID123",
        "location": "Boulder Colorado",
        "rate": 100,
        "pitch": 100,
        "metrics": [
          "summary",
          "temperature",
          "precipitation",
          "skys",
          "wind",
          "barometric pressure",
          "relative humidity",
          "dewpoint"
        ]
      }
    }
  }
}
```

## Intent Flow

### Weather Request Flow

```
User: "Alexa, ask Clima Cast for the weather"
    │
    ▼
┌─────────────────────┐
│ LaunchRequest or    │
│ MetricIntent        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│ get_user_and_location()     │
│ - Load User from cache      │
│ - Load Location from cache  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ parse_when()                │
│ - Determine time period     │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ get_current() or            │
│ get_forecast()              │
│ - Fetch from NWS API        │
│ - Use cached stations/zones │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ respond()                   │
│ - Format with user settings │
│ - Apply rate/pitch          │
└──────────┬──────────────────┘
           │
           ▼
    Response to user
```

## Class Hierarchy

```
AbstractRequestHandler (ASK SDK)
    │
    ├── BaseIntentHandler (custom)
    │   │
    │   ├── LaunchRequestHandler
    │   ├── MetricIntentHandler
    │   ├── SetLocationIntentHandler
    │   ├── StoreDataIntentHandler
    │   ├── GetDataIntentHandler
    │   └── ... (other handlers)
    │
    └── SessionEndedRequestHandler

Base (custom)
    │
    ├── GridPoints
    ├── Observations
    ├── Alerts
    │   └── Alert
    ├── Location
    └── User

CustomSkillBuilder (ASK SDK)
    │
    └── sb (instance)
        ├── DynamoDbAdapter
        ├── Request Handlers
        └── Exception Handlers
```

## Key Design Decisions

### 1. Why Direct DynamoDB Access for Shared Caches?

**Problem**: ASK SDK's AttributesManager is scoped to individual users
**Solution**: Direct DynamoDB access with fixed partition key "SHARED_CACHE"
**Benefit**: All users can access same cached location/station/zone data

### 2. Why Keep User Cache in ASK SDK?

**Problem**: Need per-user preferences and settings
**Solution**: Use ASK SDK's standard persistent attributes
**Benefit**: Automatic user isolation, session caching, built-in best practices

### 3. Why Single Table?

**Problem**: Multiple tables increase complexity
**Solution**: Store all data in one table with different partition keys
**Benefit**: Simpler deployment, lower costs, easier monitoring

### 4. Why CustomSkillBuilder?

**Problem**: Standard SkillBuilder doesn't support persistence
**Solution**: Use CustomSkillBuilder with DynamoDB adapter
**Benefit**: Enable persistent attributes while maintaining flexibility

## Performance Characteristics

### Shared Cache Access
- **Latency**: Single DynamoDB read/write
- **Size Limit**: 400KB per item (need to monitor)
- **Concurrency**: DynamoDB handles concurrent access
- **Cost**: One RCU/WCU per access

### User Cache Access
- **Latency**: Cached in Lambda memory during session
- **Size Limit**: 400KB per user (typically <1KB)
- **Concurrency**: Per-user, no contention
- **Cost**: One RCU at session start

### Recommendations
1. Monitor shared cache item size
2. Implement cache pruning if approaching 400KB
3. Use TTL to expire old entries
4. Consider splitting shared cache if needed

## Security Considerations

### Data Isolation
- User preferences isolated by partition key
- Shared caches accessible but read-only for users
- No cross-user data leakage possible

### IAM Permissions
```json
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem"
  ],
  "Resource": "arn:aws:dynamodb:*:*:table/climacast_persistence"
}
```

### Data Validation
- Input validation on all user data
- TTL enforcement on cached data
- Type checking on cache operations

## Monitoring and Debugging

### CloudWatch Metrics
- Lambda duration
- DynamoDB read/write units
- Error rates
- Cache hit/miss (via custom metrics)

### CloudWatch Logs
- Cache operations logged
- DynamoDB errors captured
- User interactions tracked

### Debug Commands
```javascript
// In Lambda:
console.log("Cache get:", cache_name, key);
console.log("Cache put:", cache_name, key_str);
```

## Conclusion

The new architecture provides:
- ✅ Simplified deployment
- ✅ Better user isolation
- ✅ Reduced operational complexity
- ✅ Lower costs
- ✅ Standard Alexa patterns
- ✅ Easier maintenance

While maintaining:
- ✅ All existing functionality
- ✅ Cache performance
- ✅ Data consistency
- ✅ User experience
