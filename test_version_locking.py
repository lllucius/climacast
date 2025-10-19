#!/usr/bin/env python3
"""
Test script to verify version-based locking for shared caches
"""

import os
import sys
from unittest.mock import MagicMock, Mock, call
from botocore.exceptions import ClientError

# Set environment variables before importing lambda_function
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['app_id'] = 'test-app-id'
os.environ['here_api_key'] = 'test-here-api-key'

# Add lambda directory to path
sys.path.insert(0, '/home/runner/work/climacast/climacast/lambda')

import lambda_function


def test_version_locking_success():
    """Test that version locking works correctly on successful write"""
    print("Testing version locking - successful write...")
    
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
    
    # Mock the DynamoDB table access
    original_ddb = lambda_function.DDB
    mock_table = Mock()
    
    # Simulate initial state with no version
    mock_table.get_item.return_value = {"Item": {"attributes": {}, "version": 0}}
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
        
        # Verify get_item was called to read current version
        assert mock_table.get_item.called, "get_item should have been called to read version"
        
        # Verify put_item was called with version incremented
        assert mock_table.put_item.called, "put_item should have been called"
        put_call_args = mock_table.put_item.call_args
        
        # Check that version was included in the Item
        assert "Item" in put_call_args[1], "Item should be in put_item call"
        assert "version" in put_call_args[1]["Item"], "version should be in Item"
        assert put_call_args[1]["Item"]["version"] == 1, "version should be incremented to 1"
        
        print("  ✓ Version locking successful write test passed!")
    finally:
        # Restore original DDB
        lambda_function.DDB = original_ddb


def test_version_locking_with_existing_version():
    """Test that version locking uses conditional expression with existing version"""
    print("Testing version locking - with existing version...")
    
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
    
    # Mock the DynamoDB table access
    original_ddb = lambda_function.DDB
    mock_table = Mock()
    
    # Simulate existing state with version 5
    mock_table.get_item.return_value = {
        "Item": {
            "attributes": {
                "LocationCache": {
                    "existing_key": {"location": "existing"}
                }
            },
            "version": 5
        }
    }
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
        
        # Verify put_item was called with conditional expression
        assert mock_table.put_item.called, "put_item should have been called"
        put_call_args = mock_table.put_item.call_args
        
        # Check that version was incremented
        assert put_call_args[1]["Item"]["version"] == 6, "version should be incremented to 6"
        
        # Check that conditional expression was used
        assert "ConditionExpression" in put_call_args[1], "ConditionExpression should be present"
        assert "ExpressionAttributeValues" in put_call_args[1], "ExpressionAttributeValues should be present"
        assert put_call_args[1]["ExpressionAttributeValues"][":current_version"] == 5, \
            "current_version should be 5"
        
        print("  ✓ Version locking with existing version test passed!")
    finally:
        # Restore original DDB
        lambda_function.DDB = original_ddb


def test_version_locking_retry_on_conflict():
    """Test that version locking retries on conditional check failure"""
    print("Testing version locking - retry on conflict...")
    
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
    
    # Mock the DynamoDB table access
    original_ddb = lambda_function.DDB
    mock_table = Mock()
    
    # Simulate version conflict on first attempt, then success
    # First get_item returns version 5
    # After retry, get_item returns version 6 (someone else updated it)
    mock_table.get_item.side_effect = [
        {"Item": {"attributes": {}, "version": 5}},
        {"Item": {"attributes": {}, "version": 6}}
    ]
    
    # First put_item raises ConditionalCheckFailedException
    # Second put_item succeeds
    conditional_error = ClientError(
        {
            "Error": {
                "Code": "ConditionalCheckFailedException",
                "Message": "The conditional request failed"
            }
        },
        "PutItem"
    )
    mock_table.put_item.side_effect = [conditional_error, {}]
    
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
        
        # Verify get_item was called twice (initial + retry)
        assert mock_table.get_item.call_count == 2, \
            f"get_item should have been called twice, but was called {mock_table.get_item.call_count} times"
        
        # Verify put_item was called twice (initial + retry)
        assert mock_table.put_item.call_count == 2, \
            f"put_item should have been called twice, but was called {mock_table.put_item.call_count} times"
        
        # Check that the second put_item used version 7 (6 + 1)
        second_put_call = mock_table.put_item.call_args_list[1]
        assert second_put_call[1]["Item"]["version"] == 7, \
            "Second attempt should use version 7"
        
        print("  ✓ Version locking retry test passed!")
    finally:
        # Restore original DDB
        lambda_function.DDB = original_ddb


def test_cache_get_with_version():
    """Test that cache_get properly handles version field"""
    print("Testing cache_get with version field...")
    
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
    
    # Mock the DynamoDB table access
    original_ddb = lambda_function.DDB
    mock_table = Mock()
    
    # Simulate cache with data and version
    mock_table.get_item.return_value = {
        "Item": {
            "attributes": {
                "LocationCache": {
                    "test_test": {
                        "location": "test city",
                        "city": "test",
                        "state": "test",
                        "ttl": 9999999999  # Far in the future
                    }
                }
            },
            "version": 3
        }
    }
    
    mock_ddb = Mock()
    mock_ddb.Table.return_value = mock_table
    lambda_function.DDB = mock_ddb
    
    try:
        test_key = {"city": "test", "state": "test"}
        result = base.cache_get("LocationCache", test_key)
        
        # Verify we got the item back
        assert result is not None, "Should retrieve cached item"
        assert result["location"] == "test city", "Retrieved item should match"
        
        # Verify get_item was called
        assert mock_table.get_item.called, "get_item should have been called"
        
        print("  ✓ cache_get with version test passed!")
    finally:
        # Restore original DDB
        lambda_function.DDB = original_ddb


def main():
    """Run all tests"""
    print("=" * 60)
    print("Version-Based Locking Tests for Shared Caches")
    print("=" * 60)
    
    try:
        test_version_locking_success()
        test_version_locking_with_existing_version()
        test_version_locking_retry_on_conflict()
        test_cache_get_with_version()
        
        print("\n" + "=" * 60)
        print("✓ ALL VERSION LOCKING TESTS PASSED!")
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
