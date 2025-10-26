"""
Storage modules for Clima Cast.

This package contains cache and settings handlers for persistent storage.
"""

from .cache_handler import CacheHandler
from .local_handlers import LocalJsonCacheHandler, LocalJsonSettingsHandler
from .settings_handler import AlexaSettingsHandler, SettingsHandler

__all__ = [
    "CacheHandler",
    "SettingsHandler",
    "AlexaSettingsHandler",
    "LocalJsonCacheHandler",
    "LocalJsonSettingsHandler",
]
