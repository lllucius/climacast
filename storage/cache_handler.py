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
Cache handler for Clima Cast.

This module provides DynamoDB-based caching for weather data.
"""

import logging
from time import time
from typing import Any, Dict, Optional

from boto3 import resource as resource

# Configure logging
logger = logging.getLogger(__name__)


class CacheHandler(object):
    """
    Handles all cache operations using a single DynamoDB table.
    The table uses a composite key structure:
    - pk (partition key): cache type (e.g., 'location#<location>', 'station#<id>', 'zone#<id>')
    - sk (sort key): always 'data' for cache items
    
    The cache data is stored as a dict in the 'cache_data' attribute.
    Shared caches (location, station, zone) must be atomically protected.
    """
    
    # Cache type prefixes
    LOCATION_PREFIX = "location#"
    STATION_PREFIX = "station#"
    ZONE_PREFIX = "zone#"
    
    def __init__(self, table_name: str, region: str = "us-east-1") -> None:
        """
        Initialize the cache handler with the Alexa-provided table.
        
        Args:
            table_name: Name of the DynamoDB table to use
            region: AWS region name
        """
        self.ddb = resource("dynamodb", region_name=region)
        self.table = self.ddb.Table(table_name)
    
    def _make_key(self, cache_type: str, cache_id: str) -> Dict[str, str]:
        """
        Create a composite key for the cache item.
        
        Args:
            cache_type: Type prefix
            cache_id: Cache identifier
            
        Returns:
            Dict with pk and sk keys
        """
        return {
            "pk": f"{cache_type}{cache_id}",
            "sk": "data"
        }
    
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
            key = self._make_key(cache_type, cache_id)
            response = self.table.get_item(Key=key)
            
            if "Item" not in response:
                return None
            
            item = response["Item"]
            # Return the cache_data dict
            return item.get("cache_data", {})
        except Exception as e:
            logger.error(f"Error getting cache item {cache_type}{cache_id}: {e}")
            return None
    
    def put(self, cache_type: str, cache_id: str, cache_data: Dict[str, Any], ttl_days: int = 35) -> None:
        """
        Store an item in the cache.
        
        Args:
            cache_type: Type prefix (e.g., LOCATION_PREFIX)
            cache_id: Unique identifier for the cache item
            cache_data: Dict containing the data to cache
            ttl_days: Time to live in days (0 = no expiration)
        """
        try:
            key = self._make_key(cache_type, cache_id)
            item = {**key, "cache_data": cache_data}
            
            if ttl_days > 0:
                item["ttl"] = int(time()) + (ttl_days * 24 * 60 * 60)
            
            self.table.put_item(Item=item)
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
    
    def put_location(self, location_id: str, location_data: Dict[str, Any], ttl_days: int = 35) -> None:
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
    
    def put_station(self, station_id: str, station_data: Dict[str, Any], ttl_days: int = 35) -> None:
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
    
    def put_zone(self, zone_id: str, zone_data: Dict[str, Any], ttl_days: int = 35) -> None:
        """
        Store zone cache data.
        
        Args:
            zone_id: Zone identifier
            zone_data: Zone data to cache
            ttl_days: Time to live in days
        """
        self.put(self.ZONE_PREFIX, zone_id, zone_data, ttl_days)
