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
Core weather processing logic for Clima Cast.

This module contains all the business logic for processing weather requests,
independent of the Lambda/Alexa infrastructure. It can be used by both the
Lambda function (via ASK SDK handlers) and the CLI for local testing.
"""

import json
import os
import re
from difflib import SequenceMatcher
from math import sqrt
from time import time

import requests
from aniso8601.duration import parse_duration
from cachetools import TTLCache, cached
from datetime import datetime
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Try to import DynamoDB-related modules (only available in Lambda)
try:
    from boto3 import resource
    from botocore.exceptions import ClientError
    HAS_DYNAMODB = True
except ImportError:
    HAS_DYNAMODB = False
    resource = None
    ClientError = None

# Load environment variables
load_dotenv()

# DynamoDB resources (only used when running in Lambda mode)
PERSISTENCE_REGION = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
PERSISTENCE_TABLE_NAME = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')

if PERSISTENCE_REGION and PERSISTENCE_TABLE_NAME and HAS_DYNAMODB:
    ddb_resource = resource('dynamodb', region_name=PERSISTENCE_REGION)
else:
    ddb_resource = None

"""
    Constants and configuration
"""
VERSION = 2
REVISION = 0

NORMALIZE = None
NORMALIZE_RE = [r"(?P<meridian>\d+\s*(am|pm))",
                r"(?P<deg>\s(1|-1))\s*degrees",
                r"(?P<ign>[A-Z][A-Z][CZ]\d\d\d.*?/.*?/)",
                r"(?P<nm>\d+\s*(nm))(?=\s|\W|$)",
                r"(?P<kt>\d+\s*(kt))(?=\s|\W|$)",
                r"(?P<tz>(?<=\s|\.)(hadt|hast|akdt|akst|pdt|pst|mdt|mst|cdt|cst|edt|est))(?=\s|\W|$)",
                r"(?P<sub>(?<=\s|\.)(ft|mph|nws|pt\.|pt))(?=\s|\W|$)",
                r"(?P<wind>(?<=\s|\.)(n|nne|ne|ene|e|ese|se|sse|s|ssw|sw|wsw|w|wnw|nw|nnw))(?=\s|$)",
                r"(?P<st>(?<=\s|\.)[A-Z][A-Z])(?=\s|\W|$)"]

FUNCS = {"LaunchRequest": ["launch_request", False],
         "SessionEndRequest": ["session_end_request", False],
         "SessionEndedRequest": ["session_ended_request", False],

         "AMAZON.CancelIntent": ["cancel_intent", False],
         "AMAZON.HelpIntent": ["help_intent", False],
         "AMAZON.NoIntent": ["no_intent", False],
         "AMAZON.StartOverIntent": ["start_over_intent", False],
         "AMAZON.StopIntent": ["stop_intent", False],
         "AMAZON.YesIntent": ["yes_intent", False],

         "MetricIntent": ["metric_intent", True],
         "MetricPosIntent": ["metric_intent", True],

         "GetSettingIntent": ["get_setting_intent", True],
         "SetPitchIntent": ["set_pitch_intent", False],
         "SetRateIntent": ["set_rate_intent", False],
         "SetLocationIntent": ["set_location_intent", False],

         "GetCustomIntent": ["get_custom_intent", False],
         "AddCustomIntent": ["add_custom_intent", False],
         "RemCustomIntent": ["remove_custom_intent", False],
         "RstCustomIntent": ["reset_custom_intent", False]}

SLOTS = ["day",
         "leadin",
         "location",
         "metric",
         "month",
         "percent",
         "quarter",
         "setting",
         "when_abs",
         "when_any",
         "when_pos",
         "zip_conn",
         "zipcode"]

QUARTERS = ["morning",
            "afternoon",
            "evening",
            "overnight",
            "tonight",
            "night"]

DAYS = ["monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday"]

MONTH_DAYS_XLATE = {"1st": "first",
                    "2nd": "second",
                    "3rd": "third",
                    "4th": "fourth",
                    "5th": "fifth",
                    "6th": "sixth",
                    "7th": "seventh",
                    "8th": "eighth",
                    "9th": "ninth",
                    "10th": "tenth",
                    "11th": "eleventh",
                    "12th": "twelfth",
                    "13th": "thirteenth",
                    "14th": "fourteenth",
                    "15th": "fifteenth",
                    "16th": "sixteenth",
                    "17th": "seventeenth",
                    "18th": "eighteenth",
                    "19th": "nineteenth",
                    "20th": "twentieth",
                    "21st": "twenty first",
                    "22nd": "twenty second",
                    "23rd": "twenty third",
                    "24th": "twenty fourth",
                    "25th": "twenty fifth",
                    "26th": "twenty sixth",
                    "27th": "twenty seventh",
                    "28th": "twenty eighth",
                    "29th": "twenty ninth",
                    "30th": "thirtieth",
                    "31st": "thirty first",
                    "11st": "eleventh",
                    "13rd": "thirteenth",
                    "20 second": "twenty second"}

MONTH_DAYS = ["first",
              "second",
              "third",
              "fourth",
              "fifth",
              "sixth",
              "seventh",
              "eighth",
              "ninth",
              "tenth",
              "eleventh",
              "twelfth",
              "thirteenth",
              "fourteenth",
              "fifteenth",
              "sixteenth",
              "seventeenth",
              "eighteenth",
              "nineteenth",
              "twentieth",
              "twenty first",
              "twenty second",
              "twenty third",
              "twenty fourth",
              "twenty fifth",
              "twenty sixth",
              "twenty seventh",
              "twenty eighth",
              "twenty ninth",
              "thirtieth",
              "thirty first"]

MONTH_NAMES = ["january",
               "february",
               "march",
               "april",
               "may",
               "june",
               "july",
               "august",
               "september",
               "october",
               "november",
               "december"]

METRICS = {"summary": ["summary", 1],
           "temp": ["temperature", 2],
           "temperature": ["temperature", 2],
           "wind chill": ["temperature", 2],
           "heat index": ["temperature", 2],
           "precipitation": ["precipitation", 3],
           "chance of rain": ["precipitation", 3],
           "chance of snow": ["precipitation", 3],
           "rain chance": ["precipitation", 3],
           "snow chance": ["precipitation", 3],
           "skys": ["skys", 4],
           "wind": ["wind", 5],
           "barometric pressure": ["barometric pressure", 6],
           "pressure": ["barometric pressure", 6],
           "humidity": ["relative humidity", 7],
           "relative humidity": ["relative humidity", 7],
           "dewpoint": ["dewpoint", 8],
           "dew point": ["dewpoint", 8],
           "weather": ["all", 0],
           "conditions": ["all", 0],
           "extended forecast": ["extended forecast", 0],
           "forecast": ["all", 0],
           "rainy": ["precipitation", 0],
           "raining": ["precipitation", 0],
           "snowy": ["precipitation", 0],
           "snowing": ["precipitation", 0],
           "windy": ["wind", 0],
           "cloudy": ["skys", 0],
           "overcast": ["skys", 0],
           "clear": ["skys", 0],
           "sunny": ["skys", 0],
           "rain": ["precipitation", 0],
           "snow": ["precipitation", 0]}

ANGLES = [["north", "N", 11.25],
          ["north northeast", "NNE", 33.75],
          ["northeast", "NE", 56.25],
          ["east northeast", "ENE", 78.75],
          ["east", "E", 101.25],
          ["east southeast", "ESE", 123.75],
          ["southeast", "SE", 146.25],
          ["south southeast", "SSE", 168.75],
          ["south", "S", 191.25],
          ["south southwest", "SSW", 213.75],
          ["southwest", "SW", 236.25],
          ["west southwest", "WSW", 258.75],
          ["west", "W", 281.25],
          ["west northwest", "WNW", 303.75],
          ["northwest", "NW", 326.25],
          ["north northwest", "NNW", 348.75],
          ["north", "N", 360]]

STATES = ["alabama", "al",
          "alaska", "ak",
          "arizona", "az",
          "arkansas", "ar",
          "dc", "dc",
          "california", "ca",
          "colorado", "co",
          "connecticut", "ct",
          "delaware", "de",
          "florida", "fl",
          "georgia", "ga",
          "hawaii", "hi",
          "idaho", "id",
          "illinois", "il",
          "indiana", "in",
          "iowa", "ia",
          "kansas", "ks",
          "kentucky", "ky",
          "louisiana", "la",
          "maine", "me",
          "maryland", "md",
          "massachusetts", "ma",
          "michigan", "mi",
          "minnesota", "mn",
          "mississippi", "ms",
          "missouri", "mo",
          "montana", "mt",
          "nebraska", "ne",
          "nevada", "nv",
          "new hampshire", "nh",
          "new jersey", "nj",
          "new mexico", "nm",
          "new york", "ny",
          "north carolina", "nc",
          "north dakota", "nd",
          "ohio", "oh",
          "oklahoma", "ok",
          "oregon", "or",
          "pennsylvania", "pa",
          "peurto rico", "pr",
          "rhode island", "ri",
          "south carolina", "sc",
          "south dakota", "sd",
          "tennessee", "tn",
          "texas", "tx",
          "utah", "ut",
          "vermont", "vt",
          "virginia", "va",
          "washington", "wa",
          "west virginia", "wv",
          "wisconsin", "wi",
          "wyoming", "wy"]

SETTINGS = {"location": "location",
            "pitch": "pitch",
            "rate": "rate",
            "forecast": "forecast"}

TIME_QUARTERS = {0: ["overnight", False],
                 1: ["morning", True],
                 2: ["after noon", True],
                 3: ["evening", False]}

# Most of these are guesses.  "good" means observed in data
WEATHER_COVERAGE = {"areas_of": "areas of",                         # good
                    "brief": "brief",
                    "chance": "a chance of",                        # good
                    "definite": "definite",                         # good
                    "frequent": "frequent",
                    "intermittent": "intermittent",
                    "isolated": "isolated",                         # good
                    "likely": "likely",                             # good
                    "numerous": "numerous",                         # good
                    "occasional": "occasional",                     # good
                    "patchy": "patchy",                             # good
                    "periods_of": "periods of",
                    "scattered": "scattered",                       # good
                    "slight_chance": "a slight chance of",          # good
                    "widespread": "widespread"}                     # good

WEATHER_WEATHER = {"blowing_dust": "blowing dust",
                   "blowing_sand": "blowing sand",
                   "blowing_snow": "blowing snow",
                   "drizzle": "drizzle",                            # good
                   "fog": "fog or mist",                            # good
                   "freezing_drizzle": "freezing drizzle",
                   "freezing_fog": "freezing fog",                  # good
                   "freezing_rain": "freezing rain",                # good
                   "freezing_spray": "freezing spray",
                   "frost": "frost",
                   "hail": "hail",
                   "haze": "haze",                                  # good
                   "ice_crystals": "ice crystals",
                   "ice_fog": "ice fog",
                   "ice_pellets": "sleet",
                   "rain": "rain",                                  # good
                   "rain_showers": "rain showers",                  # good
                   "smoke": "smoke",
                   "snow": "snow",                                  # good
                   "snow_showers": "snow showers",                  # good
                   "thunderstorms": "thunderstorms",                # good
                   "volcanic ash": "volcanic ash",
                   "water_spouts": "water spouts"}

WEATHER_INTENSITY = {"": ["", 0],                                   # good
                     "very_light": ["very light", 1],               # good
                     "light": ["light", 2],                         # good
                     "moderate": ["moderate", 3],                   # good
                     "heavy": ["heavy", 4]}                         # good

WEATHER_VISIBILITY = {"": None}

WEATHER_ATTRIBUTES = {"damaging_wind": "damaging wind",                     # good
                      "dry": "dry",
                      "frequent_lightning": "frequent lightning",
                      "gusty_wind": "gusty winds",                          # good
                      "heavy_rain": "heavy rain",                           # good
                      "highest_ranking": "highest ranking",
                      "include_unconditionally": "include unconditionally",
                      "large_hail": "large hail",                           # good
                      "mixture": "mixture",
                      "on_bridges": "on bridges and overpasses",
                      "on_grassy": "on grassy areas",
                      "or": "or",
                      "outlying": "outlying areas",
                      "small_hail": "small hail",                           # good
                      "tornado": "tornado"}

# Known location corrections for common speech recognition errors
# This is used as a fallback before fuzzy matching
_KNOWN_LOCATION_CORRECTIONS = {
    "gnome alaska": "nome alaska",
    "woodberry minnesota": "woodbury minnesota"
}

# Common US city names for fuzzy matching when location is misheard
_COMMON_US_CITIES = [
    "nome alaska", "fairbanks alaska", "anchorage alaska", "juneau alaska",
    "phoenix arizona", "tucson arizona", "mesa arizona",
    "los angeles california", "san francisco california", "san diego california", "sacramento california",
    "denver colorado", "colorado springs colorado", "boulder colorado",
    "miami florida", "orlando florida", "tampa florida", "jacksonville florida",
    "atlanta georgia", "augusta georgia", "columbus georgia", "savannah georgia",
    "chicago illinois", "springfield illinois", "peoria illinois",
    "indianapolis indiana", "fort wayne indiana",
    "boston massachusetts", "worcester massachusetts", "springfield massachusetts",
    "detroit michigan", "grand rapids michigan", "lansing michigan",
    "minneapolis minnesota", "saint paul minnesota", "duluth minnesota", "woodbury minnesota",
    "kansas city missouri", "saint louis missouri", "springfield missouri",
    "las vegas nevada", "reno nevada", "henderson nevada",
    "new york new york", "buffalo new york", "rochester new york", "albany new york",
    "charlotte north carolina", "raleigh north carolina", "greensboro north carolina",
    "columbus ohio", "cleveland ohio", "cincinnati ohio", "toledo ohio",
    "portland oregon", "salem oregon", "eugene oregon",
    "philadelphia pennsylvania", "pittsburgh pennsylvania", "harrisburg pennsylvania",
    "nashville tennessee", "memphis tennessee", "knoxville tennessee", "chattanooga tennessee",
    "houston texas", "dallas texas", "san antonio texas", "austin texas", "fort worth texas",
    "seattle washington", "spokane washington", "tacoma washington",
    "milwaukee wisconsin", "madison wisconsin", "green bay wisconsin"
]


def correct_location_name(name):
    """
    Correct commonly misheard location names using known corrections and fuzzy matching.
    
    This replaces the simple LOCATION_XLATE dictionary with a more robust solution
    that can handle a wider variety of speech recognition errors.
    
    Args:
        name: The location name as heard by Alexa (normalized to lowercase)
        
    Returns:
        The corrected location name, or the original if no correction is needed
    """
    # First check known corrections for exact matches
    if name in _KNOWN_LOCATION_CORRECTIONS:
        return _KNOWN_LOCATION_CORRECTIONS[name]
    
    # Use fuzzy matching to find the closest match from common cities
    # Only suggest corrections for high confidence matches (>0.85 similarity)
    best_match = None
    best_ratio = 0.85  # Threshold to avoid false corrections
    
    for city in _COMMON_US_CITIES:
        ratio = SequenceMatcher(None, name, city).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = city
    
    return best_match if best_match else name


HERE_API_KEY = os.environ.get("here_api_key", "")

HTTPS = requests.Session()

# Cache up to 100 HTTP responses for 1 hour
HTTP_CACHE = TTLCache(maxsize=100, ttl=3600)


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

    print("NOTIFY:\n\n  %s\n\n%s" % (sub, text))


@cached(HTTP_CACHE)
def get_api_data(url):
    """
        Cached HTTP GET request for API data
    """
    headers = {"User-Agent": "ClimacastAlexaSkill/2.0 (climacast@homerow.net)",
               "Accept": "application/ld+json, application/json"}
    r = HTTPS.get(url, headers=headers)
    if r.status_code != 200 or r.text is None or r.text == "":
        return None, r.status_code, r.url, r.content
    return json.loads(r.text), r.status_code, r.url, None

class Base(object):
    def __init__(self, event, attributes_manager=None, cache_adapter=None):
        self.event = event
        self._attributes_manager = attributes_manager
        self._cache_adapter = cache_adapter

    def get_zone(self, zoneId, zoneType):
        """
            Returns the zone information for the give zone ID
        """
        zoneId = zoneId.rsplit("/")[-1]
        zone = self.cache_get("ZoneCache", {"id": zoneId})
        if zone is None:
            data = self.https("zones/%s/%s" % (zoneType, zoneId))
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get zone info for %s" % zoneId, data)
                return {}
            zone = self.put_zone("ZoneCache", data)

        return zone

    def put_zone(self, cache_name, data):
        """
            Writes the zone information to the cache
        """
        zone = {"id": data["id"],
                "type": data["type"],
                "name": data["name"]}

        self.cache_put(cache_name, zone)

        return zone

    def get_forecast_zone(self, zoneId):
        """
            Returns the forecast zone for the given zone ID
        """
        return self.get_zone(zoneId, "forecast")

    def get_county_zone(self, zoneId):
        """
            Return the county zone for the given zone ID
        """
        return self.get_zone(zoneId, "county")

    def get_fire_zone(self, zoneId):
        """
            Returns the fire zone for the given zone ID
        """
        return self.get_zone(zoneId, "fire")

    def get_stations(self, coords):
        """
            Returns the list of stations nearest to furthest order
            from the given coordinates
        """
        #print("coords", coords)
        data = self.https("points/%s/stations" % coords)
        #print("DATA", data)
        if data is None or data.get("status", 0) != 0:
            notify(self.event, "Unable to get stations for %s" % coords, data)
            return []

        return [station.rsplit("/")[-1] for station in data["observationStations"]]

    def get_station(self, stationId):
        """
            Returns the station information for the given station ID
        """
        stationId = stationId.rsplit("/")[-1]
        station = self.cache_get("StationCache", {"id": stationId})
        if station is None:
            data = self.https("stations/%s" % stationId)
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get station %s" % stationId, data)
                return None
            station = self.put_station("StationCache", data)

        return station

    def put_station(self, cache_name, data):
        """
            Save station information to the cache
        """
        name = data["name"].split(",")[-1].strip().rstrip()

        # DC station names seem to be reversed from the rest
        if name == "DC":
            name = data["name"].split(",")[0].strip().rstrip()

        station = {"id": data["stationIdentifier"],
                   "name": name}

        self.cache_put(cache_name, station)

        return station

    def get_product(self, product):
        """
            Return the text for the given product
        """
        text = ""

        # Retrieve list of features provided by the given CWA
        data = self.https("products/types/%s/locations/%s" % (product, self.loc["cwa"]))
        if data is None or data.get("status", 0) != 0:
            notify(self.event, "Unable to get %s product list" % product, data)
            return None

        # Retrieve the most current feature
        if len(data["@graph"]) > 0:
            data = self.https("products/%s" % (data["@graph"][0]["id"]))
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get product %s" % product, data)
                return None
            text = data["productText"]

        return text

    def cache_get(self, cache_name, key):
        """
            Retrieve an item from the cache using the provided cache name and key.
            
            If a cache_adapter is provided, use it. Otherwise, fallback to direct
            DynamoDB access for backward compatibility.
        """
        # Use cache adapter if available
        if self._cache_adapter:
            return self._cache_adapter.get(cache_name, key)
        
        # Fallback to direct DynamoDB access (legacy code)
        # Build a key string from the key dict
        # Sort to ensure consistent key ordering
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Access persistent attributes directly based on cache type
        if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
            # For shared caches, read directly from DynamoDB with shared key
            table = ddb_resource.Table(PERSISTENCE_TABLE_NAME)
            try:
                response = table.get_item(Key={"id": "SHARED_CACHE"})
                if "Item" not in response:
                    return None
                attrs = response["Item"].get("attributes", {})
                current_version = response["Item"].get("version", 0)
            except Exception:
                return None
        else:
            # For user-specific caches, use the attributes manager
            if not hasattr(self, '_attributes_manager'):
                return None
            attrs = self._attributes_manager.persistent_attributes
            current_version = None
        
        # Get the cache dict
        cache_dict = attrs.get(cache_name, {})
        
        # Check if item exists and if TTL is still valid
        item = cache_dict.get(key_str)
        if item is None:
            return None
            
        # Check TTL if present
        if "ttl" in item and item["ttl"] < int(time()):
            # Item expired, remove it
            del cache_dict[key_str]
            attrs[cache_name] = cache_dict
            
            # Save the updated cache
            if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
                # Use optimistic locking for shared caches
                table = ddb_resource.Table(PERSISTENCE_TABLE_NAME)
                new_version = current_version + 1
                try:
                    if current_version == 0:
                        # First write or no version - no condition needed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            }
                        )
                    else:
                        # Conditional write to ensure version hasn't changed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            },
                            ConditionExpression="version = :current_version",
                            ExpressionAttributeValues={
                                ":current_version": current_version
                            }
                        )
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                        # Version conflict - someone else modified it, that's ok for expiry
                        print(f"Version conflict when removing expired item, skipping")
                    else:
                        print(f"Error saving shared cache: {e}")
                except Exception as e:
                    print(f"Error saving shared cache: {e}")
            else:
                if hasattr(self, '_attributes_manager'):
                    self._attributes_manager.save_persistent_attributes()
            
            return None
            
        return item

    def cache_put(self, cache_name, key, ttl=35):
        """
            Write an item to the cache using the provided cache name, key, and time to live.
            
            If a cache_adapter is provided, use it. Otherwise, fallback to direct
            DynamoDB access for backward compatibility.
        """
        # Use cache adapter if available
        if self._cache_adapter:
            return self._cache_adapter.put(cache_name, key, ttl)
        
        # Fallback to direct DynamoDB access (legacy code)
        # Build a key string from the key dict
        # Sort to ensure consistent key ordering
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Add TTL if specified
        if ttl != 0:
            key["ttl"] = int(time()) + (ttl * 24 * 60 * 60)
        
        # Access persistent attributes directly based on cache type
        if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
            # For shared caches, use optimistic locking with version number
            table = ddb_resource.Table(PERSISTENCE_TABLE_NAME)
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Read current version and attributes
                    response = table.get_item(Key={"id": "SHARED_CACHE"})
                    if "Item" in response:
                        attrs = response["Item"].get("attributes", {})
                        current_version = response["Item"].get("version", 0)
                    else:
                        attrs = {}
                        current_version = 0
                except Exception as e:
                    print(f"Error reading shared cache: {e}")
                    attrs = {}
                    current_version = 0
                
                # Update cache dict
                cache_dict = attrs.get(cache_name, {})
                cache_dict[key_str] = key
                attrs[cache_name] = cache_dict
                
                # Increment version for optimistic locking
                new_version = current_version + 1
                
                # Write back to DynamoDB with conditional expression
                try:
                    if current_version == 0:
                        # First write or item doesn't exist - no condition needed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            }
                        )
                    else:
                        # Conditional write to ensure version hasn't changed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            },
                            ConditionExpression="version = :current_version",
                            ExpressionAttributeValues={
                                ":current_version": current_version
                            }
                        )
                    # Success - exit retry loop
                    break
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                        # Version mismatch - retry with exponential backoff
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Version conflict on shared cache write, retry {retry_count}/{max_retries}")
                            # Simple exponential backoff (could be improved with jitter)
                            import time as time_module
                            time_module.sleep(0.1 * (2 ** retry_count))
                        else:
                            print(f"Failed to write shared cache after {max_retries} retries")
                    else:
                        print(f"Error saving shared cache: {e}")
                        break
                except Exception as e:
                    print(f"Error saving shared cache: {e}")
                    break
        else:
            # For user-specific caches, use the attributes manager
            if not hasattr(self, '_attributes_manager'):
                return
            
            attrs = self._attributes_manager.persistent_attributes
            cache_dict = attrs.get(cache_name, {})
            cache_dict[key_str] = key
            attrs[cache_name] = cache_dict
            self._attributes_manager.save_persistent_attributes()

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

        #print("URL:", url_result)
        #print("PAGE:", json.dumps(data, indent=4))

        return data

    def to_skys(self, percent, isday):
        """
            Convert the sky cover percentage to text
        """
        if percent is not None:
            if 0.0 <= percent < 12.5:
                percent = "sunny" if isday else "clear"
            elif 12.5 <= percent < 25.0:
                percent = "mostly sunny" if isday else "mostly clear"
            elif 25.0 <= percent < 50.0:
                percent = "partly sunny" if isday else "partly cloudy"
            elif 50.0 <= percent < 87.5:
                percent = "mostly cloudy"
            elif 87.5 <= percent <= 100.0:
                percent = "cloudy"
            else:
                percent = None

        return percent

    def to_percent(self, percent):
        """
            Return the given value, if any, as an integer
        """
        return None if percent is None else int(percent)

    def mb_to_in(self, mb):
        """
            Convert the given millibar value, if any, to inches
        """
        # Every so often we get back a value of 900 which seems to be
        # some sort of "low value".  So, just consider it invalid.
        if mb == 900:
            return None
        return None if mb is None else "{:.2f}".format(mb * 0.0295301)

    def pa_to_in(self, pa):
        """
            Convert the given pascals, if any, to inches
        """
        return None if pa is None else "{:.2f}".format(pa * 0.000295301)

    def mm_to_in(self, mm, as_text=False):
        """
            Convert the given millimeters, if any, to inches.  If requested,
            further convert inches to words.
        """
        inches = None if mm is None else "{:.2f}".format(mm * 0.0393701)
        if not as_text or not inches:
            return inches

        inches = float(inches)
        whole = int(inches)
        frac = inches - whole

        if inches == 0:
            return inches, "", ""

        if inches < 0.1:
            amt = "less than a tenth"
        elif 0.1 <= frac < 0.125:
            amt = "less than a quarter"
        elif 0.125 <= frac < 0.375:
            amt = "a quarter"
        elif 0.375 <= frac < 0.625:
            amt = "a half"
        elif 0.625 <= frac < 0.875:
            amt = "three quarters"
        else:
            whole += 1
            frac = 0.0
            amt = "%d" % whole

        if whole == 0:
            return inches, amt, "of an inch"

        if frac == 0.0:
            return inches, amt, "inch%s" % "" if whole == 1 else "es"

        return inches, "%d and %s" % (whole, amt), "of an inch"

    def c_to_f(self, c):
        """
            Convert the given celcius value, if any, to fahrenheit
        """
        return None if c is None else "{:.0f}".format(c * 9 / 5 + 32)

    def mps_to_mph(self, mps):
        """
            Convert the given meters per second, if any, to miles per hour
        """
        return None if mps is None or mps == 0 else "{:.0f}".format(mps * 2.23694)

    def da_to_dir(self, da):
        """
            Convert the given degrees (angle), if any, to a compass direction
        """
        if da is not None:
            for item in ANGLES:
                if da < item[2]:
                    return item[0]
        return None

    def dir_to_dir(self, da):
        """
            Convert the given short direction to long
        """
        if da is not None:
            for item in ANGLES:
                if da == item[1]:
                    return item[0]
        return None

    def to_wind_chill(self, F, mph):
        if F > 50.0 or mph <= 3.0:
            return None

        return round(35.74 + .6215*F - 35.75*pow(mph, 0.16) + 0.4275*F*pow(mph, 0.16))

    def to_heat_index(self, F, rh):
        """
            Calculate the heat index
            Taken from: http://www.wpc.ncep.noaa.gov/html/heatindex.shtml
        """
        if rh > 100.0 or rh < 0.0:
            return None

        if F <= 40.0:
            return F

        hitemp = 61.0+((F-68.0)*1.2)+(rh*0.094)
        hifinal = 0.5*(F+hitemp)

        if hifinal > 79.0:
            hi = -42.379+2.04901523*F+10.14333127*rh-0.22475541*F*rh-6.83783*(pow(10, -3))*(pow(F, 2))-5.481717*(pow(10, -2))*(pow(rh, 2))+1.22874*(pow(10, -3))*(pow(F, 2))*rh+8.5282*(pow(10, -4))*F*(pow(rh, 2))-1.99*(pow(10, -6))*(pow(F, 2))*(pow(rh, 2))
            if (rh <= 13) and (F >= 80.0) and (F <= 112.0):
                adj1 = (13.0-rh)/4.0
                adj2 = sqrt((17.0-abs(F-95.0))/17.0)
                adj = adj1 * adj2
                hi = hi - adj
            elif (rh > 85.0) and (F >= 80.0) and (F <= 87.0):
                adj1 = (rh-85.0)/10.0
                adj2 = (87.0-F)/5.0
                adj = adj1 * adj2
                hi = hi + adj
        else:
            hi = hifinal

        return int(round(hi))

    def normalize(self, text):
        """
            Tries to identify various text patterns and replaces them
            with easier to hear alternatives
        """
        #print("TEXT", text)
        # Compile (and save) all of the regular expressions
        global NORMALIZE
        if NORMALIZE is None:
            NORMALIZE = re.compile("(" + "|".join(NORMALIZE_RE) + ")", re.IGNORECASE)

        # Iterate through the matches found in the text
        out = ""
        last = 0
        text = text.replace("\n", " ")
        for match in NORMALIZE.finditer(text):
            # Collect the leading text fragment
            #print("'" + text[last:match.start()] + "'")
            out += text[last:match.start()]

            # Process the matched groups (there should only be 1)
            last = match.end()
            for group in match.groupdict().items():
                value = group[1]
                if value is None:
                    continue

                #print("N", group[0], "V", group[1])
                name = group[0]

                # Convert a state abbreviation to the full name, with the exception
                # IN, NE, and OR since they can't be distinguished from normal text.
                # And DC since we just want to leave that as-is.
                if name == "st":
                    try:
                        st = value.lower()
                        if st in "in ne or dc":
                            out += value
                        else:
                            out += STATES[STATES.index(st) - 1]
                    except (ValueError, IndexError):
                        out += value

                # Substitute full text for abbreviations
                elif name == "sub":
                    out += {"ft": "feet",
                            "nws": "national weather service",
                            "mph": "miles per hour",
                            "pt": "point",
                            "pt.": "point"}[value.lower()]

                # Convert nautical miles
                elif name == "nm":
                    out += value[:-2] + " nautical miles"

                # Convert knots
                elif name == "kt":
                    out += value[:-2] + " knots"

                # Convert AM/PM and correct the time format so it speaks correctly
                elif name == "meridian":
                    time = value[:-2].strip()
                    if len(time) > 2:
                        time = time[:-2] + ":" + time[-2:]
                    out += time + " " + ".".join(list(value[-2:])) + "."

                # Ensure time zone identifiers are abbreviations so they speak properly
                elif name == "tz":
                    out += ".".join(list(value)) + "."

                # Just ignore it so it will be removed from the text
                elif name == "ign":
                    pass

                # Convert wind direction abbreviations to full text
                elif name == "wind":
                    value = value.upper()
                    for dir in ANGLES:
                        if dir[1] == value:
                            value = dir[0]
                    out += value

                # Change -1|1 degrees to -1|1 degree
                elif name == "deg":
                    out += value + " degree"

        # Tack on the final fragment and return
        return (out + text[last:]).lower()

    def is_day(self, when):
        """
            Determine if given time is during the day
        """
        return True if 6 <= when.hour < 18 else False


class GridPoints(Base):
    def __init__(self, event, tz, cwa, gridpoint, attributes_manager=None, cache_adapter=None):
        super().__init__(event, attributes_manager, cache_adapter)
        self.tz = tz
        self.data = self.https("gridpoints/%s/%s" % (cwa, gridpoint))
        #print(json.dumps(self.data, indent=4))
        #notify(event, "PRESSURE", json.dumps(self.data, indent=4))
        self.values = {}
        self.times = {}
        self.highs = {}
        self.lows = {}

    def set_interval(self, stime, etime):
        self.values = {}
        self.highs = {}
        self.lows = {}
        self.stime = stime
        self.etime = etime

        if self.data:
            dts, dte = self.in_range(self.data["validTimes"], stime, etime)
            if dts and dte:
                return True

        return False

    def in_range(self, time, stime, etime):
        dt, _, dur = time.partition("/")
        dts = parser.parse(dt).astimezone(self.tz)
        dte = dts + parse_duration(dur, relative=True)

        if stime >= dts and stime < dte \
           or etime >= dts and etime < dte:
            return dts, dte

        return None, None

    def get_values(self, metric):
        if metric not in self.values:
            vals = []
            times = []
            stime = self.stime
            #print("GETV", metric, self.stime, self.etime)
            for value in self.data.get(metric, {}).get("values", {}):
                dts, dte = self.in_range(value["validTime"], stime, self.etime)
                if dts and dte:
                    v = value["value"]
                    #print("VAL", v, stime)
                    while stime < self.etime and stime < dte:
                        vals.append(v)
                        times.append(stime)
                        stime += relativedelta(hours=+1)
                if stime >= self.etime:
                    break
            self.values[metric] = vals
            self.times[metric] = times

        #print("GETV", self.values[metric])
        return self.values[metric]

    def get_low(self, metric):
        if metric not in self.lows:
            values = [value for value in self.get_values(metric) if value is not None]
            if len(values) == 0:
                return None
            self.lows[metric] = min(values)

        return self.lows[metric]

    def get_high(self, metric):
        if metric not in self.highs:
            values = [value for value in self.get_values(metric) if value is not None]
            if len(values) == 0:
                return None
            self.highs[metric] = max(values)

        return self.highs[metric]

    def get_initial(self, metric):
        values = self.get_values(metric)
        return values[0] if len(values) > 0 else None

    def get_final(self, metric):
        values = self.get_values(metric)
        return values[-1] if len(values) > 0 else None

    @property
    def temp_low(self):
        return self.c_to_f(self.get_low("temperature"))

    @property
    def temp_high(self):
        return self.c_to_f(self.get_high("temperature"))

    @property
    def temp_initial(self):
        return self.c_to_f(self.get_initial("temperature"))

    @property
    def temp_final(self):
        return self.c_to_f(self.get_final("temperature"))

    @property
    def humidity_low(self):
        return self.to_percent(self.get_low("relativeHumidity"))

    @property
    def humidity_high(self):
        return self.to_percent(self.get_high("relativeHumidity"))

    @property
    def humidity_initial(self):
        return self.to_percent(self.get_initial("relativeHumidity"))

    @property
    def humidity_final(self):
        return self.to_percent(self.get_final("relativeHumidity"))

    @property
    def dewpoint_low(self):
        return self.c_to_f(self.get_low("dewpoint"))

    @property
    def dewpoint_high(self):
        return self.c_to_f(self.get_high("dewpoint"))

    @property
    def dewpoint_initial(self):
        return self.c_to_f(self.get_initial("dewpoint"))

    @property
    def dewpoint_final(self):
        return self.c_to_f(self.get_final("dewpoint"))

    @property
    def pressure_low(self):
        return self.mb_to_in(self.get_low("pressure"))

    @property
    def pressure_high(self):
        return self.mb_to_in(self.get_high("pressure"))

    @property
    def pressure_initial(self):
        return self.mb_to_in(self.get_initial("pressure"))

    @property
    def pressure_final(self):
        return self.mb_to_in(self.get_final("pressure"))

    @property
    def pressure_trend(self):
        values = self.get_values("pressure")
        if values[0] > values[-1]:
            return "falling"
        if values[0] < values[-1]:
            return "rising"
        return "steady"

    @property
    def precip_chance_low(self):
        return self.to_percent(self.get_low("probabilityOfPrecipitation"))

    @property
    def precip_chance_high(self):
        return self.to_percent(self.get_high("probabilityOfPrecipitation"))

    @property
    def precip_chance_initial(self):
        return self.to_percent(self.get_initial("probabilityOfPrecipitation"))

    @property
    def precip_chance_final(self):
        return self.to_percent(self.get_final("probabilityOfPrecipitation"))

    @property
    def precip_amount_low(self):
        return self.mm_to_in(self.get_low("quantitativePrecipitation"), as_text=True)

    @property
    def precip_amount_high(self):
        return self.mm_to_in(self.get_high("quantitativePrecipitation"), as_text=True)

    @property
    def precip_amount_initial(self):
        return self.mm_to_in(self.get_initial("quantitativePrecipitation"), as_text=True)

    @property
    def precip_amount_final(self):
        return self.mm_to_in(self.get_final("quantitativePrecipitation"), as_text=True)

    @property
    def snow_amount_low(self):
        return self.mm_to_in(self.get_low("snowfallAmount"), as_text=True)

    @property
    def snow_amount_high(self):
        return self.mm_to_in(self.get_high("snowfallAmount"), as_text=True)

    @property
    def snow_amount_initial(self):
        return self.mm_to_in(self.get_initial("snowfallAmount"), as_text=True)

    @property
    def snow_amount_final(self):
        return self.mm_to_in(self.get_final("snowfallAmount"), as_text=True)

    def _extract_weather_attributes(self, weather_values):
        """
        Extract weather attributes from weather values.
        
        Args:
            weather_values: List of weather data values
            
        Returns:
            List of unique weather attribute descriptions
        """
        attributes = []
        for value in weather_values:
            for weather_item in value:
                for attr in weather_item.get("attributes") or []:
                    attr_text = WEATHER_ATTRIBUTES.get(attr, attr.replace("_", " "))
                    if attr_text not in attributes:
                        attributes.append(attr_text)
        return attributes
    
    def _aggregate_weather_types(self, weather_values):
        """
        Aggregate weather types, intensities, and coverage from weather values.
        
        Args:
            weather_values: List of weather data values
            
        Returns:
            Tuple of (types, intensities, coverage) dictionaries
            - types: Maps weather type to set of intensity levels
            - intensities: Maps weather type to dict of intensity levels and descriptions
            - coverage: Maps weather type to set of coverage codes (not used in final output)
        """
        types = {}
        intensities = {}
        coverage = {}
        
        for value in weather_values:
            for weather_item in value:
                # Get normalized weather type
                weather_type = weather_item.get("weather") or ""
                weather_type = WEATHER_WEATHER.get(weather_type, weather_type.replace("_", " "))
                
                if not weather_type:
                    continue
                
                # Initialize tracking for this weather type
                if weather_type not in types:
                    types[weather_type] = set()
                    coverage[weather_type] = set()
                    intensities[weather_type] = {}
                
                # Get normalized intensity
                intensity = weather_item.get("intensity") or ""
                intensity_data = WEATHER_INTENSITY.get(intensity, ["", 0])
                intensity_text, intensity_level = intensity_data[0], intensity_data[1]
                
                # Track intensity information
                types[weather_type].add(intensity_level)
                intensities[weather_type][intensity_level] = intensity_text
                
                # Track coverage (for potential future use)
                cover = weather_item.get("coverage") or ""
                if cover == "slight_chance":
                    coverage[weather_type].add(0)
                elif cover == "chance":
                    coverage[weather_type].add(1)
                else:
                    coverage[weather_type].add(2)
        
        return types, intensities, coverage
    
    def _format_weather_description(self, types, intensities):
        """
        Format weather types and intensities into natural language.
        
        Args:
            types: Dictionary mapping weather type to set of intensity levels
            intensities: Dictionary mapping weather type to intensity descriptions
            
        Returns:
            String describing the weather conditions
        """
        descriptions = []
        
        for weather_type in types:
            intensity_levels = types[weather_type]
            min_level = min(intensity_levels)
            max_level = max(intensity_levels)
            
            # Build description for this weather type
            description = ""
            
            # Add intensity qualifier if applicable
            if min_level == max_level and min_level != 0:
                # Single intensity level (not zero/none)
                description = intensities[weather_type][min_level] + " "
            elif min_level != 0 and max_level != 0:
                # Range of intensities
                description = (intensities[weather_type][min_level] + " to " +
                             intensities[weather_type][max_level] + " ")
            
            description += weather_type
            descriptions.append(description)
        
        # Join descriptions with proper grammar
        if len(descriptions) == 0:
            return ""
        elif len(descriptions) == 1:
            return descriptions[0]
        elif len(descriptions) == 2:
            return descriptions[0] + " and " + descriptions[1]
        else:
            return ", ".join(descriptions[:-1]) + " and " + descriptions[-1]
    
    def _format_severe_attributes(self, attributes):
        """
        Format severe weather attributes into natural language.
        
        Args:
            attributes: List of severe weather attributes
            
        Returns:
            String describing severe weather attributes, or empty string if none
        """
        if len(attributes) == 0:
            return ""
        
        if len(attributes) == 1:
            return ". Some storms could be severe with " + attributes[0]
        else:
            # Join all but last with commas, add "and" before last
            return (". Some storms could be severe with " + 
                   ", ".join(attributes[:-1]) + " and " + attributes[-1])

    @property
    def weather_text(self):
        """
        Provides a natural language description of expected weather conditions.
        
        This method processes weather data including weather types, intensities,
        coverage, and severe weather attributes to generate a human-readable
        forecast description.
        
        Returns:
            String description of weather, or None if no weather data available
        """
        weather_values = self.get_values("weather")
        if weather_values is None or len(weather_values) == 0:
            return None
        
        # Extract weather information
        attributes = self._extract_weather_attributes(weather_values)
        types, intensities, coverage = self._aggregate_weather_types(weather_values)
        
        # Build the description
        description = self._format_weather_description(types, intensities)
        description += self._format_severe_attributes(attributes)
        
        return description if description else None

    @property
    def wind_speed_low(self):
        return self.mps_to_mph(self.get_low("windSpeed"))

    @property
    def wind_speed_high(self):
        return self.mps_to_mph(self.get_high("windSpeed"))

    @property
    def wind_speed_initial(self):
        return self.mps_to_mph(self.get_initial("windSpeed"))

    @property
    def wind_speed_final(self):
        return self.mps_to_mph(self.get_final("windSpeed"))

    @property
    def wind_direction_initial(self):
        values = self.get_values("windDirection")
        return self.da_to_dir(values[0]) if len(values) > 0 else None

    @property
    def wind_direction_final(self):
        values = self.get_values("windDirection")
        return self.da_to_dir(values[-1]) if len(values) > 0 else None

    @property
    def wind_gust_low(self):
        return self.mps_to_mph(self.get_low("windGust"))

    @property
    def wind_gust_high(self):
        return self.mps_to_mph(self.get_high("windGust"))

    @property
    def wind_gust_initial(self):
        return self.mps_to_mph(self.get_initial("windGust"))

    @property
    def wind_gust_final(self):
        return self.mps_to_mph(self.get_final("windGust"))

    @property
    def wind_chill_low(self):
        return self.c_to_f(self.get_low("windChill"))

    @property
    def wind_chill_high(self):
        return self.c_to_f(self.get_high("windChill"))

    @property
    def wind_chill_initial(self):
        return self.c_to_f(self.get_initial("windChill"))

    @property
    def wind_chill_final(self):
        return self.c_to_f(self.get_final("windChill"))

    @property
    def heat_index_low(self):
        return self.c_to_f(self.get_low("heatIndex"))

    @property
    def heat_index_high(self):
        return self.c_to_f(self.get_high("heatIndex"))

    @property
    def heat_index_initial(self):
        return self.c_to_f(self.get_initial("heatIndex"))

    @property
    def heat_index_final(self):
        return self.c_to_f(self.get_final("heatIndex"))

    @property
    def skys_initial(self):
        return self.to_skys(self.get_initial("skyCover"), self.is_day(self.stime))

    @property
    def skys_final(self):
        return self.to_skys(self.get_final("skyCover"), self.is_day(self.stime))


class Observations(Base):
    def __init__(self, event, stations, limit=3, attributes_manager=None, cache_adapter=None):
        super().__init__(event, attributes_manager, cache_adapter)
        self.stations = stations
        self.data = None
        self.observations = None
        self.station = None
        self.index = 0

        # Retrieve the current observations from the nearest station
        for stationid in self.stations:
            # Get the station info
            station = self.get_station(stationid)
            #print("STATION", station)
            if station is None:
                continue

            # Get the current observations for this station
            data = self.https("stations/%s/observations?limit=%d" % (stationid, limit))
            #print(json.dumps(data, indent=4))
            if data is None or data.get("status", 0) != 0:
                continue

            # Look for the first "valid" set, from newest to oldest
            self.index = 0
            for obs in data["@graph"]:
                # Verify it's valid (for station SFOC1, it's None)
                if obs["rawMessage"] and obs["temperature"]["value"]:
                    self.observations = obs
                    self.station = station
                    self.data = data
                    break
                self.index += 1

            # We've found usable observations, so we're done
            if self.observations:
                break

    def get_value(self, metric):
        return self.observations[metric]["value"]

    @property
    def is_good(self):
        return self.observations is not None

    @property
    def station_id(self):
        return self.station["stationIdentifier"]

    @property
    def station_name(self):
        return self.station["name"]

    @property
    def time_reported(self):
        return parser.parse(self.observations["timestamp"])

    @property
    def description(self):
        return self.observations["textDescription"]

    @property
    def wind_speed(self):
        return self.mps_to_mph(self.get_value("windSpeed"))

    @property
    def wind_direction(self):
        return self.da_to_dir(self.get_value("windDirection"))

    @property
    def wind_gust(self):
        return self.mps_to_mph(self.get_value("windGust"))

    @property
    def temp(self):
        return self.c_to_f(self.get_value("temperature"))

    @property
    def wind_chill(self):
        return self.c_to_f(self.get_value("windChill"))

    @property
    def heat_index(self):
        return self.c_to_f(self.get_value("heatIndex"))

    @property
    def feels_like(self):
        return self.wind_chill() or self.heat_index()

    @property
    def dewpoint(self):
        return self.c_to_f(self.get_value("dewpoint"))

    @property
    def humidity(self):
        return self.to_percent(self.get_value("relativeHumidity"))

    @property
    def pressure(self):
        return self.pa_to_in(self.get_value("barometricPressure"))

    @property
    def pressure_trend(self):
        if self.index < len(self.data["@graph"]) - 1:
            prev = self.data["@graph"][self.index + 1]["barometricPressure"]["value"]
            curr = self.data["@graph"][self.index]["barometricPressure"]["value"]
            if curr < prev:
                return "falling"
            if curr > prev:
                return "rising"
            return "steady"

        return None


class Alerts(Base):
    class Alert(Base):
        def __init__(self, event, alert, attributes_manager=None, cache_adapter=None):
            super().__init__(event, attributes_manager, cache_adapter)
            self.alert = alert

        @property
        def expires(self):
            return self.alert["expires"]

        @property
        def event(self):
            return self.alert["event"].replace("\n", " ").lower()

        @property
        def area(self):
            return self.normalize(self.alert["areaDesc"])

        @property
        def headline(self):
            return self.normalize(self.alert["headline"])

        @property
        def description(self):
            return self.normalize(self.alert["description"])

        @property
        def instruction(self):
            return self.normalize(self.alert["instruction"])

    def __init__(self, event, zoneid, attributes_manager=None, cache_adapter=None):
        super().__init__(event, attributes_manager, cache_adapter)
        self.zoneid = zoneid
        self._title = ""
        self._alerts = []
        data = self.https("alerts/active?status=actual&zone=" + zoneid)
        if data is not None and "@graph" in data:
            self._title = data["title"]
            self._alerts = data["@graph"]

    def __iter__(self):
        for alert in self._alerts:
            yield self.Alert(self.event, alert, self._attributes_manager, self._cache_adapter)

    def __len__(self):
        return len(self._alerts)

    @property
    def title(self):
        return self._title


class Location(Base):
    def __init__(self, event, attributes_manager=None, cache_adapter=None):
        super().__init__(event, attributes_manager, cache_adapter)

    def set(self, name, default=None):
        # Normalize name
        name = name.strip().lower()

        # Break it up by words and reconstruct
        words = name.split()
        name = " ".join(words)

        # Correct known recognition problems using fuzzy matching
        corrected_name = correct_location_name(name)
        if corrected_name != name:
            name = corrected_name
            words = name.split()
            name = " ".join(words)

        # Bail on a recognition problem
        if words[-1] == "?":
            #notify(self.event, "location not recognized")
            return "You location was not recognized.  Please try again."

        # Does it look like a zip code?
        if words[-1].isdigit():
            name = words[-1]

            # Zipcodes preceded by the word "for" can be misunderstood by Alexa
            if len(name) == 6 and name[0] == "2":
                name = name[1:]

            if len(name) != 5:
                return "%s could not be located" % self.spoken_name(name)

            # Retrieve the location data from the cache
            loc = self.cache_get("LocationCache", {"location": "%s" % name})
            if loc is not None:
                self.loc = loc
                return None

            # Have a new location, so retrieve the base info
            coords, props = self.here_geocode("%s" % name)
            if coords is None:
                #notify(self.event, "Zip code not found: %s" % name)
                return "%s could not be located" % self.spoken_name(name)
            city = name
            state = ""
        else:
            # Extract city and state when the state name has 2 words
            city = " ".join(words[:-2])
            state = " ".join(words[-2:])

            hasstate = state in STATES
            if not hasstate:
                # Must be a 1 word state name
                city = " ".join(words[:-1])
                state = " ".join(words[-1:])
                # Special case for Maine
                state = state if state != "main" else "maine"
                hasstate = state in STATES

            # No recognizable state name, use previously set name if we have it
            if not hasstate:
                if default is None:
                    return "You must set the default location"
                city = name
                state = default.state

            #print("CITY", city, "STATE", state)
            # Retrieve the location data from the cache
            loc = self.cache_get("LocationCache", {"location": "%s %s" % (city, state)})
            #print("loc", loc)
            #if loc is not None:
            #    self.loc = loc
            #    return None

            # Have a new location, so retrieve the base info
            coords, props = self.here_geocode("%s %s" % (city, state))
            if coords is None:
                #notify(self.event, "City '%s' State '%s' not found" % (city, state))
                return "%s %s could not be located.  Try using the zip code." % (city, state)

        # Get the NWS location information (limit to 4 decimal places for the API)
        point = self.https("points/%s,%s" %
                           (("%.4f" % coords[0]).rstrip("0").rstrip("."),
                            ("%.4f" % coords[1]).rstrip("0").rstrip(".")))

        # Make sure we have the real location
        if point is None or "relativeLocation" not in point:
            notify(self.event, "No relativeLocation for city '%s' state '%s'" % (city, state))
            return "%s %s could not be located" % (city, state)

        # Initialize location
        loc = {}

        # Now, get the corrected NWS point
        rel = point["relativeLocation"]

        # Extract the NWS information
        loc["city"] = rel["city"].lower()
        loc["state"] = STATES[STATES.index(rel["state"].lower()) - 1]
        loc["cwa"] = point["cwa"]
        loc["gridPoint"] = "%s,%s" % (point["gridX"], point["gridY"])
        loc["timeZone"] = point["timeZone"]

# geometry no longer seems to be provided
#        yx = re.match(r".*\((.*?)\s+(.*?)\)", rel["geometry"]).groups()
#
#        # And store it
#        loc = {}
#        loc["coords"] = "%s,%s" % \
#                        (("%.4f" % float(yx[1])).rstrip("0").rstrip("."),
#                         ("%.4f" % float(yx[0])).rstrip("0").rstrip("."))
#
#        # Retrieve the NWS location again using the corrected point
#        point = self.https("points/%s" % loc["coords"])
#        if point is None:
#            return "%s %s could not be located" % (city, state)

        # Retrieve the location data from the cache
        rloc = self.cache_get("LocationCache", {"location": "%s %s" % (loc["city"], loc["state"])})
        if rloc is None:
            # Have a new location, so retrieve the base info
            rcoords, _ = self.here_geocode("%s %s" % (loc["city"], loc["state"]))
            if rcoords is not None:
                loc["coords"] = "%s,%s" % (rcoords[0], rcoords[1])
            else:
                loc["coords"] = coords
        else:
            loc["coords"] = rloc["coords"]

        # Retrieve the forecast zone name
        data = self.get_forecast_zone(point["forecastZone"])
        loc["forecastZoneId"] = data["id"]
        loc["forecastZoneName"] = data["name"]

        # Some NWS locations are missing the county zone, so try to deduce it by getting
        # the county coordinates from HERE geocoding and asking NWS for that point.
        if "county" not in point and "county" in props:
            county = props["county"].lower().split()
            if county[-1] == "county":
                county[-1] = ""
            county = " ".join(list(county))
            coords, props = self.here_geocode("%s county %s" % (county, loc["state"]))
            if coords is not None:
                pt = self.https("points/%s,%s" %
                                (("%.4f" % coords[0]).rstrip("0").rstrip("."),
                                 ("%.4f" % coords[1]).rstrip("0").rstrip(".")))
                if "county" in pt:
                    point["county"] = pt["county"]

        # Retrieve the county zone name
        data = self.get_county_zone(point.get("county", "missing"))
        loc["countyZoneId"] = data.get("id", "missing")
        loc["countyZoneName"] = data.get("name", "missing")

        # Retrieve the observation stations
        data = self.get_stations(loc["coords"])
        loc["observationStations"] = data

        # Put it to the cache
        loc["location"] = "%s %s" % (city, state) if state else city
        self.cache_put("LocationCache", loc)

        # And remember
        self.loc = loc

        return None

    def here_geocode(self, search):
        """
        Use HERE.com geocoding API to geocode a location.
        
        Args:
            search: Location string to geocode (city, state, zip code, etc.)
            
        Returns:
            Tuple of ((lat, lng), properties_dict) or (None, None) if not found
        """
        # HERE.com API uses spaces, not plus signs
        geo = self.https("v1/geocode?q=%s&apiKey=%s" % (search.replace(" ", "+"), HERE_API_KEY), loc="geocode.search.hereapi.com")
        if geo is None or \
           "items" not in geo or \
           len(geo["items"]) == 0:
            return None, None
        
        # Get the first result
        result = geo["items"][0]
        
        # Extract properties from address components
        props = {}
        if "address" in result:
            address = result["address"]
            # Map HERE.com address fields to our property names
            if "county" in address:
                props["County"] = address["county"]
            if "state" in address:
                props["State"] = address["state"]
            if "stateCode" in address:
                props["StateCode"] = address["stateCode"]
            if "city" in address:
                props["City"] = address["city"]
        
        # Return coordinates and properties
        return (result["position"]["lat"], result["position"]["lng"]), props

    def spoken_name(self, name=None):
        loc = name or self.loc["location"]
        return "zip code " + " ".join(list(loc)) if loc and loc.isdigit() else loc

    @property
    def name(self):
        return self.loc["location"]

    @property
    def coords(self):
        return self.loc["coords"]

    @property
    def city(self):
        return self.loc["city"]

    @property
    def state(self):
        return self.loc["state"]

    @property
    def cwa(self):
        return self.loc["cwa"]

    @property
    def grid_point(self):
        return self.loc["gridPoint"]

    @property
    def timeZone(self):
        return self.loc["timeZone"]

    @property
    def forecastZoneId(self):
        return self.loc["forecastZoneId"]

    @property
    def forecastZoneName(self):
        return self.loc["forecastZoneName"]

    @property
    def countyZoneId(self):
        return self.loc["countyZoneId"]

    @property
    def countyZoneName(self):
        return self.loc["countyZoneName"]

    @property
    def observationStations(self):
        return self.loc["observationStations"]

    @property
    def tz(self):
        return tz.gettz(self.loc["timeZone"])


class User(Base):
    def __init__(self, event, userid, attributes_manager=None, cache_adapter=None):
        super().__init__(event, attributes_manager, cache_adapter)
        self._userid = userid
        self._location = None
        self._rate = 100
        self._pitch = 100
        self.get_default_metrics()

        # Get or create the user's profile
        user = self.cache_get("UserCache", {"userid": userid})
        if user is None:
            self.save()
        else:
            self._userid = user.get("userid", self._userid)
            self._location = user.get("location", self._location)
            self._rate = user.get("rate", self._rate)
            self._pitch = user.get("pitch", self._pitch)
            self._metrics = user.get("metrics", self._metrics)

    def save(self):
        item = {"userid": self._userid,
                "location": self._location,
                "rate": self._rate,
                "pitch": self._pitch,
                "metrics": self._metrics}
        self.cache_put("UserCache", item, ttl=0)

    def get_default_metrics(self):
        metrics = {}
        for name, value in METRICS.values():
            if value and name not in metrics:
                metrics[value] = name
        self._metrics = []
        for i in range(1, len(metrics) + 1):
            self._metrics.append(metrics[i])

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, location):
        self._location = location
        self.save()

    @property
    def rate(self):
        return self._rate

    @rate.setter
    def rate(self, rate):
        self._rate = rate
        self.save()

    @property
    def pitch(self):
        return self._pitch

    @pitch.setter
    def pitch(self, pitch):
        self._pitch = pitch
        self.save()

    @property
    def metrics(self):
        return self._metrics

    @metrics.setter
    def metrics(self, metrics):
        self._metrics = metrics
        self.save()

    def add_metric(self, metric):
        if metric not in self._metrics:
            self._metrics.append(metric)
            self.save()

    def remove_metric(self, metric):
        if metric in self._metrics:
            self._metrics.remove(metric)
            self.save()

    def reset_metrics(self):
        self.get_default_metrics()
        self.save()

    def has_metric(self, metric):
        return metric in self._metrics

# =============================================================================
# ASK SDK Request Handlers
# =============================================================================




# =============================================================================
# WeatherProcessor - High-level interface for CLI and testing
# =============================================================================

class WeatherProcessor:
    """
    Main weather processing class.
    
    This class provides a simplified interface to the weather processing logic,
    designed for CLI testing. It uses the processing classes defined above
    with the cache_adapter abstraction.
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
        
        # Set the HERE API key environment variable
        os.environ['here_api_key'] = here_api_key
    
    def build_event(self, request_data):
        """
        Build an event dictionary from request data.
        
        Args:
            request_data: Request data dictionary
            
        Returns:
            Event dictionary compatible with processing classes
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
        elif request_type == "SessionEndedRequest":
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
