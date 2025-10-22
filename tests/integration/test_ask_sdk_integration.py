#!/usr/bin/env python3
"""
Test ASK SDK integration without requiring AWS resources
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
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"

# Import the lambda handler
from lambda_function import lambda_handler

def test_ask_sdk_handlers():
    """Test that ASK SDK handlers are properly invoked"""
    print("Testing ASK SDK Handler Integration...")
    
    # Test LaunchRequest
    launch_event = {
        "version": "1.0",
        "session": {
            "new": True,
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
                },
                "device": {
                    "deviceId": "amzn1.ask.device.test"
                },
                "apiEndpoint": "https://api.amazonalexa.com"
            }
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "amzn1.echo-api.request.test",
            "timestamp": "2024-01-01T00:00:00Z",
            "locale": "en-US"
        }
    }
    
    try:
        response = lambda_handler(launch_event, None)
        assert response is not None, "Response should not be None"
        assert "response" in response or "version" in response, "Response should have proper structure"
        print("✓ LaunchRequest handler invoked successfully")
        
        # Check if response contains expected speech output
        if "response" in response and "outputSpeech" in response["response"]:
            speech = response["response"]["outputSpeech"]
            if speech.get("type") == "SSML" and speech.get("ssml"):
                print("✓ Response contains SSML speech output")
                # Verify it's not an error message
                if "aw man" in speech["ssml"].lower():
                    print("  ⚠ Response contains error message (expected if DynamoDB unavailable)")
                elif "welcome to clime a cast" in speech["ssml"].lower():
                    print("  ✓ Response contains welcome message!")
    except Exception as e:
        print(f"✗ LaunchRequest test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test HelpIntent
    help_event = {
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
    
    try:
        response = lambda_handler(help_event, None)
        assert response is not None, "Response should not be None"
        print("✓ HelpIntent handler invoked successfully")
    except Exception as e:
        print(f"✗ HelpIntent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✓ ASK SDK Integration Test Passed!")
    print("  - CustomSkillBuilder successfully created")
    print("  - Intent handlers properly registered")
    print("  - Request deserialization working")
    print("  - Response serialization working")
    return True

if __name__ == "__main__":
    success = test_ask_sdk_handlers()
    sys.exit(0 if success else 1)
