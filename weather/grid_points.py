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
GridPoints class for handling forecast grid data from NWS API.

This module provides the GridPoints class for processing weather forecast
data from the National Weather Service gridpoints endpoint.
"""

from aniso8601.duration import parse_duration
from dateutil import parser
from dateutil.relativedelta import relativedelta

from utils.constants import (WEATHER_ATTRIBUTES, WEATHER_COVERAGE,
                             WEATHER_INTENSITY, WEATHER_WEATHER)
from weather.base import WeatherBase


class GridPoints(WeatherBase):
    """
    Handles forecast grid data from the NWS API.

    This class retrieves and processes weather forecast data for a specific
    grid point, including temperature, precipitation, wind, and other metrics.
    """

    def __init__(self, event, tz, cwa, gridpoint, cache_handler=None):
        """
        Initialize GridPoints with location and time information.

        Args:
            event: Event dictionary
            tz: Timezone object
            cwa: County Warning Area
            gridpoint: Grid point coordinates
            cache_handler: Optional cache handler
        """
        super().__init__(event, cache_handler)
        self.tz = tz
        self.data = self.https("gridpoints/%s/%s" % (cwa, gridpoint))
        self.values = {}
        self.times = {}
        self.highs = {}
        self.lows = {}

    def set_interval(self, stime, etime):
        """
        Set the time interval for weather data retrieval.

        Args:
            stime: Start time
            etime: End time

        Returns:
            True if valid data exists in range, False otherwise
        """
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
        """
        Check if a time period overlaps with the given range.

        Args:
            time: Time string in ISO 8601 format
            stime: Start time
            etime: End time

        Returns:
            Tuple of (start_datetime, end_datetime) or (None, None)
        """
        dt, _, dur = time.partition("/")
        dts = parser.parse(dt).astimezone(self.tz)
        dte = dts + parse_duration(dur)  # , relative=True)

        if stime >= dts and stime < dte or etime >= dts and etime < dte:
            return dts, dte

        return None, None

    def get_values(self, metric):
        """
        Get hourly values for a specific metric.

        Args:
            metric: Metric name (e.g., 'temperature', 'precipitation')

        Returns:
            List of values
        """
        if metric not in self.values:
            vals = []
            times = []
            stime = self.stime
            for value in self.data.get(metric, {}).get("values", {}):
                dts, dte = self.in_range(value["validTime"], stime, self.etime)
                if dts and dte:
                    v = value["value"]
                    while stime < self.etime and stime < dte:
                        vals.append(v)
                        times.append(stime)
                        stime += relativedelta(hours=+1)
                if stime >= self.etime:
                    break
            self.values[metric] = vals
            self.times[metric] = times

        return self.values[metric]

    def get_low(self, metric):
        """Get the low value for a metric."""
        if metric not in self.lows:
            values = [value for value in self.get_values(metric) if value is not None]
            if len(values) == 0:
                self.lows[metric] = None
            else:
                self.lows[metric] = min(values)

        return self.lows[metric]

    def get_high(self, metric):
        """Get the high value for a metric."""
        if metric not in self.highs:
            values = [value for value in self.get_values(metric) if value is not None]
            if len(values) == 0:
                self.highs[metric] = None
            else:
                self.highs[metric] = max(values)

        return self.highs[metric]

    def get_initial(self, metric):
        """Get the initial value for a metric."""
        values = self.get_values(metric)
        return values[0] if len(values) > 0 else None

    def get_final(self, metric):
        """Get the final value for a metric."""
        values = self.get_values(metric)
        return values[-1] if len(values) > 0 else None

    def get_times(self, metric):
        """Get the times associated with a metric."""
        self.get_values(metric)
        return self.times.get(metric, [])

    # Temperature properties
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

    # Humidity properties
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

    # Dewpoint properties
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

    # Barometric pressure properties
    @property
    def pressure_low(self):
        return self.pa_to_in(self.get_low("pressure"))

    @property
    def pressure_high(self):
        return self.pa_to_in(self.get_high("pressure"))

    @property
    def pressure_initial(self):
        return self.pa_to_in(self.get_initial("pressure"))

    @property
    def pressure_final(self):
        return self.pa_to_in(self.get_final("pressure"))

    # Precipitation properties
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
        return self.mm_to_in(
            self.get_initial("quantitativePrecipitation"), as_text=True
        )

    @property
    def precip_amount_final(self):
        return self.mm_to_in(self.get_final("quantitativePrecipitation"), as_text=True)

    @property
    def precip_total(self):
        values = [
            value
            for value in self.get_values("quantitativePrecipitation")
            if value is not None
        ]
        if len(values) == 0:
            return None
        return self.mm_to_in(sum(values))

    @property
    def precip_probability(self):
        return self.to_percent(self.get_high("probabilityOfPrecipitation"))

    @property
    def precip_text(self):
        inches, amt, whole = self.mm_to_in(
            sum(
                [
                    value if value else 0
                    for value in self.get_values("quantitativePrecipitation")
                ]
            ),
            True,
        )
        if inches == "0.00":
            return ""
        text = []
        if amt:
            text.append(amt)
        if whole:
            text.append(whole)
        if len(text) > 0:
            if whole:
                text.append("inch" if whole == "one" else "inches")
            else:
                text.append("of an inch")
        return " ".join(text) if len(text) > 0 else ""

    # Snow properties
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
    def snow_total(self):
        values = [
            value for value in self.get_values("snowfallAmount") if value is not None
        ]
        if len(values) == 0:
            return None
        return self.mm_to_in(sum(values))

    @property
    def snow_text(self):
        inches, amt, whole = self.mm_to_in(
            sum([value if value else 0 for value in self.get_values("snowfallAmount")]),
            True,
        )
        if inches == "0.00":
            return ""
        text = []
        if amt:
            text.append(amt)
        if whole:
            text.append(whole)
        if len(text) > 0:
            if whole:
                text.append("inch" if whole == "one" else "inches")
            else:
                text.append("of an inch")
        return " ".join(text) if len(text) > 0 else ""

    # Wind properties
    @property
    def wind_speed_low(self):
        return self.kph_to_mph(self.get_low("windSpeed"))

    @property
    def wind_speed_high(self):
        return self.kph_to_mph(self.get_high("windSpeed"))

    @property
    def wind_speed_initial(self):
        return self.kph_to_mph(self.get_initial("windSpeed"))

    @property
    def wind_speed_final(self):
        return self.kph_to_mph(self.get_final("windSpeed"))

    @property
    def wind_direction_initial(self):
        return self.da_to_dir(self.get_initial("windDirection"))

    @property
    def wind_direction_final(self):
        return self.da_to_dir(self.get_final("windDirection"))

    @property
    def wind_gust_low(self):
        return self.kph_to_mph(self.get_low("windGust"))

    @property
    def wind_gust_high(self):
        return self.kph_to_mph(self.get_high("windGust"))

    @property
    def wind_gust_initial(self):
        return self.kph_to_mph(self.get_initial("windGust"))

    @property
    def wind_gust_final(self):
        return self.kph_to_mph(self.get_final("windGust"))

    # Heat index and wind chill
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

    # Sky cover
    @property
    def skys_initial(self):
        return self.to_skys(self.get_initial("skyCover"), self.is_day(self.stime))

    @property
    def skys_final(self):
        return self.to_skys(self.get_final("skyCover"), self.is_day(self.stime))

    @property
    def weather_text(self):
        """
        Provides a description of the expected weather.
        TODO: Not at all happy with this. It needs to be redone.
        """
        d = []

        for w in self.data.get("weather", {}).get("values", []):
            dts, dte = self.in_range(w["validTime"], self.stime, self.etime)
            if not dts or not dte:
                continue

            for v in w["value"]:
                cov = WEATHER_COVERAGE.get(v.get("coverage", ""), "")
                wea = WEATHER_WEATHER.get(v.get("weather", ""), "")
                v.get("visibility", {}).get("value", "")
                ints = v.get("intensity", "")
                inte = WEATHER_INTENSITY.get(ints, ["", 0])
                atts = v.get("attributes", [])
                att = []

                if inte[1] >= 4:
                    inte = "heavy"
                elif inte[1] >= 3:
                    inte = "moderate"
                elif inte[1] >= 2:
                    inte = "light"
                else:
                    inte = ""

                for a in atts:
                    t = WEATHER_ATTRIBUTES.get(a, "")
                    if t:
                        att.append(t)

                txt = " ".join([s for s in [cov, inte, wea] + att if s])
                if txt not in d and txt:
                    d.append(txt)

        return ", then ".join(d) if d else ""
