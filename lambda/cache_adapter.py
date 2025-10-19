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
Cache adapter interface and implementations.

This module provides an abstraction layer for caching to allow different
storage backends (DynamoDB for Lambda, JSON files for CLI).
"""

from abc import ABC, abstractmethod
from time import time
import json
import os


class CacheAdapter(ABC):
    """Abstract base class for cache adapters."""
    
    @abstractmethod
    def get(self, cache_name, key):
        """
        Retrieve an item from the cache.
        
        Args:
            cache_name: Name of the cache (e.g., "LocationCache", "StationCache")
            key: Dictionary with key fields (e.g., {"id": "station123"})
            
        Returns:
            The cached item dictionary, or None if not found or expired
        """
        pass
    
    @abstractmethod
    def put(self, cache_name, key, ttl=35):
        """
        Store an item in the cache.
        
        Args:
            cache_name: Name of the cache
            key: Dictionary with key fields and data to store
            ttl: Time to live in days (0 means no expiration)
        """
        pass


class DynamoDBCacheAdapter(CacheAdapter):
    """
    Cache adapter for DynamoDB persistence.
    
    Used by the Lambda function to store caches in DynamoDB.
    Shared caches (LocationCache, StationCache, ZoneCache) are stored in a
    single DynamoDB item with partition key "SHARED_CACHE" to be accessible
    across all users. Uses optimistic locking with version numbers for
    concurrent write safety.
    """
    
    def __init__(self, ddb_resource, table_name, attributes_manager=None):
        """
        Initialize DynamoDB cache adapter.
        
        Args:
            ddb_resource: boto3 DynamoDB resource
            table_name: Name of the DynamoDB table
            attributes_manager: ASK SDK attributes manager (for user caches)
        """
        self.ddb_resource = ddb_resource
        self.table_name = table_name
        self.attributes_manager = attributes_manager
    
    def get(self, cache_name, key):
        """Get item from DynamoDB cache."""
        from botocore.exceptions import ClientError
        
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Access persistent attributes directly based on cache type
        if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
            # For shared caches, read directly from DynamoDB with shared key
            table = self.ddb_resource.Table(self.table_name)
            try:
                response = table.get_item(Key={"id": "SHARED_CACHE"})
                if "Item" not in response:
                    return None
                attrs = response["Item"].get("attributes", {})
                current_version = response["Item"].get("version", 0)
            except Exception:
                return None
        else:
            # For user-specific caches, use the attributes manager
            if not self.attributes_manager:
                return None
            attrs = self.attributes_manager.persistent_attributes
            current_version = None
        
        # Get the cache dict
        cache_dict = attrs.get(cache_name, {})
        
        # Check if item exists and if TTL is still valid
        item = cache_dict.get(key_str)
        if item is None:
            return None
            
        # Check TTL if present
        if "ttl" in item and item["ttl"] < int(time()):
            # Item expired, remove it
            del cache_dict[key_str]
            attrs[cache_name] = cache_dict
            
            # Save the updated cache
            if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
                # Use optimistic locking for shared caches
                table = self.ddb_resource.Table(self.table_name)
                new_version = current_version + 1
                try:
                    if current_version == 0:
                        # First write or no version - no condition needed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            }
                        )
                    else:
                        # Conditional write to ensure version hasn't changed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            },
                            ConditionExpression="version = :current_version",
                            ExpressionAttributeValues={
                                ":current_version": current_version
                            }
                        )
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                        # Version conflict - someone else modified it, that's ok for expiry
                        print(f"Version conflict when removing expired item, skipping")
                    else:
                        print(f"Error saving shared cache: {e}")
                except Exception as e:
                    print(f"Error saving shared cache: {e}")
            else:
                if self.attributes_manager:
                    self.attributes_manager.save_persistent_attributes()
            
            return None
            
        return item
    
    def put(self, cache_name, key, ttl=35):
        """Put item into DynamoDB cache."""
        from botocore.exceptions import ClientError
        
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Add TTL if specified
        if ttl != 0:
            key["ttl"] = int(time()) + (ttl * 24 * 60 * 60)
        
        # Access persistent attributes directly based on cache type
        if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
            # For shared caches, use optimistic locking with version number
            table = self.ddb_resource.Table(self.table_name)
            max_retries = 5
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Read current version and attributes
                    response = table.get_item(Key={"id": "SHARED_CACHE"})
                    if "Item" in response:
                        attrs = response["Item"].get("attributes", {})
                        current_version = response["Item"].get("version", 0)
                    else:
                        attrs = {}
                        current_version = 0
                except Exception as e:
                    print(f"Error reading shared cache: {e}")
                    attrs = {}
                    current_version = 0
                
                # Update cache dict
                cache_dict = attrs.get(cache_name, {})
                cache_dict[key_str] = key
                attrs[cache_name] = cache_dict
                
                # Increment version for optimistic locking
                new_version = current_version + 1
                
                # Write back to DynamoDB with conditional expression
                try:
                    if current_version == 0:
                        # First write or item doesn't exist - no condition needed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            }
                        )
                    else:
                        # Conditional write to ensure version hasn't changed
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            },
                            ConditionExpression="version = :current_version",
                            ExpressionAttributeValues={
                                ":current_version": current_version
                            }
                        )
                    # Success - exit retry loop
                    break
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                        # Version mismatch - retry with exponential backoff
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Version conflict on shared cache write, retry {retry_count}/{max_retries}")
                            # Simple exponential backoff
                            import time as time_module
                            time_module.sleep(0.1 * (2 ** retry_count))
                        else:
                            print(f"Failed to write shared cache after {max_retries} retries")
                    else:
                        print(f"Error saving shared cache: {e}")
                        break
                except Exception as e:
                    print(f"Error saving shared cache: {e}")
                    break
        else:
            # For user-specific caches, use the attributes manager
            if not self.attributes_manager:
                return
            
            attrs = self.attributes_manager.persistent_attributes
            cache_dict = attrs.get(cache_name, {})
            cache_dict[key_str] = key
            attrs[cache_name] = cache_dict
            self.attributes_manager.save_persistent_attributes()


class JSONFileCacheAdapter(CacheAdapter):
    """
    Cache adapter for JSON file persistence.
    
    Used by the CLI to store caches in local JSON files for testing.
    Each cache is stored in a separate JSON file.
    """
    
    def __init__(self, cache_dir=".climacast_cache"):
        """
        Initialize JSON file cache adapter.
        
        Args:
            cache_dir: Directory to store cache files (default: .climacast_cache)
        """
        self.cache_dir = cache_dir
        # Create cache directory if it doesn't exist
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def _get_cache_file(self, cache_name):
        """Get the file path for a cache."""
        return os.path.join(self.cache_dir, f"{cache_name}.json")
    
    def _load_cache(self, cache_name):
        """Load cache from JSON file."""
        cache_file = self._get_cache_file(cache_name)
        if not os.path.exists(cache_file):
            return {}
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError):
            return {}
    
    def _save_cache(self, cache_name, cache_dict):
        """Save cache to JSON file."""
        cache_file = self._get_cache_file(cache_name)
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_dict, f, indent=2)
        except IOError as e:
            print(f"Error saving cache {cache_name}: {e}")
    
    def get(self, cache_name, key):
        """Get item from JSON file cache."""
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Load cache
        cache_dict = self._load_cache(cache_name)
        
        # Check if item exists
        item = cache_dict.get(key_str)
        if item is None:
            return None
        
        # Check TTL if present
        if "ttl" in item and item["ttl"] < int(time()):
            # Item expired, remove it
            del cache_dict[key_str]
            self._save_cache(cache_name, cache_dict)
            return None
        
        return item
    
    def put(self, cache_name, key, ttl=35):
        """Put item into JSON file cache."""
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Add TTL if specified
        if ttl != 0:
            key["ttl"] = int(time()) + (ttl * 24 * 60 * 60)
        
        # Load cache
        cache_dict = self._load_cache(cache_name)
        
        # Update cache dict
        cache_dict[key_str] = key
        
        # Save cache
        self._save_cache(cache_name, cache_dict)
