"""
Storage modules for Clima Cast.

This package contains cache and settings handlers for persistent storage.
"""

from .cache_handler import CacheHandler
from .settings_handler import SettingsHandler, AlexaSettingsHandler
from .local_handlers import LocalJsonCacheHandler, LocalJsonSettingsHandler

__all__ = [
    'CacheHandler',
    'SettingsHandler', 
    'AlexaSettingsHandler',
    'LocalJsonCacheHandler', 
    'LocalJsonSettingsHandler'
]
