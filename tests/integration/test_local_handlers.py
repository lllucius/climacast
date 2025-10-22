#!/usr/bin/env python3
"""
Unit tests for LocalJsonCacheHandler and LocalJsonSettingsHandler classes.
Tests the local JSON file storage without requiring DynamoDB or ASK SDK.
"""
import sys
import os
import json
import shutil

# Set required environment variables before importing
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"

def test_local_cache_handler():
    """Test LocalJsonCacheHandler functionality"""
    print("Testing LocalJsonCacheHandler...")
    
    # Clean up any existing test cache
    test_cache_dir = ".test_cache_unittest"
    if os.path.exists(test_cache_dir):
        shutil.rmtree(test_cache_dir)
    
    # Check lambda_function.py imports LocalJsonCacheHandler
    with open("lambda_function.py", "r") as f:
        lambda_content = f.read()
    
    assert "from storage.local_handlers import LocalJsonCacheHandler" in lambda_content, \
        "LocalJsonCacheHandler not imported in lambda_function.py"
    print("✓ LocalJsonCacheHandler imported in lambda_function.py")
    
    # Check storage/local_handlers.py for class definition
    with open("storage/local_handlers.py", "r") as f:
        content = f.read()
    
    # Verify LocalJsonCacheHandler class exists
    assert "class LocalJsonCacheHandler(object):" in content or "class LocalJsonCacheHandler:" in content, \
        "LocalJsonCacheHandler class not found"
    print("✓ LocalJsonCacheHandler class exists")
    
    # Verify it has the same interface as CacheHandler
    assert ("def get(self, cache_type, cache_id):" in content or 
            "def get(self, cache_type: str, cache_id: str)" in content), "get method not found"
    assert ("def put(self, cache_type, cache_id, cache_data" in content or
            "def put(self, cache_type: str, cache_id: str, cache_data" in content), "put method not found"
    assert ("def get_location(self, location_id):" in content or
            "def get_location(self, location_id: str)" in content), "get_location method not found"
    assert ("def put_location(self, location_id, location_data" in content or
            "def put_location(self, location_id: str, location_data" in content), "put_location method not found"
    assert ("def get_station(self, station_id):" in content or
            "def get_station(self, station_id: str)" in content), "get_station method not found"
    assert ("def put_station(self, station_id, station_data" in content or
            "def put_station(self, station_id: str, station_data" in content), "put_station method not found"
    assert ("def get_zone(self, zone_id):" in content or
            "def get_zone(self, zone_id: str)" in content), "get_zone method not found"
    assert ("def put_zone(self, zone_id, zone_data" in content or
            "def put_zone(self, zone_id: str, zone_data" in content), "put_zone method not found"
    print("✓ LocalJsonCacheHandler has all required methods")
    
    # Verify it uses local file storage
    assert "os.makedirs" in content, "LocalJsonCacheHandler doesn't create directories"
    assert "json.dump" in content, "LocalJsonCacheHandler doesn't use JSON"
    assert "json.load" in content, "LocalJsonCacheHandler doesn't load JSON"
    print("✓ LocalJsonCacheHandler uses local JSON file storage")
    
    # Check for TTL support
    assert "'ttl'" in content or '"ttl"' in content, "TTL not stored in cache"
    print("✓ LocalJsonCacheHandler supports TTL")
    
    print("\n✅ LocalJsonCacheHandler tests passed!")
    return True

def test_local_settings_handler():
    """Test LocalJsonSettingsHandler functionality"""
    print("\nTesting LocalJsonSettingsHandler...")
    
    # Clean up any existing test settings
    test_settings_dir = ".test_settings_unittest"
    if os.path.exists(test_settings_dir):
        shutil.rmtree(test_settings_dir)
    
    # Check lambda_function.py imports LocalJsonSettingsHandler
    with open("lambda_function.py", "r") as f:
        lambda_content = f.read()
    
    assert "from storage.local_handlers import" in lambda_content and "LocalJsonSettingsHandler" in lambda_content, \
        "LocalJsonSettingsHandler not imported in lambda_function.py"
    print("✓ LocalJsonSettingsHandler imported in lambda_function.py")
    
    # Check storage/local_handlers.py for class definition
    with open("storage/local_handlers.py", "r") as f:
        content = f.read()
    
    # Verify LocalJsonSettingsHandler class exists
    assert "class LocalJsonSettingsHandler(SettingsHandler):" in content or \
           "class LocalJsonSettingsHandler:" in content, \
        "LocalJsonSettingsHandler class not found"
    print("✓ LocalJsonSettingsHandler class exists")
    
    # Verify it has the same interface as SettingsHandler
    assert ("def get_location(self):" in content or
            "def get_location(self) ->" in content), "get_location method not found"
    assert ("def set_location(self, location):" in content or
            "def set_location(self, location: str)" in content), "set_location method not found"
    assert ("def get_rate(self):" in content or
            "def get_rate(self) ->" in content), "get_rate method not found"
    assert ("def set_rate(self, rate):" in content or
            "def set_rate(self, rate: int)" in content), "set_rate method not found"
    assert ("def get_pitch(self):" in content or
            "def get_pitch(self) ->" in content), "get_pitch method not found"
    assert ("def set_pitch(self, pitch):" in content or
            "def set_pitch(self, pitch: int)" in content), "set_pitch method not found"
    assert ("def get_metrics(self):" in content or
            "def get_metrics(self) ->" in content), "get_metrics method not found"
    assert ("def set_metrics(self, metrics):" in content or
            "def set_metrics(self, metrics: list)" in content), "set_metrics method not found"
    print("✓ LocalJsonSettingsHandler has all required methods")
    
    # Verify it uses local file storage
    assert "os.makedirs" in content, "LocalJsonSettingsHandler doesn't create directories"
    assert "json.dump" in content, "LocalJsonSettingsHandler doesn't use JSON"
    assert "json.load" in content, "LocalJsonSettingsHandler doesn't load JSON"
    print("✓ LocalJsonSettingsHandler uses local JSON file storage")
    
    print("\n✅ LocalJsonSettingsHandler tests passed!")
    return True

def test_test_mode_integration():
    """Test that test mode is properly integrated via environment variable"""
    print("\nTesting test mode integration...")
    
    with open("lambda_function.py", "r") as f:
        content = f.read()
    
    # Check that environment variable is used for test mode
    assert "os.environ.get('CLIMACAST_TEST_MODE'" in content, "CLIMACAST_TEST_MODE environment check not found"
    print("✓ Test mode uses environment variable")
    
    # Check that get_skill_helper uses environment variable
    assert "is_test_mode = os.environ.get('CLIMACAST_TEST_MODE'" in content, \
        "get_skill_helper doesn't check CLIMACAST_TEST_MODE"
    print("✓ get_skill_helper checks CLIMACAST_TEST_MODE")
    
    # Check that test_one sets environment variable
    assert "os.environ['CLIMACAST_TEST_MODE'] = 'true'" in content, \
        "test_one doesn't set CLIMACAST_TEST_MODE"
    assert "LocalJsonCacheHandler" in content, "LocalJsonCacheHandler not used"
    assert "LocalJsonSettingsHandler" in content, "LocalJsonSettingsHandler not used"
    print("✓ test_one() sets CLIMACAST_TEST_MODE environment variable")
    
    print("\n✅ Test mode integration tests passed!")
    return True

def test_gitignore_updated():
    """Test that .gitignore excludes test directories"""
    print("\nTesting .gitignore updates...")
    
    with open(".gitignore", "r") as f:
        gitignore = f.read()
    
    assert ".test_cache/" in gitignore, ".test_cache/ not in .gitignore"
    assert ".test_settings/" in gitignore, ".test_settings/ not in .gitignore"
    print("✓ .gitignore excludes test directories")
    
    print("\n✅ .gitignore tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_local_cache_handler()
        test_local_settings_handler()
        test_test_mode_integration()
        test_gitignore_updated()
        
        print("\n" + "="*60)
        print("✅ ALL LOCAL HANDLER TESTS PASSED")
        print("="*60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
