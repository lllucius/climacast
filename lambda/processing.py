#!/usr/bin/python3

# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

"""
Core weather processing logic separated from Lambda handler.

This module contains the core business logic for processing weather requests,
separated from the Alexa Skill Lambda handler. This allows for local testing
via CLI interface.
"""

import json
import re
from math import sqrt
from time import time

import requests
from aniso8601.duration import parse_duration
from cachetools import TTLCache, cached
from datetime import datetime
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta

from cache_adapter import CacheAdapter


# HTTP session for API requests
HTTPS = requests.Session()

# Cache up to 100 HTTP responses for 1 hour
HTTP_CACHE = TTLCache(maxsize=100, ttl=3600)


@cached(HTTP_CACHE)
def get_api_data(url):
    """
        Cached HTTP GET request for API data
    """
    headers = {"User-Agent": "ClimacastAlexaSkill/2.0 (climacast@homerow.net)",
               "Accept": "application/ld+json"}
    r = HTTPS.get(url, headers=headers)
    if r.status_code != 200 or r.text is None or r.text == "":
        return None, r.status_code, r.url, r.content
    return json.loads(r.text), r.status_code, r.url, None


def notify(event, sub, msg=None):
    """
        Send SNS message of an unusual event
    """
    text = ""
    if "request" in event:
        request = event["request"]
        intent = request.get("intent", None) if request else None
        slots = intent.get("slots", None) if intent else None

        if intent:
            text += "REQUEST:\n\n"
            text += "  " + request["type"]
            if "name" in intent:
                text += " - " + intent["name"]
            text += "\n\n"

        # Define SLOTS locally - these were imported from globals before
        SLOTS = ["day", "leadin", "location", "metric", "month", "percent",
                 "quarter", "setting", "when_abs", "when_any", "when_pos",
                 "zip_conn", "zipcode"]
        
        if slots:
            text += "SLOTS:\n\n"
            for slot in SLOTS:
                text += "  %-15s %s\n" % (slot + ":", str(slots.get(slot, {}).get("value", None)))
            text += "\n"

    text += "EVENT:\n\n"
    text += json.dumps(event, indent=4)
    text += "\n\n"

    if msg:
        text += "MESSAGE:\n\n"
        text += "  " + msg
        text += "\n\n"

    print("NOTIFY:\n\n  %s\n\n%s" % (sub, text))


class WeatherProcessor:
    """
    Main weather processing class.
    
    This class contains all the core weather processing logic, separated from
    the Lambda/Alexa-specific handler code. It can be instantiated with different
    cache adapters (DynamoDB for Lambda, JSON files for CLI).
    """
    
    def __init__(self, cache_adapter, here_api_key):
        """
        Initialize weather processor.
        
        Args:
            cache_adapter: CacheAdapter instance for caching
            here_api_key: HERE.com API key for geocoding
        """
        self.cache_adapter = cache_adapter
        self.here_api_key = here_api_key
        self.event = {}  # Will be set when processing a request
    
    def https(self, path, loc="api.weather.gov"):
        """
            Retrieve the JSON data from the given path and location
        """
        url = "https://%s/%s" % (loc, path.replace(" ", "+"))
        data, status_code, url_result, content = get_api_data(url)

        if data is None:
            notify(self.event,
                        "HTTPSTATUS: %s" % status_code,
                        "URL: %s\n\n%s" % (url_result, content))
            return None

        return data
    
    def process_request(self, request_data):
        """
        Process a weather request.
        
        Args:
            request_data: Dictionary containing request information:
                - request_type: Type of request (LaunchRequest, MetricIntent, etc.)
                - intent_name: Name of the intent (optional)
                - slots: Dictionary of slot values (optional)
                - user_id: User ID for profile
                - session_data: Session attributes (optional)
                
        Returns:
            Dictionary with response:
                - speech: Text to speak
                - should_end_session: Whether to end the session
                - session_attributes: Updated session attributes
        """
        # Store event for notify
        self.event = {
            "session": {
                "user": {"userId": request_data.get("user_id", "test-user")}
            },
            "request": {
                "type": request_data.get("request_type"),
                "intent": {
                    "name": request_data.get("intent_name"),
                    "slots": request_data.get("slots", {})
                }
            }
        }
        
        # Process based on request type
        request_type = request_data.get("request_type")
        intent_name = request_data.get("intent_name")
        
        if request_type == "LaunchRequest":
            return self._handle_launch(request_data)
        elif intent_name == "MetricIntent" or intent_name == "MetricPosIntent":
            return self._handle_metric(request_data)
        elif intent_name == "SetLocationIntent":
            return self._handle_set_location(request_data)
        elif intent_name == "GetSettingIntent":
            return self._handle_get_setting(request_data)
        elif intent_name == "AMAZON.HelpIntent":
            return self._handle_help(request_data)
        elif intent_name == "AMAZON.StopIntent" or intent_name == "AMAZON.CancelIntent":
            return self._handle_stop(request_data)
        else:
            return {
                "speech": "I didn't understand that request.",
                "should_end_session": False,
                "session_attributes": {}
            }
    
    def _handle_launch(self, request_data):
        """Handle launch request."""
        text = "Welcome to Clime a Cast. " \
               "For current conditions, use phrases like: What's the weather. "\
               "For forecasts, try phrases like: What's the forecast."
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_metric(self, request_data):
        """Handle metric intent (weather queries)."""
        slots = request_data.get("slots", {})
        user_id = request_data.get("user_id", "test-user")
        
        # Get user profile (simplified for now)
        user_location = request_data.get("user_location")
        
        if not user_location:
            return {
                "speech": "You must set a default location first.",
                "should_end_session": False,
                "session_attributes": {}
            }
        
        metric = slots.get("metric", {}).get("value")
        if not metric:
            return {
                "speech": "You must include a metric like temperature, humidity or wind",
                "should_end_session": False,
                "session_attributes": {}
            }
        
        # This is a simplified version - full implementation would include
        # all the weather processing logic
        text = f"Processing weather metric: {metric} for location {user_location}"
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_set_location(self, request_data):
        """Handle set location intent."""
        slots = request_data.get("slots", {})
        location = slots.get("location", {}).get("value") or slots.get("zipcode", {}).get("value")
        
        if not location:
            return {
                "speech": "You must include a location.",
                "should_end_session": False,
                "session_attributes": {}
            }
        
        # This would normally set the user's location
        text = f"Your default location has been set to {location}."
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {"user_location": location}
        }
    
    def _handle_get_setting(self, request_data):
        """Handle get setting intent."""
        user_location = request_data.get("user_location", "not set")
        text = f"Your location is set to {user_location}."
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_help(self, request_data):
        """Handle help intent."""
        text = """
            For complete information, please refer to the Clima Cast skill
            page in the Alexa app.
            You may get the current conditions with phrases like:
                What's the weather?
                What's the humidity in Baton Rouge, Louisiana?
            """
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_stop(self, request_data):
        """Handle stop/cancel intent."""
        return {
            "speech": "Thank you for using Clime a Cast.",
            "should_end_session": True,
            "session_attributes": {}
        }
