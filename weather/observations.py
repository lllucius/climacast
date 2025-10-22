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
Observations class for handling current weather observations from NWS API.

This module provides the Observations class for processing current weather
conditions from National Weather Service observation stations.
"""

from typing import Dict, Any, Optional
from weather.base import WeatherBase


class Observations(WeatherBase):
    """
    Handles current weather observations from NWS observation stations.
    
    This class retrieves and processes current weather conditions including
    temperature, humidity, wind, pressure, and other metrics.
    """
    
    def __init__(self, event, stations, cache_handler=None):
        """
        Initialize Observations with station list.
        
        Args:
            event: Event dictionary
            stations: List of station IDs to query
            cache_handler: Optional cache handler
        """
        super().__init__(event, cache_handler)
        self.data = None
        self.station = None

        for stationId in stations:
            station = self.get_station(stationId)
            if station:
                data = self.https("stations/%s/observations" % stationId)
                if data and data.get("features"):
                    self.data = data["features"][0]["properties"]
                    self.station = station
                    break

    @property
    def temp(self):
        """Current temperature in Fahrenheit."""
        return self.c_to_f(self.data.get("temperature", {}).get("value"))

    @property
    def humidity(self):
        """Current relative humidity as percentage."""
        return self.to_percent(self.data.get("relativeHumidity", {}).get("value"))

    @property
    def dewpoint(self):
        """Current dewpoint in Fahrenheit."""
        return self.c_to_f(self.data.get("dewpoint", {}).get("value"))

    @property
    def pressure(self):
        """Current barometric pressure in inches."""
        return self.pa_to_in(self.data.get("barometricPressure", {}).get("value"))

    @property
    def wind_speed(self):
        """Current wind speed in mph."""
        return self.mps_to_mph(self.data.get("windSpeed", {}).get("value"))

    @property
    def wind_dir(self):
        """Current wind direction."""
        return self.da_to_dir(self.data.get("windDirection", {}).get("value"))

    @property
    def skys(self):
        """Current sky conditions."""
        return self.data.get("textDescription")

    @property
    def wind_chill(self):
        """Current wind chill temperature."""
        wc = self.data.get("windChill", {}).get("value")
        return self.c_to_f(wc) if wc else None

    @property
    def heat_index(self):
        """Current heat index."""
        hi = self.data.get("heatIndex", {}).get("value")
        return self.c_to_f(hi) if hi else None


# Backward compatibility alias
Observations.__name__ = "Observations"
