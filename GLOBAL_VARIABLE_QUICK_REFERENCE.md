# Global Variable Patterns - Quick Reference Guide

## Overview

This quick reference summarizes the recommendations from `GLOBAL_VARIABLE_ANALYSIS.md` for refactoring global/static variables in the Climacast codebase.

---

## At a Glance

| Category | Count | Current Pattern | Recommendation | Priority |
|----------|-------|----------------|----------------|----------|
| Config Variables | 7 | Config class | Keep as-is | N/A |
| Singleton Instances | 3 | Module globals | Factory functions | High |
| Constants | 15+ | Module constants | Keep as-is | N/A |
| Cross-module Deps | 3 | Late binding | Lazy imports | High |
| Test Flags | 2 | Global flags | Environment vars | High |

---

## Priority 1: High-Value Changes (4-6 hours)

### 1. Convert Singleton Instances to Factory Functions

**Before:**
```python
HTTPS = httpx.Client(timeout=30)
GEOLOCATOR = Geolocator(HERE_API_KEY, HTTPS)
CACHE_HANDLER = CacheHandler(TABLE_NAME, region)
```

**After:**
```python
_https_client = None
def get_https_client() -> httpx.Client:
    global _https_client
    if _https_client is None:
        _https_client = httpx.Client(timeout=Config.HTTP_TIMEOUT, follow_redirects=True)
    return _https_client

_geolocator_instance = None
def get_geolocator() -> Geolocator:
    global _geolocator_instance
    if _geolocator_instance is None:
        _geolocator_instance = Geolocator(Config.HERE_API_KEY, get_https_client())
    return _geolocator_instance

_cache_handler_instance = None
def get_cache_handler() -> CacheHandler:
    global _cache_handler_instance
    if _cache_handler_instance is None:
        _cache_handler_instance = CacheHandler(Config.DYNAMODB_TABLE_NAME, Config.DYNAMODB_REGION)
    return _cache_handler_instance
```

**Benefits:**
- ✅ Easy to mock in tests
- ✅ Lazy initialization
- ✅ Clear ownership

---

### 2. Replace Test Mode Globals with Environment Variable

**Before:**
```python
TEST_MODE = False
TEST_CACHE_HANDLER = None
TEST_SETTINGS_HANDLER = None

# In code:
if TEST_MODE and TEST_CACHE_HANDLER and TEST_SETTINGS_HANDLER:
    # Use test handlers
```

**After:**
```python
# Remove global variables completely

# In code:
is_test_mode = os.environ.get('CLIMACAST_TEST_MODE', '').lower() == 'true'
if is_test_mode:
    cache_handler = LocalJsonCacheHandler(".test_cache")
    settings_handler = LocalJsonSettingsHandler(user_id, ".test_settings")
else:
    # Production handlers
```

**Benefits:**
- ✅ Standard testing pattern
- ✅ No global state
- ✅ Per-run configuration

---

### 3. Fix Cross-Module Dependencies

**Before:**
```python
# weather/base.py
notify = None
HTTPS = None

def https(self, path):
    global HTTPS, notify
    if HTTPS is None:
        import lambda_function
        HTTPS = lambda_function.HTTPS
        notify = lambda_function.notify
```

**After:**
```python
# weather/base.py
def _get_https_client():
    """Lazy import to avoid circular dependency."""
    from lambda_function import get_https_client
    return get_https_client()

def _get_notify():
    """Lazy import to avoid circular dependency."""
    from lambda_function import notify
    return notify

def https(self, path):
    client = _get_https_client()
    notify_func = _get_notify()
```

**Benefits:**
- ✅ No global state
- ✅ Clear dependencies
- ✅ Easy to mock

---

## Priority 2: Nice to Have (3-4 hours)

### 4. Remove Backward Compatibility Globals

**Remove these:**
```python
EVTID = Config.EVENT_ID          # Use Config.EVENT_ID
APPID = Config.APP_ID            # Use Config.APP_ID
HERE_API_KEY = Config.HERE_API_KEY  # Use Config.HERE_API_KEY
DUID = Config.DATA_UPDATE_ID     # Use Config.DATA_UPDATE_ID
TABLE_NAME = Config.DYNAMODB_TABLE_NAME  # Use Config.DYNAMODB_TABLE_NAME
```

**Find and replace all references to use `Config.XXX` directly.**

---

### 5. Add Config Validation

**Add to Config class:**
```python
@classmethod
def validate(cls):
    """Validate required configuration."""
    if not cls.HERE_API_KEY:
        raise ValueError("HERE_API_KEY is required")
    if not cls.APP_ID:
        raise ValueError("APP_ID is required")
    # etc.

# Call at startup
Config.validate()
```

---

## Keep As-Is: These Patterns Are Good

### 1. Config Class
```python
class Config:
    EVENT_ID: str = os.environ.get("event_id", "")
    APP_ID: str = os.environ.get("app_id", "amzn1.ask.skill.test")
    # ... etc
```
✅ This is a good pattern for environment-based configuration.

---

### 2. Module Constants
```python
# utils/constants.py
SLOTS = ["day", "leadin", "location", ...]
DAYS = ["monday", "tuesday", ...]
METRICS = {"summary": ["summary", 1], ...}
STATES = ["alabama", "al", "alaska", "ak", ...]
```
✅ Standard Python practice for constants and lookup tables.

---

## Testing Examples

### Mocking Factory Functions

**Easy to Mock:**
```python
@patch('lambda_function.get_https_client')
def test_weather_api(mock_get_client):
    mock_client = Mock()
    mock_client.get.return_value = Mock(status_code=200, text='{"test": true}')
    mock_get_client.return_value = mock_client
    
    # Test your code
    result = some_function_that_uses_http()
    
    # Verify
    mock_client.get.assert_called_once()
```

### Environment-Based Testing

**Clean Test Setup:**
```python
def test_with_test_mode():
    os.environ['CLIMACAST_TEST_MODE'] = 'true'
    
    # Create skill - will use local handlers
    skill = create_skill(handler_input)
    
    # Test...
    
    # Cleanup
    del os.environ['CLIMACAST_TEST_MODE']
```

---

## Implementation Checklist

### Phase 1: Factory Functions (Week 1)
- [ ] Add factory functions for HTTPS, GEOLOCATOR, CACHE_HANDLER
- [ ] Update all usage to call functions instead of using globals
- [ ] Keep old globals temporarily for backward compatibility
- [ ] Run all tests
- [ ] Deploy and verify

### Phase 2: Test Mode Cleanup (Week 2)
- [ ] Remove TEST_MODE, TEST_CACHE_HANDLER, TEST_SETTINGS_HANDLER
- [ ] Update get_skill_helper to use environment variable
- [ ] Update all test files to set CLIMACAST_TEST_MODE
- [ ] Run all tests
- [ ] Update documentation

### Phase 3: Cross-Module Dependencies (Week 3)
- [ ] Add lazy import helper functions
- [ ] Update weather/base.py
- [ ] Update weather/location.py
- [ ] Remove global variable declarations
- [ ] Run all tests

### Phase 4: Cleanup (Week 4)
- [ ] Remove backward compatibility globals (EVTID, etc.)
- [ ] Add Config.validate() method
- [ ] Update all documentation
- [ ] Final testing
- [ ] Deploy

---

## Estimated Effort

| Phase | Time | Risk |
|-------|------|------|
| Phase 1: Factory functions | 4-6 hours | Low |
| Phase 2: Test mode | 2-3 hours | Low |
| Phase 3: Cross-module deps | 1-2 hours | Medium |
| Phase 4: Cleanup | 1-2 hours | Low |
| **Total** | **8-13 hours** | **Low-Medium** |

---

## Expected Benefits

1. **Better Testability:** Mock dependencies easily
2. **Cleaner Code:** Explicit dependencies
3. **Easier Debugging:** Clear initialization points
4. **Modern Patterns:** Follow Python best practices
5. **Maintainability:** Less global state to track

---

## What NOT to Do

❌ **Don't** use dependency injection everywhere - too much refactoring  
❌ **Don't** create singleton classes - unnecessary complexity  
❌ **Don't** convert constants to Enums - doesn't add value  
❌ **Don't** create a service registry - overkill for this project  

---

## Questions or Issues?

Refer to the comprehensive analysis in `GLOBAL_VARIABLE_ANALYSIS.md` for:
- Detailed pros/cons for each pattern
- Alternative approaches considered
- Migration strategies
- Code examples
- Risk mitigation

---

**Last Updated:** October 22, 2025  
**See Also:** `GLOBAL_VARIABLE_ANALYSIS.md` for complete analysis
