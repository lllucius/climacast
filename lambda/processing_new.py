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
from math import sqrt
from time import time

import requests
from aniso8601.duration import parse_duration
from cachetools import TTLCache, cached
from datetime import datetime
from dateutil import parser, tz
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# TODO: Need to figure out a better way to handle misunderstood names
LOCATION_XLATE = {"gnome alaska": "nome alaska",
                  "woodberry minnesota": "woodbury minnesota"}

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
