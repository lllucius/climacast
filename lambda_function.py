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
import requests
#from aniso8601 import parse_duration
from aniso8601.duration import parse_duration
from boto3 import resource as awsresource, client as awsclient
from datetime import datetime
from dateutil import parser, tz
from dateutil.relativedelta import *
from xml.etree.ElementTree import *
from lxml import html
from time import time

"""
    Anything defined here will persist for the duration of the lambda
    container, so only initialize them once to reduce initialization time.
"""
VERSION = 1
REVISION = 0

EVTID = os.environ.get("event_id", "")
APPID = os.environ.get("app_id", "amzn1.ask.skill.test")
MQID = os.environ.get("mapquest_id", "")
DUID = os.environ.get("dataupdate_id", "amzn1.ask.data.update")

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
                    "20 second": "twenty second"};

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

SNS = awsclient("sns")
DDB = awsresource("dynamodb", region_name="us-east-1")
LOCATIONCACHE = DDB.Table("LocationCache")
STATIONCACHE = DDB.Table("StationCache")
USERCACHE = DDB.Table("UserCache")
ZONECACHE = DDB.Table("ZoneCache")
HTTPS = requests.Session()

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

    if ("session" in event and "testing" in event["session"]) or EVTID == "":
        print("NOTIFY:\n\n  %s\n\n%s" % (sub, text))
    else:
        SNS.publish(TopicArn=EVTID, Subject=sub, Message=text[:2**18])

class Base(object):
    def __init__(self, event):
        self.event = event

    def get_zone(self, zoneId, zoneType):
        """
            Returns the zone information for the give zone ID
        """
        zoneId = zoneId.rsplit("/")[-1]
        zone = self.cache_get(ZONECACHE, {"id": zoneId})
        if zone is None:
            data = self.https("zones/%s/%s" % (zoneType, zoneId))
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get zone info for %s" % zoneId, data)
                return {}
            zone = self.put_zone(ZONECACHE, data)

        return zone
 
    def put_zone(self, table, data):
        """
            Writes the zone information to the cache
        """
        zone = {"id": data["id"],
                "type": data["type"],
                "name": data["name"]}

        self.cache_put(table, zone)

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
        station = self.cache_get(STATIONCACHE, {"id": stationId})
        if station is None:
            data = self.https("stations/%s" % stationId)
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get station %s" % stationId, data)
                return None
            station = self.put_station(STATIONCACHE, data)

        return station

    def put_station(self, table, data):
        """
            Save station information to the cache
        """
        name = data["name"].split(",")[-1].strip().rstrip()

        # DC station names seem to be reversed from the rest
        if name == "DC":
            name = data["name"].split(",")[0].strip().rstrip()

        station = {"id": data["stationIdentifier"],
                   "name": name}

        self.cache_put(table, station)

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

    def cache_get(self, table, key):
        """
            Retrieve an item from the cache using the provided table and key
        """
        item = table.get_item(Key=key)
        if item is None or "Item" not in item:
            return None
        return item["Item"]

    def cache_put(self, table, key, ttl=35):
        """
            Write an item to the cache using the provided table, key, and time to live
        """
        if ttl != 0:
            key["ttl"] = int(time()) + (ttl * 24 * 60 * 60)
        table.put_item(Item=key)

    def https(self, path, loc="api.weather.gov"):
        """
            Retrieve the JSON data from the given path and location
        """
        headers = {"User-Agent": "ClimacastAlexaSkill/1.0 (climacast@homerow.net)",
                   "Accept": "application/ld+json"}
        r = HTTPS.get("https://%s/%s" % (loc, path.replace(" ", "+")), headers=headers)
        if r.status_code != 200 or r.text is None or r.text == "":
            notify(self.event,
                        "HTTPSTATUS: %s" % r.status_code,
                        "URL: %s\n\n%s" % (r.url, r.content))
            return None
            
        #print("URL:", r.url)
        #print("PAGE:", json.dumps(r.json(), indent=4))
        
        return json.loads(r.text)

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
            hi = -42.379+2.04901523*F+10.14333127*rh-0.22475541*F*rh-6.83783*(pow(10, -3))*(pow(F, 2))-5.481717*(pow(10, -2))*(pow(rh, 2))+1.22874*(pow(10, -3))*(pow(F, 2))*rh+8.5282*(pow(10, -4))*F*(pow(rh, 2))-1.99*(pow(10, -6))*(pow(F, 2))*(pow(rh,2))
            if (rh <= 13) and (F >= 80.0) and (F <= 112.0):
                from math import sqrt
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
                    except:
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
    def __init__(self, event, tz, cwa, gridpoint):
        super().__init__(event)
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
                if dte and dte:
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
        values = get_values("pressure")
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
            hi =  max(types[t])
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
            d +=  ", ".join(attrs) + last

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
    def __init__(self, event, stations, limit=3):
        super().__init__(event)
        self.stations = stations
        self.xml = None
        self.station = None

        # Retrieve the current observations from the nearest station
        for stationid in self.stations:
            # Get the station info
            station = self.get_station(stationid)
            #print("STATION", station)
            if station is None:
                continue

            r = HTTPS.get("https://w1.weather.gov/xml/current_obs/%s.xml" % stationid)
            if r.status_code != 200 or r.text is None or r.text == "":
                continue

            self.station = station
            self.xml = XML(r.text.encode("UTF-8"))

            r = HTTPS.get("https://w1.weather.gov/data/obhistory/%s.html" % stationid)
            if r.status_code == 200 and r.content:
                tree = html.fromstring(r.content)

                self.obs = []
                try:
                    rows = tree.find(".//th").getparent()
                    for row in rows.itersiblings():
                        kids = row.getchildren()
                        if len(kids) > 0 and kids[0].tag == "td":
                            self.obs.append({"time": kids[1].text,
                                             "wind": kids[2].text,
                                             "weather": kids[4].text,
                                             "temp": kids[6].text,
                                             "humidity": kids[10].text,
                                             "windchill": kids[11].text,
                                             "heatindex": kids[12].text,
                                             "pressure": kids[13].text,
                                             "precip1": kids[15].text,
                                             "precip3": kids[16].text,
                                             "precip6": kids[17].text})
                except:
                    pass
            break

    def get_value(self, metric):
        e = self.xml.find(metric)
        return e.text if e is not None else None

    def get_rounded(self, metric):
        f = self.get_value(metric)
        return "%.0f" % float(f) if f else None

    @property
    def is_good(self):
        return self.xml is not None

    @property
    def station_id(self):
        return self.station["stationIdentifier"]

    @property
    def station_name(self):
        return self.station["name"]

    @property
    def time_reported(self):
        return parser.parse(self.get_value("observation_time_rfc822"))

    @property
    def description(self):
        return self.get_value("weather")

    @property
    def wind_speed(self):
        return self.get_rounded("wind_mph")

    @property
    def wind_direction(self):
        return self.get_value("wind_dir")

    @property
    def wind_gust(self):
        return self.get_rounded("wind_gust_mph")

    @property
    def temp(self):
        return self.get_rounded("temp_f")

    @property
    def wind_chill(self):
        wc = self.get_value("windchill_f")
        if wc:
            return wc

        t = self.get_value("temp_f")
        ws = self.get_value("wind_mph")
        if t and ws:
            return self.to_wind_chill(float(t), float(ws))

        return None

    @property
    def heat_index(self):
        hi = self.get_value("heat_index_f")
        if hi:
            return hi

        t = self.get_value("temp_f")
        rh = self.get_value("relative_humidity")
        if t and rh:
            return self.to_heat_index(float(t), float(rh))

        return None

    @property
    def feels_like(self):
        return self.wind_chill() or self.heat_index()

    @property
    def dewpoint(self):
        return self.get_rounded("dewpoint_f")

    @property
    def humidity(self):
        return self.get_value("relative_humidity")

    @property
    def pressure(self):
        return self.get_value("pressure_in")

    @property
    def pressure_trend(self):
        if self.obs:
            prev = float(self.obs[1]["pressure"])
            curr = float(self.obs[0]["pressure"])
            if curr < prev:
                return "falling"
            if curr > prev:
                return "rising"
            return "steady"

        return None

class Observationsv3(Base):
    def __init__(self, event, stations, limit=3):
        super().__init__(event)
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
        def __init__(self, event, alert):
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

    def __init__(self, event, zoneid):
        super().__init__(event)
        self.zoneid = zoneid
        self._title = ""
        self._alerts = []
        data = self.https("alerts/active?status=actual&zone=" + zoneid)
        if data is not None and "@graph" in data:
            self._title = data["title"]
            self._alerts = data["@graph"]

    def __iter__(self):
        for alert in self._alerts:
            yield self.Alert(self.event, alert)

    def __len__(self):
        return len(self._alerts)

    @property
    def title(self):
        return self._title

class Location(Base):
    def __init__(self, event):
        super().__init__(event)

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
            loc = self.cache_get(LOCATIONCACHE, {"location": "%s" % name})
            if loc is not None:
                self.loc = loc
                return None

            # Have a new location, so retrieve the base info
            coords, props = self.mapquest("%s" % name)
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
            loc = self.cache_get(LOCATIONCACHE, {"location": "%s %s" % (city, state)})
            #print("loc", loc)
            #if loc is not None:
            #    self.loc = loc
            #    return None

            # Have a new location, so retrieve the base info
            coords, props = self.mapquest("%s+%s" % (city, state))
            if coords is None:
                #notify(self.event, "City '%s' State '%s' not found" % (city, state))
                return "%s %s could not be located.  Try using the zip code." % (city, state)

        # Get the NWS location information (limit to 4 decimal places for the API)
        point = self.https("points/%s,%s" % \
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
        rloc = self.cache_get(LOCATIONCACHE, {"location": "%s %s" % (loc["city"], loc["state"])})
        if rloc is None:
            # Have a new location, so retrieve the base info
            rcoords, rprops = self.mapquest("%s+%s" % (loc["city"], loc["state"]))
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
        # the county coordinates from mapquest and asking NWS for that point.
        if "county" not in point and "county" in props:
            county = props["county"].lower().split()
            if county[-1] == "county":
                county[-1] = ""
            county = " ".join(list(county))
            coords, props = self.mapquest("%s+county+%s" % (county, loc["state"]))
            if coords is not None:
                pt = self.https("points/%s,%s" % \
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
        self.cache_put(LOCATIONCACHE, loc)

        # And remember
        self.loc = loc

        return None

    def mapquest(self, search):
        geo = self.https("geocoding/v1/address?key=%s&inFormat=kvp&outFormat=json&location=%s&thumbMaps=false" % (MQID, search.replace(" ", "+")), loc="www.mapquestapi.com")
        if geo is None or \
           len(geo["results"]) == 0 or \
           len(geo["results"][0]["locations"]) == 0:
            return None, None
        #print("GEO", geo)
        loc = geo["results"][0]["locations"][0]

        props = {}
        for n in loc:
            if n.startswith("adminArea") and n.endswith("Type") and loc[n] != "":
                props[loc[n]] = loc[n[:-4]]

        if "County" in props:
            props["County"] = props["County"].rsplit(" ", 1)[0]

        return (geo["results"][0]["locations"][0]["latLng"]["lat"], \
                geo["results"][0]["locations"][0]["latLng"]["lng"]), \
               props

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
    def state(self):
        return self.loc["state"]

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
    def __init__(self, event, userid):
        super().__init__(event)
        self._userid = userid
        self._location = None
        self._rate = 100
        self._pitch = 100
        self.get_default_metrics()

        # Get or create the user's profile
        user = self.cache_get(USERCACHE, {"userid": userid})
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
        self.cache_put(USERCACHE, item, ttl=0)

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

class DataLoad(Base):
    def __init__(self, event):
        super().__init__(event)

    def handle_event(self):
        if DUID not in self.event.get("resources", []):
            return None

        for zoneType in ["forecast", "county"]:
            print("Loading %s zones" % (zoneType))
            self.load_data("zones/%s" % (zoneType), ZONECACHE, self.put_zone)

        print("Loading stations")
        self.load_data("stations", STATIONCACHE, self.put_station)

    def load_data(self, url, table, putter):
        data = self.https(url)
        with table.batch_writer() as batch:
            print("Items:", len(data["@graph"]))
            for item in data["@graph"]:
                putter(batch, item)

class Skill(Base):
    def __init__(self, event):
        super().__init__(event)
        self.loc = None
        self.end = True

    def handle_event(self):
        self.session = self.event["session"]
        self.attrs = self.session.get("attributes", {})
        self.request = self.event["request"]
        self.intent = self.request.get("intent", {})

        # Load or create the user's profile
        self.user = User(self.event, self.session["user"]["userId"])

        # Amazon says to verify our application id
        if self.session["application"]["applicationId"] != APPID:
            return self.respond("Invoked from unknown application.")

        # Retrieve the default location info
        if self.user.location:
            loc = Location(self.event)
            text = loc.set(self.user.location)
            if text is None:
                self.loc = loc

        # Load the slot values
        self.slots = type("slots", (), {})
        slots = self.intent.get("slots", {})
        for slot in SLOTS:
            val = slots.get(slot, {}).get("value", None)
            setattr(self.slots, slot, val.strip().lower() if val else None)
            print("SLOT:", slot, getattr(self.slots, slot))

        # Determine the request type
        rtype = self.request["type"]
        if rtype == "IntentRequest":
            name = self.intent["name"]
        else:
            name = rtype
        print("INTENT:", name)

        # Look it up and verify the location, if the intent expects one
        if name in FUNCS:
            # Verify the location, if this request requires it
            if FUNCS[name][1]:
                text = self.get_location()
                if text is not None:
                    return self.respond(text)

                # Determine the start and end times for the request.
                # NOTE:  Must be done after getting the requested location to
                #        set the timezone correctly.
                self.get_when()

            # Get the associated method name
            name = FUNCS[name][0]
        
        return getattr(self, name, self.default_handler)()

    def respond(self, text, end=None):
        new = self.session["new"]
        if end is None:
            end = new

        prompt = None
        if not end:
            prompt = "For %s, say help, " % ("more examples" if new else "example requests") + \
                     "To interrupt speaking, say Alexa, cancel, " + \
                     "If you are done, say stop."
            text += ". " if text.strip()[-1] != "." else " "
            text += prompt if new else "if you are done, say stop."
        return {
                 "version": "1.0",
                 "sessionAttributes": self.attrs,
                 "response":
                 {
                   "outputSpeech":
                   {
                     "type": "SSML",
                     "ssml": '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
                             (self.user.rate,
                              self.user.pitch - 100,
                              text)
                   },
                   "reprompt":
                   {
                     "outputSpeech":
                     {
                       "type": "SSML",
                        "ssml": '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
                                (self.user.rate,
                                 self.user.pitch - 100,
                                 prompt)
                     },
                   },
                   "shouldEndSession": end
                 } 
               }

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

        return self.respond(text, end=False)

    def session_end_request(self):
        return self.respond("Thank you for using Clime a Cast.", end=True)

    def session_ended_request(self):
        if "error" in self.request:
            notify(self.event, "Error detected", self.request["error"]["message"])
            return self.respond(self.request["error"]["message"], end=True)
    
        notify(self.event, "Session Ended", self.request["reason"])
        return self.respond(self.request["reason"], end=True)

    def cancel_intent(self):
        return self.respond("Canceled.")
 
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
        return self.respond(text)

    def metric_intent(self):
        metric = self.slots.metric
        if metric is None:
            return self.respond("You must include a metric like temperature, humidity or wind")

        if metric == "alerts":
            return self.get_alerts()
 
        if metric == "extended forecast":
            return self.get_extended()

        if metric not in METRICS:
            return self.respond("%s is an unrecognized metric." % metric)

        metrics = self.user.metrics if METRICS[metric][0] == "all" else [METRICS[metric][0]]

        # These are absolute
        if metric == "forecast" or self.has_when:
            return self.get_forecast(metrics)

        # Try to extract the intent of the request
        leadin = self.slots.leadin or ""
        if "chance" in metric or "will" in leadin or "going" in leadin:
            return self.get_forecast(metrics)

        return self.get_current(metrics)

    def get_setting_intent(self):
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
            return self.respond("Unrecognized setting: %s" % setting)

        text = ""
        for setting in settings:
            if text != "":
                text += ", "
                if setting == settings[-1]:
                    text += "and "
            if setting == "location":
                text += "the location is set to %s." % self.loc.spoken_name()
            elif setting == "pitch":
                text += "the voice pitch is set to %d percent." % self.user.pitch
            elif setting == "rate":
                text += "the voice rate is set to %d percent." % self.user.rate
            elif setting == "forecast":
                text += "the custom forecast will include the %s." % \
                        ", ".join(list(self.user.metrics[:-1])) + " and " + self.user.metrics[-1]

        return self.respond(text)

    def set_location_intent(self):
        text = self.get_location(req=True)
        if text is None:
            self.user.location = self.loc.name
            text = "Your default location has been set to %s." % self.loc.spoken_name()

        return self.respond(text)

    def set_pitch_intent(self):
        if self.slots.percent and self.slots.percent.isdigit():
            pitch = int(self.slots.percent)
            if 130 >= pitch >= 70:
                self.user.pitch = pitch
                text = "Voice pitch has been set to %d percent." % pitch
            else:
                text = "The pitch must be between 70 and 130 percent"
        else:
            text = "Expected a percentage when setting the pitch"

        return self.respond(text)

    def set_rate_intent(self):
        if self.slots.percent and self.slots.percent.isdigit():
            rate = int(self.slots.percent)
            if 150 >= rate >= 50:
                self.user.rate = rate
                text = "Voice rate has been set to %d percent." % rate
            else:
                text = "The rate must be between 50 and 150 percent"
        else:
            text = "Expected a percentage when setting the rate"

        return self.respond(text)

    def get_custom_intent(self):
        text = "The custom forecast will include the %s." % \
               ", ".join(list(self.user.metrics[:-1])) + " and " + self.user.metrics[-1]
        return self.respond(text)


    def add_custom_intent(self):
        metric = self.slots.metric
        if metric is None:
            return self.respond("You must include a metric like temperature, humidity or wind.")

        if metric not in METRICS:
            return self.respond("%s is an unrecognized metric." % metric)

        metric = METRICS[metric]
        if not metric[1]:
            return self.respond("%s can't be used when customizing the forecast." % metric[0])

        if self.user.has_metric(metric[0]):
            return self.respond("%s is already included in the custom forecast." % metric[0])
    
        self.user.add_metric(metric[0])

        return self.respond("%s has been added to the custom forecast." % metric[0])

    def remove_custom_intent(self):
        metric = self.slots.metric
        if metric is None:
            return self.respond("You must include a metric like temperature, humidity or wind.")

        if metric not in METRICS:
            return self.respond("%s is an unrecognized metric." % metric)

        metric = METRICS[metric]
        if not metric[1]:
            return self.respond("%s can't be used when customizing the forecast." % metric[0])

        if not self.user.has_metric(metric[0]):
            return self.respond("%s is already excluded from the custom forecast." % metric[0])
    
        self.user.remove_metric(metric[0])

        return self.respond("%s has been removed from the custom forecast." % metric[0])

    def reset_custom_intent(self):
        self.user.reset_metrics()

        return self.respond("the custom forecast has been reset to defaults.")

    def get_alerts(self):
        alerts = Alerts(self.event, self.loc.countyZoneId)
        if len(alerts) == 0:
            text = "No alerts in effect at this time for %s." % self.loc.city
        else:
            text = alerts.title + "...\n"
            for alert in alerts:
                text += alert.headline + "...\n"
                text += "for " + alert.area + "...\n"
                text += alert.description + "...\n"
                text += alert.instruction + "...\n"
        
        return self.respond(self.normalize(text))

    def get_current(self, metrics):
        text = ""

        if False:
            alerts = Alerts(self.event, self.loc.countyZoneId)
            cnt = len(alerts)
            if cnt > 0:
                text += "There's %d alert%s in effect for your area! " % \
                       (cnt,
                        "s" if cnt > 1 else "")

        # Retrieve the current observations from the nearest station
        obs = Observations(self.event, self.loc.observationStations)
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

        return self.respond(self.normalize(text))

    def get_discussion(self):
        match = re.compile(".*(^\.SHORT TERM.*?)^&&$",
                           re.MULTILINE|re.DOTALL).match(self.get_product("AFD"))
        if not match:
            return self.respond("Unable to extract forecast discussion")

        text = match.group(1)

        return self.respond(text)

    def get_extended(self):
        data = self.https("points/%s/forecast" % self.loc.coords)
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

        return self.respond(self.normalize(header + text))

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
        gp = GridPoints(self.event, self.loc.tz, self.loc.cwa, self.loc.grid_point)
        for metric in metrics:
            metric = METRICS[metric][0]
            #print("FORECAST METRIC", metric, "STIME", stime, "ETIME", etime)
#            if gp.set_interval(stime, etime):
            if not gp.set_interval(stime, etime):
                text = "Forecast information is unavailable for %s %s" % \
                       (MONTH_NAMES[self.stime.month - 1],
                        MONTH_DAYS[self.stime.day - 1])
                return self.respond(text)

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

        return self.respond(fulltext)

    def get_location(self, req=False):
        if self.slots.location or self.slots.zipcode:
            loc = Location(self.event)
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

def lambda_handler(event, context=None):
    #print(json.dumps(event, indent=4))
    try:
        if "event-type" in event:
            if event["event-type"] == "pinger":
                return 
            else:
                DataLoad(event).handle_event()
        else:
            return Skill(event).handle_event()
    except SystemExit:
        pass
    except:
        import traceback
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


def test_load():
    with open("datarefresh.json") as f:
        event = json.load(f)
        event["resources"] = ["amzn1.ask.data.update"]
        lambda_handler(event)

def test_one():
    with open(sys.argv[1] if len(sys.argv) > 1 else "test.json") as f:
        event = json.load(f)
        event["session"]["application"]["applicationId"] = "amzn1.ask.skill.test"
        event["session"]["testing"] = True
        event["session"]["user"]["userId"] = "testuser"
        print(json.dumps(lambda_handler(event), indent=4))

if __name__ == "__main__":
    import logging
    import sys
    from cachecontrol import CacheControl, CacheControlAdapter
    from cachecontrol.caches.file_cache import FileCache
    from cachecontrol.heuristics import ExpiresAfter
    logging.basicConfig()
    HTTPS.mount('https://', CacheControlAdapter(cache=FileCache(".webcache"),
                                                heuristic=ExpiresAfter(hours=1)))

    if len(sys.argv) > 1 and sys.argv[1] == "load":
        z = test_load()
    else:
        z = test_one()
