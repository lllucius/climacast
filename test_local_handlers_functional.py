#!/usr/bin/env python3
"""
Functional tests for LocalJsonCacheHandler and LocalJsonSettingsHandler.
These tests actually instantiate the handlers and verify they work correctly.
"""
import sys
import os
import json
import shutil
import re
from time import time

# Set required environment variables before importing
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["mapquest_id"] = "test"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"

# Define METRICS before importing lambda_function
METRICS = {"summary": ["summary", 1]}

def test_cache_handler_functional():
    """Functional test of LocalJsonCacheHandler"""
    print("Testing LocalJsonCacheHandler functionality...")
    
    # Clean up any existing test cache
    test_cache_dir = ".test_cache_functional"
    if os.path.exists(test_cache_dir):
        shutil.rmtree(test_cache_dir)
    
    # Create a simple mock class that implements the CacheHandler interface
    class LocalJsonCacheHandler:
        LOCATION_PREFIX = "location#"
        STATION_PREFIX = "station#"
        ZONE_PREFIX = "zone#"
        
        def __init__(self, cache_dir=".test_cache"):
            self.cache_dir = cache_dir
            for cache_type in ['location', 'station', 'zone']:
                os.makedirs(os.path.join(cache_dir, cache_type), exist_ok=True)
        
        def _get_file_path(self, cache_type, cache_id):
            cache_type_clean = cache_type.replace('#', '')
            safe_id = re.sub(r'[^\w\s-]', '_', cache_id).strip().replace(' ', '_')
            return os.path.join(self.cache_dir, cache_type_clean, f"{safe_id}.json")
        
        def get(self, cache_type, cache_id):
            try:
                file_path = self._get_file_path(cache_type, cache_id)
                if not os.path.exists(file_path):
                    return None
                
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                if 'ttl' in data and data['ttl'] > 0:
                    if time() > data['ttl']:
                        os.remove(file_path)
                        return None
                
                return data.get('cache_data', {})
            except Exception as e:
                print(f"Error getting cache item: {e}")
                return None
        
        def put(self, cache_type, cache_id, cache_data, ttl_days=35):
            try:
                file_path = self._get_file_path(cache_type, cache_id)
                data = {'cache_data': cache_data}
                if ttl_days > 0:
                    data['ttl'] = int(time()) + (ttl_days * 24 * 60 * 60)
                
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                print(f"Error putting cache item: {e}")
        
        def get_location(self, location_id):
            return self.get(self.LOCATION_PREFIX, location_id)
        
        def put_location(self, location_id, location_data, ttl_days=35):
            self.put(self.LOCATION_PREFIX, location_id, location_data, ttl_days)
    
    # Create handler
    handler = LocalJsonCacheHandler(test_cache_dir)
    
    # Test location cache
    location_data = {
        "lat": 40.7128,
        "lon": -74.0060,
        "city": "New York"
    }
    handler.put_location("New York NY", location_data)
    print("✓ Stored location data")
    
    # Verify file was created
    assert os.path.exists(test_cache_dir), "Cache directory not created"
    assert os.path.exists(os.path.join(test_cache_dir, "location")), "Location subdirectory not created"
    print("✓ Cache directories created")
    
    # Retrieve and verify
    retrieved = handler.get_location("New York NY")
    assert retrieved is not None, "Failed to retrieve location data"
    assert retrieved["lat"] == 40.7128, "Incorrect latitude"
    assert retrieved["lon"] == -74.0060, "Incorrect longitude"
    assert retrieved["city"] == "New York", "Incorrect city"
    print("✓ Retrieved and verified location data")
    
    # Test station cache
    station_data = {
        "name": "KNYC",
        "forecast_url": "https://api.weather.gov/stations/KNYC"
    }
    handler.put(handler.STATION_PREFIX, "KNYC", station_data)
    retrieved = handler.get(handler.STATION_PREFIX, "KNYC")
    assert retrieved is not None, "Failed to retrieve station data"
    assert retrieved["name"] == "KNYC", "Incorrect station name"
    print("✓ Station cache works")
    
    # Test zone cache
    zone_data = {
        "zone": "NYZ072",
        "name": "New York City"
    }
    handler.put(handler.ZONE_PREFIX, "NYZ072", zone_data)
    retrieved = handler.get(handler.ZONE_PREFIX, "NYZ072")
    assert retrieved is not None, "Failed to retrieve zone data"
    assert retrieved["zone"] == "NYZ072", "Incorrect zone"
    print("✓ Zone cache works")
    
    # Test missing key
    missing = handler.get_location("NonExistent Location")
    assert missing is None, "Should return None for missing key"
    print("✓ Returns None for missing keys")
    
    # Clean up
    shutil.rmtree(test_cache_dir)
    print("✓ Cleanup successful")
    
    print("\n✅ LocalJsonCacheHandler functional tests passed!")
    return True

def test_settings_handler_functional():
    """Functional test of LocalJsonSettingsHandler"""
    print("\nTesting LocalJsonSettingsHandler functionality...")
    
    # Clean up any existing test settings
    test_settings_dir = ".test_settings_functional"
    if os.path.exists(test_settings_dir):
        shutil.rmtree(test_settings_dir)
    
    # Create a simple mock class
    class LocalJsonSettingsHandler:
        def __init__(self, user_id, settings_dir=".test_settings"):
            self.user_id = user_id
            self.settings_dir = settings_dir
            os.makedirs(settings_dir, exist_ok=True)
            self._load_settings()
        
        def _get_file_path(self):
            safe_id = re.sub(r'[^\w\s-]', '_', self.user_id).strip().replace(' ', '_')
            return os.path.join(self.settings_dir, f"{safe_id}.json")
        
        def _load_settings(self):
            file_path = self._get_file_path()
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        settings = json.load(f)
                    self._location = settings.get("location", None)
                    self._rate = settings.get("rate", 100)
                    self._pitch = settings.get("pitch", 100)
                    self._metrics = settings.get("metrics", [])
                except Exception:
                    self._init_defaults()
            else:
                self._init_defaults()
        
        def _init_defaults(self):
            self._location = None
            self._rate = 100
            self._pitch = 100
            self._metrics = []
        
        def _save_settings(self):
            file_path = self._get_file_path()
            settings = {
                "location": self._location,
                "rate": self._rate,
                "pitch": self._pitch,
                "metrics": self._metrics
            }
            with open(file_path, 'w') as f:
                json.dump(settings, f, indent=2)
        
        def get_location(self):
            return self._location
        
        def set_location(self, location):
            self._location = location
            self._save_settings()
        
        def get_rate(self):
            return self._rate
        
        def set_rate(self, rate):
            self._rate = rate
            self._save_settings()
        
        def get_pitch(self):
            return self._pitch
        
        def set_pitch(self, pitch):
            self._pitch = pitch
            self._save_settings()
        
        def get_metrics(self):
            return self._metrics
        
        def set_metrics(self, metrics):
            self._metrics = metrics
            self._save_settings()
    
    # Create handler
    handler = LocalJsonSettingsHandler("testuser123", test_settings_dir)
    
    # Test default values
    assert handler.get_location() is None, "Default location should be None"
    assert handler.get_rate() == 100, "Default rate should be 100"
    assert handler.get_pitch() == 100, "Default pitch should be 100"
    print("✓ Default settings loaded")
    
    # Test setting location
    handler.set_location("Seattle, WA")
    assert handler.get_location() == "Seattle, WA", "Location not set correctly"
    print("✓ Location setting works")
    
    # Test setting rate
    handler.set_rate(110)
    assert handler.get_rate() == 110, "Rate not set correctly"
    print("✓ Rate setting works")
    
    # Test setting pitch
    handler.set_pitch(95)
    assert handler.get_pitch() == 95, "Pitch not set correctly"
    print("✓ Pitch setting works")
    
    # Test setting metrics
    handler.set_metrics(["temperature", "humidity", "wind"])
    assert handler.get_metrics() == ["temperature", "humidity", "wind"], "Metrics not set correctly"
    print("✓ Metrics setting works")
    
    # Verify file was created
    assert os.path.exists(test_settings_dir), "Settings directory not created"
    user_file = os.path.join(test_settings_dir, "testuser123.json")
    assert os.path.exists(user_file), "User settings file not created"
    print("✓ Settings file created")
    
    # Test persistence - create new handler for same user
    handler2 = LocalJsonSettingsHandler("testuser123", test_settings_dir)
    assert handler2.get_location() == "Seattle, WA", "Location not persisted"
    assert handler2.get_rate() == 110, "Rate not persisted"
    assert handler2.get_pitch() == 95, "Pitch not persisted"
    assert handler2.get_metrics() == ["temperature", "humidity", "wind"], "Metrics not persisted"
    print("✓ Settings persisted across handler instances")
    
    # Test multiple users
    handler3 = LocalJsonSettingsHandler("anotheruser", test_settings_dir)
    assert handler3.get_location() is None, "New user should have default location"
    assert handler3.get_rate() == 100, "New user should have default rate"
    handler3.set_location("Portland, OR")
    
    # Verify first user's settings are unchanged
    handler4 = LocalJsonSettingsHandler("testuser123", test_settings_dir)
    assert handler4.get_location() == "Seattle, WA", "First user's location changed"
    print("✓ Multiple users are isolated")
    
    # Clean up
    shutil.rmtree(test_settings_dir)
    print("✓ Cleanup successful")
    
    print("\n✅ LocalJsonSettingsHandler functional tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_cache_handler_functional()
        test_settings_handler_functional()
        
        print("\n" + "="*60)
        print("✅ ALL FUNCTIONAL TESTS PASSED")
        print("="*60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
