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
Command-line interface for testing Clima Cast weather processing.

This CLI allows you to test the weather processing logic locally without
needing to deploy to AWS Lambda or use the Alexa service.
"""

import argparse
import os
import sys
from datetime import datetime
from dateutil import tz
from dateutil.relativedelta import relativedelta

# Add current directory to path to import weather_processor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weather_processor import (
    Base, GridPoints, Observations, Alerts, Location, User,
    METRICS, DAYS, MONTH_NAMES, MONTH_DAYS
)


def create_test_event(user_id="cli_test_user"):
    """Create a minimal event structure for testing"""
    return {
        "session": {
            "new": True,
            "sessionId": "cli-session",
            "application": {
                "applicationId": os.environ.get("app_id", "amzn1.ask.skill.test")
            },
            "attributes": {},
            "user": {
                "userId": user_id
            },
            "testing": True  # Flag to prevent SNS notifications
        },
        "request": {
            "type": "IntentRequest",
            "requestId": "cli-request",
            "timestamp": datetime.now().isoformat()
        }
    }


def get_current_conditions(location_name, metrics=None):
    """Get current weather conditions for a location"""
    event = create_test_event()
    
    # Set up location
    loc = Location(event)
    error = loc.set(location_name)
    if error:
        print(f"Error: {error}")
        return
    
    print(f"\nCurrent conditions for {loc.spoken_name()}:")
    print(f"  Location: {loc.city}, {loc.state}")
    print(f"  Coordinates: {loc.coords}")
    print()
    
    # Get observations
    obs = Observations(event, loc.observationStations)
    if not obs.is_good:
        print("  Observation data is currently unavailable.")
        return
    
    # Default metrics if none specified
    if metrics is None:
        metrics = ["temperature", "wind", "relative humidity", "barometric pressure"]
    
    print(f"  Station: {obs.station_name}")
    print(f"  Reported: {obs.time_reported.astimezone(loc.tz).strftime('%I:%M %p %Z')}")
    print(f"  Conditions: {obs.description}")
    print()
    
    for metric in metrics:
        if metric == "temperature":
            if obs.temp:
                print(f"  Temperature: {obs.temp}°F")
                if obs.wind_chill:
                    print(f"    Wind Chill: {obs.wind_chill}°F")
                elif obs.heat_index:
                    print(f"    Heat Index: {obs.heat_index}°F")
        elif metric == "wind":
            if obs.wind_speed and obs.wind_speed != "0":
                if obs.wind_direction:
                    print(f"  Wind: {obs.wind_direction} at {obs.wind_speed} mph")
                else:
                    print(f"  Wind: {obs.wind_speed} mph")
                if obs.wind_gust:
                    print(f"    Gusts: {obs.wind_gust} mph")
            else:
                print(f"  Wind: Calm")
        elif metric == "relative humidity":
            if obs.humidity:
                print(f"  Humidity: {obs.humidity}%")
        elif metric == "dewpoint":
            if obs.dewpoint:
                print(f"  Dewpoint: {obs.dewpoint}°F")
        elif metric == "barometric pressure":
            if obs.pressure:
                trend = obs.pressure_trend
                trend_str = f" ({trend})" if trend else ""
                print(f"  Pressure: {obs.pressure} in{trend_str}")


def get_forecast(location_name, when="today", metrics=None):
    """Get weather forecast for a location"""
    event = create_test_event()
    
    # Set up location
    loc = Location(event)
    error = loc.set(location_name)
    if error:
        print(f"Error: {error}")
        return
    
    print(f"\nForecast for {loc.spoken_name()}:")
    print(f"  Location: {loc.city}, {loc.state}")
    print()
    
    # Parse when
    now = datetime.now(tz=loc.tz) + relativedelta(minute=0, second=0, microsecond=0)
    base = now + relativedelta(hour=6)
    stime = base
    hours = 12
    sname = when
    
    when_lower = when.lower()
    if when_lower == "today":
        stime = base if now.hour < 18 else base + relativedelta(hour=18)
        hours = 12
        sname = "today" if stime.hour == 6 else "tonight"
    elif when_lower == "tonight":
        stime = base + relativedelta(hour=18)
        hours = 12
        sname = "tonight"
    elif when_lower == "tomorrow":
        stime = base + relativedelta(days=+1, hour=6)
        hours = 12
        sname = "tomorrow"
    elif when_lower in DAYS:
        d = ((DAYS.index(when_lower) - stime.weekday()) % 7)
        stime = base + relativedelta(days=+d, hour=6)
        hours = 12
        sname = DAYS[stime.weekday()]
    
    etime = stime + relativedelta(hours=hours)
    
    print(f"  Period: {sname}")
    print(f"  Time range: {stime.strftime('%a %I:%M %p')} - {etime.strftime('%a %I:%M %p %Z')}")
    print()
    
    # Default metrics if none specified
    if metrics is None:
        metrics = ["summary", "temperature", "wind", "precipitation"]
    
    # Get gridpoint data
    gp = GridPoints(event, loc.tz, loc.cwa, loc.grid_point)
    if not gp.set_interval(stime, etime):
        print(f"  Forecast information is unavailable for {sname}")
        return
    
    isday = 6 <= stime.hour < 18
    
    for metric in metrics:
        metric_name = METRICS.get(metric, [metric])[0]
        
        if metric_name == "summary":
            wt = gp.weather_text
            if wt:
                print(f"  Summary: {wt}")
        elif metric_name == "temperature":
            t = gp.temp_high if isday else gp.temp_low
            if t:
                print(f"  Temperature: {'High' if isday else 'Low'} of {t}°F")
                wcl = gp.wind_chill_low
                wch = gp.wind_chill_high
                if wcl:
                    if wcl == wch:
                        print(f"    Wind Chill: {wcl}°F")
                    else:
                        print(f"    Wind Chill: {wcl}-{wch}°F")
                hil = gp.heat_index_low
                hih = gp.heat_index_high
                if hil:
                    if hil == hih:
                        print(f"    Heat Index: {hil}°F")
                    else:
                        print(f"    Heat Index: {hil}-{hih}°F")
        elif metric_name == "wind":
            wsh = gp.wind_speed_high
            wsl = gp.wind_speed_low
            wdi = gp.wind_direction_initial
            if wsh:
                if wsh == wsl:
                    print(f"  Wind: {wdi or 'Variable'} at {wsh} mph")
                else:
                    print(f"  Wind: {wdi or 'Variable'} at {wsl}-{wsh} mph")
                wg = gp.wind_gust_high
                if wg:
                    print(f"    Gusts: up to {wg} mph")
            else:
                print(f"  Wind: Calm")
        elif metric_name == "precipitation":
            pch = gp.precip_chance_high
            if pch is not None:
                if pch == 0:
                    print(f"  Precipitation: None expected")
                else:
                    print(f"  Precipitation: {pch}% chance")
                    pal = gp.precip_amount_low
                    pah = gp.precip_amount_high
                    if pah and pah[0] != 0:
                        if pal and pal[1] == pah[1]:
                            print(f"    Amount: {pah[1]} {pah[2]}")
                        elif pal:
                            print(f"    Amount: {pal[1]} to {pah[1]} {pah[2]}")
        elif metric_name == "relative humidity":
            hh = gp.humidity_high
            if hh:
                print(f"  Humidity: up to {hh}%")
        elif metric_name == "barometric pressure":
            pl = gp.pressure_low
            if pl:
                print(f"  Pressure: {pl} in")
        elif metric_name == "dewpoint":
            dh = gp.dewpoint_high
            if dh:
                print(f"  Dewpoint: {dh}°F")
        elif metric_name == "skys":
            si = gp.skys_initial
            sf = gp.skys_final
            if si:
                if si == sf:
                    print(f"  Sky: {si}")
                else:
                    print(f"  Sky: {si} changing to {sf}")


def get_alerts(location_name):
    """Get weather alerts for a location"""
    event = create_test_event()
    
    # Set up location
    loc = Location(event)
    error = loc.set(location_name)
    if error:
        print(f"Error: {error}")
        return
    
    print(f"\nWeather alerts for {loc.spoken_name()}:")
    print(f"  Location: {loc.city}, {loc.state}")
    print(f"  Zone: {loc.countyZoneName}")
    print()
    
    # Get alerts
    alerts = Alerts(event, loc.countyZoneId)
    if len(alerts) == 0:
        print("  No alerts in effect at this time.")
        return
    
    print(f"  {alerts.title}")
    print()
    
    for i, alert in enumerate(alerts, 1):
        print(f"  Alert {i}:")
        print(f"    Event: {alert.event}")
        print(f"    Area: {alert.area}")
        print(f"    Headline: {alert.headline}")
        print()


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Clima Cast weather CLI - Test weather processing locally",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get current conditions
  %(prog)s current "Boulder, Colorado"
  %(prog)s current 80302

  # Get forecast
  %(prog)s forecast "Seattle, Washington"
  %(prog)s forecast "Miami, FL" --when tomorrow
  %(prog)s forecast 10001 --when friday

  # Get alerts
  %(prog)s alerts "New Orleans, Louisiana"

  # Specify metrics
  %(prog)s current "Chicago, IL" --metrics temperature wind
  %(prog)s forecast "Portland, OR" --metrics temperature precipitation

Environment variables:
  mapquest_id    MapQuest API key (required)
  app_id         Application ID (optional)
        """
    )
    
    parser.add_argument(
        "command",
        choices=["current", "forecast", "alerts"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "location",
        help="Location (city, state or zip code)"
    )
    
    parser.add_argument(
        "--when",
        default="today",
        help="Time period for forecast (today, tonight, tomorrow, monday, etc.)"
    )
    
    parser.add_argument(
        "--metrics",
        nargs="+",
        help="Specific metrics to display (temperature, wind, precipitation, etc.)"
    )
    
    args = parser.parse_args()
    
    # Check for required environment variables
    if not os.environ.get("mapquest_id"):
        print("Error: mapquest_id environment variable is required", file=sys.stderr)
        print("Set it with: export mapquest_id=YOUR_KEY", file=sys.stderr)
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == "current":
            get_current_conditions(args.location, args.metrics)
        elif args.command == "forecast":
            get_forecast(args.location, args.when, args.metrics)
        elif args.command == "alerts":
            get_alerts(args.location)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
