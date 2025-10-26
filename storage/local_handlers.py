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
Local testing handlers for Clima Cast.

This module provides file-based implementations of cache and settings handlers
for local testing without requiring AWS DynamoDB access.
"""

import json
import logging
import os
import re
from time import time
from typing import Any, Dict, Optional

from utils.constants import get_default_metrics

# Configure logging
logger = logging.getLogger(__name__)


class LocalJsonCacheHandler(object):
    """
    Cache handler implementation using local JSON files for testing.
    This allows testing without requiring DynamoDB access.

    Cache files are stored in a local directory with the structure:
    - cache_dir/
      - location/
        - <location_id>.json
      - station/
        - <station_id>.json
      - zone/
        - <zone_id>.json
    """

    LOCATION_PREFIX = "location#"
    STATION_PREFIX = "station#"
    ZONE_PREFIX = "zone#"

    def __init__(self, cache_dir: str = ".test_cache") -> None:
        """
        Initialize the cache handler with a local directory.

        Args:
            cache_dir: Directory to store cache JSON files
        """
        self.cache_dir = cache_dir

        # Create cache directories if they don't exist
        for cache_type in ["location", "station", "zone"]:
            os.makedirs(os.path.join(cache_dir, cache_type), exist_ok=True)

    def _get_file_path(self, cache_type: str, cache_id: str) -> str:
        """
        Get the file path for a cache item.

        Args:
            cache_type: Type prefix (e.g., 'location#')
            cache_id: Unique identifier for the cache item

        Returns:
            Path to the cache file
        """
        # Remove prefix from cache_type for directory name
        cache_type_clean = cache_type.replace("#", "")
        # Sanitize cache_id for filename (replace special chars)
        safe_id = re.sub(r"[^\w\s-]", "_", cache_id).strip().replace(" ", "_")
        return os.path.join(self.cache_dir, cache_type_clean, f"{safe_id}.json")

    def get(self, cache_type: str, cache_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the cache.

        Args:
            cache_type: Type prefix (e.g., LOCATION_PREFIX)
            cache_id: Unique identifier for the cache item

        Returns:
            Dict containing the cached data, or None if not found
        """
        try:
            file_path = self._get_file_path(cache_type, cache_id)
            if not os.path.exists(file_path):
                return None

            with open(file_path, "r") as f:
                data = json.load(f)

            # Check TTL if present
            if "ttl" in data and data["ttl"] > 0:
                if time() > data["ttl"]:
                    # Cache expired, remove file
                    os.remove(file_path)
                    return None

            return data.get("cache_data", {})
        except Exception as e:
            logger.error(f"Error getting cache item {cache_type}{cache_id}: {e}")
            return None

    def put(
        self,
        cache_type: str,
        cache_id: str,
        cache_data: Dict[str, Any],
        ttl_days: int = 35,
    ) -> None:
        """
        Store an item in the cache.

        Args:
            cache_type: Type prefix (e.g., LOCATION_PREFIX)
            cache_id: Unique identifier for the cache item
            cache_data: Dict containing the data to cache
            ttl_days: Time to live in days (0 = no expiration)
        """
        try:
            file_path = self._get_file_path(cache_type, cache_id)

            data = {"cache_data": cache_data}
            if ttl_days > 0:
                data["ttl"] = int(time()) + (ttl_days * 24 * 60 * 60)

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error putting cache item {cache_type}{cache_id}: {e}")

    def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
        """
        Get location cache data.

        Args:
            location_id: Location identifier

        Returns:
            Cached location data or None
        """
        return self.get(self.LOCATION_PREFIX, location_id)

    def put_location(
        self, location_id: str, location_data: Dict[str, Any], ttl_days: int = 35
    ) -> None:
        """
        Store location cache data.

        Args:
            location_id: Location identifier
            location_data: Location data to cache
            ttl_days: Time to live in days
        """
        self.put(self.LOCATION_PREFIX, location_id, location_data, ttl_days)

    def get_station(self, station_id: str) -> Optional[Dict[str, Any]]:
        """
        Get station cache data.

        Args:
            station_id: Station identifier

        Returns:
            Cached station data or None
        """
        return self.get(self.STATION_PREFIX, station_id)

    def put_station(
        self, station_id: str, station_data: Dict[str, Any], ttl_days: int = 35
    ) -> None:
        """
        Store station cache data.

        Args:
            station_id: Station identifier
            station_data: Station data to cache
            ttl_days: Time to live in days
        """
        self.put(self.STATION_PREFIX, station_id, station_data, ttl_days)

    def get_zone(self, zone_id: str) -> Optional[Dict[str, Any]]:
        """
        Get zone cache data.

        Args:
            zone_id: Zone identifier

        Returns:
            Cached zone data or None
        """
        return self.get(self.ZONE_PREFIX, zone_id)

    def put_zone(
        self, zone_id: str, zone_data: Dict[str, Any], ttl_days: int = 35
    ) -> None:
        """
        Store zone cache data.

        Args:
            zone_id: Zone identifier
            zone_data: Zone data to cache
            ttl_days: Time to live in days
        """
        self.put(self.ZONE_PREFIX, zone_id, zone_data, ttl_days)


class LocalJsonSettingsHandler:
    """
    Settings handler implementation using local JSON files for testing.
    This allows testing without requiring DynamoDB access.

    Settings are stored in a single JSON file per user.
    Implements the same interface as lambda_function.SettingsHandler.
    """

    def __init__(self, user_id: str, settings_dir: str = ".test_settings") -> None:
        """
        Initialize with a user ID and local directory for settings storage.

        Args:
            user_id: User identifier
            settings_dir: Directory to store settings JSON files
        """
        self.user_id = user_id
        self.settings_dir = settings_dir

        # Create settings directory if it doesn't exist
        os.makedirs(settings_dir, exist_ok=True)

        self._load_settings()

    def _get_file_path(self) -> str:
        """
        Get the file path for user settings.

        Returns:
            Path to user's settings file
        """
        # Sanitize user_id for filename
        safe_id = re.sub(r"[^\w\s-]", "_", self.user_id).strip().replace(" ", "_")
        return os.path.join(self.settings_dir, f"{safe_id}.json")

    def _get_default_metrics(self) -> list:
        """
        Get default metrics list.

        Returns:
            List of default metric names in order
        """
        return get_default_metrics()

    def _load_settings(self) -> None:
        """Load settings from local JSON file."""
        file_path = self._get_file_path()

        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    settings = json.load(f)

                self._location = settings.get("location", None)
                self._rate = settings.get("rate", 100)
                self._pitch = settings.get("pitch", 100)
                self._metrics = settings.get("metrics", self._get_default_metrics())
            except Exception as e:
                logger.error(f"Error loading settings for {self.user_id}: {e}")
                self._init_defaults()
        else:
            self._init_defaults()

    def _init_defaults(self) -> None:
        """Initialize with default settings."""
        self._location = None
        self._rate = 100
        self._pitch = 100
        self._metrics = self._get_default_metrics()

    def _save_settings(self) -> None:
        """Save settings to local JSON file."""
        file_path = self._get_file_path()

        settings = {
            "location": self._location,
            "rate": self._rate,
            "pitch": self._pitch,
            "metrics": self._metrics,
        }

        try:
            with open(file_path, "w") as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving settings for {self.user_id}: {e}")

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

    def get_metrics(self) -> list:
        """
        Get user's custom metrics list.

        Returns:
            List of metric names
        """
        return self._metrics

    def set_metrics(self, metrics: list) -> None:
        """
        Set user's custom metrics list.

        Args:
            metrics: List of metric names
        """
        self._metrics = metrics
        self._save_settings()
