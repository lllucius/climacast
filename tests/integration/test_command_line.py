#!/usr/bin/env python3
"""
Test command line processing functionality for lambda_function.py
"""
import json
import os
import subprocess
import sys
import tempfile

# Add the parent directories to the path
test_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(test_dir))
sys.path.insert(0, root_dir)

# Set required environment variables
os.environ["app_id"] = "amzn1.ask.skill.test"
os.environ["here_api_key"] = "test"
os.environ["event_id"] = ""
os.environ["dataupdate_id"] = "amzn1.ask.data.update"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"

from lambda_function import build_test_event, parse_slot_args  # noqa: E402


def test_build_test_event_launch_request():
    """Test building a LaunchRequest event"""
    print("Testing build_test_event for LaunchRequest...")
    
    event = build_test_event("LaunchRequest")
    
    assert event is not None
    assert event["request"]["type"] == "LaunchRequest"
    assert event["version"] == "1.0"
    assert "session" in event
    assert "context" in event
    
    print("✓ LaunchRequest event built successfully")


def test_build_test_event_with_intent():
    """Test building an IntentRequest event with slots"""
    print("Testing build_test_event for IntentRequest with slots...")
    
    slots = {
        "metric": "temperature",
        "location": "Seattle, Washington"
    }
    
    event = build_test_event("MetricIntent", slots)
    
    assert event is not None
    assert event["request"]["type"] == "IntentRequest"
    assert event["request"]["intent"]["name"] == "MetricIntent"
    assert "slots" in event["request"]["intent"]
    assert event["request"]["intent"]["slots"]["metric"]["value"] == "temperature"
    assert event["request"]["intent"]["slots"]["location"]["value"] == "Seattle, Washington"
    
    print("✓ IntentRequest event with slots built successfully")


def test_parse_slot_args():
    """Test parsing slot arguments"""
    print("Testing parse_slot_args...")
    
    args = ["metric=temperature", "location=Seattle, Washington", "percent=85"]
    slots = parse_slot_args(args)
    
    assert len(slots) == 3
    assert slots["metric"] == "temperature"
    assert slots["location"] == "Seattle, Washington"
    assert slots["percent"] == "85"
    
    print("✓ Slot arguments parsed successfully")


def test_parse_slot_args_with_invalid():
    """Test parsing slot arguments with invalid entries"""
    print("Testing parse_slot_args with invalid arguments...")
    
    args = ["metric=temperature", "invalid_arg", "location=Seattle"]
    slots = parse_slot_args(args)
    
    # Should only parse valid key=value pairs
    assert len(slots) == 2
    assert slots["metric"] == "temperature"
    assert slots["location"] == "Seattle"
    
    print("✓ Invalid arguments handled correctly")


def test_command_line_intent_only():
    """Test command line with intent only"""
    print("Testing command line with intent only...")
    
    result = subprocess.run(
        ["python3", "lambda_function.py", "LaunchRequest"],
        capture_output=True,
        text=True,
        env={**os.environ, "AWS_DEFAULT_REGION": "us-east-1", "here_api_key": "test"}
    )
    
    assert result.returncode == 0
    output = result.stdout
    
    # Parse JSON output
    response = json.loads(output)
    assert "response" in response
    assert "outputSpeech" in response["response"]
    
    print("✓ Command line with intent only works")


def test_command_line_intent_with_slots():
    """Test command line with intent and slots"""
    print("Testing command line with intent and slots...")
    
    result = subprocess.run(
        ["python3", "lambda_function.py", "SetPitchIntent", "percent=90"],
        capture_output=True,
        text=True,
        env={**os.environ, "AWS_DEFAULT_REGION": "us-east-1", "here_api_key": "test"}
    )
    
    assert result.returncode == 0
    output = result.stdout
    
    # Parse JSON output
    response = json.loads(output)
    assert "response" in response
    
    # Check that the pitch was set
    speech = response["response"]["outputSpeech"]["ssml"]
    assert "90 percent" in speech.lower()
    
    print("✓ Command line with intent and slots works")


def test_command_line_file_mode():
    """Test command line file mode"""
    print("Testing command line file mode...")
    
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Test cases\n")
        f.write("LaunchRequest\n")
        f.write("AMAZON.HelpIntent\n")
        f.write("SetPitchIntent percent=85\n")
        temp_file = f.name
    
    try:
        result = subprocess.run(
            ["python3", "lambda_function.py", "--file", temp_file],
            capture_output=True,
            text=True,
            env={**os.environ, "AWS_DEFAULT_REGION": "us-east-1", "here_api_key": "test"}
        )
        
        assert result.returncode == 0
        output = result.stdout
        
        # Check that all test cases were processed
        assert "Test case" in output
        assert "LaunchRequest" in output
        assert "AMAZON.HelpIntent" in output
        assert "SetPitchIntent" in output
        
        print("✓ Command line file mode works")
    finally:
        os.unlink(temp_file)


def test_command_line_help():
    """Test command line help"""
    print("Testing command line help...")
    
    result = subprocess.run(
        ["python3", "lambda_function.py", "--help"],
        capture_output=True,
        text=True,
        env={**os.environ, "AWS_DEFAULT_REGION": "us-east-1", "here_api_key": "test"}
    )
    
    assert result.returncode == 0
    output = result.stdout
    
    # Check that help text is displayed
    assert "usage:" in output
    assert "Intent name" in output
    assert "Examples:" in output
    
    print("✓ Command line help works")


if __name__ == "__main__":
    # Run all tests
    tests = [
        test_build_test_event_launch_request,
        test_build_test_event_with_intent,
        test_parse_slot_args,
        test_parse_slot_args_with_invalid,
        test_command_line_intent_only,
        test_command_line_intent_with_slots,
        test_command_line_file_mode,
        test_command_line_help,
    ]
    
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*60}")
    if failed == 0:
        print("✓ All command line processing tests passed!")
    else:
        print(f"✗ {failed} test(s) failed")
    print('='*60)
    
    sys.exit(0 if failed == 0 else 1)
