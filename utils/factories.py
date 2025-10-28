#!/usr/bin/python3

# =============================================================================
#
# Copyright 2017 by Leland Lucius
#
# Released under the GNU Affero GPL
# See: https://github.com/lllucius/climacast/blob/master/LICENSE
#
# =============================================================================

import logging

import httpx

from storage.cache_handler import CacheHandler
from utils.config import Config
from utils.geolocator import Geolocator

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# =============================================================================
# Factory Functions for Singleton Instances
# =============================================================================

_https_client = None


def get_https_client() -> httpx.Client:
    """
    Get or create the global HTTPS client instance.

    Returns:
        httpx.Client: Configured HTTP client for API calls
    """
    global _https_client
    if _https_client is None:
        _https_client = httpx.Client(timeout=Config.HTTP_TIMEOUT, follow_redirects=True)
    return _https_client


_geolocator_instance = None


def get_geolocator() -> Geolocator:
    """
    Get or create the global geolocator instance.

    Returns:
        Geolocator: Configured geolocator for geocoding operations
    """
    global _geolocator_instance
    if _geolocator_instance is None:
        _geolocator_instance = Geolocator(
            api_key=Config.HERE_API_KEY, session=get_https_client()
        )
    return _geolocator_instance


_cache_handler_instance = None


def get_cache_handler() -> CacheHandler:
    """
    Get or create the global cache handler instance.

    Returns:
        CacheHandler: Configured cache handler for DynamoDB operations
    """
    global _cache_handler_instance
    if _cache_handler_instance is None:
        _cache_handler_instance = CacheHandler(
            table_name=Config.DYNAMODB_TABLE_NAME, region=Config.DYNAMODB_REGION
        )
    return _cache_handler_instance
