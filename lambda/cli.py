#!/usr/bin/env python3

# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

"""
Command-line interface for testing Clima Cast processing locally.

This CLI allows you to test the weather processing logic without deploying
to AWS Lambda. It emulates Alexa Skill JSON input and uses JSON file caching
instead of DynamoDB.
"""

import argparse
import json
import os
import sys

from cache_adapter import JSONFileCacheAdapter
from processing import WeatherProcessor
from dotenv import load_dotenv


def load_request_template(template_type):
    """
    Load a request template.
    
    Args:
        template_type: Type of template (e.g., "launch", "metric", "set_location")
        
    Returns:
        Dictionary with request template
    """
    templates = {
        "launch": {
            "request_type": "LaunchRequest",
            "user_id": "test-user"
        },
        "metric": {
            "request_type": "IntentRequest",
            "intent_name": "MetricIntent",
            "user_id": "test-user",
            "slots": {
                "metric": {"value": "temperature"}
            }
        },
        "set_location": {
            "request_type": "IntentRequest",
            "intent_name": "SetLocationIntent",
            "user_id": "test-user",
            "slots": {
                "location": {"value": "Boulder Colorado"}
            }
        },
        "get_setting": {
            "request_type": "IntentRequest",
            "intent_name": "GetSettingIntent",
            "user_id": "test-user"
        },
        "help": {
            "request_type": "IntentRequest",
            "intent_name": "AMAZON.HelpIntent",
            "user_id": "test-user"
        },
        "stop": {
            "request_type": "IntentRequest",
            "intent_name": "AMAZON.StopIntent",
            "user_id": "test-user"
        }
    }
    
    return templates.get(template_type)


def emulate_alexa_request(request_type, slots=None, user_id="test-user", user_location=None):
    """
    Emulate an Alexa Skill request in JSON format.
    
    Args:
        request_type: Type of request or intent name
        slots: Dictionary of slot values
        user_id: User ID for the request
        user_location: Default location for the user
        
    Returns:
        Dictionary with request data
    """
    # Start with template if available
    template = load_request_template(request_type)
    
    if template:
        request_data = template.copy()
    else:
        # Assume it's an intent name
        request_data = {
            "request_type": "IntentRequest",
            "intent_name": request_type,
            "user_id": user_id
        }
    
    # Override with provided values
    if slots:
        request_data["slots"] = slots
    
    if user_location:
        request_data["user_location"] = user_location
    
    return request_data


def simulate_workflow(processor, args):
    """
    Simulate a typical Alexa skill session workflow.
    
    This simulates the order of intents as they would be called when running as a skill:
    1. GetDataIntent - Load cached data at session start
    2. LaunchRequest - Welcome message
    3. User interactions (set location, query weather, etc.)
    4. StoreDataIntent - Save cached data before session end
    5. SessionEndedRequest - End session
    """
    print("\n" + "=" * 60)
    print("SIMULATING ALEXA SKILL SESSION WORKFLOW")
    print("=" * 60)
    
    user_id = args.user_id
    location = args.location
    
    # Step 1: GetDataIntent - Load cached data
    print("\n[Step 1] Loading cached data (GetDataIntent)...")
    request_data = {
        "request_type": "IntentRequest",
        "intent_name": "GetDataIntent",
        "user_id": user_id
    }
    response = processor.process_request(request_data)
    print(f"Response: {response['speech']}")
    
    # Step 2: LaunchRequest
    print("\n[Step 2] Launch request...")
    request_data = {
        "request_type": "LaunchRequest",
        "user_id": user_id
    }
    response = processor.process_request(request_data)
    print(f"Response: {response['speech']}")
    
    # Step 3: Set location if provided
    if location:
        print(f"\n[Step 3] Setting location to {location}...")
        request_data = {
            "request_type": "IntentRequest",
            "intent_name": "SetLocationIntent",
            "user_id": user_id,
            "slots": {"location": {"value": location}}
        }
        response = processor.process_request(request_data)
        print(f"Response: {response['speech']}")
    
    # Step 4: Query weather
    print("\n[Step 4] Querying current weather...")
    request_data = {
        "request_type": "IntentRequest",
        "intent_name": "MetricIntent",
        "user_id": user_id,
        "slots": {"metric": {"value": "temperature"}}
    }
    if location:
        request_data["slots"]["location"] = {"value": location}
    response = processor.process_request(request_data)
    print(f"Response: {response['speech']}")
    
    # Step 5: Get settings
    print("\n[Step 5] Getting current settings...")
    request_data = {
        "request_type": "IntentRequest",
        "intent_name": "GetSettingIntent",
        "user_id": user_id
    }
    response = processor.process_request(request_data)
    print(f"Response: {response['speech']}")
    
    # Step 6: StoreDataIntent - Save cached data
    print("\n[Step 6] Saving cached data (StoreDataIntent)...")
    request_data = {
        "request_type": "IntentRequest",
        "intent_name": "StoreDataIntent",
        "user_id": user_id
    }
    response = processor.process_request(request_data)
    print(f"Response: {response['speech']}")
    
    # Step 7: Stop/Cancel
    print("\n[Step 7] Stopping session (AMAZON.StopIntent)...")
    request_data = {
        "request_type": "IntentRequest",
        "intent_name": "AMAZON.StopIntent",
        "user_id": user_id
    }
    response = processor.process_request(request_data)
    print(f"Response: {response['speech']}")
    
    # Step 8: SessionEndedRequest
    print("\n[Step 8] Session ended...")
    request_data = {
        "request_type": "SessionEndedRequest",
        "user_id": user_id
    }
    response = processor.process_request(request_data)
    print("Session terminated.")
    
    print("\n" + "=" * 60)
    print("WORKFLOW SIMULATION COMPLETE")
    print("=" * 60 + "\n")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Clima Cast CLI - Test weather processing locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Launch request
  %(prog)s launch
  
  # Get weather for a metric
  %(prog)s metric --metric temperature --location "Boulder Colorado"
  
  # Set default location
  %(prog)s set_location --location "Boulder Colorado"
  
  # Get settings
  %(prog)s get_setting
  
  # Use JSON input file
  %(prog)s --json-input request.json
  
  # Specify cache directory
  %(prog)s --cache-dir /tmp/climacast_cache metric --metric wind
        """
    )
    
    parser.add_argument(
        "--cache-dir",
        default=".climacast_cache",
        help="Directory for JSON cache files (default: .climacast_cache)"
    )
    
    parser.add_argument(
        "--json-input",
        help="Path to JSON file containing request data"
    )
    
    parser.add_argument(
        "--json-output",
        help="Path to write JSON response (default: stdout)"
    )
    
    parser.add_argument(
        "--user-id",
        default="test-user",
        help="User ID for the request (default: test-user)"
    )
    
    parser.add_argument(
        "--user-location",
        help="Default location for the user"
    )
    
    # Subparsers for different request types
    subparsers = parser.add_subparsers(dest="command", help="Request type")
    
    # Launch request
    subparsers.add_parser("launch", help="Launch request")
    
    # Metric request
    metric_parser = subparsers.add_parser("metric", help="Query weather metric")
    metric_parser.add_argument("--metric", required=True, help="Metric to query (e.g., temperature, wind)")
    metric_parser.add_argument("--location", help="Location for the query")
    metric_parser.add_argument("--when", help="When (e.g., today, tomorrow, monday)")
    
    # Set location
    location_parser = subparsers.add_parser("set_location", help="Set default location")
    location_parser.add_argument("--location", required=True, help="Location to set")
    
    # Set pitch
    pitch_parser = subparsers.add_parser("set_pitch", help="Set voice pitch")
    pitch_parser.add_argument("--percent", required=True, type=int, help="Pitch percentage (70-130)")
    
    # Set rate
    rate_parser = subparsers.add_parser("set_rate", help="Set voice rate")
    rate_parser.add_argument("--percent", required=True, type=int, help="Rate percentage (50-150)")
    
    # Get setting
    subparsers.add_parser("get_setting", help="Get current settings")
    
    # Get custom
    subparsers.add_parser("get_custom", help="Get custom forecast settings")
    
    # Add custom
    add_custom_parser = subparsers.add_parser("add_custom", help="Add metric to custom forecast")
    add_custom_parser.add_argument("--metric", required=True, help="Metric to add")
    
    # Remove custom
    remove_custom_parser = subparsers.add_parser("remove_custom", help="Remove metric from custom forecast")
    remove_custom_parser.add_argument("--metric", required=True, help="Metric to remove")
    
    # Reset custom
    subparsers.add_parser("reset_custom", help="Reset custom forecast to defaults")
    
    # Store data
    subparsers.add_parser("store_data", help="Save cache data")
    
    # Get data
    subparsers.add_parser("get_data", help="Load and report cache data")
    
    # Help
    subparsers.add_parser("help", help="Get help information")
    
    # AMAZON intents
    subparsers.add_parser("yes", help="AMAZON.YesIntent")
    subparsers.add_parser("no", help="AMAZON.NoIntent")
    subparsers.add_parser("start_over", help="AMAZON.StartOverIntent")
    subparsers.add_parser("cancel", help="AMAZON.CancelIntent")
    
    # Stop
    subparsers.add_parser("stop", help="Stop/cancel")
    
    # Session ended
    subparsers.add_parser("session_ended", help="Session ended request")
    
    # Simulate workflow
    simulate_parser = subparsers.add_parser("simulate", help="Simulate a typical skill session workflow")
    simulate_parser.add_argument("--location", help="Location for the simulation")
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    here_api_key = os.environ.get("here_api_key", "")
    
    if not here_api_key:
        print("Warning: here_api_key not found in environment. Geocoding may fail.", file=sys.stderr)
    
    # Initialize cache adapter
    cache_adapter = JSONFileCacheAdapter(cache_dir=args.cache_dir)
    
    # Initialize processor
    processor = WeatherProcessor(cache_adapter, here_api_key)
    
    # Build request data
    if args.json_input:
        # Load from JSON file
        try:
            with open(args.json_input, 'r') as f:
                request_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading JSON input: {e}", file=sys.stderr)
            return 1
    elif args.command:
        # Build from command-line arguments
        if args.command == "metric":
            slots = {"metric": {"value": args.metric}}
            if args.location:
                slots["location"] = {"value": args.location}
            if args.when:
                slots["when_any"] = {"value": args.when}
            request_data = emulate_alexa_request("metric", slots=slots, 
                                                 user_id=args.user_id,
                                                 user_location=args.user_location)
        elif args.command == "set_location":
            slots = {"location": {"value": args.location}}
            request_data = emulate_alexa_request("set_location", slots=slots,
                                                 user_id=args.user_id)
        elif args.command == "set_pitch":
            slots = {"percent": {"value": str(args.percent)}}
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "SetPitchIntent",
                "user_id": args.user_id,
                "slots": slots
            }
        elif args.command == "set_rate":
            slots = {"percent": {"value": str(args.percent)}}
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "SetRateIntent",
                "user_id": args.user_id,
                "slots": slots
            }
        elif args.command == "get_custom":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "GetCustomIntent",
                "user_id": args.user_id
            }
        elif args.command == "add_custom":
            slots = {"metric": {"value": args.metric}}
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "AddCustomIntent",
                "user_id": args.user_id,
                "slots": slots
            }
        elif args.command == "remove_custom":
            slots = {"metric": {"value": args.metric}}
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "RemCustomIntent",
                "user_id": args.user_id,
                "slots": slots
            }
        elif args.command == "reset_custom":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "RstCustomIntent",
                "user_id": args.user_id
            }
        elif args.command == "store_data":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "StoreDataIntent",
                "user_id": args.user_id
            }
        elif args.command == "get_data":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "GetDataIntent",
                "user_id": args.user_id
            }
        elif args.command == "yes":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "AMAZON.YesIntent",
                "user_id": args.user_id
            }
        elif args.command == "no":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "AMAZON.NoIntent",
                "user_id": args.user_id
            }
        elif args.command == "start_over":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "AMAZON.StartOverIntent",
                "user_id": args.user_id
            }
        elif args.command == "cancel":
            request_data = {
                "request_type": "IntentRequest",
                "intent_name": "AMAZON.CancelIntent",
                "user_id": args.user_id
            }
        elif args.command == "session_ended":
            request_data = {
                "request_type": "SessionEndedRequest",
                "user_id": args.user_id
            }
        elif args.command == "simulate":
            return simulate_workflow(processor, args)
        else:
            request_data = emulate_alexa_request(args.command, user_id=args.user_id,
                                                 user_location=args.user_location)
    else:
        parser.print_help()
        return 1
    
    # Process request
    try:
        response = processor.process_request(request_data)
    except Exception as e:
        print(f"Error processing request: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # Output response
    if args.json_output:
        try:
            with open(args.json_output, 'w') as f:
                json.dump(response, f, indent=2)
            print(f"Response written to {args.json_output}")
        except IOError as e:
            print(f"Error writing JSON output: {e}", file=sys.stderr)
            return 1
    else:
        # Pretty print to stdout
        print("\n" + "=" * 60)
        print("RESPONSE")
        print("=" * 60)
        print(f"\nSpeech: {response.get('speech', '')}")
        print(f"\nEnd Session: {response.get('should_end_session', False)}")
        if response.get('session_attributes'):
            print(f"\nSession Attributes: {json.dumps(response['session_attributes'], indent=2)}")
        print("\n" + "=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
