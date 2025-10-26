"""
Constants and configuration data for the Climacast Alexa skill.

This module contains all constant definitions used throughout the skill,
including weather-related dictionaries, date/time mappings, and location data.
"""

# Slot names used in Alexa interaction model
SLOTS = [
    "day",
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
    "zipcode",
]

# Time period names
QUARTERS = ["morning", "afternoon", "evening", "overnight", "tonight", "night"]

# Day names
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Translation from ordinal numbers to words
MONTH_DAYS_XLATE = {
    "1st": "first",
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
    "20 second": "twenty second",
}

# Day names as words
MONTH_DAYS = [
    "first",
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
    "thirty first",
]

# Month names
MONTH_NAMES = [
    "january",
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
    "december",
]

# Weather metrics mapping
# Format: {"user_term": ["canonical_name", priority]}
METRICS = {
    "summary": ["summary", 1],
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
    "snow": ["precipitation", 0],
}

# Wind direction angles
# Format: ["name", "abbreviation", max_angle]
ANGLES = [
    ["north", "N", 11.25],
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
    ["north", "N", 360],
]

# US States and territories
# Format: [full_name, abbreviation, ...]
STATES = [
    "alabama",
    "al",
    "alaska",
    "ak",
    "arizona",
    "az",
    "arkansas",
    "ar",
    "dc",
    "dc",
    "california",
    "ca",
    "colorado",
    "co",
    "connecticut",
    "ct",
    "delaware",
    "de",
    "florida",
    "fl",
    "georgia",
    "ga",
    "hawaii",
    "hi",
    "idaho",
    "id",
    "illinois",
    "il",
    "indiana",
    "in",
    "iowa",
    "ia",
    "kansas",
    "ks",
    "kentucky",
    "ky",
    "louisiana",
    "la",
    "maine",
    "me",
    "maryland",
    "md",
    "massachusetts",
    "ma",
    "michigan",
    "mi",
    "minnesota",
    "mn",
    "mississippi",
    "ms",
    "missouri",
    "mo",
    "montana",
    "mt",
    "nebraska",
    "ne",
    "nevada",
    "nv",
    "new hampshire",
    "nh",
    "new jersey",
    "nj",
    "new mexico",
    "nm",
    "new york",
    "ny",
    "north carolina",
    "nc",
    "north dakota",
    "nd",
    "ohio",
    "oh",
    "oklahoma",
    "ok",
    "oregon",
    "or",
    "pennsylvania",
    "pa",
    "peurto rico",
    "pr",
    "rhode island",
    "ri",
    "south carolina",
    "sc",
    "south dakota",
    "sd",
    "tennessee",
    "tn",
    "texas",
    "tx",
    "utah",
    "ut",
    "vermont",
    "vt",
    "virginia",
    "va",
    "washington",
    "wa",
    "west virginia",
    "wv",
    "wisconsin",
    "wi",
    "wyoming",
    "wy",
]

# User settings names
SETTINGS = {
    "location": "location",
    "pitch": "pitch",
    "rate": "rate",
    "forecast": "forecast",
}

# Time quarters for day periods
# Format: {hour_quarter: ["name", is_daytime]}
TIME_QUARTERS = {
    0: ["overnight", False],
    1: ["morning", True],
    2: ["after noon", True],
    3: ["evening", False],
}

# Weather coverage descriptions
# Most of these are guesses. "good" means observed in data
WEATHER_COVERAGE = {
    "areas_of": "areas of",  # good
    "brief": "brief",
    "chance": "a chance of",  # good
    "definite": "definite",  # good
    "frequent": "frequent",
    "intermittent": "intermittent",
    "isolated": "isolated",  # good
    "likely": "likely",  # good
    "numerous": "numerous",  # good
    "occasional": "occasional",  # good
    "patchy": "patchy",  # good
    "periods_of": "periods of",
    "scattered": "scattered",  # good
    "slight_chance": "a slight chance of",  # good
    "widespread": "widespread",
}  # good

# Weather condition types
WEATHER_WEATHER = {
    "blowing_dust": "blowing dust",
    "blowing_sand": "blowing sand",
    "blowing_snow": "blowing snow",
    "drizzle": "drizzle",  # good
    "fog": "fog or mist",  # good
    "freezing_drizzle": "freezing drizzle",
    "freezing_fog": "freezing fog",  # good
    "freezing_rain": "freezing rain",  # good
    "freezing_spray": "freezing spray",
    "frost": "frost",
    "hail": "hail",
    "haze": "haze",  # good
    "ice_crystals": "ice crystals",
    "ice_fog": "ice fog",
    "ice_pellets": "sleet",
    "rain": "rain",  # good
    "rain_showers": "rain showers",  # good
    "smoke": "smoke",
    "snow": "snow",  # good
    "snow_showers": "snow showers",  # good
    "thunderstorms": "thunderstorms",  # good
    "volcanic ash": "volcanic ash",
    "water_spouts": "water spouts",
}

# Weather intensity levels
WEATHER_INTENSITY = {
    "": ["", 0],  # good
    "very_light": ["very light", 1],  # good
    "light": ["light", 2],  # good
    "moderate": ["moderate", 3],  # good
    "heavy": ["heavy", 4],
}  # good

# Weather visibility
WEATHER_VISIBILITY = {"": None}

# Weather attributes
WEATHER_ATTRIBUTES = {
    "damaging_wind": "damaging wind",  # good
    "dry": "dry",
    "frequent_lightning": "frequent lightning",
    "gusty_wind": "gusty winds",  # good
    "heavy_rain": "heavy rain",  # good
    "highest_ranking": "highest ranking",
    "include_unconditionally": "include unconditionally",
    "large_hail": "large hail",  # good
    "mixture": "mixture",
    "on_bridges": "on bridges and overpasses",
    "on_grassy": "on grassy areas",
    "or": "or",
    "outlying": "outlying areas",
    "small_hail": "small hail",  # good
    "tornado": "tornado",
}

# Location name corrections
# TODO: Need to figure out a better way to handle misunderstood names
LOCATION_XLATE = {
    "gnome alaska": "nome alaska",
    "woodberry minnesota": "woodbury minnesota",
}

# Regular expressions for text normalization
NORMALIZE_RE = [
    r"(?P<meridian>\d+\s*(am|pm))",
    r"(?P<deg>\s(1|-1))\s*degrees",
    r"(?P<ign>[A-Z][A-Z][CZ]\d\d\d.*?/.*?/)",
    r"(?P<nm>\d+\s*(nm))(?=\s|\W|$)",
    r"(?P<kt>\d+\s*(kt))(?=\s|\W|$)",
    r"(?P<tz>(?<=\s|\.)(hadt|hast|akdt|akst|pdt|pst|mdt|mst|cdt|cst|edt|est))(?=\s|\W|$)",
    r"(?P<sub>(?<=\s|\.)(ft|mph|nws|pt\.|pt))(?=\s|\W|$)",
    r"(?P<wind>(?<=\s|\.)(n|nne|ne|ene|e|ese|se|sse|s|ssw|sw|wsw|w|wnw|nw|nnw))(?=\s|$)",
    r"(?P<st>(?<=\s|\.)[A-Z][A-Z])(?=\s|\W|$)",
]


def get_default_metrics():
    """
    Returns the default ordered list of forecast metrics.

    This function consolidates the default metrics initialization logic
    that was previously duplicated across multiple locations.

    Returns:
        List[str]: Ordered list of default metric names
    """
    metrics = {}
    for name, value in METRICS.values():
        if value and name not in metrics:
            metrics[value] = name
    result = []
    for i in range(1, len(metrics) + 1):
        result.append(metrics[i])
    return result
