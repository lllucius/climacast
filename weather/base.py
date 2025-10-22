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
Base class for weather data operations.

This module provides the base functionality for interacting with the
National Weather Service API, including zone lookups, station management,
HTTP communication, and text normalization.
"""

import json
from typing import Dict, List, Optional, Any, Union

from utils import converters
from utils.text_normalizer import normalize as normalize_text
from utils.constants import ANGLES


# These will be set by lambda_function module to avoid circular imports
notify = None
HTTPS = None


class WeatherBase(object):
    """
    Base class for weather data operations.
    
    Provides common functionality for all weather classes including:
    - NWS API communication
    - Zone and station lookups
    - Caching support
    - Unit conversions
    - Text normalization
    """
    
    def __init__(self, event: Dict[str, Any], cache_handler=None) -> None:
        """
        Initialize the weather base class.
        
        Args:
            event: Event dictionary containing request information
            cache_handler: Optional cache handler for data persistence
        """
        self.event = event
        self.cache_handler = cache_handler

    def get_zone(self, zoneId: str, zoneType: str) -> Dict[str, Any]:
        """
        Returns the zone information for the given zone ID.
        
        Args:
            zoneId: Zone identifier
            zoneType: Type of zone (forecast, county, fire)
            
        Returns:
            Dict containing zone information
        """
        global notify
        if notify is None:
            import lambda_function
            notify = lambda_function.notify
            
        zoneId = zoneId.rsplit("/")[-1]
        zone = self.cache_handler.get_zone(zoneId) if self.cache_handler else None
        if zone is None:
            data = self.https("zones/%s/%s" % (zoneType, zoneId))
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get zone info for %s" % zoneId, data)
                return {}
            zone = self.put_zone(data)

        return zone
 
    def put_zone(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Writes the zone information to the cache.
        
        Args:
            data: Zone data from NWS API
            
        Returns:
            Dict containing cached zone information
        """
        zone = {"id": data["id"],
                "type": data["type"],
                "name": data["name"]}

        if self.cache_handler:
            self.cache_handler.put_zone(zone["id"], zone)

        return zone

    def get_forecast_zone(self, zoneId: str) -> Dict[str, Any]:
        """Returns the forecast zone for the given zone ID."""
        return self.get_zone(zoneId, "forecast")

    def get_county_zone(self, zoneId: str) -> Dict[str, Any]:
        """Return the county zone for the given zone ID."""
        return self.get_zone(zoneId, "county")

    def get_fire_zone(self, zoneId: str) -> Dict[str, Any]:
        """Returns the fire zone for the given zone ID."""
        return self.get_zone(zoneId, "fire")

    def get_stations(self, coords: str) -> List[str]:
        """
        Returns the list of stations nearest to furthest order
        from the given coordinates.
        
        Args:
            coords: Coordinates in "lat,lon" format
            
        Returns:
            List of station IDs
        """
        data = self.https("points/%s/stations" % coords)
        if data is None or data.get("status", 0) != 0:
            notify(self.event, "Unable to get stations for %s" % coords, data)
            return []

        return [station.rsplit("/")[-1] for station in data["observationStations"]]

    def get_station(self, stationId: str) -> Optional[Dict[str, Any]]:
        """
        Returns the station information for the given station ID.
        
        Args:
            stationId: Station identifier
            
        Returns:
            Dict containing station information or None
        """
        stationId = stationId.rsplit("/")[-1]
        station = self.cache_handler.get_station(stationId) if self.cache_handler else None
        if station is None:
            data = self.https("stations/%s" % stationId)
            if data is None or data.get("status", 0) != 0:
                notify(self.event, "Unable to get station %s" % stationId, data)
                return None
            station = self.put_station(data)

        return station

    def put_station(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save station information to the cache.
        
        Args:
            data: Station data from NWS API
            
        Returns:
            Dict containing cached station information
        """
        name = data["name"].split(",")[-1].strip().rstrip()

        # DC station names seem to be reversed from the rest
        if name == "DC":
            name = data["name"].split(",")[0].strip().rstrip()

        station = {"id": data["stationIdentifier"],
                   "name": name}

        if self.cache_handler:
            self.cache_handler.put_station(station["id"], station)

        return station

    def get_product(self, product: str) -> Optional[str]:
        """
        Return the text for the given product.
        
        Args:
            product: Product type code
            
        Returns:
            Product text or None
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

    def https(self, path: str, loc: str = "api.weather.gov") -> Optional[Dict[str, Any]]:
        """
        Retrieve the JSON data from the given path and location.
        
        Args:
            path: API path
            loc: API location (default: api.weather.gov)
            
        Returns:
            Dict containing JSON response or None
        """
        # Import HTTPS session from lambda_function
        global HTTPS, notify
        if HTTPS is None or notify is None:
            import lambda_function
            HTTPS = lambda_function.HTTPS
            notify = lambda_function.notify
            
        headers = {"User-Agent": "ClimacastAlexaSkill/1.0 (climacast@homerow.net)",
                   "Accept": "application/ld+json"}
        r = HTTPS.get("https://%s/%s" % (loc, path.replace(" ", "+")), headers=headers)
        if r.status_code != 200 or r.text is None or r.text == "":
            notify(self.event,
                        "HTTPSTATUS: %s" % r.status_code,
                        "URL: %s\n\n%s" % (r.url, r.content))
            return None
            
        return json.loads(r.text)

    # Unit conversion methods - delegate to converters module
    def to_skys(self, percent: Optional[float], isday: bool) -> Optional[str]:
        """Convert the sky cover percentage to text"""
        return converters.to_skys(percent, isday)
    
    def to_percent(self, percent: Optional[float]) -> Optional[int]:
        """Return the given value, if any, as an integer"""
        return converters.to_percent(percent)
    
    def mb_to_in(self, mb: Optional[float]) -> Optional[str]:
        """Convert the given millibar value, if any, to inches"""
        return converters.mb_to_in(mb)

    def pa_to_in(self, pa: Optional[float]) -> Optional[str]:
        """Convert the given pascals, if any, to inches"""
        return converters.pa_to_in(pa)

    def mm_to_in(self, mm: Optional[float], as_text: bool = False) -> Optional[Union[str, tuple]]:
        """
        Convert the given millimeters, if any, to inches.  If requested,
        further convert inches to words.
        """
        return converters.mm_to_in(mm, as_text)

    def c_to_f(self, c):
        """Convert the given celsius value, if any, to fahrenheit"""
        result = converters.c_to_f(c)
        return None if result is None else "{:.0f}".format(result)

    def kph_to_mph(self, kph):
        """Convert the given kilometers per hour, if any, to miles per hour"""
        return None if kph is None or kph == 0 else "{:.0f}".format(kph * 0.62137119223733)

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
        """Calculate wind chill temperature"""
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

    def normalize(self, text: str) -> str:
        """
        Normalize text for speech output.
        
        This method delegates to the utils.text_normalizer module.
        """
        return normalize_text(text)

    def is_day(self, when):
        """
        Determine if given time is during the day
        """
        return True if 6 <= when.hour < 18 else False


# Export for backward compatibility
Base = WeatherBase
