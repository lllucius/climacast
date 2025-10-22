#!/usr/bin/env python3
"""
Unit tests for CacheHandler class.
Tests the cache key structure and logic without requiring DynamoDB.
"""
import sys
import os

# Set required environment variables before importing
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"

def test_cache_handler_structure():
    """Test that CacheHandler has the expected structure"""
    # Check that CacheHandler is in storage/cache_handler.py
    
    print("Testing CacheHandler structure...")
    
    # Check lambda_function.py imports CacheHandler
    with open("lambda_function.py", "r") as f:
        lambda_content = f.read()
    
    assert "from storage.cache_handler import CacheHandler" in lambda_content, \
        "CacheHandler not imported in lambda_function.py"
    print("✓ CacheHandler imported in lambda_function.py")
    
    # Check storage/cache_handler.py for class definition
    with open("storage/cache_handler.py", "r") as f:
        content = f.read()
    
    # Check for CacheHandler class
    assert ("class CacheHandler(object):" in content or
            "class CacheHandler:" in content), "CacheHandler class not found"
    print("✓ CacheHandler class exists")
    
    # Check for key prefixes
    assert 'LOCATION_PREFIX = "location#"' in content, "LOCATION_PREFIX not found"
    assert 'STATION_PREFIX = "station#"' in content, "STATION_PREFIX not found"
    assert 'ZONE_PREFIX = "zone#"' in content, "ZONE_PREFIX not found"
    print("✓ Cache type prefixes defined")
    
    # Check for cache methods
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
    print("✓ All cache methods defined")
    
    # Check lambda_function.py for cache handler factory function
    assert "def get_cache_handler()" in lambda_content, "get_cache_handler factory function not found"
    print("✓ Cache handler factory function exists")
    
    # Check that User class is removed
    assert "class User(Base):" not in lambda_content, "User class still exists (should be removed)"
    print("✓ User class removed")
    
    # Check that Skill class uses cache_handler
    assert "def __init__(self, handler_input, cache_handler=None, settings_handler=None):" in lambda_content, "Skill doesn't accept cache_handler"
    print("✓ Skill class accepts cache_handler parameter")
    
    # Check that settings are now in SettingsHandler, not directly in Skill
    # AlexaSettingsHandler is in storage/settings_handler.py
    with open("storage/settings_handler.py", "r") as f:
        settings_content = f.read()
    
    assert "class AlexaSettingsHandler" in settings_content, "AlexaSettingsHandler not found"
    assert "persistent_attributes" in settings_content, "persistent_attributes not used"
    print("✓ Settings moved to separate SettingsHandler class")
    
    # Check that Base class accepts cache_handler (in weather/base.py)
    with open("weather/base.py", "r") as f:
        base_content = f.read()
    
    assert ("def __init__(self, event, cache_handler=None):" in base_content or
            "def __init__(self, event: Dict[str, Any], cache_handler=None)" in base_content), \
        "Base doesn't accept cache_handler"
    print("✓ Base class accepts cache_handler parameter")
    
    # Check DynamoDB persistence adapter
    assert "from ask_sdk_dynamodb.adapter import DynamoDbAdapter" in lambda_content, "DynamoDbAdapter import not found"
    assert "persistence_adapter = DynamoDbAdapter" in lambda_content, "DynamoDbAdapter not instantiated"
    print("✓ DynamoDB persistence adapter configured")
    
    print("\n✅ All CacheHandler structure tests passed!")
    return True

def test_cache_key_structure():
    """Test the cache key structure logic"""
    print("\nTesting cache key structure...")
    
    # Test key format
    prefix = "location#"
    cache_id = "Miami Florida"
    expected_pk = f"{prefix}{cache_id}"
    expected_sk = "data"
    
    print(f"  Expected PK format: {expected_pk}")
    print(f"  Expected SK: {expected_sk}")
    
    # Verify the key structure in storage/cache_handler.py
    with open("storage/cache_handler.py", "r") as f:
        content = f.read()
    
    # Check _make_key method
    assert ('"pk": f"{cache_type}{cache_id}"' in content or
            "'pk': f\"{cache_type}{cache_id}\"" in content), "PK format incorrect"
    assert ('"sk": "data"' in content or
            "'sk': \"data\"" in content), "SK format incorrect"
    print("✓ Cache key structure is correct")
    
    print("\n✅ Cache key structure tests passed!")
    return True

def test_single_table_design():
    """Verify single table design is implemented"""
    print("\nTesting single table design...")
    
    # Check storage/cache_handler.py
    with open("storage/cache_handler.py", "r") as f:
        content = f.read()
    
    # Check that old table references are removed
    assert 'DDB.Table("LocationCache")' not in content, "Old LocationCache table reference found"
    assert 'DDB.Table("StationCache")' not in content, "Old StationCache table reference found"
    assert 'DDB.Table("UserCache")' not in content, "Old UserCache table reference found"
    assert 'DDB.Table("ZoneCache")' not in content, "Old ZoneCache table reference found"
    print("✓ Old separate table references removed")
    
    # Check that single table is used
    assert ("self.table = self.ddb.Table(table_name)" in content or
            "self.table = DDB.Table(table_name)" in content), "Single table not used in CacheHandler"
    print("✓ Single table design implemented")
    
    # Check that cache_data is used
    assert ('"cache_data": cache_data' in content or
            "'cache_data': cache_data" in content), "cache_data not stored"
    assert ('item.get("cache_data"' in content or
            "item.get('cache_data'" in content), "cache_data not retrieved"
    print("✓ Cache data stored in cache_data attribute")
    
    print("\n✅ Single table design tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_cache_handler_structure()
        test_cache_key_structure()
        test_single_table_design()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
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
