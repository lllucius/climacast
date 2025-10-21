# User Settings Refactoring Summary

## Overview
This refactoring separates user settings management into a dedicated `SettingsHandler` class, following the same pattern used for the `CacheHandler` class in PR #20. This provides a clean separation of concerns and allows for different user settings backends.

## Changes Made

### 1. New SettingsHandler Class (lambda_function.py)
Created a base `SettingsHandler` class that defines the interface for user settings operations:
- `get_location()` / `set_location(location)` - Manage user's default location
- `get_rate()` / `set_rate(rate)` - Manage speech rate setting
- `get_pitch()` / `set_pitch(pitch)` - Manage speech pitch setting
- `get_metrics()` / `set_metrics(metrics)` - Manage custom forecast metrics

### 2. AlexaSettingsHandler Implementation
Created `AlexaSettingsHandler` as the default implementation that uses Alexa's `attributes_manager` for persistent storage:
- Uses `handler_input.attributes_manager.persistent_attributes` to store/retrieve settings
- Maintains backward compatibility with existing user data
- Automatically saves changes via `save_persistent_attributes()`

### 3. Updated Skill Class
Modified the `Skill` class to use the settings handler:
- Added `settings_handler` parameter to `__init__()` method
- Removed direct access to `attributes_manager` for user settings
- Updated all properties (`user_location`, `user_rate`, `user_pitch`, `user_metrics`) to delegate to `settings_handler`
- Removed old `_load_user_settings()` and `_save_user_settings()` methods
- Updated `initialize()` method to use settings handler instead of loading settings directly

### 4. Updated BaseIntentHandler
Modified to create and pass the settings handler:
- Creates `AlexaSettingsHandler` instance with `handler_input`
- Passes both `cache_handler` and `settings_handler` to `Skill` constructor

### 5. New Tests (test_settings_handler.py)
Added comprehensive tests to verify:
- `SettingsHandler` and `AlexaSettingsHandler` class structure
- All required methods are implemented
- Settings logic is properly separated from Skill class
- Integration with attributes_manager

### 6. Updated Tests (test_cache_handler.py)
Updated existing tests to accommodate the new signature and structure:
- Updated Skill `__init__` signature check to include `settings_handler` parameter
- Updated assertions to reflect that settings are now in a separate handler class

## Benefits

1. **Separation of Concerns**: User settings management is now isolated in its own class, making the code more maintainable and testable.

2. **Backend Flexibility**: The abstract `SettingsHandler` base class allows for different implementations:
   - Default: `AlexaSettingsHandler` using attributes_manager
   - Future: Could add file-based, database, or custom storage backends

3. **Consistent Architecture**: Follows the same pattern as `CacheHandler`, creating a consistent design pattern throughout the codebase.

4. **Backward Compatible**: The `AlexaSettingsHandler` implementation maintains full backward compatibility with existing user data stored in DynamoDB.

5. **Testability**: Settings logic can now be tested independently, and mock implementations can be easily created for testing.

## Code Statistics

- SettingsHandler base class: ~42 lines
- AlexaSettingsHandler implementation: ~86 lines
- Total settings handling code: ~128 lines
- Skill class: Reduced by ~87 lines (settings logic moved to handler)
- Net change: ~41 lines added (settings abstraction overhead)

## Testing

All tests pass successfully:
- ✅ test_settings_handler.py - New tests for settings handler
- ✅ test_cache_handler.py - Updated existing tests
- ✅ CodeQL security check - No vulnerabilities found

## Migration Notes

No migration is required. The refactoring maintains backward compatibility:
- Existing user settings stored in DynamoDB continue to work unchanged
- The `AlexaSettingsHandler` uses the same persistent attributes structure
- No changes to the DynamoDB schema or data

## Example Usage

To use a custom settings backend:

```python
# Create custom settings handler
class CustomSettingsHandler(SettingsHandler):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        # Load from custom storage
        
    def get_location(self):
        # Custom implementation
        pass
        
    # ... implement other methods

# In BaseIntentHandler
def get_skill_helper(self, handler_input):
    # Use custom settings handler instead of Alexa's
    settings_handler = CustomSettingsHandler(user_id)
    skill = Skill(handler_input, CACHE_HANDLER, settings_handler)
    skill.initialize()
    return skill
```

## Conclusion

This refactoring successfully separates user settings management into a dedicated handler class, providing a clean architecture that mirrors the cache handler implementation and allows for flexible storage backends while maintaining full backward compatibility.
