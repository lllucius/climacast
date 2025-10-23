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
Alerts classes for handling weather alerts from NWS API.

This module provides classes for processing weather alerts and warnings
from the National Weather Service.
"""

from weather.base import WeatherBase


class Alerts(WeatherBase):
    """
    Handles weather alerts for a specific zone.
    
    This class retrieves and processes active weather alerts, watches,
    and warnings from the National Weather Service.
    """
    
    def __init__(self, event, zone, cache_handler=None):
        """
        Initialize Alerts for a specific zone.
        
        Args:
            event: Event dictionary
            zone: Zone identifier
            cache_handler: Optional cache handler
        """
        super().__init__(event, cache_handler)
        data = self.https("alerts/active/zone/%s" % zone)
        self.data = data.get("features", []) if data else []


class Alert(WeatherBase):
    """
    Represents a single weather alert.
    
    This class processes individual alert data including event type,
    severity, urgency, and descriptive text.
    """
    
    def __init__(self, event, data, cache_handler=None):
        """
        Initialize Alert with alert data.
        
        Args:
            event: Event dictionary
            data: Alert data dictionary
            cache_handler: Optional cache handler
        """
        super().__init__(event, cache_handler)
        self.data = data.get("properties", {})

    @property
    def evt(self):
        """Alert event type."""
        return self.data.get("event")

    @property
    def headline(self):
        """Alert headline."""
        return self.data.get("headline")

    @property
    def description(self):
        """Alert description."""
        return self.data.get("description")

    @property
    def instruction(self):
        """Alert instructions."""
        return self.data.get("instruction")
