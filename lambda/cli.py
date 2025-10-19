#!/usr/bin/env python3

# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

"""
Clima Cast CLI - Command Line Interface for Weather Processing

Allows local testing of weather processing without AWS Lambda/Alexa deployment.
Uses JSON file-based caching for location/station data.
"""

import argparse
import os
import sys
from datetime import datetime
from dateutil import tz
from dateutil.relativedelta import relativedelta

# Import weather processing modules
from weather_processor import (
    Base, GridPoints, Observations, Alerts, Location, User,
    METRICS, DAYS, MONTH_NAMES, MONTH_DAYS
)
from cache_adapter import JSONFileCacheAdapter


def get_event_dict():
    """Create a simple event dictionary for CLI usage"""
    return {
        "session": {
            "new": True,
            "sessionId": "cli-session",
            "user": {"userId": "cli-user"}
        },
        "request": {"type": "CLI"}
    }


def format_location_info(loc):
    """Format location information for display"""
    print(f"\nLocation Information:")
    print(f"  Location: {loc.city}, {loc.state}")
    print(f"  Coordinates: {loc.coords}")
    print(f"  Time Zone: {loc.timeZone}")
    print(f"  Forecast Zone: {loc.forecastZoneName}")
    if loc.countyZoneName != "missing":
        print(f"  County Zone: {loc.countyZoneName}")
    print()


def get_current_conditions(location_name, metrics=None, cache_dir=".cache", api_key=None, geocoder_type="here"):
    """Get current weather conditions for a location"""
    # Set up cache and event
    cache_adapter = JSONFileCacheAdapter(cache_dir)
    event = get_event_dict()
    
    # Create location object
    loc_obj = Location(event, geocoder_api_key=api_key, geocoder_type=geocoder_type, cache_adapter=cache_adapter)
    error = loc_obj.set(location_name)
    if error:
        print(f"Error: {error}")
        return 1
    
    # Display location info
    format_location_info(loc_obj)
    
    # Get observations
    obs = Observations(event, loc_obj.observationStations, cache_adapter=cache_adapter)
    
    if not obs.is_good:
        print("Observation information is currently unavailable.")
        return 1
    
    # Display current conditions
    print(f"Current Conditions:")
    print(f"  Station: {obs.station_name}")
    print(f"  Reported: {obs.time_reported.astimezone(loc_obj.tz).strftime('%I:%M %p %Z')}")
    print(f"  Conditions: {obs.description}")
    print()
    
    # Determine which metrics to display
    if metrics is None:
        metrics = ["temperature", "wind", "relative humidity", "dewpoint", "barometric pressure"]
    
    # Display requested metrics
    for metric in metrics:
        if metric == "temperature":
            if obs.temp is not None:
                print(f"  Temperature: {obs.temp}°F")
                if obs.wind_chill is not None:
                    print(f"    Wind Chill: {obs.wind_chill}°F")
                elif obs.heat_index is not None:
                    print(f"    Heat Index: {obs.heat_index}°F")
        elif metric == "wind":
            if obs.wind_speed is None or obs.wind_speed == "0":
                print(f"  Wind: Calm")
            else:
                if obs.wind_direction is None:
                    print(f"  Wind: {obs.wind_speed} mph")
                else:
                    print(f"  Wind: {obs.wind_direction} at {obs.wind_speed} mph")
                if obs.wind_gust is not None:
                    print(f"    Gusts: {obs.wind_gust} mph")
        elif metric == "dewpoint":
            if obs.dewpoint is not None:
                print(f"  Dewpoint: {obs.dewpoint}°F")
        elif metric == "barometric pressure":
            if obs.pressure is not None:
                trend = obs.pressure_trend
                trend_str = f" ({trend})" if trend else ""
                print(f"  Pressure: {obs.pressure} in{trend_str}")
        elif metric == "relative humidity":
            if obs.humidity is not None:
                print(f"  Humidity: {obs.humidity}%")
    
    print()
    return 0


def get_forecast(location_name, when="today", metrics=None, cache_dir=".cache", api_key=None, geocoder_type="here"):
    """Get weather forecast for a location"""
    # Set up cache and event
    cache_adapter = JSONFileCacheAdapter(cache_dir)
    event = get_event_dict()
    
    # Create location object
    loc_obj = Location(event, geocoder_api_key=api_key, geocoder_type=geocoder_type, cache_adapter=cache_adapter)
    error = loc_obj.set(location_name)
    if error:
        print(f"Error: {error}")
        return 1
    
    # Display location info
    format_location_info(loc_obj)
    
    # Parse when parameter
    now = datetime.now(tz=loc_obj.tz) + relativedelta(minute=0, second=0, microsecond=0)
    base = now + relativedelta(hour=6)
    stime = base
    hours = 12
    sname = ""
    
    when = when.lower()
    
    # Handle day-based periods
    if when == "tomorrow":
        stime += relativedelta(days=+1, hour=6)
        sname = "tomorrow"
    elif when == "today":
        stime += relativedelta(hour=6 if now.hour < 18 else 18)
        sname = "today" if stime.hour == 6 else "tonight"
    elif when == "tonight":
        stime += relativedelta(hour=18)
        hours = 12
        sname = "tonight"
    elif when in DAYS:
        d = ((DAYS.index(when) - stime.weekday()) % 7)
        stime += relativedelta(days=+d, hour=6)
        sname = DAYS[stime.weekday()]
    else:
        print(f"Unknown time period: {when}")
        return 1
    
    etime = stime + relativedelta(hours=hours)
    
    # Display period info
    print(f"Forecast Period:")
    print(f"  Period: {sname}")
    print(f"  Time Range: {stime.strftime('%a %I:%M %p')} - {etime.strftime('%a %I:%M %p %Z')}")
    print()
    
    # Get gridpoint data
    base_obj = Base(event, cache_adapter)
    gp = GridPoints(event, loc_obj.tz, loc_obj.cwa, loc_obj.grid_point, cache_adapter)
    
    if not gp.set_interval(stime, etime):
        print(f"Forecast information is unavailable for {sname}")
        return 1
    
    # Determine which metrics to display
    if metrics is None:
        metrics = ["summary", "temperature", "precipitation", "wind"]
    
    # Display forecast
    print(f"Forecast:")
    
    isday = base_obj.is_day(stime)
    
    for metric in metrics:
        if metric not in METRICS:
            continue
        
        metric_name = METRICS[metric][0]
        
        if metric_name == "summary":
            wt = gp.weather_text
            if wt:
                print(f"  Summary: {wt}")
        
        elif metric_name == "temperature":
            t = gp.temp_high if isday else gp.temp_low
            if t is not None:
                temp_type = "High" if isday else "Low"
                print(f"  Temperature: {temp_type} of {t}°F")
                
                wcl = gp.wind_chill_low
                wch = gp.wind_chill_high
                if wcl is not None:
                    if wcl == wch and wcl != t:
                        print(f"    Wind Chill: {wcl}°F")
                    elif wcl != wch:
                        print(f"    Wind Chill: {wcl}-{wch}°F")
                
                hil = gp.heat_index_low
                hih = gp.heat_index_high
                if hil is not None:
                    if hil == hih and hil != t:
                        print(f"    Heat Index: {hil}°F")
                    elif hil != hih:
                        print(f"    Heat Index: {hil}-{hih}°F")
        
        elif metric_name == "wind":
            wsh = gp.wind_speed_high
            wsl = gp.wind_speed_low
            wdi = gp.wind_direction_initial
            if wsh is None:
                print(f"  Wind: Calm")
            else:
                if wsh == wsl:
                    if wdi is None:
                        print(f"  Wind: {wsh} mph")
                    else:
                        print(f"  Wind: {wdi} at {wsh} mph")
                else:
                    if wdi is None:
                        print(f"  Wind: {wsl}-{wsh} mph")
                    else:
                        print(f"  Wind: {wdi} at {wsl}-{wsh} mph")
                wg = gp.wind_gust_high
                if wg is not None:
                    print(f"    Gusts: up to {wg} mph")
        
        elif metric_name == "precipitation":
            pch = gp.precip_chance_high
            if pch is not None:
                if pch == 0:
                    print(f"  Precipitation: None forecasted")
                else:
                    print(f"  Precipitation: {pch}% chance")
                    
                    pal = gp.precip_amount_low
                    pah = gp.precip_amount_high
                    
                    if pal is not None and pah is not None and pah[0] != 0:
                        if pal[1] == pah[1] or pal[0] < 0.1:
                            print(f"    Amount: {pah[1]} {pah[2]} possible")
                        else:
                            print(f"    Amount: {pal[1]} to {pah[1]} {pah[2]} possible")
                    
                    sal = gp.snow_amount_low
                    sah = gp.snow_amount_high
                    if sal is not None and sah is not None and sah[0] != 0:
                        if sal[1] == sah[1] or sal[0] < 0.1:
                            print(f"    Snowfall: {sah[1]} {sah[2]} possible")
                        else:
                            print(f"    Snowfall: {sal[1]} to {sah[1]} {sah[2]} possible")
        
        elif metric_name == "relative humidity":
            hh = gp.humidity_high
            if hh is not None:
                print(f"  Humidity: {hh}%")
        
        elif metric_name == "dewpoint":
            dh = gp.dewpoint_high
            if dh is not None:
                print(f"  Dewpoint: {dh}°F")
        
        elif metric_name == "barometric pressure":
            pl = gp.pressure_low
            if pl is not None:
                print(f"  Pressure: {pl} in")
        
        elif metric_name == "skys":
            si = gp.skys_initial
            sf = gp.skys_final
            if si is not None:
                if si == sf:
                    print(f"  Sky: {si}")
                elif si is None or sf is None:
                    print(f"  Sky: {si or sf}")
                else:
                    print(f"  Sky: {si} changing to {sf}")
    
    print()
    return 0


def get_alerts(location_name, cache_dir=".cache", api_key=None, geocoder_type="here"):
    """Get weather alerts for a location"""
    # Set up cache and event
    cache_adapter = JSONFileCacheAdapter(cache_dir)
    event = get_event_dict()
    
    # Create location object
    loc_obj = Location(event, geocoder_api_key=api_key, geocoder_type=geocoder_type, cache_adapter=cache_adapter)
    error = loc_obj.set(location_name)
    if error:
        print(f"Error: {error}")
        return 1
    
    # Display location info
    format_location_info(loc_obj)
    
    # Get alerts
    alerts = Alerts(event, loc_obj.countyZoneId, cache_adapter)
    
    if len(alerts) == 0:
        print(f"No alerts in effect for {loc_obj.city}, {loc_obj.state}")
        print()
        return 0
    
    # Display alerts
    print(f"Weather Alerts:")
    print(f"  {alerts.title}")
    print()
    
    for i, alert in enumerate(alerts, 1):
        print(f"  Alert {i}:")
        print(f"    Event: {alert.event}")
        print(f"    Area: {alert.area}")
        print(f"    Headline: {alert.headline}")
        if alert.description:
            # Limit description length for CLI display
            desc = alert.description[:500]
            if len(alert.description) > 500:
                desc += "..."
            print(f"    Description: {desc}")
        if alert.instruction:
            # Limit instruction length for CLI display
            instr = alert.instruction[:300]
            if len(alert.instruction) > 300:
                instr += "..."
            print(f"    Instructions: {instr}")
        print()
    
    return 0


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Clima Cast CLI - Local weather information from the National Weather Service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s current "Boulder, Colorado"
  %(prog)s current 80302 --metrics temperature wind
  %(prog)s forecast "Seattle, WA" --when tomorrow
  %(prog)s forecast "Miami, FL" --when saturday --metrics temperature precipitation
  %(prog)s alerts "New Orleans, LA"

Available metrics for current conditions:
  temperature, wind, relative humidity, dewpoint, barometric pressure

Available metrics for forecast:
  summary, temperature, wind, precipitation, relative humidity, dewpoint, 
  barometric pressure, skys

Available time periods for forecast:
  today, tonight, tomorrow, monday, tuesday, wednesday, thursday, friday, 
  saturday, sunday
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Current conditions command
    current_parser = subparsers.add_parser("current", help="Get current weather conditions")
    current_parser.add_argument("location", help="Location (city, state or zip code)")
    current_parser.add_argument("--metrics", nargs="+", help="Metrics to display")
    current_parser.add_argument("--cache-dir", default=".cache", help="Cache directory (default: .cache)")
    
    # Forecast command
    forecast_parser = subparsers.add_parser("forecast", help="Get weather forecast")
    forecast_parser.add_argument("location", help="Location (city, state or zip code)")
    forecast_parser.add_argument("--when", default="today", help="Time period (default: today)")
    forecast_parser.add_argument("--metrics", nargs="+", help="Metrics to display")
    forecast_parser.add_argument("--cache-dir", default=".cache", help="Cache directory (default: .cache)")
    
    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="Get weather alerts")
    alerts_parser.add_argument("location", help="Location (city, state or zip code)")
    alerts_parser.add_argument("--cache-dir", default=".cache", help="Cache directory (default: .cache)")
    
    args = parser.parse_args()
    
    # Check for command
    if not args.command:
        parser.print_help()
        return 1
    
    # Get geocoding API key from environment
    # Try HERE.com first, then fall back to MapQuest
    here_api_key = os.getenv("here_api_key")
    mapquest_api_key = os.getenv("mapquest_id")
    
    if here_api_key:
        api_key = here_api_key
        geocoder_type = "here"
    elif mapquest_api_key:
        api_key = mapquest_api_key
        geocoder_type = "mapquest"
        print("Warning: Using deprecated MapQuest API. Please switch to HERE.com by setting here_api_key environment variable.")
        print()
    else:
        print("Error: Geocoding API key not found.")
        print()
        print("Please set one of the following environment variables:")
        print("  - here_api_key (recommended): Get a free API key from https://developer.here.com/")
        print("  - mapquest_id (deprecated): MapQuest API key")
        print()
        print("Example:")
        print("  export here_api_key=YOUR_KEY_HERE")
        return 1
    
    # Execute command
    try:
        if args.command == "current":
            return get_current_conditions(
                args.location,
                metrics=args.metrics,
                cache_dir=args.cache_dir,
                api_key=api_key,
                geocoder_type=geocoder_type
            )
        elif args.command == "forecast":
            return get_forecast(
                args.location,
                when=args.when,
                metrics=args.metrics,
                cache_dir=args.cache_dir,
                api_key=api_key,
                geocoder_type=geocoder_type
            )
        elif args.command == "alerts":
            return get_alerts(
                args.location,
                cache_dir=args.cache_dir,
                api_key=api_key,
                geocoder_type=geocoder_type
            )
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
