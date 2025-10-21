#!/usr/bin/env python3
"""
Unit tests for Geolocator class.
"""
import os
import sys

# Set required environment variables
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test"

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from geolocator import Geolocator


def test_geolocator_initialization():
    """Test that Geolocator can be initialized"""
    print("Testing Geolocator initialization...")
    
    geolocator = Geolocator("test_api_key")
    assert geolocator.api_key == "test_api_key"
    assert geolocator.base_url == "https://geocode.search.hereapi.com/v1"
    
    print("✓ Geolocator initialized successfully")
    print()


def test_geolocator_without_api_key():
    """Test that Geolocator handles missing API key gracefully"""
    print("Testing Geolocator without API key...")
    
    geolocator = Geolocator("")
    coords, props = geolocator.geocode("Miami Florida")
    
    assert coords is None
    assert props is None
    
    print("✓ Geolocator handles missing API key correctly")
    print()


def test_geolocator_interface():
    """Test that Geolocator has the expected interface"""
    print("Testing Geolocator interface...")
    
    geolocator = Geolocator("test_api_key")
    
    # Check that geocode method exists
    assert hasattr(geolocator, 'geocode')
    assert callable(geolocator.geocode)
    
    print("✓ Geolocator has correct interface")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Running Geolocator Tests")
    print("=" * 60)
    print()
    
    test_geolocator_initialization()
    test_geolocator_without_api_key()
    test_geolocator_interface()
    
    print("=" * 60)
    print("✅ ALL GEOLOCATOR TESTS PASSED")
    print("=" * 60)
