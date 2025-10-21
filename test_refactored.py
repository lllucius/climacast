#!/usr/bin/env python3
"""
Simple test script to validate the refactored ASK SDK integration
"""
import json
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set required environment variables
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"

# Import the lambda handler
from lambda_function import lambda_handler

def test_launch():
    """Test the launch request"""
    print("Testing LaunchRequest...")
    with open("test_launch.json") as f:
        event = json.load(f)
    
    response = lambda_handler(event, None)
    print("Response:")
    print(json.dumps(response, indent=2))
    
    # Verify response structure
    assert "version" in response or "response" in response, "Response should have version or response"
    print("✓ LaunchRequest test passed\n")

def test_help_intent():
    """Test the help intent"""
    print("Testing HelpIntent...")
    event = {
        "version": "1.0",
        "session": {
            "new": False,
            "sessionId": "amzn1.echo-api.session.test",
            "application": {
                "applicationId": "amzn1.ask.skill.test"
            },
            "attributes": {},
            "user": {
                "userId": "amzn1.ask.account.test"
            }
        },
        "context": {
            "System": {
                "application": {
                    "applicationId": "amzn1.ask.skill.test"
                },
                "user": {
                    "userId": "amzn1.ask.account.test"
                }
            }
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "amzn1.echo-api.request.test",
            "timestamp": "2024-01-01T00:00:00Z",
            "locale": "en-US",
            "intent": {
                "name": "AMAZON.HelpIntent",
                "confirmationStatus": "NONE"
            }
        }
    }
    
    response = lambda_handler(event, None)
    print("Response:")
    print(json.dumps(response, indent=2))
    print("✓ HelpIntent test passed\n")

if __name__ == "__main__":
    try:
        test_launch()
        test_help_intent()
        print("\n✓ All tests passed!")
    except Exception as e:
        import traceback
        print(f"\n✗ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)
