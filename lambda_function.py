#!/usr/bin/python3

# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

import json
import logging
import os
import re
import httpx
from typing import Dict, List, Optional, Any, Union
#from aniso8601 import parse_duration
from aniso8601.duration import parse_duration
from boto3 import resource as resource
from datetime import datetime
from dateutil import parser, tz
from dateutil.relativedelta import *
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, retry_if_exception_type, wait_exponential
from time import time

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.dispatch_components import AbstractRequestInterceptor, AbstractResponseInterceptor
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard
from ask_sdk_core.serialize import DefaultSerializer

from utils.geolocator import Geolocator
from utils.constants import *
from utils.constants import get_default_metrics
from utils import converters
from utils.text_normalizer import normalize as normalize_text
from storage.cache_handler import CacheHandler
from storage.settings_handler import SettingsHandler, AlexaSettingsHandler
from storage.local_handlers import LocalJsonCacheHandler, LocalJsonSettingsHandler
from weather.base import WeatherBase as Base
from weather.grid_points import GridPoints
from weather.observations import Observations
from weather.alerts import Alerts, Alert
from weather.location import Location

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

"""
    Anything defined here will persist for the duration of the lambda
    container, so only initialize them once to reduce initialization time.
"""
VERSION = 1
REVISION = 0

load_dotenv()


class Config:
    """
    Configuration class for managing environment variables and application settings.
    Provides a centralized location for all configuration values.
    
    Environment Variables:
        event_id: Event identifier for notifications
        app_id: Alexa skill application ID (default: amzn1.ask.skill.test)
        dataupdate_id: Data update identifier (default: amzn1.ask.data.update)
        here_api_key: HERE.com API key for geocoding
        DYNAMODB_PERSISTENCE_TABLE_NAME: DynamoDB table name (default: ask-{app_id})
        DYNAMODB_PERSISTENCE_REGION: AWS region (default: us-east-1)
    
    Example:
        Access configuration values:
            app_id = Config.APP_ID
            table_name = Config.DYNAMODB_TABLE_NAME
            
        For backward compatibility, global variables are maintained:
            APPID = Config.APP_ID
            TABLE_NAME = Config.DYNAMODB_TABLE_NAME
    """
    
    # Application identifiers
    EVENT_ID: str = os.environ.get("event_id", "")
    APP_ID: str = os.environ.get("app_id", "amzn1.ask.skill.test")
    DATA_UPDATE_ID: str = os.environ.get("dataupdate_id", "amzn1.ask.data.update")
    
    # API keys
    HERE_API_KEY: str = os.environ.get("here_api_key", "")
    
    # DynamoDB settings
    DYNAMODB_TABLE_NAME: str = os.environ.get("DYNAMODB_PERSISTENCE_TABLE_NAME", f"ask-{os.environ.get('app_id', 'test')}")
    DYNAMODB_REGION: str = os.environ.get("DYNAMODB_PERSISTENCE_REGION", "us-east-1")
    
    # Cache settings
    DEFAULT_CACHE_TTL_DAYS: int = 35
    
    # HTTP retry settings
    HTTP_RETRY_TOTAL: int = 3
    HTTP_RETRY_STATUS_CODES: List[int] = [429, 500, 502, 503, 504]
    HTTP_TIMEOUT: int = 30


# Maintain backward compatibility with existing code
EVTID = Config.EVENT_ID
APPID = Config.APP_ID
HERE_API_KEY = Config.HERE_API_KEY
DUID = Config.DATA_UPDATE_ID
TABLE_NAME = Config.DYNAMODB_TABLE_NAME

# Compiled normalization regex (compiled on first use) - DEPRECATED: moved to text_normalizer
NORMALIZE = None

# =============================================================================
# Factory Functions for Singleton Instances
# =============================================================================

_https_client = None

def get_https_client() -> httpx.Client:
    """
    Get or create the global HTTPS client instance.
    
    Returns:
        httpx.Client: Configured HTTP client for API calls
    """
    global _https_client
    if _https_client is None:
        _https_client = httpx.Client(
            timeout=Config.HTTP_TIMEOUT,
            follow_redirects=True
        )
    return _https_client


_geolocator_instance = None

def get_geolocator() -> Geolocator:
    """
    Get or create the global geolocator instance.
    
    Returns:
        Geolocator: Configured geolocator for geocoding operations
    """
    global _geolocator_instance
    if _geolocator_instance is None:
        _geolocator_instance = Geolocator(
            api_key=Config.HERE_API_KEY,
            session=get_https_client()
        )
    return _geolocator_instance


_cache_handler_instance = None

def get_cache_handler() -> CacheHandler:
    """
    Get or create the global cache handler instance.
    
    Returns:
        CacheHandler: Configured cache handler for DynamoDB operations
    """
    global _cache_handler_instance
    if _cache_handler_instance is None:
        _cache_handler_instance = CacheHandler(
            table_name=Config.DYNAMODB_TABLE_NAME,
            region=Config.DYNAMODB_REGION
        )
    return _cache_handler_instance


# Backward compatibility - these will be removed in Phase 4
HTTPS = get_https_client()
GEOLOCATOR = get_geolocator()
CACHE_HANDLER = get_cache_handler()

# Global test handlers (set by test_one() when running tests)
TEST_MODE = False
TEST_CACHE_HANDLER = None
TEST_SETTINGS_HANDLER = None


# =============================================================================
# Notification function
# =============================================================================

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

    logger.info(f"NOTIFY:\n\n  {sub}\n\n{text}")

# Base class now imported from weather.base module

# GridPoints class now imported from weather.gridpoints module

# Observations class now imported from weather.observations module

# Alerts class now imported from weather.alerts module

# Location class now imported from weather.location module

class Skill(Base):
    def __init__(self, handler_input, cache_handler=None, settings_handler=None):
        # Create minimal event dict for Base class (used for notifications)
        request_envelope = handler_input.request_envelope
        event = {
            "session": {
                "sessionId": request_envelope.session.session_id,
                "user": {
                    "userId": request_envelope.session.user.user_id
                }
            },
            "request": {
                "type": request_envelope.request.object_type,
                "requestId": request_envelope.request.request_id
            }
        }
        
        # Add intent info if present (for notifications)
        if hasattr(request_envelope.request, 'intent'):
            intent = request_envelope.request.intent
            event["request"]["intent"] = {
                "name": intent.name,
                "slots": {}
            }
            if intent.slots:
                for slot_name, slot in intent.slots.items():
                    event["request"]["intent"]["slots"][slot_name] = {
                        "name": slot.name,
                        "value": slot.value
                    }
        
        super().__init__(event, cache_handler)
        self.handler_input = handler_input
        self.request_envelope = request_envelope
        self.session = request_envelope.session
        self.request = request_envelope.request
        self.attrs = handler_input.attributes_manager.session_attributes
        self.settings_handler = settings_handler
        self.loc = None
        self.end = True

    @property
    def user_location(self):
        return self.settings_handler.get_location() if self.settings_handler else None

    @user_location.setter
    def user_location(self, location):
        if self.settings_handler:
            self.settings_handler.set_location(location)

    @property
    def user_rate(self):
        return self.settings_handler.get_rate() if self.settings_handler else 100

    @user_rate.setter
    def user_rate(self, rate):
        if self.settings_handler:
            self.settings_handler.set_rate(rate)

    @property
    def user_pitch(self):
        return self.settings_handler.get_pitch() if self.settings_handler else 100

    @user_pitch.setter
    def user_pitch(self, pitch):
        if self.settings_handler:
            self.settings_handler.set_pitch(pitch)

    @property
    def user_metrics(self):
        if self.settings_handler:
            return self.settings_handler.get_metrics()
        # Return default metrics if no settings handler
        return get_default_metrics()

    @user_metrics.setter
    def user_metrics(self, metrics):
        if self.settings_handler:
            self.settings_handler.set_metrics(metrics)

    def add_metric(self, metric):
        if self.settings_handler:
            current_metrics = self.settings_handler.get_metrics()
            if metric not in current_metrics:
                current_metrics.append(metric)
                self.settings_handler.set_metrics(current_metrics)

    def remove_metric(self, metric):
        if self.settings_handler:
            current_metrics = self.settings_handler.get_metrics()
            if metric in current_metrics:
                current_metrics.remove(metric)
                self.settings_handler.set_metrics(current_metrics)

    def reset_metrics(self):
        if self.settings_handler:
            # Get default metrics
            self.settings_handler.set_metrics(get_default_metrics())

    def has_metric(self, metric):
        return metric in self.user_metrics

    def initialize(self):
        """Initialize skill state from handler_input"""
        # Amazon says to verify our application id
        if self.session.application.application_id != APPID:
            raise ValueError("Invoked from unknown application.")

        # Retrieve the default location info
        location = self.user_location
        if location:
            loc = Location(self.event, self.cache_handler)
            text = loc.set(location)
            if text is None:
                self.loc = loc

        # Set all slots to None if no intent or no slots
        self.slots = type("slots", (), {})
        for slot in SLOTS:
            setattr(self.slots, slot, None)

        # Load the slot values
        if hasattr(self.request, 'intent') and self.request.intent.slots:
            for slot_name, slot in self.request.intent.slots.items():
                if slot_name in SLOTS:
                    val = slot.value
                    setattr(self.slots, slot_name, val.strip().lower() if val else None)
                    logger.info("SLOT: %s = %s", slot_name, getattr(self.slots, slot_name))
                
        # Log intent name for debugging
        if hasattr(self.request, 'intent'):
            logger.info("INTENT: %s", self.request.intent.name)
        else:
            logger.info("REQUEST: %s", self.request.object_type)

    def respond(self, text, end=None):
        new = self.session.new
        if end is None:
            end = new

        prompt = None
        if not end:
            prompt = "For %s, say help, " % ("more examples" if new else "example requests") + \
                     "To interrupt speaking, say Alexa, cancel, " + \
                     "If you are done, say stop."
            text += ". " if text.strip()[-1] != "." else " "
            text += prompt if new else "if you are done, say stop."
        
        # Build SSML speech
        speech_ssml = '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
                      (self.user_rate, self.user_pitch - 100, text)
        
        # Use ASK SDK response builder
        response_builder = self.handler_input.response_builder
        response_builder.speak(speech_ssml)
        
        if not end and prompt:
            reprompt_ssml = '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
                           (self.user_rate, self.user_pitch - 100, prompt)
            response_builder.ask(reprompt_ssml)
        
        response_builder.set_should_end_session(end)
        
        # Update session attributes
        self.handler_input.attributes_manager.session_attributes.update(self.attrs)
        
        return response_builder.response

    def default_handler(self):
        notify(self.event, "Unrecognized event", json.dumps(self.event, indent=4))
        return self.respond("Unhandled event %s, %s." % \
                            (self.request["type"],
                             self.intent["name"] if self.request["type"] == "IntentRequest" else ""))

    def launch_request(self):
        text = "Welcome to Clime a Cast. " \
               "For current conditions, use phrases like: What's the weather. "\
               "For forecasts, try phrases like: What's the forecast."
        if self.loc is None:
            text += "You must set your default location by saying something like: " \
                    "set location to Miami Florida."

        return text

    def session_end_request(self):
        return "Thank you for using Clime a Cast."

    def session_ended_request(self):
        if "error" in self.request:
            notify(self.event, "Error detected", self.request["error"]["message"])
            return self.request["error"]["message"]
    
        notify(self.event, "Session Ended", self.request["reason"])
        return self.request["reason"]

    def cancel_intent(self):
        return "Canceled."
 
    def stop_intent(self):
        return self.session_end_request()

    def help_intent(self):
        text = \
            """
            For complete information, please refer to the Clima Cast skill
            page in the Alexa app.
            You may get the current conditions with phrases like:
                For the current conditions.
                What's the humidity in Baton Rouge, Louisiana?
                How's the wind in Chicago, Illinois?
            You may get forecast by saying things like:
                For the forecast.
                What is the extended forecast.
                What's the forecast in on Saturday in Saint Paul, Minnesota?
                Is it going to be rainy tomorrow?
                What will the temperature be on Monday afternoon in Seattle, Washington?
            To check for active alerts, use phrases like:
                For the alerts.
                What are the alerts in Boise, Idaho?
                Are there any alerts?
            To get the current settings, use:
                Get the settings.
                Get the location.
                Get the pitch.
                Get the custom forecast.
            To change your settings, say:
                Set location to Boulder, Colorado.
                Set the rate to 109 percent.
                Set the pitch to 79 percent.
                Add temperature to the custom forecast.
                Remove dewpoint from the custom forecast.
                Reset the custom forecast.
            When using a location, you may use either the city name and state or the
            zip code.
            """
        return text

    def metric_intent(self):
        # Verify the location if needed
        text = self.get_location()
        if text is not None:
            return text
        
        # Determine the start and end times for the request
        self.get_when()
        
        metric = self.slots.metric
        if metric is None:
            return "You must include a metric like temperature, humidity or wind"

        if metric == "alerts":
            text = self.get_alerts()
            return text
 
        if metric == "extended forecast":
            text = self.get_extended()
            return text

        if metric not in METRICS:
            return "%s is an unrecognized metric." % metric

        metrics = self.user_metrics if METRICS[metric][0] == "all" else [METRICS[metric][0]]

        # These are absolute
        if metric == "forecast" or self.has_when:
            text = self.get_forecast(metrics)
            return text

        # Try to extract the intent of the request
        leadin = self.slots.leadin or ""
        if "chance" in metric or "will" in leadin or "going" in leadin:
            text = self.get_forecast(metrics)
            return text

        text = self.get_current(metrics)
        return text

    def get_setting_intent(self):
        # Verify location first
        text = skill.get_location()
        if text is not None:
            return text

        setting = self.slots.setting
        if setting is None:
            setting = "settings"

        words = setting.split()
        if words[0] in ["current", "default"]:
            words.remove(words[0])
        setting = words[0]

        if setting == "settings":
            settings = ["location", "pitch", "rate", "forecast"]
        elif setting in SETTINGS:
            settings = [SETTINGS[setting]]
        else:
            return "Unrecognized setting: %s" % setting

        text = ""
        for setting in settings:
            if text != "":
                text += ", "
                if setting == settings[-1]:
                    text += "and "
            if setting == "location":
                text += "the location is set to %s." % self.loc.spoken_name()
            elif setting == "pitch":
                text += "the voice pitch is set to %d percent." % self.user_pitch
            elif setting == "rate":
                text += "the voice rate is set to %d percent." % self.user_rate
            elif setting == "forecast":
                text += "the custom forecast will include the %s." % \
                        ", ".join(list(self.user_metrics[:-1])) + " and " + self.user_metrics[-1]

        return text

    def set_location_intent(self):
        text = self.get_location(req=True)
        if text is None:
            self.user_location = self.loc.name
            text = "Your default location has been set to %s." % self.loc.spoken_name()

        return text

    def set_pitch_intent(self):
        if self.slots.percent and self.slots.percent.isdigit():
            pitch = int(self.slots.percent)
            if 130 >= pitch >= 70:
                self.user_pitch = pitch
                text = "Voice pitch has been set to %d percent." % pitch
            else:
                text = "The pitch must be between 70 and 130 percent"
        else:
            text = "Expected a percentage when setting the pitch"

        return text

    def set_rate_intent(self):
        if self.slots.percent and self.slots.percent.isdigit():
            rate = int(self.slots.percent)
            if 150 >= rate >= 50:
                self.user_rate = rate
                text = "Voice rate has been set to %d percent." % rate
            else:
                text = "The rate must be between 50 and 150 percent"
        else:
            text = "Expected a percentage when setting the rate"

        return text

    def get_custom_intent(self):
        text = "The custom forecast will include the %s." % \
               ", ".join(list(self.user_metrics[:-1])) + " and " + self.user_metrics[-1]
        return text


    def add_custom_intent(self):
        metric = self.slots.metric
        if metric is None:
            return "You must include a metric like temperature, humidity or wind."

        if metric not in METRICS:
            return "%s is an unrecognized metric." % metric

        metric = METRICS[metric]
        if not metric[1]:
            return "%s can't be used when customizing the forecast." % metric[0]

        if self.has_metric(metric[0]):
            return "%s is already included in the custom forecast." % metric[0]
    
        self.add_metric(metric[0])

        return "%s has been added to the custom forecast." % metric[0]

    def remove_custom_intent(self):
        metric = self.slots.metric
        if metric is None:
            return "You must include a metric like temperature, humidity or wind."

        if metric not in METRICS:
            return "%s is an unrecognized metric." % metric

        metric = METRICS[metric]
        if not metric[1]:
            return "%s can't be used when customizing the forecast." % metric[0]

        if not self.has_metric(metric[0]):
            return "%s is already excluded from the custom forecast." % metric[0]
    
        self.remove_metric(metric[0])

        return "%s has been removed from the custom forecast." % metric[0]

    def reset_custom_intent(self):
        self.reset_metrics()

        return "the custom forecast has been reset to defaults."

    def get_alerts(self):
        alerts = Alerts(self.event, self.loc.countyZoneId, self.cache_handler)
        if len(alerts) == 0:
            text = "No alerts in effect at this time for %s." % self.loc.city
        else:
            text = alerts.title + "...\n"
            for alert in alerts:
                text += alert.headline + "...\n"
                text += "for " + alert.area + "...\n"
                text += alert.description + "...\n"
                text += alert.instruction + "...\n"
        
        return self.normalize(text)

    def get_current(self, metrics):
        text = ""

        if False:
            alerts = Alerts(self.event, self.loc.countyZoneId, self.cache_handler)
            cnt = len(alerts)
            if cnt > 0:
                text += "There's %d alert%s in effect for your area! " % \
                       (cnt,
                        "s" if cnt > 1 else "")

        # Retrieve the current observations from the nearest station
        obs = Observations(self.event, self.loc.observationStations, self.cache_handler)
        if obs.is_good:
            text += "At %s, %s reported %s, " % \
                    (obs.time_reported.astimezone(self.loc.tz).strftime("%I:%M%p"),
                     obs.station_name,
                     obs.description)

            for metric in metrics:
                if metric == "wind":
                    if obs.wind_speed is None or obs.wind_speed == "0":
                        text += "winds are calm"
                    else:
                        if obs.wind_direction is None:
                            text += "Winds are %s miles per hour" % obs.wind_speed
                        elif obs.wind_direction == "Variable":
                            text += "Winds are %s at %s miles per hour" % \
                                    (obs.wind_direction,
                                     obs.wind_speed)
                        else:
                            text += "Winds are out of the %s at %s miles per hour" % \
                                    (obs.wind_direction,
                                     obs.wind_speed)

                        if obs.wind_gust is not None:
                            text += ", gusting to %s" % obs.wind_gust
                elif metric == "temperature":
                    if obs.temp is not None:
                        text += "The temperature is %s degrees" % obs.temp
                        if obs.wind_chill is not None:
                            text += ", with a wind chill of %s degrees" % obs.wind_chill
                        elif obs.heat_index is not None:
                            text += ", with a heat index of %s degrees" % obs.heat_index
                elif metric == "dewpoint":
                    if obs.dewpoint is not None:
                        text += "The dewpoint is %s degrees" % obs.dewpoint
                elif metric == "barometric pressure":
                    if obs.pressure is not None:
                        text += "The barometric pressure is at %s inches" % obs.pressure
                        trend = obs.pressure_trend
                        if trend is not None:
                            text += " and %s" % trend
                elif metric == "relative humidity":
                    if obs.humidity is not None:
                        text += "The relative humidity is %s percent" % obs.humidity
                text += ". "
        else:
            text += "Observation information is currently unavailable."

        return self.normalize(text)

    def get_discussion(self):
        match = re.compile(r".*(^\.SHORT TERM.*?)^&&$",
                           re.MULTILINE|re.DOTALL).match(self.get_product("AFD"))
        if not match:
            return "Unable to extract forecast discussion"

        text = match.group(1)

        return text

    def get_extended(self):
        data = self.https("gridpoints/%s/%s/forecast" % (self.loc.cwa, self.loc.grid_point))
        #print(json.dumps(data, indent=4))
        if data is None or data.get("periods", None) is None:
            notify(self.event, "Extended forecast missing periods", data)
            return "the extended forecast is currently unavailable."        
        
        text = ""
        for period in data.get("periods", {}):
            text += " " + period["name"] + ", " + period["detailedForecast"]
            if text.lower().find("wind") < 0:
                wind = period["windSpeed"]
                if wind.lower().find("to") < 0:
                    wind = "around " + wind
                text += ". %s wind %s" % (self.dir_to_dir(period["windDirection"]), wind)
            text + "."

        header = "The extended forecast for the %s zone " % self.loc.forecastZoneName
        if not text:
            header += "is unavailable for %s %s " % \
                    (MONTH_NAMES[when.month - 1],
                     MONTH_DAYS[when.day - 1])

        return self.normalize(header + text)

    def get_forecast(self, metrics):
        text = ""
        snames = {0: "overnight, ",
                  6: "in the morning, ",
                  12: "in the afternoon, ",
                  18: "in the evening, "}
        enames = {0: "midnight",
                  6: "the morning",
                  12: "mid day",
                  18: "the evening"}

        stime = self.stime
        etime = self.etime 
        fulltext = ""
        gp = GridPoints(self.event, self.loc.tz, self.loc.cwa, self.loc.grid_point, self.cache_handler)
        for metric in metrics:
            metric = METRICS[metric][0]
            #print("FORECAST METRIC", metric, "STIME", stime, "ETIME", etime)
#            if gp.set_interval(stime, etime):
            if not gp.set_interval(stime, etime):
                text = "Forecast information is unavailable for %s %s" % \
                       (MONTH_NAMES[self.stime.month - 1],
                        MONTH_DAYS[self.stime.day - 1])
                return text

            isday = self.is_day(stime)
            sname = snames[stime.hour]
            ename = enames[etime.hour]

            text = ""
            if metric == "wind":
                wsh = gp.wind_speed_high
                wsl = gp.wind_speed_low
                wdi = gp.wind_direction_initial
                wdf = gp.wind_direction_final
                if wsh is None:
                    text = "winds will be calm"
                else:
                    if wsh == wsl:
                        if wdi is None:
                            text = "winds will be %s miles per hour" % \
                                   (wsh)
                        else:
                            text = "winds will be out of the %s at %s miles per hour" % \
                                   (wdi, wsh)
                    else:
                        if wdi is None:
                            text = "winds will be %s to %s miles per hour" % \
                                   (wsl, wsh)
                        else:
                            text = "winds will be out of the %s at %s to %s miles per hour" % \
                                   (wdi, wsl, wsh)
                    wg = gp.wind_gust_high
                    if wg is not None:
                        text += ", with gusts as high as %s" % wg
            elif metric == "temperature":
                t = gp.temp_high if isday else gp.temp_low
                if t is not None:
                    text = "the %s temperature will be %s degrees" % \
                           ("high" if isday else "low", t)

                    wcl = gp.wind_chill_low
                    wch = gp.wind_chill_high
                    if wcl is not None:
                        if wcl == wch:
                            if wcl != t:
                                text += ", with a wind chill of %s degrees" % wcl
                        else:
                            text += ", with a wind chill of %s to %s degrees" % (wcl, wch)

                    hil = gp.heat_index_low
                    hih = gp.heat_index_high
                    if hil is not None:
                        if hil == hih:
                            if hil != t:
                                text += ", with a heat index of %s degrees" % hil
                        else:
                            text += ", with a heat index of %s to %s degrees" % (hil, hih)
            elif metric == "dewpoint":
                dh = gp.dewpoint_high
                if dh is not None:
                    text = "the dewpoint will be %s degrees" % dh
            elif metric == "barometric pressure":
                pl = gp.pressure_low
                if pl is not None:
                    text = "the barometric pressure will be %s inches" % pl
            elif metric == "skys":
                si = gp.skys_initial
                sf = gp.skys_final
                if si is not None:
                    if si == sf:
                        text = "it will be %s" % si
                    elif si == None or sf == None:
                        text = "it will be %s" % si or sf
                    else:
                        text = "it will be %s changing to %s" % (si, sf)
            elif metric == "relative humidity":
                hh = gp.humidity_high
                if hh is not None:
                    text = 'the relative humidity will be %.0f percent' % hh
            elif metric == "precipitation":
                pch = gp.precip_chance_high
                if pch is not None:
                    if pch == 0:
                        text = "No precipitation forecasted"
                    else:
                        text = 'the chance of precipitation will be %d percent' % pch

                        pal = gp.precip_amount_low
                        pah = gp.precip_amount_high

                        if pal is not None and pah is not None and pah[0] != 0:
                            text += ", with amounts of "

                            if pal[1] == pah[1] or pal[0] < 0.1:
                                text += "%s %s possible" % (pah[1], pah[2])
                            else:
                                text += "%s to %s %s possible" % (pal[1], pah[1], pah[2])

                        sal = gp.snow_amount_low
                        sah = gp.snow_amount_high
                        if sal is not None and sah is not None and sah[0] != 0:
                            text += ", snowfall amounts of "

                            if sal[1] == sah[1] or sal[0] < 0.1:
                                text += "%s %s possible" % (sah[1], sah[2])
                            else:
                                text += "%s to %s %s possible" % (sal[1], sah[1], sah[2])
            elif metric == "summary":
                wt = gp.weather_text
                if wt:
                    text += "expect " + wt

            if text:
                fulltext += text + ". "

        if fulltext != "":
            fulltext = "%s in %s, %s" % \
                       (self.sname,
                        self.loc.city,
                        fulltext)
        else:
            fulltext = "Forecast information is unavailable for %s in %s" % \
                       (self.sname,
                        self.loc.city)

        return fulltext

    def get_location(self, req=False):
        if self.slots.location or self.slots.zipcode:
            loc = Location(self.event, self.cache_handler)
            text = loc.set(self.slots.location or self.slots.zipcode, self.loc)
            if text is None:
                self.loc = loc
        elif req:
            text = "You must include the location"
        elif self.loc is None:
            text = """"
                   You must set a default location by using phrases like:
                       Alexa, ask Clima Cast to set my location to Boulder Colorado.
                   or:
                       Alexa, ask Clima Cast to set my location to zip code 5 5 1 1 8.
                   """
        else:
            text = None

        return text

    def get_when(self):
        self.has_when = (self.slots.when_abs or \
                         self.slots.when_any or \
                         self.slots.when_pos or \
                         self.slots.day or \
                         self.slots.month) is not None

        now = datetime.now(tz=self.loc.tz) + relativedelta(minute=0, second=0, microsecond=0)
        base = now + relativedelta(hour=6)
        stime = base
        hours = 12
        quarter = None
        sname = ""

        # Handle the days like Monday or Today.
        day = self.slots.when_abs or self.slots.when_any or self.slots.when_pos
        if day:
            # Remove possessive/plural suffixes.  Also, sometimes we will get
            # "over night" instead of "overnight" so fix it.
            day = re.sub(r"'*s$", "", day).replace("over night", "overnight").split()

            # Handle a couple of special cases
            if len(day) > 1:
                # Put "overnight" after the day name.
                if day[0] == "overnight":
                    day = [day[1], "overnight"]
                # Get rid of "this" (as in, this afternoon or this monday)
                elif day[0] == "this":
                    day = [day[1]]

            # Now, determine the actual day           
            if day[0] == "tomorrow":
                stime += relativedelta(days=+1, hour=6)
            elif day[0] in DAYS:
                d = ((DAYS.index(day[0]) - stime.weekday()) % 7)
                stime += relativedelta(days=+d, hour=6)

            # Set the name now, otherwise the user will hear it as a day off 
            # if they used "overnight"
            sname = DAYS[stime.weekday()]
            is_today = stime == base

            #key: [number of days to add, starting hour, duration, label]
            specs = {"today":     [0, 6,  12, ""],
                     "tonight":   [0, 18, 12, " night"],
                     "night":     [0, 18, 12, " night"],
                     "overnight": [1, 0,  6,  " overnight"],
                     "morning":   [0, 6,  6,  " morning"], 
                     "afternoon": [0, 12, 6,  " afternoon"], 
                     "evening":   [0, 18, 6,  " evening"]}

            # Handle any special references
            if day[-1] in specs:
                spec = specs[day[-1]]
                stime += relativedelta(days=spec[0], hour=spec[1])
                hours = spec[2]
                sname += spec[3]

            # Convert back to today, tonight, this, if the resulting day is the
            # same as today's
            if is_today:
                day = sname.split()
                if hours == 6:
                    sname = "overnight" if day[1] == "overnight" else "this " + day[1]
                else:
                    sname = "tonight" if stime.hour == 18 else "today"

        # Handle the day and month usage
        elif self.slots.day is not None:
            month = stime.month
            day = stime.day

            # Get and validate the DAY
            d = self.slots.day
            if d.isdigit() and 1 <= int(d) <= 31:
                d = MONTH_DAYS[int(d) - 1]
            elif d in MONTH_DAYS_XLATE:
                d = MONTH_DAYS_XLATE[d]

            # If it's valid, look for the MONTH
            if d in MONTH_DAYS:
                day = MONTH_DAYS.index(d) + 1

                # Get and validate the month, if any
                if self.slots.month is not None:
                    m = self.slots.month
                    if m in MONTH_NAMES:
                        month = MONTH_NAMES.index(m) + 1
                    else:
                        #notify(self.event, "Unexpected month %s" % m)
                        pass
            else:
                #notify(self.event, "Unexpected day %s" % d)
                pass

            # Adjust the date relative to today
            if month == stime.month and day == stime.day:
                pass
            elif month == stime.month and day < stime.day:
                if self.slots.month:
                    stime += relativedelta(years=+1, month=month, day=day)
                else:
                    stime += relativedelta(months=+1, day=day)
            elif month > stime.month:
                stime += relativedelta(month=month, day=day)
            elif month < stime.month:
                stime += relativedelta(years=+1, month=month, day=day)
            elif day > stime.day:
                stime += relativedelta(day=day)
            elif day < stime.day:
                stime += relativedelta(months=+1, day=day)

            sname = "today" if stime == base else DAYS[stime.weekday()]
        else:
            stime += relativedelta(hour=6 if now.hour < 18 else 18)
            sname = "today" if stime.hour == 6 else "tonight"

        # Set the start and end times, the period name, and the number of periods
        self.stime = stime
        self.etime = self.stime + relativedelta(hours=hours)
        self.sname = sname
        self.quarters = hours // 6
        #print("WHEN:", self.stime, self.etime, self.quarters, quarter)

# ============================================================================
# ASK SDK Request Handlers
# ============================================================================

class BaseIntentHandler(AbstractRequestHandler):
    """Base handler providing common functionality for all intent handlers"""
    
    def get_skill_helper(self, handler_input):
        """Create and initialize Skill instance from handler_input"""
        global TEST_MODE, TEST_CACHE_HANDLER, TEST_SETTINGS_HANDLER
        
        # Use test handlers if in test mode
        if TEST_MODE and TEST_CACHE_HANDLER and TEST_SETTINGS_HANDLER:
            cache_handler = TEST_CACHE_HANDLER
            settings_handler = TEST_SETTINGS_HANDLER
            # Create Skill instance with test handlers
            skill = Skill(handler_input, cache_handler, settings_handler)
        else:
            # Use production handlers (DynamoDB-based)
            # Create settings handler using Alexa's attributes_manager
            settings_handler = AlexaSettingsHandler(handler_input)
            
            # Create Skill instance with modern ASK SDK objects, cache handler, and settings handler
            skill = Skill(handler_input, CACHE_HANDLER, settings_handler)
        
        # Initialize skill (loads location, slots, etc.)
        skill.initialize()
        
        return skill


class LaunchRequestHandler(BaseIntentHandler):
    """Handler for Skill Launch"""
    
    def can_handle(self, handler_input):
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.launch_request()
        return skill.respond(text, end=False)


class SessionEndedRequestHandler(BaseIntentHandler):
    """Handler for Session End"""
    
    def can_handle(self, handler_input):
        return is_request_type("SessionEndedRequest")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        
        # Check for errors in the request
        if hasattr(handler_input.request_envelope.request, 'error'):
            error = handler_input.request_envelope.request.error
            notify(skill.event, "Error detected", error.message if error else "Unknown error")
        
        if hasattr(handler_input.request_envelope.request, 'reason'):
            reason = handler_input.request_envelope.request.reason
            notify(skill.event, "Session Ended", str(reason))
        
        return handler_input.response_builder.response


class CancelAndStopIntentHandler(BaseIntentHandler):
    """Handler for Cancel and Stop Intents"""
    
    def can_handle(self, handler_input):
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        
        if is_intent_name("AMAZON.CancelIntent")(handler_input):
            return skill.respond("Canceled.", end=True)
        else:
            return skill.respond("Thank you for using Clime a Cast.", end=True)


class HelpIntentHandler(BaseIntentHandler):
    """Handler for Help Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("AMAZON.HelpIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.help_intent()
        return skill.respond(text, end=False)


class MetricIntentHandler(BaseIntentHandler):
    """Handler for Metric Intent"""
    
    def can_handle(self, handler_input):
        return (is_intent_name("MetricIntent")(handler_input) or
                is_intent_name("MetricPosIntent")(handler_input))
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.metric_intent()
        return skill.respond(text, end=False)


class GetSettingIntentHandler(BaseIntentHandler):
    """Handler for Get Setting Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("GetSettingIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.get_setting_intent()
        return skill.respond(text, end=False)


class SetLocationIntentHandler(BaseIntentHandler):
    """Handler for Set Location Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("SetLocationIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.set_location_intent()
        return skill.respond(text, end=False)


class SetPitchIntentHandler(BaseIntentHandler):
    """Handler for Set Pitch Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("SetPitchIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.set_pitch_intent()
        return skill.respond(text, end=False)


class SetRateIntentHandler(BaseIntentHandler):
    """Handler for Set Rate Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("SetRateIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.set_rate_intent()
        return skill.respond(text, end=False)


class GetCustomIntentHandler(BaseIntentHandler):
    """Handler for Get Custom Forecast Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("GetCustomIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.get_custom_intent()
        return skill.respond(text, end=False)


class AddCustomIntentHandler(BaseIntentHandler):
    """Handler for Add Custom Forecast Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("AddCustomIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.add_custom_intent()
        return skill.respond(text, end=False)


class RemoveCustomIntentHandler(BaseIntentHandler):
    """Handler for Remove Custom Forecast Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("RemCustomIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.remove_custom_intent()
        return skill.respond(text, end=False)


class ResetCustomIntentHandler(BaseIntentHandler):
    """Handler for Reset Custom Forecast Intent"""
    
    def can_handle(self, handler_input):
        return is_intent_name("RstCustomIntent")(handler_input)
    
    def handle(self, handler_input):
        skill = self.get_skill_helper(handler_input)
        text = skill.reset_custom_intent()
        return skill.respond(text, end=False)


# ============================================================================
# Request and Response Interceptors
# ============================================================================

class RequestLogger(AbstractRequestInterceptor):
    """Log the request envelope."""
    
    def process(self, handler_input):
        logger.info("Request Envelope: %s", handler_input.request_envelope)


class ResponseLogger(AbstractResponseInterceptor):
    """Log the response envelope."""
    
    def process(self, handler_input, response):
        logger.info("Response: %s", response)


# ============================================================================
# Exception Handler
# ============================================================================

class AllExceptionHandler(AbstractExceptionHandler):
    """Catch all exception handler."""
    
    def can_handle(self, handler_input, exception):
        return True
    
    def handle(self, handler_input, exception):
        logger.error("Exception encountered: %s", exception)
        
        # Get event-like structure for notify
        session_attr = handler_input.attributes_manager.session_attributes
        request_envelope = handler_input.request_envelope
        event = {
            "session": {
                "sessionId": request_envelope.session.session_id,
                "user": {
                    "userId": request_envelope.session.user.user_id
                }
            },
            "request": {
                "type": request_envelope.request.object_type,
                "requestId": request_envelope.request.request_id
            }
        }
        
        import traceback
        notify(event, "Exception", traceback.format_exc())
        
        speech = ('<say-as interpret-as="interjection">aw man</say-as>'
                  '<prosody pitch="+25%">'
                  'Clima Cast has experienced an error. The author has been '
                  'notified and will address it as soon as possible. Until then '
                  'you might be able to rephrase your request to get around the issue.'
                  '</prosody>')
        
        handler_input.response_builder.speak(speech).set_should_end_session(True)
        return handler_input.response_builder.response


# ============================================================================
# Skill Builder
# ============================================================================

# Import DynamoDB persistence adapter
from ask_sdk_dynamodb.adapter import DynamoDbAdapter

# Create DynamoDB persistence adapter for user settings
persistence_adapter = DynamoDbAdapter(
    table_name=TABLE_NAME,
    create_table=False,  # Table should already exist or be created by Alexa
    partition_key_name="id",
    attribute_name="attributes"
)

# Create skill builder instance with persistence adapter
sb = CustomSkillBuilder(persistence_adapter=persistence_adapter)

# Register request handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(MetricIntentHandler())
sb.add_request_handler(GetSettingIntentHandler())
sb.add_request_handler(SetLocationIntentHandler())
sb.add_request_handler(SetPitchIntentHandler())
sb.add_request_handler(SetRateIntentHandler())
sb.add_request_handler(GetCustomIntentHandler())
sb.add_request_handler(AddCustomIntentHandler())
sb.add_request_handler(RemoveCustomIntentHandler())
sb.add_request_handler(ResetCustomIntentHandler())

# Register exception handler
sb.add_exception_handler(AllExceptionHandler())

# Register request and response interceptors
sb.add_global_request_interceptor(RequestLogger())
sb.add_global_response_interceptor(ResponseLogger())

# Create the skill instance
skill_instance = sb.create()


# ============================================================================
# Lambda Handler
# ============================================================================

def lambda_handler(event, context=None):
    """
    Lambda handler for Alexa skill using ASK SDK.
    """
    #print(json.dumps(event, indent=4))
    try:
        from ask_sdk_model import RequestEnvelope
        
        serializer = DefaultSerializer()
        request_envelope = serializer.deserialize(
            json.dumps(event), RequestEnvelope
        )
        
        response_envelope = skill_instance.invoke(request_envelope, context)
        
        # Serialize the response back to dict for Lambda
        if response_envelope:
            response_dict = serializer.serialize(response_envelope)
            # If response_dict is already a dict, return it; otherwise parse it
            if isinstance(response_dict, dict):
                return response_dict
            elif isinstance(response_dict, str):
                return json.loads(response_dict)
            else:
                return response_dict
        return None
        
    except SystemExit:
        pass
    except Exception as e:
        import traceback
        logger.error("Lambda handler exception: %s", traceback.format_exc())
        notify(event, "Exception", traceback.format_exc())
        text = '<say-as interpret-as="interjection">aw man</say-as>' + \
               '<prosody pitch="+25%">' + \
               "Clima Cast has experienced an error.  The author has been " + \
               "notified and will address it as soon as possible.  Until then " + \
               "you might be able to rephrase your request to get around the issue." + \
               '</prosody>'
        return {
                 "version": "1.0",
                 "response":
                 {
                   "outputSpeech":
                   {
                     "type": "SSML",
                     "ssml": '<speak>%s</speak>' % text
                   },
                   "reprompt":
                   {
                     "outputSpeech":
                     {
                       "type": "SSML",
                        "ssml": None
                     },
                   },
                   "shouldEndSession": True
                 } 
               }


def test_one():
    global TEST_MODE, TEST_CACHE_HANDLER, TEST_SETTINGS_HANDLER
    
    # Enable test mode and set up local JSON handlers
    TEST_MODE = True
    TEST_CACHE_HANDLER = LocalJsonCacheHandler(".test_cache")
    
    with open(sys.argv[1] if len(sys.argv) > 1 else "test.json") as f:
        event = json.load(f)
        event["session"]["application"]["applicationId"] = "amzn1.ask.skill.test"
        event["session"]["testing"] = True
        
        # Extract user_id from the event and create settings handler
        user_id = event.get("session", {}).get("user", {}).get("userId", "testuser")
        event["session"]["user"]["userId"] = user_id
        TEST_SETTINGS_HANDLER = LocalJsonSettingsHandler(user_id, ".test_settings")
        
        # Print output for testing (this is only used in __main__ test mode)
        print(json.dumps(lambda_handler(event), indent=4))

if __name__ == "__main__":
    import logging
    import sys
    logging.basicConfig()
    # Note: httpx doesn't need the cachecontrol library like requests did
    # The client is already configured with proper timeouts

    test_one()
