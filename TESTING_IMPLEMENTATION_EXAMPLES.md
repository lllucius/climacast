# Local Testing Implementation Examples

This document provides concrete code examples of what the local testing infrastructure would look like for the Clima Cast Alexa skill. These examples demonstrate the practical implementation of the concepts outlined in the LOCAL_TESTING_ANALYSIS.md document.

## Table of Contents

1. [Mock Classes](#mock-classes)
2. [Test Runner](#test-runner)
3. [Test Fixtures](#test-fixtures)
4. [Service Abstraction](#service-abstraction)
5. [Complete Test Example](#complete-test-example)

## Mock Classes

### MockCacheHandler

```python
# tests/mocks/mock_cache_handler.py

class MockCacheHandler:
    """
    In-memory mock of CacheHandler for testing without DynamoDB.
    Simulates cache operations using Python dictionaries.
    """
    
    def __init__(self):
        """Initialize in-memory storage"""
        self._cache = {}
    
    def _make_key(self, cache_type, cache_id):
        """Create a cache key"""
        return f"{cache_type}{cache_id}"
    
    def get(self, cache_type, cache_id):
        """Retrieve an item from cache"""
        key = self._make_key(cache_type, cache_id)
        return self._cache.get(key)
    
    def put(self, cache_type, cache_id, cache_data, ttl_days=35):
        """Store an item in cache"""
        key = self._make_key(cache_type, cache_id)
        self._cache[key] = cache_data
    
    def get_location(self, location_id):
        """Get location cache data"""
        return self.get("location#", location_id)
    
    def put_location(self, location_id, location_data, ttl_days=35):
        """Store location cache data"""
        self.put("location#", location_id, location_data, ttl_days)
    
    def get_station(self, station_id):
        """Get station cache data"""
        return self.get("station#", station_id)
    
    def put_station(self, station_id, station_data, ttl_days=35):
        """Store station cache data"""
        self.put("station#", station_id, station_data, ttl_days)
    
    def get_zone(self, zone_id):
        """Get zone cache data"""
        return self.get("zone#", zone_id)
    
    def put_zone(self, zone_id, zone_data, ttl_days=35):
        """Store zone cache data"""
        self.put("zone#", zone_id, zone_data, ttl_days)
    
    def clear(self):
        """Clear all cached data (useful between tests)"""
        self._cache = {}
    
    def load_fixtures(self, fixtures):
        """Load test fixtures into cache"""
        for cache_type, items in fixtures.items():
            for item_id, item_data in items.items():
                self.put(cache_type, item_id, item_data)
```

### MockSettingsHandler

```python
# tests/mocks/mock_settings_handler.py

class MockSettingsHandler:
    """
    In-memory mock of SettingsHandler for testing without DynamoDB.
    Simulates user settings using Python dictionaries.
    """
    
    def __init__(self, user_id="test-user"):
        """Initialize with test user ID"""
        self.user_id = user_id
        self._settings = {}
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default settings"""
        self._settings = {
            "location": None,
            "rate": 100,
            "pitch": 100,
            "metrics": self._get_default_metrics()
        }
    
    def _get_default_metrics(self):
        """Get default metrics list"""
        # Copy logic from AlexaSettingsHandler
        return ["summary", "temperature", "precipitation", "skys", 
                "wind", "barometric pressure", "relative humidity", "dewpoint"]
    
    def get_location(self):
        """Get user's default location"""
        return self._settings.get("location")
    
    def set_location(self, location):
        """Set user's default location"""
        self._settings["location"] = location
    
    def get_rate(self):
        """Get user's speech rate setting"""
        return self._settings.get("rate", 100)
    
    def set_rate(self, rate):
        """Set user's speech rate setting"""
        self._settings["rate"] = rate
    
    def get_pitch(self):
        """Get user's speech pitch setting"""
        return self._settings.get("pitch", 100)
    
    def set_pitch(self, pitch):
        """Set user's speech pitch setting"""
        self._settings["pitch"] = pitch
    
    def get_metrics(self):
        """Get user's custom metrics list"""
        return self._settings.get("metrics", self._get_default_metrics())
    
    def set_metrics(self, metrics):
        """Set user's custom metrics list"""
        self._settings["metrics"] = metrics
    
    def reset(self):
        """Reset to default settings"""
        self._load_defaults()
    
    def load_profile(self, profile):
        """Load a specific test profile"""
        self._settings.update(profile)
```

### MockHTTPSession

```python
# tests/mocks/mock_http_session.py

import json
import re
from pathlib import Path

class MockHTTPSession:
    """
    Mock HTTP session that returns predefined responses instead of making real API calls.
    """
    
    def __init__(self, fixture_dir="tests/fixtures/api_mocks"):
        """Initialize with fixture directory"""
        self.fixture_dir = Path(fixture_dir)
        self.url_patterns = []
        self.call_log = []
    
    def register_pattern(self, pattern, fixture_file):
        """
        Register a URL pattern with corresponding fixture file.
        
        Args:
            pattern: Regex pattern to match URLs
            fixture_file: Path to JSON fixture file (relative to fixture_dir)
        """
        self.url_patterns.append({
            "pattern": re.compile(pattern),
            "fixture": fixture_file
        })
    
    def get(self, url, headers=None):
        """
        Mock GET request that returns fixture data.
        
        Args:
            url: Request URL
            headers: Request headers (ignored in mock)
        
        Returns:
            MockResponse object with status_code and text/json
        """
        # Log the call
        self.call_log.append({"method": "GET", "url": url, "headers": headers})
        
        # Find matching pattern
        for pattern_info in self.url_patterns:
            if pattern_info["pattern"].search(url):
                fixture_path = self.fixture_dir / pattern_info["fixture"]
                
                if fixture_path.exists():
                    with open(fixture_path, 'r') as f:
                        data = json.load(f)
                    return MockResponse(200, json.dumps(data), data)
                else:
                    return MockResponse(404, '{"error": "Fixture not found"}', 
                                      {"error": "Fixture not found"})
        
        # No pattern matched
        return MockResponse(404, '{"error": "No mock registered for this URL"}',
                          {"error": f"No mock registered for: {url}"})
    
    def clear_log(self):
        """Clear call log"""
        self.call_log = []
    
    def get_calls(self):
        """Get all logged calls"""
        return self.call_log

class MockResponse:
    """Mock response object"""
    
    def __init__(self, status_code, text, json_data):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self.content = text.encode('utf-8')
        self.url = ""
    
    def json(self):
        """Return JSON data"""
        return self._json_data
```

## Test Runner

### Basic Test Runner

```python
# tests/test_runner.py

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import mocks
from tests.mocks.mock_cache_handler import MockCacheHandler
from tests.mocks.mock_settings_handler import MockSettingsHandler
from tests.mocks.mock_http_session import MockHTTPSession

# Set environment for testing
os.environ["TESTING"] = "true"
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["mapquest_id"] = "test"

class TestRunner:
    """
    Test runner for Clima Cast skill using predefined JSON files.
    """
    
    def __init__(self, config_file="tests/test_config.json"):
        """Initialize test runner with configuration"""
        self.config = self.load_config(config_file)
        self.results = []
        self.setup_mocks()
    
    def load_config(self, config_file):
        """Load test configuration"""
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def setup_mocks(self):
        """Setup mock services"""
        # Create mock instances
        self.mock_cache = MockCacheHandler()
        self.mock_http = MockHTTPSession(self.config.get("mock_data_dir", "tests/fixtures/api_mocks"))
        
        # Load cache fixtures if specified
        if "cache_fixtures" in self.config:
            self.mock_cache.load_fixtures(self.config["cache_fixtures"])
        
        # Register HTTP patterns
        if "api_patterns" in self.config:
            for pattern_info in self.config["api_patterns"]:
                self.mock_http.register_pattern(
                    pattern_info["pattern"],
                    pattern_info["fixture"]
                )
        
        # Replace global instances in lambda_function
        import lambda_function
        lambda_function.CACHE_HANDLER = self.mock_cache
        lambda_function.HTTPS = self.mock_http
    
    def run_test(self, test_file: str, expected: Dict = None) -> Dict:
        """
        Run a single test from JSON file.
        
        Args:
            test_file: Path to test JSON file
            expected: Expected response characteristics
        
        Returns:
            Test result dictionary
        """
        print(f"\nRunning test: {test_file}")
        
        # Load test JSON
        with open(test_file, 'r') as f:
            event = json.load(f)
        
        # Setup test user settings if specified
        user_id = event["session"]["user"]["userId"]
        test_settings = self.get_test_user_settings(user_id)
        if test_settings:
            mock_settings = MockSettingsHandler(user_id)
            mock_settings.load_profile(test_settings)
        
        # Execute test
        try:
            from lambda_function import lambda_handler
            response = lambda_handler(event, None)
            
            # Validate response
            validation_result = self.validate_response(response, expected)
            
            result = {
                "test_file": test_file,
                "status": "PASSED" if validation_result["passed"] else "FAILED",
                "response": response,
                "validation": validation_result,
                "error": None
            }
            
        except Exception as e:
            result = {
                "test_file": test_file,
                "status": "ERROR",
                "response": None,
                "validation": None,
                "error": str(e)
            }
            import traceback
            result["traceback"] = traceback.format_exc()
        
        self.results.append(result)
        return result
    
    def get_test_user_settings(self, user_id: str) -> Dict:
        """Get settings for test user"""
        test_users = self.config.get("test_users", {})
        return test_users.get(user_id, {})
    
    def validate_response(self, response: Dict, expected: Dict) -> Dict:
        """
        Validate response against expected characteristics.
        
        Args:
            response: Actual response from lambda_handler
            expected: Expected response characteristics
        
        Returns:
            Validation result with passed status and details
        """
        if expected is None:
            return {"passed": True, "checks": []}
        
        checks = []
        all_passed = True
        
        # Check response structure
        if "response" not in response:
            checks.append({
                "check": "response_structure",
                "passed": False,
                "message": "Response missing 'response' key"
            })
            all_passed = False
        else:
            checks.append({
                "check": "response_structure",
                "passed": True,
                "message": "Response has correct structure"
            })
        
        # Check for expected text in speech output
        if "contains" in expected:
            speech = self.extract_speech_text(response)
            for expected_text in expected["contains"]:
                if expected_text.lower() in speech.lower():
                    checks.append({
                        "check": f"contains '{expected_text}'",
                        "passed": True,
                        "message": f"Speech contains expected text"
                    })
                else:
                    checks.append({
                        "check": f"contains '{expected_text}'",
                        "passed": False,
                        "message": f"Speech does not contain: {expected_text}"
                    })
                    all_passed = False
        
        # Check session end flag
        if "should_end_session" in expected:
            actual_end = response.get("response", {}).get("shouldEndSession", True)
            expected_end = expected["should_end_session"]
            passed = actual_end == expected_end
            checks.append({
                "check": "should_end_session",
                "passed": passed,
                "message": f"Expected {expected_end}, got {actual_end}"
            })
            if not passed:
                all_passed = False
        
        return {
            "passed": all_passed,
            "checks": checks
        }
    
    def extract_speech_text(self, response: Dict) -> str:
        """Extract plain text from speech output"""
        output_speech = response.get("response", {}).get("outputSpeech", {})
        
        if output_speech.get("type") == "SSML":
            import re
            ssml = output_speech.get("ssml", "")
            # Remove SSML tags
            text = re.sub(r'<[^>]+>', '', ssml)
            return text
        elif output_speech.get("type") == "PlainText":
            return output_speech.get("text", "")
        
        return ""
    
    def run_test_suite(self, test_files: List[str], suite_name: str = ""):
        """Run multiple tests"""
        print(f"\n{'='*60}")
        print(f"Running test suite: {suite_name or 'Default'}")
        print(f"{'='*60}")
        
        for test_file in test_files:
            # Get expected results if configured
            expected = None
            for test_config in self.config.get("tests", []):
                if test_config.get("file") == test_file:
                    expected = test_config.get("expected", {})
                    break
            
            result = self.run_test(test_file, expected)
            
            # Print result
            status_symbol = "✓" if result["status"] == "PASSED" else "✗"
            print(f"{status_symbol} {result['test_file']}: {result['status']}")
            
            if result["status"] == "FAILED" and result["validation"]:
                for check in result["validation"]["checks"]:
                    if not check["passed"]:
                        print(f"  - {check['message']}")
            
            if result["status"] == "ERROR":
                print(f"  Error: {result['error']}")
    
    def print_summary(self):
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        print(f"\n{'='*60}")
        print(f"Test Summary")
        print(f"{'='*60}")
        print(f"Total:  {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Errors: {errors}")
        print(f"\nSuccess Rate: {(passed/total*100) if total > 0 else 0:.1f}%")
        
        return passed == total

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clima Cast Test Runner")
    parser.add_argument("--config", default="tests/test_config.json",
                       help="Test configuration file")
    parser.add_argument("--file", help="Run single test file")
    parser.add_argument("--suite", help="Run specific test suite")
    parser.add_argument("--verbose", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    runner = TestRunner(args.config)
    
    if args.file:
        # Run single test
        result = runner.run_test(args.file)
        runner.print_summary()
        sys.exit(0 if result["status"] == "PASSED" else 1)
    
    elif args.suite:
        # Run specific suite
        suites = runner.config.get("test_suites", [])
        for suite in suites:
            if suite["name"] == args.suite:
                test_files = [t["file"] for t in suite["tests"]]
                runner.run_test_suite(test_files, suite["name"])
                break
    else:
        # Run all suites
        suites = runner.config.get("test_suites", [])
        for suite in suites:
            test_files = [t["file"] for t in suite["tests"]]
            runner.run_test_suite(test_files, suite["name"])
    
    success = runner.print_summary()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
```

## Test Fixtures

### Example Test Request Files

#### Launch Request
```json
// tests/fixtures/requests/launch/launch_new_user.json
{
  "version": "1.0",
  "session": {
    "new": true,
    "sessionId": "amzn1.echo-api.session.test-launch-001",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "attributes": {},
    "user": {
      "userId": "test-user-new"
    }
  },
  "context": {
    "System": {
      "application": {
        "applicationId": "amzn1.ask.skill.test"
      },
      "user": {
        "userId": "test-user-new"
      },
      "device": {
        "deviceId": "amzn1.ask.device.test"
      }
    }
  },
  "request": {
    "type": "LaunchRequest",
    "requestId": "amzn1.echo-api.request.test-launch-001",
    "timestamp": "2024-01-15T10:00:00Z",
    "locale": "en-US"
  }
}
```

#### Current Temperature Query
```json
// tests/fixtures/requests/intents/metric/current_temp_no_location.json
{
  "version": "1.0",
  "session": {
    "new": false,
    "sessionId": "amzn1.echo-api.session.test-metric-001",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "attributes": {},
    "user": {
      "userId": "test-user-configured"
    }
  },
  "context": {
    "System": {
      "application": {
        "applicationId": "amzn1.ask.skill.test"
      },
      "user": {
        "userId": "test-user-configured"
      }
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.test-metric-001",
    "timestamp": "2024-01-15T10:05:00Z",
    "locale": "en-US",
    "intent": {
      "name": "MetricIntent",
      "confirmationStatus": "NONE",
      "slots": {
        "metric": {
          "name": "metric",
          "value": "temperature",
          "confirmationStatus": "NONE"
        }
      }
    }
  }
}
```

#### Forecast Query with Location and Time
```json
// tests/fixtures/requests/intents/metric/forecast_tomorrow_with_location.json
{
  "version": "1.0",
  "session": {
    "new": false,
    "sessionId": "amzn1.echo-api.session.test-metric-002",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "attributes": {},
    "user": {
      "userId": "test-user-001"
    }
  },
  "context": {
    "System": {
      "application": {
        "applicationId": "amzn1.ask.skill.test"
      },
      "user": {
        "userId": "test-user-001"
      }
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.test-metric-002",
    "timestamp": "2024-01-15T14:30:00Z",
    "locale": "en-US",
    "intent": {
      "name": "MetricIntent",
      "confirmationStatus": "NONE",
      "slots": {
        "metric": {
          "name": "metric",
          "value": "forecast",
          "confirmationStatus": "NONE"
        },
        "when_any": {
          "name": "when_any",
          "value": "tomorrow",
          "confirmationStatus": "NONE"
        },
        "location": {
          "name": "location",
          "value": "seattle washington",
          "confirmationStatus": "NONE"
        }
      }
    }
  }
}
```

#### Set Location Intent
```json
// tests/fixtures/requests/intents/settings/set_location_city_state.json
{
  "version": "1.0",
  "session": {
    "new": false,
    "sessionId": "amzn1.echo-api.session.test-settings-001",
    "application": {
      "applicationId": "amzn1.ask.skill.test"
    },
    "attributes": {},
    "user": {
      "userId": "test-user-001"
    }
  },
  "context": {
    "System": {
      "application": {
        "applicationId": "amzn1.ask.skill.test"
      },
      "user": {
        "userId": "test-user-001"
      }
    }
  },
  "request": {
    "type": "IntentRequest",
    "requestId": "amzn1.echo-api.request.test-settings-001",
    "timestamp": "2024-01-15T10:00:00Z",
    "locale": "en-US",
    "intent": {
      "name": "SetLocationIntent",
      "confirmationStatus": "NONE",
      "slots": {
        "location": {
          "name": "location",
          "value": "boulder colorado",
          "confirmationStatus": "NONE"
        }
      }
    }
  }
}
```

### Example Mock API Responses

#### NWS Points Response
```json
// tests/fixtures/api_mocks/nws/points/seattle_wa.json
{
  "@context": ["https://geojson.org/geojson-ld/geojson-context.jsonld"],
  "id": "https://api.weather.gov/points/47.6062,-122.3321",
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [-122.3321, 47.6062]
  },
  "properties": {
    "cwa": "SEW",
    "forecastOffice": "https://api.weather.gov/offices/SEW",
    "gridId": "SEW",
    "gridX": 124,
    "gridY": 67,
    "forecast": "https://api.weather.gov/gridpoints/SEW/124,67/forecast",
    "forecastHourly": "https://api.weather.gov/gridpoints/SEW/124,67/forecast/hourly",
    "forecastGridData": "https://api.weather.gov/gridpoints/SEW/124,67",
    "observationStations": "https://api.weather.gov/gridpoints/SEW/124,67/stations",
    "relativeLocation": {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-122.3321, 47.6062]
      },
      "properties": {
        "city": "Seattle",
        "state": "WA"
      }
    },
    "forecastZone": "https://api.weather.gov/zones/forecast/WAZ558",
    "county": "https://api.weather.gov/zones/county/WAC033",
    "fireWeatherZone": "https://api.weather.gov/zones/fire/WAZ654",
    "timeZone": "America/Los_Angeles"
  }
}
```

#### Station Observations XML Mock
```xml
<!-- tests/fixtures/api_mocks/nws/observations/KSEA.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<current_observation>
  <credit>NOAA's National Weather Service</credit>
  <location>Seattle-Tacoma International Airport, WA</location>
  <station_id>KSEA</station_id>
  <latitude>47.45</latitude>
  <longitude>-122.31</longitude>
  <observation_time>Last Updated on Jan 15 2024, 10:53 am PST</observation_time>
  <observation_time_rfc822>Mon, 15 Jan 2024 10:53:00 -0800</observation_time_rfc822>
  <weather>Overcast</weather>
  <temperature_string>45.0 F (7.2 C)</temperature_string>
  <temp_f>45.0</temp_f>
  <temp_c>7.2</temp_c>
  <relative_humidity>87</relative_humidity>
  <wind_string>Southwest at 12.7 MPH (11 KT)</wind_string>
  <wind_dir>Southwest</wind_dir>
  <wind_degrees>230</wind_degrees>
  <wind_mph>12.7</wind_mph>
  <wind_kt>11</wind_kt>
  <pressure_string>1013.6 mb</pressure_string>
  <pressure_mb>1013.6</pressure_mb>
  <pressure_in>29.93</pressure_in>
  <dewpoint_string>41.0 F (5.0 C)</dewpoint_string>
  <dewpoint_f>41.0</dewpoint_f>
  <dewpoint_c>5.0</dewpoint_c>
  <visibility_mi>10.00</visibility_mi>
</current_observation>
```

### Test Configuration File

```json
// tests/test_config.json
{
  "mock_data_dir": "tests/fixtures/api_mocks",
  "test_users": {
    "test-user-new": {},
    "test-user-configured": {
      "location": "seattle washington",
      "pitch": 100,
      "rate": 100,
      "metrics": ["summary", "temperature", "precipitation", "wind"]
    },
    "test-user-001": {
      "location": "boulder colorado",
      "pitch": 95,
      "rate": 110,
      "metrics": ["summary", "temperature", "precipitation", "skys", "wind", "relative humidity"]
    }
  },
  "cache_fixtures": {
    "location#": {
      "seattle washington": {
        "location": "seattle washington",
        "city": "seattle",
        "state": "washington",
        "coords": "47.6062,-122.3321",
        "cwa": "SEW",
        "gridPoint": "124,67",
        "timeZone": "America/Los_Angeles",
        "forecastZoneId": "WAZ558",
        "forecastZoneName": "Seattle Area",
        "countyZoneId": "WAC033",
        "countyZoneName": "King County",
        "observationStations": ["KSEA", "KBFI", "KRNT"]
      }
    },
    "station#": {
      "KSEA": {
        "id": "KSEA",
        "name": "Seattle-Tacoma International Airport"
      }
    }
  },
  "api_patterns": [
    {
      "pattern": "api\\.weather\\.gov/points/47\\.6062,-122\\.3321",
      "fixture": "nws/points/seattle_wa.json"
    },
    {
      "pattern": "api\\.weather\\.gov/points/25\\.7617,-80\\.1918",
      "fixture": "nws/points/miami_fl.json"
    },
    {
      "pattern": "w1\\.weather\\.gov/xml/current_obs/KSEA\\.xml",
      "fixture": "nws/observations/KSEA.xml"
    }
  ],
  "test_suites": [
    {
      "name": "Core Intents",
      "tests": [
        {
          "file": "tests/fixtures/requests/launch/launch_new_user.json",
          "expected": {
            "contains": ["Welcome to Clime a Cast", "set your default location"],
            "should_end_session": false
          }
        },
        {
          "file": "tests/fixtures/requests/intents/help.json",
          "expected": {
            "contains": ["complete information", "Clima Cast skill page"],
            "should_end_session": false
          }
        }
      ]
    },
    {
      "name": "Weather Queries",
      "tests": [
        {
          "file": "tests/fixtures/requests/intents/metric/current_temp_no_location.json",
          "expected": {
            "contains": ["temperature", "degrees"],
            "should_end_session": false
          }
        },
        {
          "file": "tests/fixtures/requests/intents/metric/forecast_tomorrow_with_location.json",
          "expected": {
            "contains": ["tomorrow", "seattle"],
            "should_end_session": false
          }
        }
      ]
    },
    {
      "name": "Settings Management",
      "tests": [
        {
          "file": "tests/fixtures/requests/intents/settings/set_location_city_state.json",
          "expected": {
            "contains": ["default location has been set", "boulder colorado"],
            "should_end_session": false
          }
        }
      ]
    }
  ]
}
```

## Service Abstraction

### Weather Service Interface

```python
# tests/services/weather_service.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

class WeatherService(ABC):
    """Abstract interface for weather data retrieval"""
    
    @abstractmethod
    def get_point_info(self, lat: float, lon: float) -> Optional[Dict]:
        """Get point information for coordinates"""
        pass
    
    @abstractmethod
    def get_gridpoints(self, cwa: str, grid_x: int, grid_y: int) -> Optional[Dict]:
        """Get gridpoint data"""
        pass
    
    @abstractmethod
    def get_forecast(self, cwa: str, grid_x: int, grid_y: int) -> Optional[Dict]:
        """Get forecast data"""
        pass
    
    @abstractmethod
    def get_station_obs(self, station_id: str) -> Optional[str]:
        """Get station observations XML"""
        pass
    
    @abstractmethod
    def get_alerts(self, zone_id: str) -> Optional[Dict]:
        """Get active alerts for zone"""
        pass
    
    @abstractmethod
    def get_zone_info(self, zone_type: str, zone_id: str) -> Optional[Dict]:
        """Get zone information"""
        pass

class RealWeatherService(WeatherService):
    """Real NWS API implementation"""
    
    def __init__(self, http_session):
        self.http = http_session
        self.base_url = "https://api.weather.gov"
    
    def get_point_info(self, lat: float, lon: float) -> Optional[Dict]:
        url = f"{self.base_url}/points/{lat:.4f},{lon:.4f}"
        response = self.http.get(url)
        return response.json() if response.status_code == 200 else None
    
    def get_gridpoints(self, cwa: str, grid_x: int, grid_y: int) -> Optional[Dict]:
        url = f"{self.base_url}/gridpoints/{cwa}/{grid_x},{grid_y}"
        response = self.http.get(url)
        return response.json() if response.status_code == 200 else None
    
    # ... implement other methods

class MockWeatherService(WeatherService):
    """Mock implementation for testing"""
    
    def __init__(self, fixture_loader):
        self.fixtures = fixture_loader
    
    def get_point_info(self, lat: float, lon: float) -> Optional[Dict]:
        # Load from fixture based on coordinates
        fixture_key = f"points/{lat:.4f}_{lon:.4f}"
        return self.fixtures.load(fixture_key)
    
    def get_gridpoints(self, cwa: str, grid_x: int, grid_y: int) -> Optional[Dict]:
        fixture_key = f"gridpoints/{cwa}_{grid_x}_{grid_y}"
        return self.fixtures.load(fixture_key)
    
    # ... implement other methods with fixture loading
```

## Complete Test Example

### End-to-End Test Script

```python
# tests/test_complete_flow.py

"""
Complete end-to-end test demonstrating the full testing workflow.
"""

import sys
import os
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup testing environment
os.environ["TESTING"] = "true"
os.environ["app_id"] = "amzn1.ask.skill.test"

from tests.test_runner import TestRunner

def test_new_user_flow():
    """
    Test complete flow for new user:
    1. Launch skill
    2. Try to ask for weather (should prompt for location)
    3. Set location
    4. Ask for weather again (should work)
    """
    print("\n" + "="*60)
    print("Testing: New User Complete Flow")
    print("="*60)
    
    runner = TestRunner("tests/test_config.json")
    
    # Step 1: Launch
    print("\nStep 1: Launch skill as new user")
    result1 = runner.run_test(
        "tests/fixtures/requests/launch/launch_new_user.json",
        expected={"contains": ["Welcome", "set your default location"]}
    )
    assert result1["status"] == "PASSED", "Launch failed"
    print("✓ Launch successful, prompted for location")
    
    # Step 2: Try weather query without location
    print("\nStep 2: Ask for weather without setting location")
    result2 = runner.run_test(
        "tests/fixtures/requests/intents/metric/current_conditions_no_location.json",
        expected={"contains": ["must set a default location"]}
    )
    assert result2["status"] == "PASSED", "Should prompt for location"
    print("✓ Correctly prompted for location")
    
    # Step 3: Set location
    print("\nStep 3: Set default location")
    result3 = runner.run_test(
        "tests/fixtures/requests/intents/settings/set_location_seattle.json",
        expected={"contains": ["default location has been set", "seattle"]}
    )
    assert result3["status"] == "PASSED", "Set location failed"
    print("✓ Location set successfully")
    
    # Step 4: Weather query with location
    print("\nStep 4: Ask for weather again")
    result4 = runner.run_test(
        "tests/fixtures/requests/intents/metric/current_conditions_use_default.json",
        expected={"contains": ["temperature", "seattle"]}
    )
    assert result4["status"] == "PASSED", "Weather query failed"
    print("✓ Weather query successful")
    
    print("\n" + "="*60)
    print("Complete Flow Test: PASSED")
    print("="*60)

def test_forecast_queries():
    """Test various forecast query patterns"""
    print("\n" + "="*60)
    print("Testing: Forecast Query Variations")
    print("="*60)
    
    runner = TestRunner("tests/test_config.json")
    
    test_cases = [
        ("Tomorrow's forecast", 
         "tests/fixtures/requests/intents/metric/forecast_tomorrow.json",
         ["tomorrow"]),
        
        ("Monday afternoon forecast",
         "tests/fixtures/requests/intents/metric/forecast_monday_afternoon.json",
         ["monday", "afternoon"]),
        
        ("Will it rain check",
         "tests/fixtures/requests/intents/metric/will_it_rain_tomorrow.json",
         ["precipitation", "chance"]),
    ]
    
    for name, test_file, expected_words in test_cases:
        print(f"\nTesting: {name}")
        result = runner.run_test(test_file, expected={"contains": expected_words})
        assert result["status"] == "PASSED", f"{name} failed"
        print(f"✓ {name} passed")
    
    print("\n" + "="*60)
    print("Forecast Query Tests: ALL PASSED")
    print("="*60)

if __name__ == "__main__":
    try:
        test_new_user_flow()
        test_forecast_queries()
        print("\n" + "="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
```

## Usage Examples

### Running Tests

```bash
# Run all tests
python tests/test_runner.py

# Run specific test file
python tests/test_runner.py --file tests/fixtures/requests/launch/launch_new_user.json

# Run specific test suite
python tests/test_runner.py --suite "Weather Queries"

# Run with verbose output
python tests/test_runner.py --verbose

# Run complete flow tests
python tests/test_complete_flow.py
```

### Creating New Test Cases

```bash
# 1. Create JSON request file
# tests/fixtures/requests/intents/metric/my_test.json

# 2. Create any needed mock API responses
# tests/fixtures/api_mocks/nws/my_response.json

# 3. Add to test configuration
# Edit tests/test_config.json and add test to appropriate suite

# 4. Run the test
python tests/test_runner.py --file tests/fixtures/requests/intents/metric/my_test.json
```

## Conclusion

This implementation provides:

1. **Comprehensive mocking** - No external dependencies during testing
2. **Easy test creation** - Just add JSON files
3. **Flexible validation** - Check response content and behavior
4. **Extensible design** - Easy to add new test cases and validations
5. **Clear documentation** - Examples for all common scenarios

The testing infrastructure allows developers to:
- Test locally without AWS credentials
- Create reproducible test scenarios
- Validate all skill functionality
- Debug issues effectively
- Maintain high code quality
