#!/usr/bin/env python3
"""
Test script to verify the refactoring works correctly.
"""

import sys
import os

# Set dummy AWS credentials for testing
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'dummy'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy'
os.environ['mapquest_id'] = os.environ.get('mapquest_id', 'test')

def test_imports():
    """Test that all modules import correctly"""
    print("Testing imports...")
    
    try:
        import weather_processor
        print("✓ weather_processor imports successfully")
    except Exception as e:
        print(f"✗ weather_processor import failed: {e}")
        return False
    
    try:
        import lambda_function
        print("✓ lambda_function imports successfully")
    except Exception as e:
        print(f"✗ lambda_function import failed: {e}")
        return False
    
    try:
        import cli
        print("✓ cli imports successfully")
    except Exception as e:
        print(f"✗ cli import failed: {e}")
        return False
    
    return True

def test_classes():
    """Test that classes are accessible"""
    print("\nTesting classes...")
    
    try:
        from weather_processor import Base, GridPoints, Observations, Alerts, Location, User
        print("✓ All classes import successfully from weather_processor")
    except Exception as e:
        print(f"✗ Class import failed: {e}")
        return False
    
    # Test class instantiation with minimal event
    event = {
        "session": {
            "new": True,
            "sessionId": "test",
            "application": {"applicationId": "test"},
            "attributes": {},
            "user": {"userId": "test"},
            "testing": True
        },
        "request": {"type": "test"}
    }
    
    try:
        base = Base(event)
        print("✓ Base class instantiates successfully")
    except Exception as e:
        print(f"✗ Base class instantiation failed: {e}")
        return False
    
    try:
        location = Location(event)
        print("✓ Location class instantiates successfully")
    except Exception as e:
        print(f"✗ Location class instantiation failed: {e}")
        return False
    
    return True

def test_lambda_function():
    """Test that lambda_function has the handler"""
    print("\nTesting lambda function...")
    
    try:
        import lambda_function
        
        if hasattr(lambda_function, 'lambda_handler'):
            print("✓ lambda_handler function exists")
        else:
            print("✗ lambda_handler function not found")
            return False
        
        if hasattr(lambda_function, 'sb'):
            print("✓ SkillBuilder (sb) exists")
        else:
            print("✗ SkillBuilder (sb) not found")
            return False
        
    except Exception as e:
        print(f"✗ Lambda function test failed: {e}")
        return False
    
    return True

def test_cli():
    """Test that CLI has main function"""
    print("\nTesting CLI...")
    
    try:
        import cli
        
        if hasattr(cli, 'main'):
            print("✓ CLI main function exists")
        else:
            print("✗ CLI main function not found")
            return False
        
        if hasattr(cli, 'get_current_conditions'):
            print("✓ get_current_conditions function exists")
        else:
            print("✗ get_current_conditions function not found")
            return False
        
        if hasattr(cli, 'get_forecast'):
            print("✓ get_forecast function exists")
        else:
            print("✗ get_forecast function not found")
            return False
        
        if hasattr(cli, 'get_alerts'):
            print("✓ get_alerts function exists")
        else:
            print("✗ get_alerts function not found")
            return False
        
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False
    
    return True

def test_constants():
    """Test that constants are accessible"""
    print("\nTesting constants...")
    
    try:
        from weather_processor import METRICS, DAYS, MONTH_NAMES, STATES
        print(f"✓ METRICS defined ({len(METRICS)} metrics)")
        print(f"✓ DAYS defined ({len(DAYS)} days)")
        print(f"✓ MONTH_NAMES defined ({len(MONTH_NAMES)} months)")
        print(f"✓ STATES defined ({len(STATES)} states)")
    except Exception as e:
        print(f"✗ Constants test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Refactored Code Structure")
    print("=" * 60)
    
    all_passed = True
    
    all_passed = test_imports() and all_passed
    all_passed = test_classes() and all_passed
    all_passed = test_lambda_function() and all_passed
    all_passed = test_cli() and all_passed
    all_passed = test_constants() and all_passed
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some tests failed!")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
