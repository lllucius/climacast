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

from unittest.mock import Mock, patch  # noqa: E402

from lambda_function import Location, get_geolocator  # noqa: E402


def test_location_uses_geolocator():
    """Test that Location.mapquest method uses get_geolocator"""
    print("Testing Location integration with Geolocator...")

    # Create a mock event
    event = {
        "session": {"sessionId": "test-session", "user": {"userId": "test-user"}},
        "request": {"type": "LaunchRequest", "requestId": "test-request"},
    }

    # Create a Location instance
    location = Location(event, cache_handler=None)

    # Mock the geolocator instance
    with patch("lambda_function.get_geolocator") as mock_get_geolocator:
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = (
            (40.7128, -74.0060),
            {"State": "New York", "City": "New York"},
        )
        mock_get_geolocator.return_value = mock_geolocator

        # Call the mapquest method
        coords, props = location.mapquest("New York NY")

        # Verify the geolocator was called
        mock_geolocator.geocode.assert_called_once_with("New York NY")

        # Verify the results
        assert coords == (40.7128, -74.0060)
        assert props == {"State": "New York", "City": "New York"}

    print("✓ Location.mapquest correctly delegates to get_geolocator")
    print()


def test_location_handles_geocoding_failure():
    """Test that Location handles geocoding failures gracefully"""
    print("Testing Location handles geocoding failures...")

    event = {
        "session": {"sessionId": "test-session", "user": {"userId": "test-user"}},
        "request": {"type": "LaunchRequest", "requestId": "test-request"},
    }

    location = Location(event, cache_handler=None)

    # Mock the geolocator to return None
    with patch("lambda_function.get_geolocator") as mock_get_geolocator:
        mock_geolocator = Mock()
        mock_geolocator.geocode.return_value = (None, None)
        mock_get_geolocator.return_value = mock_geolocator

        coords, props = location.mapquest("InvalidLocation")

        assert coords is None
        assert props is None

    print("✓ Location handles geocoding failures correctly")
    print()


def test_geolocator_initialized_with_api_key():
    """Test that get_geolocator returns initialized geolocator"""
    print("Testing geolocator initialization...")

    geolocator = get_geolocator()
    assert geolocator is not None
    assert geolocator.api_key == "test_key"
    assert geolocator.base_url == "https://geocode.search.hereapi.com/v1"

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
