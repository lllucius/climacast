#!/usr/bin/env python3
"""
Integration test for Geolocator with Location class.
Tests that the mapquest method properly delegates to the Geolocator.
"""
import os
import sys

# Set required environment variables before importing
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test_key"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_TABLE_NAME"] = "test-table"

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lambda_function import Location, GEOLOCATOR
from unittest.mock import Mock, patch


def test_location_uses_geolocator():
    """Test that Location.mapquest method uses GEOLOCATOR"""
    print("Testing Location integration with Geolocator...")
    
    # Create a mock event
    event = {
        "session": {
            "sessionId": "test-session",
            "user": {"userId": "test-user"}
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "test-request"
        }
    }
    
    # Create a Location instance
    location = Location(event, cache_handler=None)
    
    # Mock the GEOLOCATOR.geocode method
    with patch.object(GEOLOCATOR, 'geocode') as mock_geocode:
        # Set up the mock to return test data
        mock_geocode.return_value = ((40.7128, -74.0060), {"State": "New York", "City": "New York"})
        
        # Call the mapquest method
        coords, props = location.mapquest("New York NY")
        
        # Verify the geolocator was called
        mock_geocode.assert_called_once_with("New York NY")
        
        # Verify the results
        assert coords == (40.7128, -74.0060)
        assert props == {"State": "New York", "City": "New York"}
    
    print("✓ Location.mapquest correctly delegates to GEOLOCATOR")
    print()


def test_location_handles_geocoding_failure():
    """Test that Location handles geocoding failures gracefully"""
    print("Testing Location handles geocoding failures...")
    
    event = {
        "session": {
            "sessionId": "test-session",
            "user": {"userId": "test-user"}
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "test-request"
        }
    }
    
    location = Location(event, cache_handler=None)
    
    # Mock the GEOLOCATOR.geocode method to return None
    with patch.object(GEOLOCATOR, 'geocode') as mock_geocode:
        mock_geocode.return_value = (None, None)
        
        coords, props = location.mapquest("InvalidLocation")
        
        assert coords is None
        assert props is None
    
    print("✓ Location handles geocoding failures correctly")
    print()


def test_geolocator_initialized_with_api_key():
    """Test that GEOLOCATOR is initialized with the HERE_API_KEY"""
    print("Testing GEOLOCATOR initialization...")
    
    assert GEOLOCATOR is not None
    assert GEOLOCATOR.api_key == "test_key"
    assert GEOLOCATOR.base_url == "https://geocode.search.hereapi.com/v1"
    
    print("✓ GEOLOCATOR initialized with correct API key")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Running Geolocator Integration Tests")
    print("=" * 60)
    print()
    
    test_geolocator_initialized_with_api_key()
    test_location_uses_geolocator()
    test_location_handles_geocoding_failure()
    
    print("=" * 60)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("=" * 60)
