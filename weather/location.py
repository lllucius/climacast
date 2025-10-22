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
Location class for geocoding and location management.

This module provides the Location class for converting location names
and zip codes to coordinates and retrieving associated weather zones.
"""

from typing import Dict, Any, Optional, Tuple
from dateutil import tz

from weather.base import WeatherBase
from utils.constants import STATES, LOCATION_XLATE


# Global GEOLOCATOR will be set by lambda_function
GEOLOCATOR = None


def notify(event, subject, message=None):
    """Placeholder for notify function - will be replaced by lambda_function import"""
    import logging
    logging.error(f"{subject}: {message}")


class Location(WeatherBase):
    """
    Handles location geocoding and NWS zone information.
    
    This class converts location names or zip codes to coordinates,
    retrieves associated weather zones, and manages location data.
    """
    
    def __init__(self, event, cache_handler=None):
        """
        Initialize Location handler.
        
        Args:
            event: Event dictionary
            cache_handler: Optional cache handler
        """
        super().__init__(event, cache_handler)

    def set(self, name, default=None):
        """
        Set the location by name or zip code.
        
        Args:
            name: Location name or zip code
            default: Default location object if name doesn't have state
            
        Returns:
            None on success, error message string on failure
        """
        # Import notify if needed
        global notify, GEOLOCATOR
        if notify is None or GEOLOCATOR is None:
            import lambda_function
            notify = lambda_function.notify
            GEOLOCATOR = lambda_function.GEOLOCATOR
            
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
            loc = self.cache_handler.get_location("%s" % name) if self.cache_handler else None
            if loc is not None:
                self.loc = loc
                return None

            # Have a new location, so retrieve the base info
            coords, props = self.mapquest("%s" % name)
            if coords is None:
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

            # Retrieve the location data from the cache
            loc = self.cache_handler.get_location("%s %s" % (city, state)) if self.cache_handler else None

            # Have a new location, so retrieve the base info
            coords, props = self.mapquest("%s+%s" % (city, state))
            if coords is None:
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

        # Retrieve the location data from the cache
        rloc = self.cache_handler.get_location("%s %s" % (loc["city"], loc["state"])) if self.cache_handler else None
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
        # the county coordinates from the geolocator and asking NWS for that point.
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
        if self.cache_handler:
            self.cache_handler.put_location(loc["location"], loc)

        # And remember
        self.loc = loc

        return None

    def mapquest(self, search):
        """
        Geocode a location using the Geolocator class.
        This method is kept for backward compatibility but now uses HERE.com API.
        
        Args:
            search: Location string to geocode
            
        Returns:
            Tuple of (coordinates, properties) where coordinates is (lat, lng) or None
        """
        global GEOLOCATOR
        if GEOLOCATOR is None:
            import lambda_function
            GEOLOCATOR = lambda_function.GEOLOCATOR
        return GEOLOCATOR.geocode(search)

    def spoken_name(self, name=None):
        """Get the spoken form of the location name."""
        loc = name or self.loc["location"]
        return "zip code " + " ".join(list(loc)) if loc and loc.isdigit() else loc

    @property
    def name(self):
        """Location name."""
        return self.loc["location"]

    @property
    def coords(self):
        """Location coordinates."""
        return self.loc["coords"]

    @property
    def city(self):
        """City name."""
        return self.loc["city"]

    @property
    def state(self):
        """State name."""
        return self.loc["state"]

    @property
    def cwa(self):
        """County Warning Area."""
        return self.loc["cwa"]

    @property
    def grid_point(self):
        """Grid point coordinates."""
        return self.loc["gridPoint"]

    @property
    def timeZone(self):
        """Time zone identifier."""
        return self.loc["timeZone"]

    @property 
    def forecastZoneId(self):
        """Forecast zone ID."""
        return self.loc["forecastZoneId"]

    @property 
    def forecastZoneName(self):
        """Forecast zone name."""
        return self.loc["forecastZoneName"]

    @property 
    def countyZoneId(self):
        """County zone ID."""
        return self.loc["countyZoneId"]

    @property 
    def countyZoneName(self):
        """County zone name."""
        return self.loc["countyZoneName"]

    @property
    def observationStations(self):
        """List of observation stations."""
        return self.loc["observationStations"]

    @property
    def tz(self):
        """Timezone object."""
        return tz.gettz(self.loc["timeZone"])


# Backward compatibility alias
Location.__name__ = "Location"
