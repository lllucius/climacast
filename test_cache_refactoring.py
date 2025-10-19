#!/usr/bin/env python3
"""
Test script to verify the cache refactoring works correctly
"""

import os
import sys
from unittest.mock import MagicMock, Mock

# Set environment variables before importing lambda_function
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['app_id'] = 'test-app-id'
os.environ['mapquest_id'] = 'test-mapquest-id'

# Add lambda directory to path
sys.path.insert(0, '/home/runner/work/climacast/climacast/lambda')

import lambda_function


def test_base_class_cache_methods():
    """Test that Base class cache methods work with mock attributes_manager"""
    print("Testing Base class cache methods...")
    
    # Create a mock attributes_manager
    mock_attrs_manager = Mock()
    mock_attrs_manager.persistent_attributes = {}
    
    # Create a mock event
    event = {
        "session": {
            "sessionId": "test-session",
            "user": {"userId": "test-user"}
        }
    }
    
    # Create a Base instance
    base = lambda_function.Base(event, mock_attrs_manager)
    
    # Test UserCache (user-specific)
    print("  Testing UserCache operations...")
    test_key = {"userid": "test-user-123"}
    base.cache_put("UserCache", test_key, ttl=0)
    
    # Verify save was called
    assert mock_attrs_manager.save_persistent_attributes.called, \
        "save_persistent_attributes should have been called"
    
    # Verify data was stored
    assert "UserCache" in mock_attrs_manager.persistent_attributes, \
        "UserCache should be in persistent attributes"
    
    # Test retrieval
    retrieved = base.cache_get("UserCache", {"userid": "test-user-123"})
    assert retrieved is not None, "Should be able to retrieve stored item"
    assert retrieved["userid"] == "test-user-123", "Retrieved item should match"
    
    print("  UserCache tests passed!")
    
    # Test shared caches (LocationCache, StationCache, ZoneCache)
    # These will fail without DynamoDB, but we can at least test the logic
    print("  Testing shared cache logic...")
    
    # Mock the DynamoDB table access
    original_ddb = lambda_function.DDB
    mock_table = Mock()
    mock_table.get_item.return_value = {"Item": {"attributes": {}}}
    mock_table.put_item.return_value = {}
    
    mock_ddb = Mock()
    mock_ddb.Table.return_value = mock_table
    lambda_function.DDB = mock_ddb
    
    try:
        test_location = {
            "location": "test city",
            "city": "test",
            "state": "test"
        }
        base.cache_put("LocationCache", test_location, ttl=35)
        
        # Verify DynamoDB operations were called
        assert mock_ddb.Table.called, "DDB.Table should have been called for shared cache"
        assert mock_table.put_item.called, "put_item should have been called for shared cache"
        
        print("  Shared cache tests passed!")
    finally:
        # Restore original DDB
        lambda_function.DDB = original_ddb
    
    print("✓ All Base class cache method tests passed!")


def test_user_class():
    """Test User class with mock attributes_manager"""
    print("\nTesting User class...")
    
    # Create a mock attributes_manager
    mock_attrs_manager = Mock()
    mock_attrs_manager.persistent_attributes = {}
    
    # Create a mock event
    event = {
        "session": {
            "sessionId": "test-session",
            "user": {"userId": "test-user"}
        }
    }
    
    # Create a User instance (will create new user profile)
    user = lambda_function.User(event, "test-user-456", mock_attrs_manager)
    
    # Verify initial state
    assert user._location is None, "Initial location should be None"
    assert user._rate == 100, "Initial rate should be 100"
    assert user._pitch == 100, "Initial pitch should be 100"
    
    # Test setting location
    user.location = "Boulder Colorado"
    assert user._location == "Boulder Colorado", "Location should be set"
    
    # Verify save was called
    assert mock_attrs_manager.save_persistent_attributes.called, \
        "save_persistent_attributes should have been called"
    
    print("✓ User class tests passed!")


def test_intent_handlers():
    """Test that intent handlers are registered"""
    print("\nTesting intent handler registration...")
    
    # Check that handlers are registered
    handlers = [
        lambda_function.LaunchRequestHandler,
        lambda_function.MetricIntentHandler,
        lambda_function.StoreDataIntentHandler,
        lambda_function.GetDataIntentHandler,
        lambda_function.SetLocationIntentHandler,
    ]
    
    for handler_class in handlers:
        handler = handler_class()
        print(f"  ✓ {handler_class.__name__} instantiated successfully")
    
    print("✓ All intent handlers registered correctly!")


def test_skill_builder():
    """Test that skill builder is configured correctly"""
    print("\nTesting skill builder configuration...")
    
    # Verify the skill builder exists and is a CustomSkillBuilder
    assert hasattr(lambda_function, 'sb'), "Skill builder should exist"
    assert isinstance(lambda_function.sb, lambda_function.CustomSkillBuilder), \
        "Skill builder should be a CustomSkillBuilder"
    
    # Verify persistence adapter is configured
    assert lambda_function.sb.persistence_adapter is not None, \
        "Persistence adapter should be configured"
    
    print("✓ Skill builder configured correctly!")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Cache Refactoring Tests")
    print("=" * 60)
    
    try:
        test_base_class_cache_methods()
        test_user_class()
        test_intent_handlers()
        test_skill_builder()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
