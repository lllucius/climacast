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
Settings handlers for Clima Cast.

This module provides base and Alexa-specific implementations for managing
user settings.
"""

import logging
from typing import List, Optional

from ask_sdk_core.handler_input import HandlerInput

from utils.constants import get_default_metrics

# Configure logging
logger = logging.getLogger(__name__)


class SettingsHandler(object):
    """
    Base class for handling user settings operations.
    This allows different backends for user settings storage.
    """
    
    def __init__(self) -> None:
        """Initialize the settings handler."""
        pass
    
    def get_location(self) -> Optional[str]:
        """Get user's default location."""
        raise NotImplementedError("Subclass must implement get_location()")
    
    def set_location(self, location: str) -> None:
        """Set user's default location."""
        raise NotImplementedError("Subclass must implement set_location()")
    
    def get_rate(self) -> int:
        """Get user's speech rate setting."""
        raise NotImplementedError("Subclass must implement get_rate()")
    
    def set_rate(self, rate: int) -> None:
        """Set user's speech rate setting."""
        raise NotImplementedError("Subclass must implement set_rate()")
    
    def get_pitch(self) -> int:
        """Get user's speech pitch setting."""
        raise NotImplementedError("Subclass must implement get_pitch()")
    
    def set_pitch(self, pitch: int) -> None:
        """Set user's speech pitch setting."""
        raise NotImplementedError("Subclass must implement set_pitch()")
    
    def get_metrics(self) -> List[str]:
        """Get user's custom metrics list."""
        raise NotImplementedError("Subclass must implement get_metrics()")
    
    def set_metrics(self, metrics: List[str]) -> None:
        """Set user's custom metrics list."""
        raise NotImplementedError("Subclass must implement set_metrics()")


class AlexaSettingsHandler(SettingsHandler):
    """
    Settings handler implementation using Alexa's attributes_manager.
    This is the default backend for storing user settings in DynamoDB
    via the ASK SDK's persistent attributes.
    """
    
    def __init__(self, handler_input: HandlerInput) -> None:
        """
        Initialize with Alexa handler input for accessing attributes_manager.
        
        Args:
            handler_input: ASK SDK HandlerInput object
        """
        super().__init__()
        self.handler_input = handler_input
        self.attr_mgr = handler_input.attributes_manager
        self._load_settings()
    
    def _get_default_metrics(self) -> List[str]:
        """
        Get default metrics list.
        
        Returns:
            List of default metric names in order
        """
        return get_default_metrics()
    
    def _load_settings(self) -> None:
        """Load settings from persistent attributes."""
        persistent_attrs = self.attr_mgr.persistent_attributes
        
        # Initialize settings from persistent attributes or use defaults
        self._location = persistent_attrs.get("location", None)
        self._rate = persistent_attrs.get("rate", 100)
        self._pitch = persistent_attrs.get("pitch", 100)
        self._metrics = persistent_attrs.get("metrics", self._get_default_metrics())
    
    def _save_settings(self) -> None:
        """Save settings to persistent attributes."""
        persistent_attrs = self.attr_mgr.persistent_attributes
        
        persistent_attrs["location"] = self._location
        persistent_attrs["rate"] = self._rate
        persistent_attrs["pitch"] = self._pitch
        persistent_attrs["metrics"] = self._metrics
        
        self.attr_mgr.save_persistent_attributes()
    
    def get_location(self) -> Optional[str]:
        """
        Get user's default location.
        
        Returns:
            User's location or None
        """
        return self._location
    
    def set_location(self, location: str) -> None:
        """
        Set user's default location.
        
        Args:
            location: Location string to set
        """
        self._location = location
        self._save_settings()
    
    def get_rate(self) -> int:
        """
        Get user's speech rate setting.
        
        Returns:
            Speech rate percentage (100 = normal)
        """
        return self._rate
    
    def set_rate(self, rate: int) -> None:
        """
        Set user's speech rate setting.
        
        Args:
            rate: Speech rate percentage
        """
        self._rate = rate
        self._save_settings()
    
    def get_pitch(self) -> int:
        """
        Get user's speech pitch setting.
        
        Returns:
            Speech pitch percentage (100 = normal)
        """
        return self._pitch
    
    def set_pitch(self, pitch: int) -> None:
        """
        Set user's speech pitch setting.
        
        Args:
            pitch: Speech pitch percentage
        """
        self._pitch = pitch
        self._save_settings()
    
    def get_metrics(self) -> List[str]:
        """
        Get user's custom metrics list.
        
        Returns:
            List of metric names
        """
        return self._metrics
    
    def set_metrics(self, metrics: List[str]) -> None:
        """
        Set user's custom metrics list.
        
        Args:
            metrics: List of metric names
        """
        self._metrics = metrics
        self._save_settings()
