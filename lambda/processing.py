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
import os
import sys

# Add lambda directory to path if needed
lambda_dir = os.path.dirname(os.path.abspath(__file__))
if lambda_dir not in sys.path:
    sys.path.insert(0, lambda_dir)

# Import the weather processing classes from lambda_function
from lambda_function import (
    Base, User, Location, Observations, GridPoints, Alerts,
    METRICS, DAYS, QUARTERS, MONTH_DAYS, MONTH_NAMES
)


class WeatherProcessor:
    """
    Main weather processing class.
    
    This class provides a simplified interface to the weather processing logic,
    designed for CLI testing. It wraps the existing classes from lambda_function.py
    and uses the cache_adapter abstraction.
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
        
        # Set the HERE API key environment variable for lambda_function
        os.environ['here_api_key'] = here_api_key
    
    def build_event(self, request_data):
        """
        Build an event dictionary from request data.
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            Event dictionary compatible with lambda_function classes
        """
        event = {
            "session": {
                "new": True,
                "sessionId": "test-session",
                "user": {
                    "userId": request_data.get("user_id", "test-user")
                },
                "attributes": request_data.get("session_attributes", {})
            },
            "request": {
                "type": request_data.get("request_type"),
            }
        }
        
        if "intent_name" in request_data:
            event["request"]["intent"] = {
                "name": request_data["intent_name"],
                "slots": {}
            }
            
            # Convert slot format
            for slot_name, slot_value in request_data.get("slots", {}).items():
                if isinstance(slot_value, dict):
                    event["request"]["intent"]["slots"][slot_name] = slot_value
                else:
                    event["request"]["intent"]["slots"][slot_name] = {"value": slot_value}
        
        return event
    
    def process_request(self, request_data):
        """
        Process a weather request.
        
        Args:
            request_data: Dictionary containing request information:
                - request_type: Type of request (LaunchRequest, IntentRequest)
                - intent_name: Name of the intent (optional)
                - slots: Dictionary of slot values (optional)
                - user_id: User ID for profile
                - user_location: Default location (optional)
                - session_attributes: Session attributes (optional)
                
        Returns:
            Dictionary with response:
                - speech: Text to speak
                - should_end_session: Whether to end the session
                - session_attributes: Updated session attributes
        """
        # Build event
        event = self.build_event(request_data)
        
        # Get user
        user_id = request_data.get("user_id", "test-user")
        user = User(event, user_id, attributes_manager=None, cache_adapter=self.cache_adapter)
        
        # Override user location if provided in request
        if request_data.get("user_location"):
            user._location = request_data["user_location"]
        
        # Process based on request type
        request_type = request_data.get("request_type")
        intent_name = request_data.get("intent_name")
        
        if request_type == "LaunchRequest":
            return self._handle_launch(event, user)
        elif intent_name == "MetricIntent" or intent_name == "MetricPosIntent":
            return self._handle_metric(event, user, request_data)
        elif intent_name == "SetLocationIntent":
            return self._handle_set_location(event, user, request_data)
        elif intent_name == "GetSettingIntent":
            return self._handle_get_setting(event, user, request_data)
        elif intent_name == "SetPitchIntent":
            return self._handle_set_pitch(event, user, request_data)
        elif intent_name == "SetRateIntent":
            return self._handle_set_rate(event, user, request_data)
        elif intent_name == "GetCustomIntent":
            return self._handle_get_custom(event, user)
        elif intent_name == "AddCustomIntent":
            return self._handle_add_custom(event, user, request_data)
        elif intent_name == "RemCustomIntent":
            return self._handle_remove_custom(event, user, request_data)
        elif intent_name == "RstCustomIntent":
            return self._handle_reset_custom(event, user)
        elif intent_name == "StoreDataIntent":
            return self._handle_store_data(event, user)
        elif intent_name == "GetDataIntent":
            return self._handle_get_data(event, user)
        elif intent_name == "AMAZON.HelpIntent":
            return self._handle_help(event, user)
        elif intent_name == "AMAZON.StopIntent" or intent_name == "AMAZON.CancelIntent":
            return self._handle_stop(event, user)
        elif intent_name == "AMAZON.NoIntent" or intent_name == "AMAZON.YesIntent" or intent_name == "AMAZON.StartOverIntent":
            return self._handle_fallback(event, user)
        elif intent_name == "SessionEndedRequest":
            return self._handle_session_ended(event, user)
        else:
            return {
                "speech": "I didn't understand that request.",
                "should_end_session": False,
                "session_attributes": {}
            }
    
    def _handle_launch(self, event, user):
        """Handle launch request."""
        text = "Welcome to Clime a Cast. " \
               "For current conditions, use phrases like: What's the weather. " \
               "For forecasts, try phrases like: What's the forecast."
        
        if not user.location:
            text += " You must set your default location by saying something like: " \
                    "set location to Miami Florida."
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_metric(self, event, user, request_data):
        """Handle metric intent (weather queries)."""
        slots = request_data.get("slots", {})
        
        # Get location
        location_name = None
        if "location" in slots:
            location_name = slots["location"].get("value") if isinstance(slots["location"], dict) else slots["location"]
        elif "zipcode" in slots:
            location_name = slots["zipcode"].get("value") if isinstance(slots["zipcode"], dict) else slots["zipcode"]
        
        if location_name:
            location_obj = Location(event, attributes_manager=None, cache_adapter=self.cache_adapter)
            error_text = location_obj.set(location_name)
            if error_text:
                return {
                    "speech": error_text,
                    "should_end_session": False,
                    "session_attributes": {}
                }
            loc = location_obj
        elif user.location:
            location_obj = Location(event, attributes_manager=None, cache_adapter=self.cache_adapter)
            error_text = location_obj.set(user.location)
            if error_text:
                return {
                    "speech": error_text,
                    "should_end_session": False,
                    "session_attributes": {}
                }
            loc = location_obj
        else:
            return {
                "speech": "You must set a default location first or specify a location in your query.",
                "should_end_session": False,
                "session_attributes": {}
            }
        
        # Get metric
        metric = slots.get("metric", {})
        if isinstance(metric, dict):
            metric = metric.get("value")
        
        if not metric:
            return {
                "speech": "You must include a metric like temperature, humidity or wind",
                "should_end_session": False,
                "session_attributes": {}
            }
        
        # Process metric
        if metric == "alerts":
            alerts = Alerts(event, loc.countyZoneId, attributes_manager=None, cache_adapter=self.cache_adapter)
            if len(alerts) == 0:
                text = f"No alerts in effect at this time for {loc.city}."
            else:
                text = alerts.title + "... "
                for alert in alerts:
                    text += alert.headline + "... "
                    text += "for " + alert.area + "... "
            
            # Normalize
            base = Base(event, attributes_manager=None, cache_adapter=self.cache_adapter)
            text = base.normalize(text)
            
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        # For now, just return a basic message for other metrics
        # Full implementation would include current/forecast logic
        text = f"Processing {metric} for {loc.city}, {loc.state}"
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_set_location(self, event, user, request_data):
        """Handle set location intent."""
        slots = request_data.get("slots", {})
        location_name = slots.get("location", {})
        if isinstance(location_name, dict):
            location_name = location_name.get("value")
        
        if not location_name:
            location_name = slots.get("zipcode", {})
            if isinstance(location_name, dict):
                location_name = location_name.get("value")
        
        if not location_name:
            return {
                "speech": "You must include a location.",
                "should_end_session": False,
                "session_attributes": {}
            }
        
        location_obj = Location(event, attributes_manager=None, cache_adapter=self.cache_adapter)
        error_text = location_obj.set(location_name)
        
        if error_text:
            text = error_text
        else:
            user.location = location_obj.name
            text = f"Your default location has been set to {location_obj.spoken_name()}."
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {"user_location": user.location}
        }
    
    def _handle_get_setting(self, event, user, request_data):
        """Handle get setting intent."""
        if user.location:
            location_obj = Location(event, attributes_manager=None, cache_adapter=self.cache_adapter)
            error_text = location_obj.set(user.location)
            if error_text:
                text = "Location is set but invalid."
            else:
                text = f"Your location is set to {location_obj.spoken_name()}."
        else:
            text = "You have not set a default location."
        
        text += f" Voice pitch is {user.pitch} percent. Voice rate is {user.rate} percent."
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_help(self, event, user):
        """Handle help intent."""
        text = """
            For complete information, please refer to the Clima Cast skill
            page in the Alexa app.
            You may get the current conditions with phrases like:
                What's the weather?
                What's the humidity in Baton Rouge, Louisiana?
            You may get forecasts by saying things like:
                What's the forecast?
                What will the temperature be tomorrow?
            To check for active alerts:
                Are there any alerts?
            """
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_stop(self, event, user):
        """Handle stop/cancel intent."""
        return {
            "speech": "Thank you for using Clime a Cast.",
            "should_end_session": True,
            "session_attributes": {}
        }
    
    def _handle_set_pitch(self, event, user, request_data):
        """Handle set pitch intent."""
        slots = request_data.get("slots", {})
        percent = slots.get("percent", {})
        if isinstance(percent, dict):
            percent = percent.get("value")
        
        if percent and percent.isdigit():
            pitch = int(percent)
            if 130 >= pitch >= 70:
                user.pitch = pitch
                text = f"Voice pitch has been set to {pitch} percent."
            else:
                text = "The pitch must be between 70 and 130 percent"
        else:
            text = "Expected a percentage when setting the pitch"
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_set_rate(self, event, user, request_data):
        """Handle set rate intent."""
        slots = request_data.get("slots", {})
        percent = slots.get("percent", {})
        if isinstance(percent, dict):
            percent = percent.get("value")
        
        if percent and percent.isdigit():
            rate = int(percent)
            if 150 >= rate >= 50:
                user.rate = rate
                text = f"Voice rate has been set to {rate} percent."
            else:
                text = "The rate must be between 50 and 150 percent"
        else:
            text = "Expected a percentage when setting the rate"
        
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_get_custom(self, event, user):
        """Handle get custom intent."""
        text = "The custom forecast will include the " + \
               ", ".join(list(user.metrics[:-1])) + " and " + user.metrics[-1] + "."
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_add_custom(self, event, user, request_data):
        """Handle add custom intent."""
        slots = request_data.get("slots", {})
        metric = slots.get("metric", {})
        if isinstance(metric, dict):
            metric = metric.get("value")
        
        if not metric:
            text = "You must include a metric like temperature, humidity or wind."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        if metric not in METRICS:
            text = f"{metric} is an unrecognized metric."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        metric_info = METRICS[metric]
        if not metric_info[1]:
            text = f"{metric_info[0]} can't be used when customizing the forecast."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        if user.has_metric(metric_info[0]):
            text = f"{metric_info[0]} is already included in the custom forecast."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        user.add_metric(metric_info[0])
        text = f"{metric_info[0]} has been added to the custom forecast."
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_remove_custom(self, event, user, request_data):
        """Handle remove custom intent."""
        slots = request_data.get("slots", {})
        metric = slots.get("metric", {})
        if isinstance(metric, dict):
            metric = metric.get("value")
        
        if not metric:
            text = "You must include a metric like temperature, humidity or wind."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        if metric not in METRICS:
            text = f"{metric} is an unrecognized metric."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        metric_info = METRICS[metric]
        if not metric_info[1]:
            text = f"{metric_info[0]} can't be used when customizing the forecast."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        if not user.has_metric(metric_info[0]):
            text = f"{metric_info[0]} is already excluded from the custom forecast."
            return {
                "speech": text,
                "should_end_session": False,
                "session_attributes": {}
            }
        
        user.remove_metric(metric_info[0])
        text = f"{metric_info[0]} has been removed from the custom forecast."
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_reset_custom(self, event, user):
        """Handle reset custom intent."""
        user.reset_metrics()
        text = "The custom forecast has been reset to defaults."
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_store_data(self, event, user):
        """Handle store data intent - saves cache data."""
        # In CLI mode, the cache adapter automatically saves to JSON files
        # This is called to explicitly save all data
        text = "Data has been saved successfully."
        return {
            "speech": text,
            "should_end_session": True,
            "session_attributes": {}
        }
    
    def _handle_get_data(self, event, user):
        """Handle get data intent - loads cache data."""
        # In CLI mode, the cache adapter automatically loads from JSON files
        # This provides a report on the cache status
        location_count = len(self.cache_adapter._load_cache("LocationCache"))
        station_count = len(self.cache_adapter._load_cache("StationCache"))
        zone_count = len(self.cache_adapter._load_cache("ZoneCache"))
        user_count = len(self.cache_adapter._load_cache("UserCache"))
        
        text = f"Data has been loaded. LocationCache has {location_count} items, " \
               f"StationCache has {station_count} items, " \
               f"ZoneCache has {zone_count} items, " \
               f"and UserCache has {user_count} items."
        
        return {
            "speech": text,
            "should_end_session": True,
            "session_attributes": {}
        }
    
    def _handle_fallback(self, event, user):
        """Handle fallback, yes, no, and start over intents."""
        text = "I didn't understand that. " \
               "You can ask for current conditions, forecasts, or alerts. " \
               "Say help for more information."
        return {
            "speech": text,
            "should_end_session": False,
            "session_attributes": {}
        }
    
    def _handle_session_ended(self, event, user):
        """Handle session ended request."""
        return {
            "speech": "",
            "should_end_session": True,
            "session_attributes": {}
        }
