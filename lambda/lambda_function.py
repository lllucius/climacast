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
Lambda function handler for Clima Cast Alexa Skill.

This module contains the ASK SDK request handlers that integrate with
the weather processing logic in processing.py.
"""

import json
import os

os.environ["AWS_REGION"] = os.getenv("AWS_REGION", "us-east-1")

# ASK SDK imports
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name

# Import weather processing classes from processing.py
from processing import (
    Base, User, Location, Observations, GridPoints, Alerts,
    METRICS, DAYS, QUARTERS, MONTH_DAYS, MONTH_NAMES, SETTINGS,
    notify, SLOTS
)

# Conditionally import DynamoDB adapter only if we're in Lambda mode
PERSISTENCE_REGION = os.environ.get('DYNAMODB_PERSISTENCE_REGION')
PERSISTENCE_TABLE_NAME = os.environ.get('DYNAMODB_PERSISTENCE_TABLE_NAME')

if PERSISTENCE_REGION and PERSISTENCE_TABLE_NAME:
    from ask_sdk_dynamodb.adapter import DynamoDbAdapter
    from boto3 import resource

# Only initialize DynamoDB resources if we're running in Lambda
# (indicated by both env vars being set)
if PERSISTENCE_REGION and PERSISTENCE_TABLE_NAME:
    print("REGION", PERSISTENCE_REGION, PERSISTENCE_TABLE_NAME)
    ddb_resource = resource('dynamodb', region_name=PERSISTENCE_REGION)
    ddb_adapter = DynamoDbAdapter(
        table_name=PERSISTENCE_TABLE_NAME,
        create_table=False,
        dynamodb_resource=ddb_resource
    )
else:
    print("DynamoDB not configured - running in CLI mode")
    ddb_resource = None
    ddb_adapter = None

# =============================================================================
# ASK SDK Request Handlers
# =============================================================================

class BaseIntentHandler(AbstractRequestHandler):
    """Base class for intent handlers with common weather functionality"""

    def __init__(self):
        super().__init__()

    def get_cache_adapter(self, handler_input):
        """Get a cache adapter for the handler"""
        # Import here to avoid circular dependency
        from cache_adapter import DynamoDBCacheAdapter
        
        if ddb_resource is None:
            raise RuntimeError("DynamoDB not configured. Cannot create cache adapter.")
        
        attributes_manager = handler_input.attributes_manager
        return DynamoDBCacheAdapter(ddb_resource, PERSISTENCE_TABLE_NAME, attributes_manager)

    def get_user_and_location(self, handler_input):
        """Get user profile and location from handler_input"""
        # type: (HandlerInput) -> tuple
        session = handler_input.request_envelope.session
        user_id = session.user.user_id

        # Build event for legacy code compatibility
        event = {
            "session": {
                "new": session.new,
                "sessionId": session.session_id,
                "application": {
                    "applicationId": session.application.application_id
                },
                "attributes": session.attributes or {},
                "user": {
                    "userId": user_id
                }
            },
            "request": {}
        }

        # Get attributes manager for persistence
        attributes_manager = handler_input.attributes_manager
        cache_adapter = self.get_cache_adapter(handler_input)

        # Load user profile
        user = User(event, user_id, attributes_manager, cache_adapter)

        # Try to load default location
        loc = None
        if user.location:
            location_obj = Location(event, attributes_manager, cache_adapter)
            text = location_obj.set(user.location)
            if text is None:
                loc = location_obj

        return user, loc, event

    def get_slot_values(self, handler_input):
        """Extract slot values from intent"""
        # type: (HandlerInput) -> dict
        slots = {}
        request = handler_input.request_envelope.request
        if hasattr(request, 'intent') and request.intent.slots:
            for slot_name, slot in request.intent.slots.items():
                if slot.value:
                    slots[slot_name] = slot.value.strip().lower()
                else:
                    slots[slot_name] = None
        return slots

    def respond(self, handler_input, user, text, end=None):
        """Build response with proper formatting"""
        # type: (HandlerInput, User, str, bool) -> Response
        session = handler_input.request_envelope.session
        new = session.new
        if end is None:
            end = new

        response_builder = handler_input.response_builder

        # Add reprompt if session should continue
        prompt = None
        if not end:
            prompt = "For %s, say help, " % ("more examples" if new else "example requests") + \
                     "To interrupt speaking, say Alexa, cancel, " + \
                     "If you are done, say stop."
            text += ". " if text.strip()[-1] != "." else " "
            text += prompt if new else "if you are done, say stop."

        # Format with user's rate and pitch
        ssml = '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
               (user.rate, user.pitch - 100, text)

        response_builder.speak(ssml)

        if not end and prompt:
            prompt_ssml = '<speak><prosody rate="%d%%" pitch="%+d%%">%s</prosody></speak>' % \
                          (user.rate, user.pitch - 100, prompt)
            response_builder.ask(prompt_ssml)

        response_builder.set_should_end_session(end)
        return response_builder.response

    def get_location_from_slots(self, handler_input, event, loc, slots, req=False):
        """Process location from slot values"""
        location_name = slots.get("location") or slots.get("zipcode")

        if location_name:
            attributes_manager = handler_input.attributes_manager
            cache_adapter = self.get_cache_adapter(handler_input)
            location_obj = Location(event, attributes_manager, cache_adapter)
            text = location_obj.set(location_name, loc)
            if text is None:
                return location_obj, None
            return None, text
        elif req:
            return None, "You must include the location"
        elif loc is None:
            return None, """You must set a default location by using phrases like:
                       Alexa, ask Clima Cast to set my location to Boulder Colorado.
                   or:
                       Alexa, ask Clima Cast to set my location to zip code 5 5 1 1 8.
                   """
        return loc, None

    def parse_when(self, loc, slots):
        """Parse time/date information from slots"""
        # type: (Location, dict) -> tuple
        has_when = (slots.get("when_abs") or slots.get("when_any") or
                    slots.get("when_pos") or slots.get("day") or slots.get("month")) is not None

        now = datetime.now(tz=loc.tz) + relativedelta(minute=0, second=0, microsecond=0)
        base = now + relativedelta(hour=6)
        stime = base
        hours = 12
        sname = ""

        # Handle the days like Monday or Today
        day = slots.get("when_abs") or slots.get("when_any") or slots.get("when_pos")
        if day:
            day = re.sub(r"'*s$", "", day).replace("over night", "overnight").split()

            if len(day) > 1:
                if day[0] == "overnight":
                    day = [day[1], "overnight"]
                elif day[0] == "this":
                    day = [day[1]]

            if day[0] == "tomorrow":
                stime += relativedelta(days=+1, hour=6)
            elif day[0] in DAYS:
                d = ((DAYS.index(day[0]) - stime.weekday()) % 7)
                stime += relativedelta(days=+d, hour=6)

            sname = DAYS[stime.weekday()]
            is_today = stime == base

            specs = {"today":     [0, 6,  12, ""],
                     "tonight":   [0, 18, 12, " night"],
                     "night":     [0, 18, 12, " night"],
                     "overnight": [1, 0,  6,  " overnight"],
                     "morning":   [0, 6,  6,  " morning"],
                     "afternoon": [0, 12, 6,  " afternoon"],
                     "evening":   [0, 18, 6,  " evening"]}

            if day[-1] in specs:
                spec = specs[day[-1]]
                stime += relativedelta(days=spec[0], hour=spec[1])
                hours = spec[2]
                sname += spec[3]

            if is_today:
                day = sname.split()
                if hours == 6:
                    sname = "overnight" if day[1] == "overnight" else "this " + day[1]
                else:
                    sname = "tonight" if stime.hour == 18 else "today"

        elif slots.get("day") is not None:
            month = stime.month
            day = stime.day

            d = slots.get("day")
            if d.isdigit() and 1 <= int(d) <= 31:
                d = MONTH_DAYS[int(d) - 1]
            elif d in MONTH_DAYS_XLATE:
                d = MONTH_DAYS_XLATE[d]

            if d in MONTH_DAYS:
                day = MONTH_DAYS.index(d) + 1

                if slots.get("month") is not None:
                    m = slots.get("month")
                    if m in MONTH_NAMES:
                        month = MONTH_NAMES.index(m) + 1

            # Adjust the date relative to today
            if month == stime.month and day == stime.day:
                pass
            elif month == stime.month and day < stime.day:
                if slots.get("month"):
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

        etime = stime + relativedelta(hours=hours)
        quarters = hours // 6

        return has_when, stime, etime, sname, quarters

    def get_alerts(self, handler_input, event, loc):
        """Get weather alerts for location"""
        attributes_manager = handler_input.attributes_manager
        cache_adapter = self.get_cache_adapter(handler_input)
        alerts = Alerts(event, loc.countyZoneId, attributes_manager, cache_adapter)
        if len(alerts) == 0:
            return "No alerts in effect at this time for %s." % loc.city

        text = alerts.title + "...\n"
        for alert in alerts:
            text += alert.headline + "...\n"
            text += "for " + alert.area + "...\n"
            text += alert.description + "...\n"
            text += alert.instruction + "...\n"

        return text

    def get_current(self, handler_input, event, user, loc, metrics):
        """Get current weather conditions"""
        text = ""

        # Retrieve the current observations from the nearest station
        attributes_manager = handler_input.attributes_manager
        cache_adapter = self.get_cache_adapter(handler_input)
        obs = Observations(event, loc.observationStations, attributes_manager=attributes_manager, cache_adapter=cache_adapter)
        if obs.is_good:
            text += "At %s, %s reported %s, " % \
                    (obs.time_reported.astimezone(loc.tz).strftime("%I:%M%p"),
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
                                    (obs.wind_direction, obs.wind_speed)
                        else:
                            text += "Winds are out of the %s at %s miles per hour" % \
                                    (obs.wind_direction, obs.wind_speed)

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

        return text

    def get_extended(self, handler_input, event, loc):
        """Get extended forecast"""
        # Import normalize from Base class
        attributes_manager = handler_input.attributes_manager
        cache_adapter = self.get_cache_adapter(handler_input)
        base = Base(event, attributes_manager, cache_adapter)

        data = base.https("points/%s/forecast" % loc.coords)
        if data is None or data.get("periods", None) is None:
            notify(event, "Extended forecast missing periods", data)
            return "the extended forecast is currently unavailable."

        text = ""
        for period in data.get("periods", {}):
            text += " " + period["name"] + ", " + period["detailedForecast"]
            if text.lower().find("wind") < 0:
                wind = period["windSpeed"]
                if wind.lower().find("to") < 0:
                    wind = "around " + wind
                text += ". %s wind %s" % (base.dir_to_dir(period["windDirection"]), wind)
            text + "."

        header = "The extended forecast for the %s zone " % loc.forecastZoneName
        if not text:
            header += "is unavailable"

        return base.normalize(header + text)

    def get_forecast(self, handler_input, event, user, loc, stime, etime, sname, metrics):
        """Get weather forecast"""
        # Import normalize from Base class
        attributes_manager = handler_input.attributes_manager
        cache_adapter = self.get_cache_adapter(handler_input)
        base = Base(event, attributes_manager, cache_adapter)

        fulltext = ""
        gp = GridPoints(event, loc.tz, loc.cwa, loc.grid_point, attributes_manager, cache_adapter)

        for metric in metrics:
            metric = METRICS[metric][0]

            if not gp.set_interval(stime, etime):
                text = "Forecast information is unavailable for %s %s" % \
                       (MONTH_NAMES[stime.month - 1], MONTH_DAYS[stime.day - 1])
                return text

            isday = base.is_day(stime)
            text = ""

            if metric == "wind":
                wsh = gp.wind_speed_high
                wsl = gp.wind_speed_low
                wdi = gp.wind_direction_initial
                if wsh is None:
                    text = "winds will be calm"
                else:
                    if wsh == wsl:
                        if wdi is None:
                            text = "winds will be %s miles per hour" % wsh
                        else:
                            text = "winds will be out of the %s at %s miles per hour" % (wdi, wsh)
                    else:
                        if wdi is None:
                            text = "winds will be %s to %s miles per hour" % (wsl, wsh)
                        else:
                            text = "winds will be out of the %s at %s to %s miles per hour" % (wdi, wsl, wsh)
                    wg = gp.wind_gust_high
                    if wg is not None:
                        text += ", with gusts as high as %s" % wg

            elif metric == "temperature":
                t = gp.temp_high if isday else gp.temp_low
                if t is not None:
                    text = "the %s temperature will be %s degrees" % ("high" if isday else "low", t)

                    wcl = gp.wind_chill_low
                    wch = gp.wind_chill_high
                    if wcl is not None:
                        if wcl == wch and wcl != t:
                            text += ", with a wind chill of %s degrees" % wcl
                        elif wcl != wch:
                            text += ", with a wind chill of %s to %s degrees" % (wcl, wch)

                    hil = gp.heat_index_low
                    hih = gp.heat_index_high
                    if hil is not None:
                        if hil == hih and hil != t:
                            text += ", with a heat index of %s degrees" % hil
                        elif hil != hih:
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
                    elif si is None or sf is None:
                        text = "it will be %s" % (si or sf)
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
            fulltext = "%s in %s, %s" % (sname, loc.city, fulltext)
        else:
            fulltext = "Forecast information is unavailable for %s in %s" % (sname, loc.city)

        return fulltext


class LaunchRequestHandler(BaseIntentHandler):
    """Handler for Launch Request"""
    def can_handle(self, handler_input):
        print("+#+##+#+#+#+#")
        # type: (HandlerInput) -> bool
        return is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, _ = self.get_user_and_location(handler_input)

        text = "Welcome to Clime a Cast. " \
               "For current conditions, use phrases like: What's the weather. "\
               "For forecasts, try phrases like: What's the forecast."
        if loc is None:
            text += "You must set your default location by saying something like: " \
                    "set location to Miami Florida."

        return self.respond(handler_input, user, text, end=False)

# Session Ended Request Handler


class SessionEndedRequestHandler(BaseIntentHandler):
    """Handler for Session Ended Request"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        request = handler_input.request_envelope.request

        # Build event for notify
        session = handler_input.request_envelope.session
        event = {
            "session": {
                "sessionId": session.session_id,
                "user": {"userId": session.user.user_id}
            },
            "request": {
                "type": "SessionEndedRequest",
                "reason": str(getattr(request, 'reason', 'USER_INITIATED'))
            }
        }

        if hasattr(request, 'error') and request.error:
            event["request"]["error"] = {
                "message": request.error.message
            }
            notify(event, "Error detected", request.error.message)
        else:
            notify(event, "Session Ended", event["request"]["reason"])

        return handler_input.response_builder.response

# Help Intent Handler


class HelpIntentHandler(BaseIntentHandler):
    """Handler for Help Intent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        text = """
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
        return self.respond(handler_input, user, text)

# Cancel and Stop Intent Handler


class CancelAndStopIntentHandler(BaseIntentHandler):
    """Handler for Cancel and Stop Intent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        text = "Thank you for using Clime a Cast."
        return self.respond(handler_input, user, text, end=True)

# Fallback, Yes, No, and StartOver Intent Handler (basic responses)


class FallbackIntentHandler(BaseIntentHandler):
    """Handler for Fallback, Yes, No, and StartOver intents"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.FallbackIntent")(handler_input) or
                is_intent_name("AMAZON.YesIntent")(handler_input) or
                is_intent_name("AMAZON.NoIntent")(handler_input) or
                is_intent_name("AMAZON.StartOverIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        # For now, these all return to help
        text = "I didn't understand that. " \
               "You can ask for current conditions, forecasts, or alerts. " \
               "Say help for more information."
        return self.respond(handler_input, user, text, end=False)

# Metric Intent Handlers


class MetricIntentHandler(BaseIntentHandler):
    """Handler for MetricIntent and MetricPosIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("MetricIntent")(handler_input) or
                is_intent_name("MetricPosIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, event = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        # Check if location is required
        if loc is None:
            text = """You must set a default location by using phrases like:
                       Alexa, ask Clima Cast to set my location to Boulder Colorado.
                   or:
                       Alexa, ask Clima Cast to set my location to zip code 5 5 1 1 8.
                   """
            return self.respond(handler_input, user, text)

        # Get metric from slots
        metric = slots.get("metric")
        if metric is None:
            return self.respond(handler_input, user, "You must include a metric like temperature, humidity or wind")

        # Handle special metrics
        if metric == "alerts":
            text = self.get_alerts(handler_input, event, loc)
            # Normalize text
            attributes_manager = handler_input.attributes_manager
            cache_adapter = self.get_cache_adapter(handler_input)
            base = Base(event, attributes_manager, cache_adapter)
            return self.respond(handler_input, user, base.normalize(text))

        if metric == "extended forecast":
            text = self.get_extended(handler_input, event, loc)
            return self.respond(handler_input, user, text)

        if metric not in METRICS:
            return self.respond(handler_input, user, "%s is an unrecognized metric." % metric)

        # Determine which metrics to report
        metrics = user.metrics if METRICS[metric][0] == "all" else [METRICS[metric][0]]

        # Parse when information
        has_when, stime, etime, sname, _ = self.parse_when(loc, slots)

        # Determine if this is a forecast or current conditions request
        leadin = slots.get("leadin") or ""
        is_forecast = (metric == "forecast" or has_when or
                       "chance" in metric or "will" in leadin or "going" in leadin)

        if is_forecast:
            text = self.get_forecast(handler_input, event, user, loc, stime, etime, sname, metrics)
        else:
            text = self.get_current(handler_input, event, user, loc, metrics)
            # Normalize text
            attributes_manager = handler_input.attributes_manager
            cache_adapter = self.get_cache_adapter(handler_input)
            base = Base(event, attributes_manager, cache_adapter)
            text = base.normalize(text)

        return self.respond(handler_input, user, text)

# Settings Intent Handlers


class GetSettingIntentHandler(BaseIntentHandler):
    """Handler for GetSettingIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetSettingIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        if loc is None:
            text = "You must set a default location first."
            return self.respond(handler_input, user, text)

        setting = slots.get("setting")
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
            return self.respond(handler_input, user, "Unrecognized setting: %s" % setting)

        text = ""
        for setting in settings:
            if text != "":
                text += ", "
                if setting == settings[-1]:
                    text += "and "
            if setting == "location":
                text += "the location is set to %s." % loc.spoken_name()
            elif setting == "pitch":
                text += "the voice pitch is set to %d percent." % user.pitch
            elif setting == "rate":
                text += "the voice rate is set to %d percent." % user.rate
            elif setting == "forecast":
                text += "the custom forecast will include the %s." % \
                        ", ".join(list(user.metrics[:-1])) + " and " + user.metrics[-1]

        return self.respond(handler_input, user, text)


class SetPitchIntentHandler(BaseIntentHandler):
    """Handler for SetPitchIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("SetPitchIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        percent = slots.get("percent")
        if percent and percent.isdigit():
            pitch = int(percent)
            if 130 >= pitch >= 70:
                user.pitch = pitch
                text = "Voice pitch has been set to %d percent." % pitch
            else:
                text = "The pitch must be between 70 and 130 percent"
        else:
            text = "Expected a percentage when setting the pitch"

        return self.respond(handler_input, user, text)


class SetRateIntentHandler(BaseIntentHandler):
    """Handler for SetRateIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("SetRateIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        percent = slots.get("percent")
        if percent and percent.isdigit():
            rate = int(percent)
            if 150 >= rate >= 50:
                user.rate = rate
                text = "Voice rate has been set to %d percent." % rate
            else:
                text = "The rate must be between 50 and 150 percent"
        else:
            text = "Expected a percentage when setting the rate"

        return self.respond(handler_input, user, text)


class SetLocationIntentHandler(BaseIntentHandler):
    """Handler for SetLocationIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("SetLocationIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, loc, event = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        location_name = slots.get("location") or slots.get("zipcode")
        if not location_name:
            text = "You must include the location"
            return self.respond(handler_input, user, text)

        attributes_manager = handler_input.attributes_manager
        cache_adapter = self.get_cache_adapter(handler_input)
        location_obj = Location(event, attributes_manager, cache_adapter)
        text = location_obj.set(location_name, loc)
        if text is None:
            user.location = location_obj.name
            text = "Your default location has been set to %s." % location_obj.spoken_name()

        return self.respond(handler_input, user, text)

# Custom Forecast Intent Handlers


class GetCustomIntentHandler(BaseIntentHandler):
    """Handler for GetCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        text = "The custom forecast will include the %s." % \
               ", ".join(list(user.metrics[:-1])) + " and " + user.metrics[-1]
        return self.respond(handler_input, user, text)


class AddCustomIntentHandler(BaseIntentHandler):
    """Handler for AddCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("AddCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        metric = slots.get("metric")
        if metric is None:
            text = "You must include a metric like temperature, humidity or wind."
            return self.respond(handler_input, user, text)

        if metric not in METRICS:
            text = "%s is an unrecognized metric." % metric
            return self.respond(handler_input, user, text)

        metric_info = METRICS[metric]
        if not metric_info[1]:
            text = "%s can't be used when customizing the forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        if user.has_metric(metric_info[0]):
            text = "%s is already included in the custom forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        user.add_metric(metric_info[0])
        text = "%s has been added to the custom forecast." % metric_info[0]
        return self.respond(handler_input, user, text)


class RemoveCustomIntentHandler(BaseIntentHandler):
    """Handler for RemCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RemCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        slots = self.get_slot_values(handler_input)

        metric = slots.get("metric")
        if metric is None:
            text = "You must include a metric like temperature, humidity or wind."
            return self.respond(handler_input, user, text)

        if metric not in METRICS:
            text = "%s is an unrecognized metric." % metric
            return self.respond(handler_input, user, text)

        metric_info = METRICS[metric]
        if not metric_info[1]:
            text = "%s can't be used when customizing the forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        if not user.has_metric(metric_info[0]):
            text = "%s is already excluded from the custom forecast." % metric_info[0]
            return self.respond(handler_input, user, text)

        user.remove_metric(metric_info[0])
        text = "%s has been removed from the custom forecast." % metric_info[0]
        return self.respond(handler_input, user, text)


class ResetCustomIntentHandler(BaseIntentHandler):
    """Handler for RstCustomIntent"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("RstCustomIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)

        user.reset_metrics()
        text = "the custom forecast has been reset to defaults."
        return self.respond(handler_input, user, text)


class StoreDataIntentHandler(BaseIntentHandler):
    """Handler for StoreDataIntent - saves persistent attributes"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("StoreDataIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, _ = self.get_user_and_location(handler_input)
        
        # Save persistent attributes to DynamoDB
        attributes_manager = handler_input.attributes_manager
        attributes_manager.save_persistent_attributes()
        
        text = "Data has been saved successfully."
        return self.respond(handler_input, user, text, end=True)


class GetDataIntentHandler(BaseIntentHandler):
    """Handler for GetDataIntent - loads persistent attributes"""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_intent_name("GetDataIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        user, _, event = self.get_user_and_location(handler_input)
        
        # Load persistent attributes from DynamoDB
        attributes_manager = handler_input.attributes_manager
        
        # Get shared caches directly from DynamoDB
        table = ddb_resource.Table(PERSISTENCE_TABLE_NAME)
        try:
            response = table.get_item(Key={"id": "SHARED_CACHE"})
            if "Item" in response:
                shared_attrs = response["Item"].get("attributes", {})
            else:
                shared_attrs = {}
        except Exception:
            shared_attrs = {}
        
        location_count = len(shared_attrs.get("LocationCache", {}))
        station_count = len(shared_attrs.get("StationCache", {}))
        zone_count = len(shared_attrs.get("ZoneCache", {}))
        
        # Get user cache directly from persistent attributes
        user_attrs = attributes_manager.persistent_attributes
        user_count = len(user_attrs.get("UserCache", {}))
        
        text = f"Data has been loaded. LocationCache has {location_count} items, " \
               f"StationCache has {station_count} items, " \
               f"ZoneCache has {zone_count} items, " \
               f"and UserCache has {user_count} items."
        
        return self.respond(handler_input, user, text, end=True)


class SkillExceptionHandler(AbstractExceptionHandler):
    """Handle exceptions"""
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        import traceback
        event = {
            "session": {
                "sessionId": handler_input.request_envelope.session.session_id,
                "user": {"userId": handler_input.request_envelope.session.user.user_id}
            }
        }
        notify(event, "ASK SDK Exception", traceback.format_exc())

        speech_text = '<say-as interpret-as="interjection">aw man</say-as>' + \
                     '<prosody pitch="+25%">' + \
                     "Clima Cast has experienced an error. The author has been " + \
                     "notified and will address it as soon as possible. Until then " + \
                     "you might be able to rephrase your request to get around the issue." + \
                     '</prosody>'

        return handler_input.response_builder.speak(
            f"<speak>{speech_text}</speak>"
        ).set_should_end_session(True).response



# Only create skill builder if DynamoDB is configured (Lambda mode)
if ddb_adapter is not None:
    sb = CustomSkillBuilder(persistence_adapter=ddb_adapter)

    # Register individual intent handlers
    # Order matters - more specific handlers should be registered first
    sb.add_request_handler(LaunchRequestHandler())
    sb.add_request_handler(SessionEndedRequestHandler())
    sb.add_request_handler(HelpIntentHandler())
    sb.add_request_handler(CancelAndStopIntentHandler())
    sb.add_request_handler(MetricIntentHandler())
    sb.add_request_handler(GetSettingIntentHandler())
    sb.add_request_handler(SetPitchIntentHandler())
    sb.add_request_handler(SetRateIntentHandler())
    sb.add_request_handler(SetLocationIntentHandler())
    sb.add_request_handler(GetCustomIntentHandler())
    sb.add_request_handler(AddCustomIntentHandler())
    sb.add_request_handler(RemoveCustomIntentHandler())
    sb.add_request_handler(ResetCustomIntentHandler())
    sb.add_request_handler(StoreDataIntentHandler())
    sb.add_request_handler(GetDataIntentHandler())
    sb.add_request_handler(FallbackIntentHandler())

    # Add exception handler
    sb.add_exception_handler(SkillExceptionHandler())

    # Create lambda handler from SkillBuilder
    _skill_lambda_handler = sb.lambda_handler()


    # AWS Lambda handler entry point
    def lambda_handler(event, context):
        """Main Lambda handler that routes requests to ASK SDK"""
        print("EVENT", event)
        return _skill_lambda_handler(event, context)
else:
    # Running in CLI mode - skill builder not needed
    sb = None
    _skill_lambda_handler = None
    
    def lambda_handler(event, context):
        """Stub lambda handler when not in Lambda mode"""
        raise RuntimeError("Lambda handler cannot be called in CLI mode")

