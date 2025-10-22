# Global/Static Variable Analysis and Alternative Patterns
## Climacast Alexa Skill - Comprehensive Recommendations

**Date:** October 22, 2025  
**Purpose:** Analyze all global/static variables and recommend alternative patterns  
**Scope:** All Python files in the codebase

---

## Executive Summary

This document identifies all global and static variables throughout the Climacast codebase and provides detailed recommendations for alternative patterns. Each recommendation includes:
- Current usage analysis
- Alternative pattern options
- Pros and cons for each alternative
- Migration complexity assessment

### Key Findings

**Total Global/Static Variables Identified:** 30+

**Categories:**
1. Configuration Variables (7)
2. Singleton Instances (3)
3. Constants/Lookup Tables (15+)
4. Module-level Dependencies (3)
5. Test Mode Flags (2)

**Overall Recommendation:** Mix of patterns based on variable type and usage pattern.

---

## 1. Configuration Variables

### 1.1 Environment-based Configuration (lambda_function.py)

**Current Implementation:**
```python
# Lines 59-114 in lambda_function.py
class Config:
    EVENT_ID: str = os.environ.get("event_id", "")
    APP_ID: str = os.environ.get("app_id", "amzn1.ask.skill.test")
    DATA_UPDATE_ID: str = os.environ.get("dataupdate_id", "amzn1.ask.data.update")
    HERE_API_KEY: str = os.environ.get("here_api_key", "")
    DYNAMODB_TABLE_NAME: str = os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME", ...)
    DYNAMODB_REGION: str = os.environ.get("DYNAMODB_PERSISTENCE_REGION", "us-east-1")
    DEFAULT_CACHE_TTL_DAYS: int = 35
    HTTP_RETRY_TOTAL: int = 3
    HTTP_RETRY_STATUS_CODES: List[int] = [429, 500, 502, 503, 504]
    HTTP_TIMEOUT: int = 30

# Backward compatibility globals
EVTID = Config.EVENT_ID
APPID = Config.APP_ID
HERE_API_KEY = Config.HERE_API_KEY
DUID = Config.DATA_UPDATE_ID
TABLE_NAME = Config.DYNAMODB_TABLE_NAME
```

**Usage Pattern:**
- Read-only after initialization
- Used throughout the application for configuration
- Lambda container lifetime persistence

---

### Alternative Pattern 1: **Environment Config Class (Current Approach - RECOMMENDED)**

**Implementation:**
```python
# Already implemented - Config class with class variables
class Config:
    EVENT_ID: str = os.environ.get("event_id", "")
    APP_ID: str = os.environ.get("app_id", "amzn1.ask.skill.test")
    # ... etc
```

**Pros:**
- ✅ Centralized configuration in one place
- ✅ Type hints provide clarity
- ✅ Easy to test (can mock os.environ before import)
- ✅ Follows modern Python practices
- ✅ Good documentation potential
- ✅ Already implemented and working

**Cons:**
- ❌ Class variables are still module-level globals
- ❌ Cannot easily swap implementations at runtime
- ❌ Still loaded at import time

**Migration Complexity:** N/A (already implemented)

**Recommendation:** **KEEP AS IS** - This is a good pattern for configuration. Consider only these improvements:
1. Remove backward compatibility globals (EVTID, APPID, etc.) after updating all references
2. Add a `validate()` method to check required configurations
3. Consider using `@dataclass` for additional features

---

### Alternative Pattern 2: **Singleton Configuration Manager**

**Implementation:**
```python
class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.event_id = os.environ.get("event_id", "")
        self.app_id = os.environ.get("app_id", "amzn1.ask.skill.test")
        # ... etc
    
    def reload(self):
        """Allow reloading configuration from environment"""
        self._initialize()

# Usage
config = ConfigManager()
app_id = config.app_id
```

**Pros:**
- ✅ Single instance guaranteed
- ✅ Can add reload functionality
- ✅ Instance methods allow validation logic
- ✅ Can mock entire instance for testing

**Cons:**
- ❌ More complex than needed for static config
- ❌ Singleton pattern adds overhead
- ❌ Still essentially a global instance
- ❌ More verbose usage syntax

**Migration Complexity:** Medium (requires updating all Config references)

**Recommendation:** **NOT RECOMMENDED** - Overkill for static configuration that doesn't change during runtime.

---

### Alternative Pattern 3: **Dependency Injection via Context Object**

**Implementation:**
```python
@dataclass
class AppConfig:
    event_id: str
    app_id: str
    here_api_key: str
    dynamodb_table_name: str
    dynamodb_region: str
    
    @classmethod
    def from_environment(cls):
        return cls(
            event_id=os.environ.get("event_id", ""),
            app_id=os.environ.get("app_id", "amzn1.ask.skill.test"),
            # ... etc
        )

# Create at lambda startup
config = AppConfig.from_environment()

# Pass to classes that need it
def __init__(self, handler_input, config, cache_handler=None):
    self.config = config
    # ...
```

**Pros:**
- ✅ Explicit dependencies (no hidden globals)
- ✅ Easy to test (pass mock config)
- ✅ Type-safe with dataclass
- ✅ Clear data flow
- ✅ Can have multiple configs (dev, test, prod)

**Cons:**
- ❌ Requires passing config to many functions/classes
- ❌ Significant refactoring needed
- ❌ More verbose code
- ❌ Lambda doesn't really need multiple configs

**Migration Complexity:** High (requires updating every function/class signature)

**Recommendation:** **NOT RECOMMENDED FOR THIS PROJECT** - The benefit doesn't justify the extensive refactoring required for a Lambda function with a single configuration.

---

### Alternative Pattern 4: **Environment Variable Access via Function**

**Implementation:**
```python
def get_config(key: str, default=None):
    """Get configuration value from environment"""
    config_map = {
        'app_id': ('app_id', 'amzn1.ask.skill.test'),
        'here_api_key': ('here_api_key', ''),
        'table_name': ('DYNAMODB_PERSISTENCE_TABLE_NAME', 'ask-test'),
        # ... etc
    }
    env_key, default_val = config_map.get(key, (key, default))
    return os.environ.get(env_key, default_val or default)

# Usage
app_id = get_config('app_id')
```

**Pros:**
- ✅ Centralized access point
- ✅ Can add caching logic
- ✅ Validation in one place
- ✅ Easy to add logging/monitoring

**Cons:**
- ❌ Loses type information
- ❌ No IDE autocomplete
- ❌ String-based keys prone to typos
- ❌ Less discoverable than class attributes
- ❌ Runtime errors vs compile-time

**Migration Complexity:** Medium

**Recommendation:** **NOT RECOMMENDED** - Loss of type safety and discoverability outweighs benefits.

---

## 2. Singleton Instances

### 2.1 HTTP Client Instance (lambda_function.py)

**Current Implementation:**
```python
# Line 120
HTTPS = httpx.Client(
    timeout=Config.HTTP_TIMEOUT,
    follow_redirects=True
)
```

**Usage Pattern:**
- Shared HTTP client for NWS API calls
- Reused across Lambda invocations (container lifetime)
- Connection pooling and performance benefits

---

### Alternative Pattern 1: **Keep as Module-Level Global (Current - ACCEPTABLE)**

**Current State:**
```python
HTTPS = httpx.Client(timeout=Config.HTTP_TIMEOUT, follow_redirects=True)
```

**Pros:**
- ✅ Simple and efficient
- ✅ Reuses connections across Lambda invocations
- ✅ No overhead per request
- ✅ Standard pattern for Lambda functions

**Cons:**
- ❌ Global state makes testing harder
- ❌ Cannot easily mock without import tricks
- ❌ Tightly coupled to httpx library

**Recommendation:** **ACCEPTABLE BUT CAN BE IMPROVED**

---

### Alternative Pattern 2: **Lazy Initialization with Function**

**Implementation:**
```python
_https_client = None

def get_https_client() -> httpx.Client:
    """Get or create the global HTTPS client."""
    global _https_client
    if _https_client is None:
        _https_client = httpx.Client(
            timeout=Config.HTTP_TIMEOUT,
            follow_redirects=True
        )
    return _https_client

# Usage in code
client = get_https_client()
response = client.get(url)
```

**Pros:**
- ✅ Lazy initialization (only created when needed)
- ✅ Easy to mock (patch the function)
- ✅ Can add client validation/recreation logic
- ✅ Encapsulates creation logic
- ✅ Minimal code changes needed

**Cons:**
- ❌ Function call overhead (minimal)
- ❌ Still uses global state
- ❌ Need to call function everywhere

**Migration Complexity:** Low (simple find/replace of HTTPS with get_https_client())

**Recommendation:** **RECOMMENDED** - Good balance of simplicity and testability.

---

### Alternative Pattern 3: **Dependency Injection**

**Implementation:**
```python
class WeatherBase:
    def __init__(self, event, cache_handler=None, http_client=None):
        self.event = event
        self.cache_handler = cache_handler
        self.http_client = http_client or httpx.Client(
            timeout=Config.HTTP_TIMEOUT,
            follow_redirects=True
        )
    
    def https(self, path):
        # Use self.http_client instead of global HTTPS
        response = self.http_client.get(f"https://api.weather.gov/{path}")
        # ...
```

**Pros:**
- ✅ Fully testable (inject mock client)
- ✅ No global state
- ✅ Explicit dependencies
- ✅ Can use different clients per instance

**Cons:**
- ❌ Requires passing client through many layers
- ❌ More complex initialization
- ❌ Significant refactoring needed
- ❌ Creates new client if not provided

**Migration Complexity:** High

**Recommendation:** **NOT RECOMMENDED** - Too much effort for this codebase.

---

### Alternative Pattern 4: **HTTP Client Manager Class**

**Implementation:**
```python
class HTTPClientManager:
    """Manages HTTP client lifecycle."""
    
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> httpx.Client:
        """Get the HTTP client, creating if needed."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=Config.HTTP_TIMEOUT,
                follow_redirects=True
            )
        return self._client
    
    def close(self):
        """Close the client."""
        if self._client:
            self._client.close()
            self._client = None
    
    def recreate(self):
        """Recreate the client."""
        self.close()
        return self.client

# Module-level instance
http_manager = HTTPClientManager()

# Usage
response = http_manager.client.get(url)
```

**Pros:**
- ✅ Encapsulates client lifecycle
- ✅ Can check/recreate stale clients
- ✅ Property provides clean access
- ✅ Easy to add monitoring/logging

**Cons:**
- ❌ Added complexity
- ❌ Still essentially global
- ❌ Property call overhead

**Migration Complexity:** Medium

**Recommendation:** **OPTIONAL** - Nice to have but not essential.

---

### 2.2 Geolocator Instance (lambda_function.py)

**Current Implementation:**
```python
# Line 126
GEOLOCATOR = Geolocator(HERE_API_KEY, HTTPS)
```

**Also appears in:**
```python
# weather/location.py line 27
GEOLOCATOR = None  # Set by lambda_function
```

**Usage Pattern:**
- Single instance shared across Lambda invocations
- Initialized with API key and HTTP client
- Used for geocoding location names to coordinates

---

### Alternative Pattern 1: **Factory Function (RECOMMENDED)**

**Implementation:**
```python
_geolocator_instance = None

def get_geolocator() -> Geolocator:
    """Get or create the global geolocator instance."""
    global _geolocator_instance
    if _geolocator_instance is None:
        _geolocator_instance = Geolocator(
            api_key=Config.HERE_API_KEY,
            session=get_https_client()
        )
    return _geolocator_instance

# In location.py
def geocode_location(location_string):
    geolocator = get_geolocator()
    return geolocator.geocode(location_string)
```

**Pros:**
- ✅ Easy to mock for testing
- ✅ Lazy initialization
- ✅ Encapsulates creation logic
- ✅ Can validate API key before creating
- ✅ Minimal changes to existing code

**Cons:**
- ❌ Function call overhead
- ❌ Still uses global state

**Migration Complexity:** Low

**Recommendation:** **RECOMMENDED** - Clean pattern for singleton services.

---

### Alternative Pattern 2: **Dependency Injection via Location Class**

**Implementation:**
```python
class Location(WeatherBase):
    def __init__(self, event, cache_handler=None, geolocator=None):
        super().__init__(event, cache_handler)
        self.geolocator = geolocator or get_geolocator()
    
    def set(self, location_string, fallback=None):
        coords, props = self.geolocator.geocode(location_string)
        # ...
```

**Pros:**
- ✅ Testable (inject mock geolocator)
- ✅ Explicit dependency
- ✅ Flexible (different geolocators possible)

**Cons:**
- ❌ Requires updating all Location() creations
- ❌ More complex initialization

**Migration Complexity:** Medium

**Recommendation:** **OPTIONAL** - Consider if doing major refactoring.

---

### 2.3 Cache Handler Instance (lambda_function.py)

**Current Implementation:**
```python
# Line 129
CACHE_HANDLER = CacheHandler(TABLE_NAME, Config.DYNAMODB_REGION)
```

**Usage Pattern:**
- Single DynamoDB cache handler
- Shared across Lambda invocations
- Reuses boto3 connections

---

### Alternative Pattern 1: **Factory Function (RECOMMENDED)**

**Implementation:**
```python
_cache_handler_instance = None

def get_cache_handler() -> CacheHandler:
    """Get or create the global cache handler instance."""
    global _cache_handler_instance
    if _cache_handler_instance is None:
        _cache_handler_instance = CacheHandler(
            table_name=Config.DYNAMODB_TABLE_NAME,
            region=Config.DYNAMODB_REGION
        )
    return _cache_handler_instance

# Usage
cache = get_cache_handler()
data = cache.get_location(location_id)
```

**Pros:**
- ✅ Testable (can patch function)
- ✅ Lazy initialization
- ✅ Single point of creation
- ✅ Can add connection validation

**Cons:**
- ❌ Function call overhead
- ❌ Global state remains

**Migration Complexity:** Low

**Recommendation:** **RECOMMENDED** - Consistent with other singletons.

---

### Alternative Pattern 2: **Context Manager**

**Implementation:**
```python
class CacheContext:
    """Context manager for cache operations."""
    
    def __init__(self):
        self._handler = None
    
    def __enter__(self):
        if self._handler is None:
            self._handler = CacheHandler(
                Config.DYNAMODB_TABLE_NAME,
                Config.DYNAMODB_REGION
            )
        return self._handler
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Could close connections here if needed
        pass

# Usage
with CacheContext() as cache:
    data = cache.get_location(location_id)
```

**Pros:**
- ✅ Clean resource management
- ✅ Explicit scope
- ✅ Pythonic pattern

**Cons:**
- ❌ More verbose
- ❌ Lambda doesn't need cleanup
- ❌ Significant refactoring

**Migration Complexity:** High

**Recommendation:** **NOT RECOMMENDED** - Context managers are for resources that need cleanup. DynamoDB clients don't need this.

---

## 3. Constants and Lookup Tables

### 3.1 Data Constants (utils/constants.py)

**Current Implementation:**
```python
SLOTS = ["day", "leadin", "location", "metric", ...]
QUARTERS = ["morning", "afternoon", "evening", "overnight", ...]
DAYS = ["monday", "tuesday", "wednesday", ...]
MONTH_DAYS_XLATE = {"1st": "first", "2nd": "second", ...}
MONTH_DAYS = ["first", "second", "third", ...]
MONTH_NAMES = ["january", "february", "march", ...]
METRICS = {"summary": ["summary", 1], "temp": ["temperature", 2], ...}
ANGLES = [["north", "N", 11.25], ["north northeast", "NNE", 33.75], ...]
STATES = ["alabama", "al", "alaska", "ak", ...]
SETTINGS = {"location": "location", "pitch": "pitch", ...}
TIME_QUARTERS = {0: ["overnight", False], 1: ["morning", True], ...}
WEATHER_COVERAGE = {"areas_of": "areas of", "chance": "a chance of", ...}
WEATHER_WEATHER = {"blowing_dust": "blowing dust", "drizzle": "drizzle", ...}
WEATHER_INTENSITY = {"": ["", 0], "very_light": ["very light", 1], ...}
WEATHER_VISIBILITY = {"": None}
WEATHER_ATTRIBUTES = {"damaging_wind": "damaging wind", ...}
LOCATION_XLATE = {"gnome alaska": "nome alaska", ...}
NORMALIZE_RE = [r"(?P<meridian>\d+\s*(am|pm))", ...]
```

**Usage Pattern:**
- Pure data constants
- Read-only lookup tables
- Never modified at runtime
- Used throughout application

---

### Alternative Pattern 1: **Module Constants (Current - RECOMMENDED)**

**Current State:**
```python
# utils/constants.py
SLOTS = [...]
DAYS = [...]
METRICS = {...}
```

**Pros:**
- ✅ Simple and Pythonic
- ✅ No overhead
- ✅ Easy to understand
- ✅ Standard Python practice
- ✅ Already well organized in separate module

**Cons:**
- ❌ Can be modified (though shouldn't be)
- ❌ All loaded at import time

**Recommendation:** **KEEP AS IS** - This is the correct pattern for constants.

**Optional Improvement:**
```python
# Make truly immutable with tuple for lists
SLOTS = ("day", "leadin", "location", "metric", ...)
DAYS = ("monday", "tuesday", "wednesday", ...)

# Use MappingProxyType for dicts to make read-only
from types import MappingProxyType
_METRICS = {"summary": ["summary", 1], ...}
METRICS = MappingProxyType(_METRICS)
```

**Pros:**
- ✅ Prevents accidental modification
- ✅ Signals intent (these are constants)

**Cons:**
- ❌ Slightly more complex
- ❌ Not common Python practice
- ❌ Minimal benefit (accidental modification is unlikely)

---

### Alternative Pattern 2: **Enum Classes**

**Implementation:**
```python
from enum import Enum, auto

class Slot(Enum):
    DAY = "day"
    LEADIN = "leadin"
    LOCATION = "location"
    METRIC = "metric"
    # ...

class Day(Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    # ...

# Usage
if slot_name == Slot.METRIC.value:
    # ...
```

**Pros:**
- ✅ Type-safe
- ✅ IDE autocomplete
- ✅ Cannot be modified
- ✅ Namespace protection

**Cons:**
- ❌ More verbose
- ❌ Requires .value access
- ❌ Doesn't fit all constant types (METRICS dict)
- ❌ Significant refactoring needed

**Migration Complexity:** High

**Recommendation:** **NOT RECOMMENDED** - Constants are fine as-is. Enums don't add enough value.

---

### Alternative Pattern 3: **Configuration Class**

**Implementation:**
```python
class Constants:
    """Application constants."""
    
    SLOTS = ["day", "leadin", ...]
    DAYS = ["monday", "tuesday", ...]
    METRICS = {"summary": ["summary", 1], ...}
    
    # Prevent instantiation
    def __init__(self):
        raise TypeError("Constants class cannot be instantiated")

# Usage
from utils.constants import Constants
for day in Constants.DAYS:
    # ...
```

**Pros:**
- ✅ Organized in namespace
- ✅ Cannot instantiate
- ✅ Clear they are constants

**Cons:**
- ❌ More verbose usage
- ❌ No real benefit over module
- ❌ Extra typing

**Migration Complexity:** Medium

**Recommendation:** **NOT RECOMMENDED** - Python modules already provide namespacing.

---

## 4. Module-Level Dependencies

### 4.1 Cross-Module Dependencies (weather/base.py & weather/location.py)

**Current Implementation:**
```python
# weather/base.py lines 31-32
notify = None
HTTPS = None

# Later in methods:
def https(self, path):
    global HTTPS, notify
    if HTTPS is None or notify is None:
        import lambda_function
        HTTPS = lambda_function.HTTPS
        notify = lambda_function.notify
    # ...

# weather/location.py line 27
GEOLOCATOR = None  # Set by lambda_function
```

**Usage Pattern:**
- Avoids circular import issues
- Late binding of dependencies
- Allows modules to be imported independently

---

### Alternative Pattern 1: **Lazy Import Function (RECOMMENDED)**

**Implementation:**
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

class WeatherBase:
    def https(self, path):
        client = _get_https_client()
        notify = _get_notify()
        # Use client and notify...
```

**Pros:**
- ✅ No global state
- ✅ Clear dependency
- ✅ Avoids circular imports
- ✅ Easy to mock for testing
- ✅ Function-level import is acceptable in Python

**Cons:**
- ❌ Import overhead per call (but cached by Python)
- ❌ Less obvious at module level

**Migration Complexity:** Low

**Recommendation:** **RECOMMENDED** - Cleaner than global variable approach.

---

### Alternative Pattern 2: **Dependency Injection (Already Discussed)**

**Implementation:**
```python
class WeatherBase:
    def __init__(self, event, cache_handler=None, http_client=None, notify_func=None):
        self.event = event
        self.cache_handler = cache_handler
        self.http_client = http_client
        self.notify_func = notify_func or default_notify
```

**Recommendation:** Already covered - high effort for this project.

---

### Alternative Pattern 3: **Module Registry Pattern**

**Implementation:**
```python
# utils/registry.py
class ServiceRegistry:
    """Central registry for shared services."""
    
    _services = {}
    
    @classmethod
    def register(cls, name, service):
        cls._services[name] = service
    
    @classmethod
    def get(cls, name):
        if name not in cls._services:
            raise ValueError(f"Service {name} not registered")
        return cls._services[name]

# lambda_function.py initialization
from utils.registry import ServiceRegistry
ServiceRegistry.register('https_client', HTTPS)
ServiceRegistry.register('geolocator', GEOLOCATOR)
ServiceRegistry.register('notify', notify)

# weather/base.py usage
from utils.registry import ServiceRegistry

class WeatherBase:
    def https(self, path):
        client = ServiceRegistry.get('https_client')
        notify = ServiceRegistry.get('notify')
        # ...
```

**Pros:**
- ✅ Centralized service management
- ✅ Late binding
- ✅ Easy to swap implementations
- ✅ Clear registration point

**Cons:**
- ❌ Added complexity
- ❌ String-based keys (typo prone)
- ❌ Not type-safe
- ❌ Overkill for this project

**Migration Complexity:** Medium-High

**Recommendation:** **NOT RECOMMENDED** - Too complex for the benefit.

---

## 5. Test Mode Variables

### 5.1 Test Mode Flags (lambda_function.py)

**Current Implementation:**
```python
# Lines 132-134
TEST_MODE = False
TEST_CACHE_HANDLER = None
TEST_SETTINGS_HANDLER = None

# Usage in line 997-1003
def get_skill_helper(self, handler_input):
    global TEST_MODE, TEST_CACHE_HANDLER, TEST_SETTINGS_HANDLER
    
    if TEST_MODE and TEST_CACHE_HANDLER and TEST_SETTINGS_HANDLER:
        cache_handler = TEST_CACHE_HANDLER
        settings_handler = TEST_SETTINGS_HANDLER
    else:
        # Use production handlers
        # ...
```

**Usage Pattern:**
- Enable local testing without DynamoDB
- Set by test_one() function
- Module-level test state

---

### Alternative Pattern 1: **Environment Variable (RECOMMENDED)**

**Implementation:**
```python
# Remove TEST_MODE globals

def get_skill_helper(self, handler_input):
    # Check environment for test mode
    is_test_mode = os.environ.get('CLIMACAST_TEST_MODE', '').lower() == 'true'
    
    if is_test_mode:
        # Use local handlers for testing
        cache_handler = LocalJsonCacheHandler(".test_cache")
        user_id = handler_input.request_envelope.session.user.user_id
        settings_handler = LocalJsonSettingsHandler(user_id, ".test_settings")
    else:
        # Use production handlers
        settings_handler = AlexaSettingsHandler(handler_input)
        cache_handler = CACHE_HANDLER
    
    skill = Skill(handler_input, cache_handler, settings_handler)
    return skill
```

**Pros:**
- ✅ No global state
- ✅ Standard testing pattern
- ✅ Clean separation of test/prod
- ✅ Can set per-run

**Cons:**
- ❌ Need to set environment variable
- ❌ Slightly more setup in tests

**Migration Complexity:** Low

**Recommendation:** **RECOMMENDED** - Standard practice for test/prod configuration.

---

### Alternative Pattern 2: **Test Fixture/Context Manager**

**Implementation:**
```python
class TestContext:
    """Context manager for test mode."""
    
    def __init__(self, cache_file=".test_cache", settings_file=".test_settings"):
        self.cache_file = cache_file
        self.settings_file = settings_file
        self.cache_handler = None
        self.settings_handler = None
    
    def __enter__(self):
        self.cache_handler = LocalJsonCacheHandler(self.cache_file)
        return self
    
    def __exit__(self, *args):
        # Cleanup if needed
        pass
    
    def get_settings_handler(self, user_id):
        return LocalJsonSettingsHandler(user_id, self.settings_file)

# Usage in tests
with TestContext() as test_ctx:
    skill = Skill(
        handler_input,
        test_ctx.cache_handler,
        test_ctx.get_settings_handler(user_id)
    )
```

**Pros:**
- ✅ Clean test setup/teardown
- ✅ Explicit test context
- ✅ Pythonic pattern

**Cons:**
- ❌ More complex
- ❌ Requires test refactoring

**Migration Complexity:** Medium

**Recommendation:** **OPTIONAL** - Nice for integration tests but not necessary.

---

## 6. Summary of Recommendations

### Recommended Changes (Priority Order)

#### Priority 1: High Value, Low Effort

1. **Convert Singleton Instances to Factory Functions**
   - `HTTPS` → `get_https_client()`
   - `GEOLOCATOR` → `get_geolocator()`
   - `CACHE_HANDLER` → `get_cache_handler()`
   - **Benefit:** Improved testability with minimal changes
   - **Effort:** 2-3 hours

2. **Replace Test Mode Globals with Environment Variable**
   - Remove `TEST_MODE`, `TEST_CACHE_HANDLER`, `TEST_SETTINGS_HANDLER`
   - Use `os.environ.get('CLIMACAST_TEST_MODE')`
   - **Benefit:** Cleaner, standard testing pattern
   - **Effort:** 1 hour

3. **Fix Cross-Module Dependencies**
   - Replace global variable late-binding with lazy import functions
   - `weather/base.py` and `weather/location.py`
   - **Benefit:** Clearer dependencies, easier testing
   - **Effort:** 1-2 hours

#### Priority 2: Good to Have, Medium Effort

4. **Remove Backward Compatibility Globals**
   - Remove `EVTID`, `APPID`, `HERE_API_KEY`, `DUID`, `TABLE_NAME`
   - Update all references to use `Config.XXX`
   - **Benefit:** Cleaner code, single source of truth
   - **Effort:** 2-3 hours

5. **Add Config Validation**
   - Add `Config.validate()` method
   - Check required configuration on startup
   - **Benefit:** Fail fast on misconfiguration
   - **Effort:** 1 hour

#### Priority 3: Nice to Have, Lower Priority

6. **Make Constants Immutable**
   - Use tuples instead of lists for sequence constants
   - Use `MappingProxyType` for dictionary constants
   - **Benefit:** Prevents accidental modification
   - **Effort:** 1 hour

7. **Add Type Hints to Factory Functions**
   - Ensure all factory functions have proper return types
   - **Benefit:** Better IDE support and type checking
   - **Effort:** 30 minutes

### Patterns to Keep As-Is

1. **Config Class** - Good pattern for configuration
2. **Constants Module** - Appropriate for lookup tables
3. **Module-Level Constants** - Standard Python practice

### Patterns to Avoid

1. **Dependency Injection Everywhere** - Too much refactoring
2. **Singleton Classes** - Unnecessary complexity
3. **Enum Classes for Constants** - Doesn't add enough value
4. **Service Registry** - Overkill for this project

---

## 7. Implementation Guide

### Phase 1: Factory Functions (Week 1)

**Step 1: Create factory functions**
```python
# lambda_function.py - add these functions

_https_client = None
def get_https_client() -> httpx.Client:
    """Get or create the global HTTPS client."""
    global _https_client
    if _https_client is None:
        _https_client = httpx.Client(
            timeout=Config.HTTP_TIMEOUT,
            follow_redirects=True
        )
    return _https_client

_geolocator_instance = None
def get_geolocator() -> Geolocator:
    """Get or create the global geolocator instance."""
    global _geolocator_instance
    if _geolocator_instance is None:
        _geolocator_instance = Geolocator(
            api_key=Config.HERE_API_KEY,
            session=get_https_client()
        )
    return _geolocator_instance

_cache_handler_instance = None
def get_cache_handler() -> CacheHandler:
    """Get or create the global cache handler instance."""
    global _cache_handler_instance
    if _cache_handler_instance is None:
        _cache_handler_instance = CacheHandler(
            table_name=Config.DYNAMODB_TABLE_NAME,
            region=Config.DYNAMODB_REGION
        )
    return _cache_handler_instance
```

**Step 2: Update usage**
```python
# Find and replace:
# HTTPS → get_https_client()
# GEOLOCATOR → get_geolocator()
# CACHE_HANDLER → get_cache_handler()
```

**Step 3: Keep old globals for backward compatibility**
```python
# Deprecated - use get_xxx() functions instead
HTTPS = get_https_client()
GEOLOCATOR = get_geolocator()
CACHE_HANDLER = get_cache_handler()
```

**Step 4: Test thoroughly**

---

### Phase 2: Test Mode Cleanup (Week 2)

**Step 1: Remove globals**
```python
# Delete these lines:
# TEST_MODE = False
# TEST_CACHE_HANDLER = None
# TEST_SETTINGS_HANDLER = None
```

**Step 2: Update get_skill_helper**
```python
def get_skill_helper(self, handler_input):
    is_test_mode = os.environ.get('CLIMACAST_TEST_MODE', '').lower() == 'true'
    
    if is_test_mode:
        cache_handler = LocalJsonCacheHandler(".test_cache")
        user_id = handler_input.request_envelope.session.user.user_id
        settings_handler = LocalJsonSettingsHandler(user_id, ".test_settings")
    else:
        settings_handler = AlexaSettingsHandler(handler_input)
        cache_handler = get_cache_handler()
    
    skill = Skill(handler_input, cache_handler, settings_handler)
    skill.initialize()
    return skill
```

**Step 3: Update test files**
```python
# Set environment in tests
os.environ['CLIMACAST_TEST_MODE'] = 'true'
```

---

### Phase 3: Cross-Module Dependencies (Week 3)

**Step 1: Create lazy import helpers**
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
```

**Step 2: Update usage**
```python
# Replace global variable lookups with function calls
def https(self, path):
    client = _get_https_client()
    notify_func = _get_notify()
    # Use them...
```

**Step 3: Remove global declarations**
```python
# Delete:
# notify = None
# HTTPS = None
# GEOLOCATOR = None
```

---

## 8. Testing Strategy

### Unit Tests
```python
# Test factory functions
def test_get_https_client():
    client = get_https_client()
    assert isinstance(client, httpx.Client)
    
    # Second call returns same instance
    client2 = get_https_client()
    assert client is client2

# Test with mocking
def test_weather_api_call(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = Mock(status_code=200, text='{"data": "test"}')
    
    # Patch the factory function
    monkeypatch.setattr('lambda_function.get_https_client', lambda: mock_client)
    
    # Test code that uses the client
    # ...
```

### Integration Tests
```python
# Test with environment variables
def test_test_mode():
    os.environ['CLIMACAST_TEST_MODE'] = 'true'
    # Create skill
    # Verify it uses local handlers
    # ...
    del os.environ['CLIMACAST_TEST_MODE']
```

---

## 9. Migration Risks and Mitigation

### Risk 1: Breaking Existing Tests
**Mitigation:**
- Run all tests before changes
- Update tests incrementally
- Keep backward compatibility during transition
- Use feature flags if needed

### Risk 2: Performance Impact
**Mitigation:**
- Factory functions are lightweight
- Python caches imports
- Measure before and after
- Lambda cold start impact should be negligible

### Risk 3: Circular Import Issues
**Mitigation:**
- Test imports carefully
- Use lazy imports where needed
- Keep dependency graph simple

---

## 10. Conclusion

### Summary

The Climacast codebase has a mix of global variables serving different purposes:
- **Configuration:** Well-structured in Config class - keep as-is
- **Singletons:** Convert to factory functions for testability
- **Constants:** Appropriate module-level constants - keep as-is
- **Test Mode:** Replace with environment variables
- **Cross-Module:** Fix with lazy imports

### Expected Benefits

1. **Improved Testability:** Easier to mock dependencies
2. **Cleaner Code:** Explicit dependencies, less global state
3. **Better Maintainability:** Clear initialization patterns
4. **Minimal Risk:** Incremental changes with backward compatibility

### Estimated Effort

- **Total Time:** 8-12 hours
- **Priority 1 Changes:** 4-6 hours
- **Priority 2 Changes:** 3-4 hours
- **Priority 3 Changes:** 1-2 hours

### Next Steps

1. Review this document with team
2. Prioritize changes based on value/effort
3. Implement Phase 1 (factory functions)
4. Test thoroughly
5. Proceed with Phases 2 and 3
6. Update documentation

---

## Appendix A: Complete Variable Inventory

### Lambda Function Module (lambda_function.py)

| Variable | Type | Current Pattern | Recommended |
|----------|------|----------------|-------------|
| VERSION | Integer | Module constant | Keep |
| REVISION | Integer | Module constant | Keep |
| Config.* | Class variables | Config class | Keep |
| EVTID | String | Backward compat | Remove |
| APPID | String | Backward compat | Remove |
| HERE_API_KEY | String | Backward compat | Remove |
| DUID | String | Backward compat | Remove |
| TABLE_NAME | String | Backward compat | Remove |
| NORMALIZE | Regex | Deprecated | Remove (already deprecated) |
| HTTPS | httpx.Client | Singleton | → get_https_client() |
| GEOLOCATOR | Geolocator | Singleton | → get_geolocator() |
| CACHE_HANDLER | CacheHandler | Singleton | → get_cache_handler() |
| TEST_MODE | Boolean | Test flag | → Environment variable |
| TEST_CACHE_HANDLER | Object | Test object | → Environment variable |
| TEST_SETTINGS_HANDLER | Object | Test object | → Environment variable |

### Constants Module (utils/constants.py)

| Variable | Type | Current Pattern | Recommended |
|----------|------|----------------|-------------|
| SLOTS | List | Module constant | Keep |
| QUARTERS | List | Module constant | Keep |
| DAYS | List | Module constant | Keep |
| MONTH_DAYS_XLATE | Dict | Module constant | Keep |
| MONTH_DAYS | List | Module constant | Keep |
| MONTH_NAMES | List | Module constant | Keep |
| METRICS | Dict | Module constant | Keep |
| ANGLES | List | Module constant | Keep |
| STATES | List | Module constant | Keep |
| SETTINGS | Dict | Module constant | Keep |
| TIME_QUARTERS | Dict | Module constant | Keep |
| WEATHER_COVERAGE | Dict | Module constant | Keep |
| WEATHER_WEATHER | Dict | Module constant | Keep |
| WEATHER_INTENSITY | Dict | Module constant | Keep |
| WEATHER_VISIBILITY | Dict | Module constant | Keep |
| WEATHER_ATTRIBUTES | Dict | Module constant | Keep |
| LOCATION_XLATE | Dict | Module constant | Keep |
| NORMALIZE_RE | List | Module constant | Keep |

### Weather Base Module (weather/base.py)

| Variable | Type | Current Pattern | Recommended |
|----------|------|----------------|-------------|
| notify | Function | Late binding | → Lazy import function |
| HTTPS | httpx.Client | Late binding | → Lazy import function |

### Weather Location Module (weather/location.py)

| Variable | Type | Current Pattern | Recommended |
|----------|------|----------------|-------------|
| GEOLOCATOR | Geolocator | Late binding | → Lazy import function |

---

## Appendix B: Code Examples

### Example: Mocking with Factory Functions

**Before (hard to mock):**
```python
# lambda_function.py
HTTPS = httpx.Client(timeout=30)

# weather/base.py
def https(self, path):
    response = HTTPS.get(f"https://api.weather.gov/{path}")
    # ...

# test_weather.py (difficult)
@patch('lambda_function.HTTPS')
def test_https_call(mock_https):
    # Have to patch module-level variable
    # Tricky import timing issues
    pass
```

**After (easy to mock):**
```python
# lambda_function.py
def get_https_client():
    global _https_client
    if _https_client is None:
        _https_client = httpx.Client(timeout=30)
    return _https_client

# weather/base.py
def https(self, path):
    client = get_https_client()
    response = client.get(f"https://api.weather.gov/{path}")
    # ...

# test_weather.py (easy)
@patch('lambda_function.get_https_client')
def test_https_call(mock_get_client):
    mock_client = Mock()
    mock_client.get.return_value = Mock(status_code=200, text='{"test": true}')
    mock_get_client.return_value = mock_client
    
    # Test code...
    # Works perfectly!
```

---

**End of Document**
