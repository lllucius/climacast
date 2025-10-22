# Architecture Diagram

## Before Refactoring

```
┌─────────────────────────────────────────┐
│         Skill Class                      │
│                                          │
│  - Direct access to attributes_manager  │
│  - _load_user_settings()                │
│  - _save_user_settings()                │
│  - user_location property               │
│  - user_rate property                   │
│  - user_pitch property                  │
│  - user_metrics property                │
│  - add_metric()                         │
│  - remove_metric()                      │
│  - reset_metrics()                      │
│                                          │
│  Tightly coupled to Alexa SDK           │
└─────────────────────────────────────────┘
```

## After Refactoring

```
┌─────────────────────────────────────────┐
│         Skill Class                      │
│                                          │
│  - settings_handler: SettingsHandler    │
│  - user_location property (delegates)   │
│  - user_rate property (delegates)       │
│  - user_pitch property (delegates)      │
│  - user_metrics property (delegates)    │
│  - add_metric() (delegates)             │
│  - remove_metric() (delegates)          │
│  - reset_metrics() (delegates)          │
│                                          │
│  Decoupled from storage implementation  │
└──────────────┬──────────────────────────┘
               │ uses
               │
               ▼
┌─────────────────────────────────────────┐
│   SettingsHandler (Abstract)            │
│                                          │
│  + get_location()                       │
│  + set_location(location)               │
│  + get_rate()                           │
│  + set_rate(rate)                       │
│  + get_pitch()                          │
│  + set_pitch(pitch)                     │
│  + get_metrics()                        │
│  + set_metrics(metrics)                 │
└──────────────┬──────────────────────────┘
               │
               │ implements
               │
               ▼
┌─────────────────────────────────────────┐
│   AlexaSettingsHandler                  │
│                                          │
│  - handler_input                        │
│  - attr_mgr: AttributesManager          │
│  - _load_settings()                     │
│  - _save_settings()                     │
│  - Uses persistent_attributes           │
│                                          │
│  Default implementation using Alexa SDK │
└─────────────────────────────────────────┘
```

## Benefits of New Architecture

1. **Separation of Concerns**: Settings management is isolated
2. **Testability**: Can mock SettingsHandler for testing
3. **Flexibility**: Easy to add new storage backends
4. **Consistency**: Matches CacheHandler pattern
5. **Maintainability**: Clear responsibilities for each class

## Similar Pattern: CacheHandler

```
┌─────────────────────────────────────────┐
│         Base/Skill Classes              │
│                                          │
│  - cache_handler: CacheHandler          │
│  - Uses cache_handler for data          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│   CacheHandler                          │
│                                          │
│  - Uses DynamoDB for caching            │
│  - get_location(), put_location()       │
│  - get_station(), put_station()         │
│  - get_zone(), put_zone()               │
└─────────────────────────────────────────┘
```

Both handlers follow the same design pattern, providing consistent architecture throughout the application.
