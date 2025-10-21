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
Geolocator class for converting location names/zipcodes to coordinates.
Supports HERE.com geocoding API.
"""

import requests


class Geolocator:
    """
    Abstraction layer for geocoding services.
    Currently supports HERE.com Geocoding API.
    """
    
    def __init__(self, api_key, session=None):
        """
        Initialize the geolocator with an API key.
        
        Args:
            api_key: HERE.com API key
            session: Optional requests.Session object to use for HTTP requests
        """
        self.api_key = api_key
        self.session = session or requests.Session()
        self.base_url = "https://geocode.search.hereapi.com/v1"
    
    def geocode(self, search):
        """
        Geocode a location string (zipcode, city+state, or county).
        
        Args:
            search: Location string to geocode (e.g., "Miami Florida", "55118", "Hennepin county Minnesota")
        
        Returns:
            Tuple of (coordinates, properties) where:
                - coordinates is (latitude, longitude) or None if not found
                - properties is a dict with administrative area info (County, State, etc.) or None
        """
        if not self.api_key:
            return None, None
        
        # Clean up the search query - replace + with spaces for HERE API
        query = search.replace("+", " ").strip()
        
        # Build the API request
        params = {
            "q": query,
            "apiKey": self.api_key,
            "limit": 1,
            "in": "countryCode:USA"  # Restrict to USA since this is for US weather
        }
        
        try:
            response = self.session.get(
                f"{self.base_url}/geocode",
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                return None, None
            
            data = response.json()
            
            # Check if we got results
            if "items" not in data or len(data["items"]) == 0:
                return None, None
            
            # Extract the first result
            item = data["items"][0]
            
            # Extract coordinates
            if "position" not in item:
                return None, None
            
            coords = (item["position"]["lat"], item["position"]["lng"])
            
            # Extract administrative area information
            props = {}
            if "address" in item:
                address = item["address"]
                
                # Map HERE.com fields to expected property names
                # County information
                if "county" in address:
                    props["County"] = address["county"]
                
                # State information
                if "state" in address:
                    props["State"] = address["state"]
                
                # City information
                if "city" in address:
                    props["City"] = address["city"]
                
                # Postal code
                if "postalCode" in address:
                    props["PostalCode"] = address["postalCode"]
            
            return coords, props
            
        except Exception as e:
            print(f"Geocoding error: {e}")
            return None, None
