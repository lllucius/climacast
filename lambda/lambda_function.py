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
import os
import re
from math import sqrt
from time import time

import os
os.environ["AWS_REGION"] = os.getenv("AWS_REGION", "us-east-1")

import requests
from aniso8601.duration import parse_duration
from boto3 import resource
from botocore.exceptions import ClientError
from cachetools import TTLCache, cached
from datetime import datetime
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# ASK SDK imports
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_dynamodb.adapter import DynamoDbAdapter

"""
    Anything defined here will persist for the duration of the lambda
    container, so only initialize them once to reduce initialization time.
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

# TODO: Need to figure out a better way to handle misunderstood names
LOCATION_XLATE = {"gnome alaska": "nome alaska",
                  "woodberry minnesota": "woodbury minnesota"}

load_dotenv()

HERE_API_KEY = os.environ.get("here_api_key", "")
print("HERE_API_KEY", HERE_API_KEY)

PERSISTENCE_REGION = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
PERSISTENCE_TABLE_NAME = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')
print("REGION", PERSISTENCE_REGION, PERSISTENCE_TABLE_NAME)
ddb_resource = resource('dynamodb', region_name=PERSISTENCE_REGION)
ddb_adapter = DynamoDbAdapter(
    table_name=PERSISTENCE_TABLE_NAME,
    create_table=False,
    dynamodb_resource=ddb_resource
)

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
               "Accept": "application/ld+json"}
    r = HTTPS.get(url, headers=headers)
    if r.status_code != 200 or r.text is None or r.text == "":
        return None, r.status_code, r.url, r.content
    return json.loads(r.text), r.status_code, r.url, None


class Base(object):
    def __init__(self, event, attributes_manager=None):
        self.event = event
        self._attributes_manager = attributes_manager

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
            Uses persistent attributes directly for both shared and user-specific caches.
            
            Shared caches (LocationCache, StationCache, ZoneCache) are stored in a 
            single DynamoDB item with partition key "SHARED_CACHE" to be accessible
            across all users. Uses optimistic locking with version number when removing
            expired items from shared caches.
        """
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
            Uses persistent attributes directly for both shared and user-specific caches.
            
            Shared caches (LocationCache, StationCache, ZoneCache) are stored in a 
            single DynamoDB item with partition key "SHARED_CACHE" to be accessible
            across all users. Uses optimistic locking with a version number to handle
            concurrent writes safely.
        """
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
    def __init__(self, event, tz, cwa, gridpoint, attributes_manager=None):
        super().__init__(event, attributes_manager)
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

    @property
    def weather_text(self):
        """
            Provides a description of the expected weather.
            TODO:  Not at all happy with this.  It needs to be redone.
        """
        values = self.get_values("weather")
        if values is None or len(values) == 0:
            return None

        #for v in self.values["weather"]:
        #    for w in v:
        #        print("COVER", w["coverage"], "INTEN", w["intensity"], "WEATH", w["weather"])

        attrs = []
        types = {}
        intens = {}
        covers = {}
        for value in values:
            for w in value:
                for attr in w["attributes"] or {}:
                    attr = WEATHER_ATTRIBUTES.get(attr, attr.replace("_", " "))
                    if attr not in attrs:
                        attrs.append(attr)

                weath = w["weather"] or ""
                weath = WEATHER_WEATHER.get(weath, weath.replace("_", " "))
                inten = w["intensity"] or ""
                inten = WEATHER_INTENSITY.get(inten, "")
                cover = w["coverage"] or ""
                cover = WEATHER_COVERAGE.get(cover, cover.replace("_", " "))

                if weath:
                    if weath not in types:
                        types[weath] = set()
                        covers[weath] = set()
                        intens[weath] = {}
                    types[weath].add(inten[1])
                    intens[weath][inten[1]] = inten[0]

                    if cover == "slight_chance":
                        covers[weath].add(0)
                    elif cover == "chance":
                        covers[weath].add(1)
                    else:
                        covers[weath].add(2)

        d = ""
        i = 0
        cnt = len(types)
        for t in types:
            w = ""
            lo = min(types[t])
            hi = max(types[t])
            if lo == hi and lo != 0:
                w += intens[t][lo] + " "
            elif lo != 0 and hi != 0:
                w += intens[t][lo] + " to " + intens[t][hi] + " "
            w += t

            i = i + 1
            if i == 1:
                d = w
            elif i < cnt:
                d += ", " + w
            else:
                d += " and " + w

        if len(attrs) > 0:
            d += ". Some storms could be severe with "
            last = ""
            if len(attrs) > 1:
                last = " and " + attrs[-1]
                attrs.remove(attrs[-1])
            d += ", ".join(attrs) + last

        return d

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
    def __init__(self, event, stations, limit=3, attributes_manager=None):
        super().__init__(event, attributes_manager)
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
        def __init__(self, event, alert, attributes_manager=None):
            super().__init__(event, attributes_manager)
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

    def __init__(self, event, zoneid, attributes_manager=None):
        super().__init__(event, attributes_manager)
        self.zoneid = zoneid
        self._title = ""
        self._alerts = []
        data = self.https("alerts/active?status=actual&zone=" + zoneid)
        if data is not None and "@graph" in data:
            self._title = data["title"]
            self._alerts = data["@graph"]

    def __iter__(self):
        for alert in self._alerts:
            yield self.Alert(self.event, alert, self._attributes_manager)

    def __len__(self):
        return len(self._alerts)

    @property
    def title(self):
        return self._title


class Location(Base):
    def __init__(self, event, attributes_manager=None):
        super().__init__(event, attributes_manager)

    def set(self, name, default=None):
        # Normalize name
        name = name.strip().lower()

        # Break it up by words and reconstruct
        words = name.split()
        name = " ".join(words)

        # Correct known recognition problems
        if name in LOCATION_XLATE:
            name = LOCATION_XLATE[name]
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
    def __init__(self, event, userid, attributes_manager=None):
        super().__init__(event, attributes_manager)
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


class BaseIntentHandler(AbstractRequestHandler):
    """Base class for intent handlers with common weather functionality"""

    def __init__(self):
        super().__init__()

    def get_user_and_location(self, handler_input):
        """Get user profile and location from handler_input"""
        # type: (HandlerInput) -> tuple
        session = handler_input.request_envelope.session
        user_id = session.user.user_id

        # Build event for legacy code compatibility
        event = {
            "session": {
                "new": session.new,
                "sessionId": session.session_id,
                "application": {
                    "applicationId": session.application.application_id
                },
                "attributes": session.attributes or {},
                "user": {
                    "userId": user_id
                }
            },
            "request": {}
        }

        # Get attributes manager for persistence
        attributes_manager = handler_input.attributes_manager

        # Load user profile
        user = User(event, user_id, attributes_manager)

        # Try to load default location
        loc = None
        if user.location:
            location_obj = Location(event, attributes_manager)
            text = location_obj.set(user.location)
            if text is None:
                loc = location_obj

        return user, loc, event

    def get_slot_values(self, handler_input):
        """Extract slot values from intent"""
        # type: (HandlerInput) -> dict
        slots = {}
        request = handler_input.request_envelope.request
        if hasattr(request, 'intent') and request.intent.slots:
            for slot_name, slot in request.intent.slots.items():
                if slot.value:
                    slots[slot_name] = slot.value.strip().lower()
                else:
                    slots[slot_name] = None
        return slots

    def respond(self, handler_input, user, text, end=None):
        """Build response with proper formatting"""
        # type: (HandlerInput, User, str, bool) -> Response
        session = handler_input.request_envelope.session
        new = session.new
        if end is None:
            end = new

        response_builder = handler_input.response_builder

        # Add reprompt if session should continue
        prompt = None
        if not end:
            prompt = "For %s, say help, " % ("more examples" if new else "example requests") + \
                     "To interrupt speaking, say Alexa, cancel, " + \
                     "If you are done, say stop."
            text += ". " if text.strip()[-1] != "." else " "
            text += prompt if new else "if you are done, say stop."

        # Format with user's rate and pitch
        ssml = '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
               (user.rate, user.pitch - 100, text)

        response_builder.speak(ssml)

        if not end and prompt:
            prompt_ssml = '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
                          (user.rate, user.pitch - 100, prompt)
            response_builder.ask(prompt_ssml)

        response_builder.set_should_end_session(end)
        return response_builder.response

    def get_location_from_slots(self, handler_input, event, loc, slots, req=False):
        """Process location from slot values"""
        location_name = slots.get("location") or slots.get("zipcode")

        if location_name:
            attributes_manager = handler_input.attributes_manager
            location_obj = Location(event, attributes_manager)
            text = location_obj.set(location_name, loc)
            if text is None:
                return location_obj, None
            return None, text
        elif req:
            return None, "You must include the location"
        elif loc is None:
            return None, """You must set a default location by using phrases like:
                       Alexa, ask Clima Cast to set my location to Boulder Colorado.
                   or:
                       Alexa, ask Clima Cast to set my location to zip code 5 5 1 1 8.
                   """
        return loc, None

    def parse_when(self, loc, slots):
        """Parse time/date information from slots"""
        # type: (Location, dict) -> tuple
        has_when = (slots.get("when_abs") or slots.get("when_any") or
                    slots.get("when_pos") or slots.get("day") or slots.get("month")) is not None

        now = datetime.now(tz=loc.tz) + relativedelta(minute=0, second=0, microsecond=0)
        base = now + relativedelta(hour=6)
        stime = base
        hours = 12
        sname = ""

        # Handle the days like Monday or Today
        day = slots.get("when_abs") or slots.get("when_any") or slots.get("when_pos")
        if day:
            day = re.sub(r"'*s$", "", day).replace("over night", "overnight").split()

            if len(day) > 1:
                if day[0] == "overnight":
                    day = [day[1], "overnight"]
                elif day[0] == "this":
                    day = [day[1]]

            if day[0] == "tomorrow":
                stime += relativedelta(days=+1, hour=6)
            elif day[0] in DAYS:
                d = ((DAYS.index(day[0]) - stime.weekday()) % 7)
                stime += relativedelta(days=+d, hour=6)

            sname = DAYS[stime.weekday()]
            is_today = stime == base

            specs = {"today":     [0, 6,  12, ""],
                     "tonight":   [0, 18, 12, " night"],
                     "night":     [0, 18, 12, " night"],
                     "overnight": [1, 0,  6,  " overnight"],
                     "morning":   [0, 6,  6,  " morning"],
                     "afternoon": [0, 12, 6,  " afternoon"],
                     "evening":   [0, 18, 6,  " evening"]}

            if day[-1] in specs:
                spec = specs[day[-1]]
                stime += relativedelta(days=spec[0], hour=spec[1])
                hours = spec[2]
                sname += spec[3]

            if is_today:
                day = sname.split()
                if hours == 6:
                    sname = "overnight" if day[1] == "overnight" else "this " + day[1]
                else:
                    sname = "tonight" if stime.hour == 18 else "today"

        elif slots.get("day") is not None:
            month = stime.month
            day = stime.day

            d = slots.get("day")
            if d.isdigit() and 1 <= int(d) <= 31:
                d = MONTH_DAYS[int(d) - 1]
            elif d in MONTH_DAYS_XLATE:
                d = MONTH_DAYS_XLATE[d]

            if d in MONTH_DAYS:
                day = MONTH_DAYS.index(d) + 1

                if slots.get("month") is not None:
                    m = slots.get("month")
                    if m in MONTH_NAMES:
                        month = MONTH_NAMES.index(m) + 1

            # Adjust the date relative to today
            if month == stime.month and day == stime.day:
                pass
            elif month == stime.month and day < stime.day:
                if slots.get("month"):
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

        etime = stime + relativedelta(hours=hours)
        quarters = hours // 6

        return has_when, stime, etime, sname, quarters

    def get_alerts(self, handler_input, event, loc):
        """Get weather alerts for location"""
        attributes_manager = handler_input.attributes_manager
        alerts = Alerts(event, loc.countyZoneId, attributes_manager)
        if len(alerts) == 0:
            return "No alerts in effect at this time for %s." % loc.city

        text = alerts.title + "...\n"
        for alert in alerts:
            text += alert.headline + "...\n"
            text += "for " + alert.area + "...\n"
            text += alert.description + "...\n"
            text += alert.instruction + "...\n"

        return text

    def get_current(self, handler_input, event, user, loc, metrics):
        """Get current weather conditions"""
        text = ""

        # Retrieve the current observations from the nearest station
        attributes_manager = handler_input.attributes_manager
        obs = Observations(event, loc.observationStations, attributes_manager=attributes_manager)
        if obs.is_good:
            text += "At %s, %s reported %s, " % \
                    (obs.time_reported.astimezone(loc.tz).strftime("%I:%M%p"),
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
                                    (obs.wind_direction, obs.wind_speed)
                        else:
                            text += "Winds are out of the %s at %s miles per hour" % \
                                    (obs.wind_direction, obs.wind_speed)

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

        return text

    def get_extended(self, handler_input, event, loc):
        """Get extended forecast"""
        # Import normalize from Base class
        attributes_manager = handler_input.attributes_manager
        base = Base(event, attributes_manager)

        data = base.https("points/%s/forecast" % loc.coords)
        if data is None or data.get("periods", None) is None:
            notify(event, "Extended forecast missing periods", data)
            return "the extended forecast is currently unavailable."

        text = ""
        for period in data.get("periods", {}):
            text += " " + period["name"] + ", " + period["detailedForecast"]
            if text.lower().find("wind") < 0:
                wind = period["windSpeed"]
                if wind.lower().find("to") < 0:
                    wind = "around " + wind
                text += ". %s wind %s" % (base.dir_to_dir(period["windDirection"]), wind)
            text + "."

        header = "The extended forecast for the %s zone " % loc.forecastZoneName
        if not text:
            header += "is unavailable"

        return base.normalize(header + text)

    def get_forecast(self, handler_input, event, user, loc, stime, etime, sname, metrics):
        """Get weather forecast"""
        # Import normalize from Base class
        attributes_manager = handler_input.attributes_manager
        base = Base(event, attributes_manager)

        fulltext = ""
        gp = GridPoints(event, loc.tz, loc.cwa, loc.grid_point, attributes_manager)

        for metric in metrics:
            metric = METRICS[metric][0]

            if not gp.set_interval(stime, etime):
                text = "Forecast information is unavailable for %s %s" % \
                       (MONTH_NAMES[stime.month - 1], MONTH_DAYS[stime.day - 1])
                return text

            isday = base.is_day(stime)
            text = ""

            if metric == "wind":
                wsh = gp.wind_speed_high
                wsl = gp.wind_speed_low
                wdi = gp.wind_direction_initial
                if wsh is None:
                    text = "winds will be calm"
                else:
                    if wsh == wsl:
                        if wdi is None:
                            text = "winds will be %s miles per hour" % wsh
                        else:
                            text = "winds will be out of the %s at %s miles per hour" % (wdi, wsh)
                    else:
                        if wdi is None:
                            text = "winds will be %s to %s miles per hour" % (wsl, wsh)
                        else:
                            text = "winds will be out of the %s at %s to %s miles per hour" % (wdi, wsl, wsh)
                    wg = gp.wind_gust_high
                    if wg is not None:
                        text += ", with gusts as high as %s" % wg

            elif metric == "temperature":
                t = gp.temp_high if isday else gp.temp_low
                if t is not None:
                    text = "the %s temperature will be %s degrees" % ("high" if isday else "low", t)

                    wcl = gp.wind_chill_low
                    wch = gp.wind_chill_high
                    if wcl is not None:
                        if wcl == wch and wcl != t:
                            text += ", with a wind chill of %s degrees" % wcl
                        elif wcl != wch:
                            text += ", with a wind chill of %s to %s degrees" % (wcl, wch)

                    hil = gp.heat_index_low
                    hih = gp.heat_index_high
                    if hil is not None:
                        if hil == hih and hil != t:
                            text += ", with a heat index of %s degrees" % hil
                        elif hil != hih:
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
                    elif si is None or sf is None:
                        text = "it will be %s" % (si or sf)
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
            fulltext = "%s in %s, %s" % (sname, loc.city, fulltext)
        else:
            fulltext = "Forecast information is unavailable for %s in %s" % (sname, loc.city)

        return fulltext


class LaunchRequestHandler(BaseIntentHandler):
    """Handler for Launch Request"""
    def can_handle(self, handler_input):
        print("+#+##+#+#+#+#")
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, _ = self.get_user_and_location(handler_input)

        text = "Welcome to Clime a Cast. " \
               "For current conditions, use phrases like: What's the weather. "\
               "For forecasts, try phrases like: What's the forecast."
        if loc is None:
            text += "You must set your default location by saying something like: " \
                    "set location to Miami Florida."

        return self.respond(handler_input, user, text, end=False)

# Session Ended Request Handler


class SessionEndedRequestHandler(BaseIntentHandler):
    """Handler for Session Ended Request"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        request = handler_input.request_envelope.request

        # Build event for notify
        session = handler_input.request_envelope.session
        event = {
            "session": {
                "sessionId": session.session_id,
                "user": {"userId": session.user.user_id}
            },
            "request": {
                "type": "SessionEndedRequest",
                "reason": str(getattr(request, 'reason', 'USER_INITIATED'))
            }
        }

        if hasattr(request, 'error') and request.error:
            event["request"]["error"] = {
                "message": request.error.message
            }
            notify(event, "Error detected", request.error.message)
        else:
            notify(event, "Session Ended", event["request"]["reason"])

        return handler_input.response_builder.response

# Help Intent Handler


class HelpIntentHandler(BaseIntentHandler):
    """Handler for Help Intent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        text = """
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
        return self.respond(handler_input, user, text)

# Cancel and Stop Intent Handler


class CancelAndStopIntentHandler(BaseIntentHandler):
    """Handler for Cancel and Stop Intent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        text = "Thank you for using Clime a Cast."
        return self.respond(handler_input, user, text, end=True)

# Fallback, Yes, No, and StartOver Intent Handler (basic responses)


class FallbackIntentHandler(BaseIntentHandler):
    """Handler for Fallback, Yes, No, and StartOver intents"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.FallbackIntent")(handler_input) or
                is_intent_name("AMAZON.YesIntent")(handler_input) or
                is_intent_name("AMAZON.NoIntent")(handler_input) or
                is_intent_name("AMAZON.StartOverIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        # For now, these all return to help
        text = "I didn't understand that. " \
               "You can ask for current conditions, forecasts, or alerts. " \
               "Say help for more information."
        return self.respond(handler_input, user, text, end=False)

# Metric Intent Handlers


class MetricIntentHandler(BaseIntentHandler):
    """Handler for MetricIntent and MetricPosIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("MetricIntent")(handler_input) or
                is_intent_name("MetricPosIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, event = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        # Check if location is required
        if loc is None:
            text = """You must set a default location by using phrases like:
                       Alexa, ask Clima Cast to set my location to Boulder Colorado.
                   or:
                       Alexa, ask Clima Cast to set my location to zip code 5 5 1 1 8.
                   """
            return self.respond(handler_input, user, text)

        # Get metric from slots
        metric = slots.get("metric")
        if metric is None:
            return self.respond(handler_input, user, "You must include a metric like temperature, humidity or wind")

        # Handle special metrics
        if metric == "alerts":
            text = self.get_alerts(handler_input, event, loc)
            # Normalize text
            attributes_manager = handler_input.attributes_manager
            base = Base(event, attributes_manager)
            return self.respond(handler_input, user, base.normalize(text))

        if metric == "extended forecast":
            text = self.get_extended(handler_input, event, loc)
            return self.respond(handler_input, user, text)

        if metric not in METRICS:
            return self.respond(handler_input, user, "%s is an unrecognized metric." % metric)

        # Determine which metrics to report
        metrics = user.metrics if METRICS[metric][0] == "all" else [METRICS[metric][0]]

        # Parse when information
        has_when, stime, etime, sname, _ = self.parse_when(loc, slots)

        # Determine if this is a forecast or current conditions request
        leadin = slots.get("leadin") or ""
        is_forecast = (metric == "forecast" or has_when or
                       "chance" in metric or "will" in leadin or "going" in leadin)

        if is_forecast:
            text = self.get_forecast(handler_input, event, user, loc, stime, etime, sname, metrics)
        else:
            text = self.get_current(handler_input, event, user, loc, metrics)
            # Normalize text
            attributes_manager = handler_input.attributes_manager
            base = Base(event, attributes_manager)
            text = base.normalize(text)

        return self.respond(handler_input, user, text)

# Settings Intent Handlers


class GetSettingIntentHandler(BaseIntentHandler):
    """Handler for GetSettingIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetSettingIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        if loc is None:
            text = "You must set a default location first."
            return self.respond(handler_input, user, text)

        setting = slots.get("setting")
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
            return self.respond(handler_input, user, "Unrecognized setting: %s" % setting)

        text = ""
        for setting in settings:
            if text != "":
                text += ", "
                if setting == settings[-1]:
                    text += "and "
            if setting == "location":
                text += "the location is set to %s." % loc.spoken_name()
            elif setting == "pitch":
                text += "the voice pitch is set to %d percent." % user.pitch
            elif setting == "rate":
                text += "the voice rate is set to %d percent." % user.rate
            elif setting == "forecast":
                text += "the custom forecast will include the %s." % \
                        ", ".join(list(user.metrics[:-1])) + " and " + user.metrics[-1]

        return self.respond(handler_input, user, text)


class SetPitchIntentHandler(BaseIntentHandler):
    """Handler for SetPitchIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("SetPitchIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        percent = slots.get("percent")
        if percent and percent.isdigit():
            pitch = int(percent)
            if 130 >= pitch >= 70:
                user.pitch = pitch
                text = "Voice pitch has been set to %d percent." % pitch
            else:
                text = "The pitch must be between 70 and 130 percent"
        else:
            text = "Expected a percentage when setting the pitch"

        return self.respond(handler_input, user, text)


class SetRateIntentHandler(BaseIntentHandler):
    """Handler for SetRateIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("SetRateIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        percent = slots.get("percent")
        if percent and percent.isdigit():
            rate = int(percent)
            if 150 >= rate >= 50:
                user.rate = rate
                text = "Voice rate has been set to %d percent." % rate
            else:
                text = "The rate must be between 50 and 150 percent"
        else:
            text = "Expected a percentage when setting the rate"

        return self.respond(handler_input, user, text)


class SetLocationIntentHandler(BaseIntentHandler):
    """Handler for SetLocationIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("SetLocationIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, event = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        location_name = slots.get("location") or slots.get("zipcode")
        if not location_name:
            text = "You must include the location"
            return self.respond(handler_input, user, text)

        attributes_manager = handler_input.attributes_manager
        location_obj = Location(event, attributes_manager)
        text = location_obj.set(location_name, loc)
        if text is None:
            user.location = location_obj.name
            text = "Your default location has been set to %s." % location_obj.spoken_name()

        return self.respond(handler_input, user, text)

# Custom Forecast Intent Handlers


class GetCustomIntentHandler(BaseIntentHandler):
    """Handler for GetCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        text = "The custom forecast will include the %s." % \
               ", ".join(list(user.metrics[:-1])) + " and " + user.metrics[-1]
        return self.respond(handler_input, user, text)


class AddCustomIntentHandler(BaseIntentHandler):
    """Handler for AddCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AddCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        metric = slots.get("metric")
        if metric is None:
            text = "You must include a metric like temperature, humidity or wind."
            return self.respond(handler_input, user, text)

        if metric not in METRICS:
            text = "%s is an unrecognized metric." % metric
            return self.respond(handler_input, user, text)

        metric_info = METRICS[metric]
        if not metric_info[1]:
            text = "%s can't be used when customizing the forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        if user.has_metric(metric_info[0]):
            text = "%s is already included in the custom forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        user.add_metric(metric_info[0])
        text = "%s has been added to the custom forecast." % metric_info[0]
        return self.respond(handler_input, user, text)


class RemoveCustomIntentHandler(BaseIntentHandler):
    """Handler for RemCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RemCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        metric = slots.get("metric")
        if metric is None:
            text = "You must include a metric like temperature, humidity or wind."
            return self.respond(handler_input, user, text)

        if metric not in METRICS:
            text = "%s is an unrecognized metric." % metric
            return self.respond(handler_input, user, text)

        metric_info = METRICS[metric]
        if not metric_info[1]:
            text = "%s can't be used when customizing the forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        if not user.has_metric(metric_info[0]):
            text = "%s is already excluded from the custom forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        user.remove_metric(metric_info[0])
        text = "%s has been removed from the custom forecast." % metric_info[0]
        return self.respond(handler_input, user, text)


class ResetCustomIntentHandler(BaseIntentHandler):
    """Handler for RstCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RstCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        user.reset_metrics()
        text = "the custom forecast has been reset to defaults."
        return self.respond(handler_input, user, text)


class StoreDataIntentHandler(BaseIntentHandler):
    """Handler for StoreDataIntent - saves persistent attributes"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("StoreDataIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        
        # Save persistent attributes to DynamoDB
        attributes_manager = handler_input.attributes_manager
        attributes_manager.save_persistent_attributes()
        
        text = "Data has been saved successfully."
        return self.respond(handler_input, user, text, end=True)


class GetDataIntentHandler(BaseIntentHandler):
    """Handler for GetDataIntent - loads persistent attributes"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetDataIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, event = self.get_user_and_location(handler_input)
        
        # Load persistent attributes from DynamoDB
        attributes_manager = handler_input.attributes_manager
        
        # Get shared caches directly from DynamoDB
        table = ddb_resource.Table(PERSISTENCE_TABLE_NAME)
        try:
            response = table.get_item(Key={"id": "SHARED_CACHE"})
            if "Item" in response:
                shared_attrs = response["Item"].get("attributes", {})
            else:
                shared_attrs = {}
        except Exception:
            shared_attrs = {}
        
        location_count = len(shared_attrs.get("LocationCache", {}))
        station_count = len(shared_attrs.get("StationCache", {}))
        zone_count = len(shared_attrs.get("ZoneCache", {}))
        
        # Get user cache directly from persistent attributes
        user_attrs = attributes_manager.persistent_attributes
        user_count = len(user_attrs.get("UserCache", {}))
        
        text = f"Data has been loaded. LocationCache has {location_count} items, " \
               f"StationCache has {station_count} items, " \
               f"ZoneCache has {zone_count} items, " \
               f"and UserCache has {user_count} items."
        
        return self.respond(handler_input, user, text, end=True)


class SkillExceptionHandler(AbstractExceptionHandler):
    """Handle exceptions"""
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        import traceback
        event = {
            "session": {
                "sessionId": handler_input.request_envelope.session.session_id,
                "user": {"userId": handler_input.request_envelope.session.user.user_id}
            }
        }
        notify(event, "ASK SDK Exception", traceback.format_exc())

        speech_text = '<say-as interpret-as="interjection">aw man</say-as>' + \
                     '<prosody pitch="+25%">' + \
                     "Clima Cast has experienced an error. The author has been " + \
                     "notified and will address it as soon as possible. Until then " + \
                     "you might be able to rephrase your request to get around the issue." + \
                     '</prosody>'

        return handler_input.response_builder.speak(
            f"<speak>{speech_text}</speak>"
        ).set_should_end_session(True).response


sb = CustomSkillBuilder(persistence_adapter=ddb_adapter)

# Register individual intent handlers
# Order matters - more specific handlers should be registered first
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelAndStopIntentHandler())
sb.add_request_handler(MetricIntentHandler())
sb.add_request_handler(GetSettingIntentHandler())
sb.add_request_handler(SetPitchIntentHandler())
sb.add_request_handler(SetRateIntentHandler())
sb.add_request_handler(SetLocationIntentHandler())
sb.add_request_handler(GetCustomIntentHandler())
sb.add_request_handler(AddCustomIntentHandler())
sb.add_request_handler(RemoveCustomIntentHandler())
sb.add_request_handler(ResetCustomIntentHandler())
sb.add_request_handler(StoreDataIntentHandler())
sb.add_request_handler(GetDataIntentHandler())
sb.add_request_handler(FallbackIntentHandler())

# Add exception handler
sb.add_exception_handler(SkillExceptionHandler())

# Create lambda handler from SkillBuilder
_skill_lambda_handler = sb.lambda_handler()


# AWS Lambda handler entry point
def lambda_handler(event, context):
    """Main Lambda handler that routes requests to ASK SDK"""
    print("EVENT", event)
    return _skill_lambda_handler(event, context)

