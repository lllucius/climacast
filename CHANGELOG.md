# Changelog

All notable changes to the Climacast Alexa skill project.

## [Unreleased]

### Phase 1 - Critical Fixes (2025-10-21)
#### Fixed
- Fixed syntax error at line 405 in `lambda_function.py` (missing closing parenthesis and `self.` prefix)
- Removed duplicate HTTPS session initialization that was overriding configured retry strategy

#### Added
- Created `requirements.txt` with all project dependencies
- Enhanced `.gitignore` with IDE, pytest, and macOS patterns

---

## [2024] - Major Refactoring and Modernization

### Settings Handler Refactoring
#### Added
- Created `SettingsHandler` base class for user settings management
- Implemented `AlexaSettingsHandler` using Alexa's `attributes_manager`
- Added comprehensive test suite in `test_settings_handler.py`

#### Changed
- Refactored `Skill` class to use settings handler instead of direct attribute access
- Updated `BaseIntentHandler` to create and pass settings handler
- Settings management now follows same pattern as `CacheHandler`

#### Benefits
- Separation of concerns for user settings
- Backend flexibility for different storage implementations
- Consistent architecture with cache handler
- Full backward compatibility maintained

### DynamoDB Single Table Refactoring
#### Changed
- Consolidated from 4 separate tables to single table design
- Implemented composite key structure: `pk` (partition key) and `sk` (sort key)
  - Location: `location#<city state>` / `data`
  - Station: `station#<id>` / `data`
  - Zone: `zone#<id>` / `data`
- Cache data now stored as dict in `cache_data` attribute

#### Added
- Created `CacheHandler` class to centralize all cache operations
- Type-safe methods: `get_location()`, `put_location()`, `get_station()`, `put_station()`, `get_zone()`, `put_zone()`
- Global `CACHE_HANDLER` instance for shared cache access
- Test suite in `test_cache_handler.py`

#### Removed
- Deleted `User` class (89 lines) - replaced by ASK SDK persistence
- Removed 4 separate DynamoDB tables

#### Benefits
- Follows AWS DynamoDB best practices
- Atomic operations for shared caches
- Simplified table management
- Lower costs and better query patterns
- User settings integrated with Alexa's persistence layer

### NWS API Modernization
#### Changed
- Replaced deprecated XML-based API endpoints with modern JSON API
- Old: `https://w1.weather.gov/xml/current_obs/{id}.xml`
- New: `https://api.weather.gov/stations/{id}/observations`
- Renamed `Observationsv3` class to `Observations`

#### Removed
- Deleted old `Observations` class (146 lines) using XML/HTML parsing
- Removed dependencies: `xml.etree.ElementTree` and `lxml`
- Eliminated HTML scraping for historical data

#### Benefits
- Using actively supported API endpoints
- JSON parsing is faster than XML
- Single API call instead of multiple
- Better data quality and structure
- Removed 155 lines of complex parsing code

### ASK SDK Integration
#### Added
- Integrated `ask-sdk-core` dependency
- Created `CustomSkillBuilder` instance
- Implemented dedicated handler classes for each intent:
  - `LaunchRequestHandler`
  - `SessionEndedRequestHandler`
  - `CancelAndStopIntentHandler`
  - `HelpIntentHandler`
  - `MetricIntentHandler`
  - `GetSettingIntentHandler`
  - `SetLocationIntentHandler`
  - `SetPitchIntentHandler`
  - `SetRateIntentHandler`
  - `GetCustomIntentHandler`
  - `AddCustomIntentHandler`
  - `RemoveCustomIntentHandler`
  - `ResetCustomIntentHandler`
- Created `BaseIntentHandler` for common functionality
- Added request/response interceptors: `RequestLogger`, `ResponseLogger`
- Added exception handler: `AllExceptionHandler`

#### Changed
- Updated `lambda_handler()` to use ASK SDK request/response serialization
- Modified `Skill` class to accept `handler_input` directly
- Updated `Skill.respond()` to build ASK SDK Response using response_builder
- Simplified conversions from 75 lines to 5 lines

#### Removed
- Removed legacy event/response structure conversions (98 lines)
- Eliminated manual method routing with `FUNCS` dict

#### Benefits
- Modern architecture following Alexa best practices
- Better separation of concerns
- Easier testing with independent handler classes
- Centralized exception handling
- Built-in request/response logging
- Full backward compatibility preserved

### Python 3.12 Compatibility
#### Fixed
- Updated `collections.MutableMapping` to `collections.abc.MutableMapping` in vendored requests library:
  - `requests/cookies.py`
  - `requests/structures.py`
  - `requests/sessions.py`
- Added fallback for `method_whitelist` → `allowed_methods` in urllib3

### Skill Package API Migration
#### Added
- Created `skill-package/skill.json` - Skill manifest
- Created `skill-package/interactionModels/custom/en-US.json` - Interaction model
  - 12 intent definitions (3 Amazon built-in + 9 custom)
  - 94 sample utterances
  - 9 custom slot types with 352 total slot values
- Added `skill-package/README.md` documentation

#### Removed
- Deleted legacy `skill/intent_schema.json`
- Deleted legacy `skill/utterances` file
- Deleted 11 legacy custom slot type files (`type_*`)
- Deleted legacy `upload` deployment script

#### Benefits
- Uses modern Alexa Skill Package API format
- Better version control with JSON files
- ASK CLI integration
- Multi-locale ready
- JSON schema validation

---

## Architecture Evolution

### Before (2017-2023)
```
Lambda Handler → Skill.handle_event() → Method Routing (FUNCS dict) → Intent Methods → Manual Response Dict
4 DynamoDB Tables: LocationCache, StationCache, UserCache, ZoneCache
Monolithic lambda_function.py with manual routing
```

### After (2024-2025)
```
Lambda Handler → Request Deserialization → CustomSkillBuilder.invoke() → Intent Handler Classes
    → BaseIntentHandler → Legacy Skill Methods → skill.respond() → ASK SDK Response
Single DynamoDB Table with composite keys
CacheHandler and SettingsHandler abstractions
Modern JSON API integrations
```

---

## Testing

### Test Coverage
- `test_ask_sdk_integration.py` - ASK SDK integration tests
- `test_cache_handler.py` - Cache handler unit tests
- `test_settings_handler.py` - Settings handler unit tests
- `test_geolocator.py` - Geolocator tests
- `test_geolocator_integration.py` - Integration tests
- `test_local_handlers.py` - Local handler tests
- `test_local_handlers_functional.py` - Functional tests
- `test_refactored.py` - Refactoring verification

### Security
- All changes validated with CodeQL security scanner
- Zero vulnerabilities found in refactored code
- Removed potential XSS vectors (HTML parsing)

---

## Code Metrics

### Reductions
- Removed 4 separate DynamoDB tables → 1 table
- Removed 146 lines of XML/HTML parsing code
- Removed 89 lines from User class
- Removed 98 lines of legacy conversions
- Net: ~333 lines removed through consolidation

### Additions
- Added 120 lines for CacheHandler
- Added 128 lines for SettingsHandler
- Added dedicated handler classes for ASK SDK
- Added comprehensive test suites
- Net: Better organization despite slight size increase

### Quality Improvements
- Single table design (DynamoDB best practice)
- Atomic operations for shared caches
- Separation of concerns (handlers)
- Modern API usage (NWS, ASK SDK)
- Better testability and maintainability

---

## Migration Notes

### DynamoDB
- User settings automatically migrated on first use
- Cache items rebuilt on-demand
- No manual migration required

### ASK SDK
- Full backward compatibility maintained
- All existing functionality preserved
- No changes to skill configuration needed

### NWS API
- Drop-in replacement for observations
- Same public interface maintained
- No breaking changes

---

## Dependencies

Current dependencies as of 2025:
- `boto3>=1.28.0` - AWS SDK
- `ask-sdk-core>=1.18.0` - Alexa Skills Kit SDK
- `ask-sdk-dynamodb-persistence-adapter>=1.18.0` - DynamoDB persistence
- `python-dateutil>=2.8.2` - Date/time handling
- `aniso8601>=9.0.1` - ISO 8601 duration parsing
- `requests>=2.31.0` - HTTP client
- `python-dotenv>=1.0.0` - Environment configuration
- `pytest>=7.4.0` - Testing framework

---

## References

- [NWS API Documentation](https://www.weather.gov/documentation/services-web-api)
- [ASK SDK for Python](https://alexa-skills-kit-python-sdk.readthedocs.io/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Alexa Skill Package API](https://developer.amazon.com/docs/smapi/skill-package-api-reference.html)
