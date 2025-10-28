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

from typing import Any, Dict, List, Optional

from datetime import datetime

from weather.base import WeatherBase


class Observations(WeatherBase):
    """
    Handles current weather observations from NWS observation stations.

    This class retrieves and processes current weather conditions including
    temperature, humidity, wind, pressure, and other metrics.
    """

    def __init__(self, event: Dict[str, Any], stations: Dict[str, Any], cache_handler: Optional[Any] = None) -> None:
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
        import json

        for station in stations["@graph"]:
            print("STATIOPNS")
            print(json.dumps(station, indent=4))
            stationId = station["stationIdentifier"]
            station = self.get_station(stationId)
            print("STAT")
            print(json.dumps(station, indent=4))
            if station:
                # data = self.https(f"stations/{stationId}/observations/latest")
                print("ASDFASDFASDFASDFASDF")
                data = self.https(f"stations/{stationId}/observations?limit=10")
                if data:
                    self.data = data
                    self.station = station
                    break

    @property
    def is_good(self) -> bool:
        """Current temperature in Fahrenheit."""
        return self.data is not None

    @property
    def temp(self) -> Optional[str]:
        """Current temperature in Fahrenheit."""
        return self.c_to_f(self.data.get("temperature", {}).get("value"))

    @property
    def humidity(self) -> Optional[int]:
        """Current relative humidity as percentage."""
        return self.to_percent(self.data.get("relativeHumidity", {}).get("value"))

    @property
    def dewpoint(self) -> Optional[str]:
        """Current dewpoint in Fahrenheit."""
        return self.c_to_f(self.data.get("dewpoint", {}).get("value"))

    @property
    def pressure(self) -> Optional[str]:
        """Current barometric pressure in inches."""
        return self.pa_to_in(self.data.get("barometricPressure", {}).get("value"))

    @property
    def wind_speed(self) -> Optional[str]:
        """Current wind speed in mph."""
        return self.kph_to_mph(self.data.get("windSpeed", {}).get("value"))

    @property
    def wind_direction(self) -> Optional[str]:
        """Current wind direction."""
        return self.da_to_dir(self.data.get("windDirection", {}).get("value"))

    @property
    def wind_gust(self) -> Optional[str]:
        """Current wind speed gusts in mph."""
        return self.kph_to_mph(self.data.get("windGust", {}).get("value"))

    @property
    def skys(self) -> Optional[str]:
        """Current sky conditions."""
        return self.data.get("textDescription")

    @property
    def wind_chill(self) -> Optional[str]:
        """Current wind chill temperature."""
        wc = self.data.get("windChill", {}).get("value")
        return self.c_to_f(wc) if wc else None

    @property
    def heat_index(self) -> Optional[str]:
        """Current heat index."""
        hi = self.data.get("heatIndex", {}).get("value")
        return self.c_to_f(hi) if hi else None

    @property
    def time_reported(self) -> datetime:
        """Date and time reported."""
        print("====================")
        print(self.data.get("timestamp"))
        print(self.data)
        return datetime.fromisoformat(self.data.get("timestamp"))

    @property
    def station_name(self) -> Optional[str]:
        """Name of reporting station."""
        return self.data.get("stationName")

    @property
    def description(self) -> Optional[str]:
        """Current weather description."""
        return self.data.get("textDescription")

    @property
    def pressure_trend(self) -> None:
        """Barometric pressure trend."""
        return None
