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
Cache Abstraction Layer

Provides a unified interface for different cache backends:
- DynamoDB-based caching for AWS Lambda/Alexa
- JSON file-based caching for CLI/local testing
"""

import json
import os
from abc import ABC, abstractmethod
from time import time
from boto3 import resource
from botocore.exceptions import ClientError


class CacheAdapter(ABC):
    """Abstract base class for cache adapters"""
    
    @abstractmethod
    def get(self, cache_name, key):
        """
        Retrieve an item from the cache.
        
        Args:
            cache_name: Name of the cache (e.g., "LocationCache", "UserCache")
            key: Dictionary with key fields
            
        Returns:
            Cached item or None if not found or expired
        """
        pass
    
    @abstractmethod
    def put(self, cache_name, key, ttl=35):
        """
        Write an item to the cache.
        
        Args:
            cache_name: Name of the cache
            key: Dictionary with key fields and data
            ttl: Time to live in days (0 means no expiration)
        """
        pass


class DynamoDBCacheAdapter(CacheAdapter):
    """
    DynamoDB-based cache adapter for AWS Lambda/Alexa.
    
    Uses persistent attributes with:
    - Shared caches (LocationCache, StationCache, ZoneCache) in a single DynamoDB item
    - User caches managed through attributes manager
    """
    
    def __init__(self, attributes_manager=None, persistence_table_name=None, persistence_region=None):
        """
        Initialize DynamoDB cache adapter.
        
        Args:
            attributes_manager: ASK SDK attributes manager (for user caches)
            persistence_table_name: DynamoDB table name
            persistence_region: AWS region for DynamoDB
        """
        self.attributes_manager = attributes_manager
        self.ddb_resource = None
        self.table_name = persistence_table_name
        
        if persistence_table_name and persistence_region:
            self.ddb_resource = resource('dynamodb', region_name=persistence_region)
    
    def get(self, cache_name, key):
        """Retrieve an item from the cache"""
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Access persistent attributes based on cache type
        if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
            # Shared caches - read directly from DynamoDB
            if not self.ddb_resource or not self.table_name:
                return None
                
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
            # User-specific caches - use attributes manager
            if not self.attributes_manager:
                return None
            attrs = self.attributes_manager.persistent_attributes
            current_version = None
        
        # Get the cache dict
        cache_dict = attrs.get(cache_name, {})
        
        # Check if item exists
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
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            }
                        )
                    else:
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
        """Write an item to the cache"""
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Add TTL if specified
        if ttl != 0:
            key["ttl"] = int(time()) + (ttl * 24 * 60 * 60)
        
        # Access persistent attributes based on cache type
        if cache_name in ["LocationCache", "StationCache", "ZoneCache"]:
            # Shared caches - use optimistic locking
            if not self.ddb_resource or not self.table_name:
                return
                
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
                        table.put_item(
                            Item={
                                "id": "SHARED_CACHE",
                                "attributes": attrs,
                                "version": new_version
                            }
                        )
                    else:
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
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Version conflict on shared cache write, retry {retry_count}/{max_retries}")
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
            # User-specific caches - use attributes manager
            if not self.attributes_manager:
                return
            
            attrs = self.attributes_manager.persistent_attributes
            cache_dict = attrs.get(cache_name, {})
            cache_dict[key_str] = key
            attrs[cache_name] = cache_dict
            self.attributes_manager.save_persistent_attributes()


class JSONFileCacheAdapter(CacheAdapter):
    """
    JSON file-based cache adapter for CLI/local testing.
    
    Stores caches in JSON files in a specified directory.
    """
    
    def __init__(self, cache_dir=".cache"):
        """
        Initialize JSON file cache adapter.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_file(self, cache_name):
        """Get the file path for a cache"""
        return os.path.join(self.cache_dir, f"{cache_name}.json")
    
    def _load_cache(self, cache_name):
        """Load cache from file"""
        cache_file = self._get_cache_file(cache_name)
        if not os.path.exists(cache_file):
            return {}
        
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_cache(self, cache_name, cache_dict):
        """Save cache to file"""
        cache_file = self._get_cache_file(cache_name)
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_dict, f, indent=2)
        except IOError as e:
            print(f"Error saving cache {cache_name}: {e}")
    
    def get(self, cache_name, key):
        """Retrieve an item from the cache"""
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
        """Write an item to the cache"""
        # Build a key string from the key dict
        key_str = "_".join([str(key[k]) for k in sorted(key.keys())])
        
        # Add TTL if specified
        if ttl != 0:
            key["ttl"] = int(time()) + (ttl * 24 * 60 * 60)
        
        # Load cache
        cache_dict = self._load_cache(cache_name)
        
        # Update cache
        cache_dict[key_str] = key
        
        # Save cache
        self._save_cache(cache_name, cache_dict)
