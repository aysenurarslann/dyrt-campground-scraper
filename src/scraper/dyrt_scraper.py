#dyrt_scraper.py

"""
The Dyrt website scraper 
"""
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from geopy.geocoders import Nominatim

from src.config import (
    DYRT_API_URL, DEFAULT_HEADERS, MAX_RETRIES, RETRY_BACKOFF, 
    USE_GEOCODING, logger
)
from src.models.campground import Campground
from src.database.db import save_campgrounds


class DyrtScraper:
    """
    Scraper for The Dyrt website
    """
    def __init__(self):
        self.client = httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=30.0)
        self.geolocator = Nominatim(user_agent="TheDyrtScraper/1.0") if USE_GEOCODING else None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def close(self):
        """
        Close the HTTP client
        """
        await self.client.aclose()
        
    async def get_auth_token(self):
        """
        Get authentication token and cookies from main website
        """
        try:
            logger.info("Fetching authentication token...")
            
            # First visit the main page to get cookies
            response = await self.client.get("https://thedyrt.com/search")
            
            # Log status code and response info
            logger.debug(f"Main page status code: {response.status_code}")
            
            # Check if we have any cookies set
            cookies = self.client.cookies
            logger.info(f"Got {len(cookies)} cookies")
            
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error getting auth token: {e}")
            return False
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_BACKOFF),
        retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
        reraise=True
    )
    async def fetch_campgrounds(self, bounds: Dict[str, float], zoom: int = 5) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Fetch campgrounds from The Dyrt API within the given bounds
        """
        # Get authentication before making requests
        await self.get_auth_token()
        
        # Build bbox parameter - format: "sw_lng,sw_lat,ne_lng,ne_lat"
        bbox_value = f"{bounds['sw_lng']},{bounds['sw_lat']},{bounds['ne_lng']},{bounds['ne_lat']}"
        
        # Build params according to working API format
        params = {
            "filter[search][bbox]": bbox_value,
            "filter[search][drive_time]": "any",
            "filter[search][air_quality]": "any",
            "filter[search][electric_amperage]": "any",
            "filter[search][max_vehicle_length]": "any",
            "filter[search][price]": "any",
            "filter[search][rating]": "any",
            "sort": "recommended",
            "page[size]": 100,  # Reduced to avoid overwhelming
            "page[number]": 1
        }
        
        try:
            # Log request details
            logger.debug(f"Making API request to: {DYRT_API_URL}")
            logger.debug(f"With bbox: {bbox_value}")
            
            # Make API request
            response = await self.client.get(DYRT_API_URL, params=params)
            
            # Log response status
            logger.debug(f"Response status: {response.status_code}")
            
            # Handle different status codes
            if response.status_code == 404:
                logger.error("API endpoint not found. The endpoint may have changed.")
                # Try alternative endpoints
                alternative_urls = [
                    "https://thedyrt.com/api/v5/locations/search-results",
                    "https://thedyrt.com/api/v4/locations/search-results",
                    "https://thedyrt.com/api/v3/locations/search-results"
                ]
                
                for alt_url in alternative_urls:
                    logger.info(f"Trying alternative endpoint: {alt_url}")
                    alt_response = await self.client.get(alt_url, params=params)
                    if alt_response.status_code == 200:
                        logger.success(f"Success with alternative endpoint: {alt_url}")
                        response = alt_response
                        break
                else:
                    logger.error("All alternative endpoints failed")
                    raise httpx.HTTPStatusError(f"API endpoint not found", request=response.request, response=response)
            
            # Check for other errors
            if response.status_code >= 400:
                logger.error(f"API Error: Status {response.status_code}")
                logger.error(f"Response: {response.text[:1000]}")
            
            response.raise_for_status()
    
            # Parse JSON response
            data = response.json()
            
            logger.debug(f"API returned keys: {list(data.keys())}")
            
            # Check if too many results
            meta = data.get("meta", {})
            record_count = meta.get("record-count", 0)
            too_many_results = record_count > 100
    
            if too_many_results:
                logger.info(f"Too many results ({record_count}) for bounds. Need to subdivide.")
    
            # Extract campgrounds
            campgrounds = data.get("data", [])
            logger.info(f"Retrieved {len(campgrounds)} campgrounds")
            
            return campgrounds, too_many_results
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching campgrounds: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw response: {response.text[:500]}...")
            raise
        except Exception as e:
            logger.error(f"Error fetching campgrounds: {e}")
            raise
    
    async def get_address_from_coords(self, lat: float, lng: float) -> Optional[str]:
        """
        Get address from coordinates using reverse geocoding
        """
        if not self.geolocator:
            return None
            
        try:
            location = self.geolocator.reverse(f"{lat}, {lng}")
            return location.address if location else None
        except Exception as e:
            logger.warning(f"Error getting address from coordinates: {e}")
            return None
    
    def subdivide_bounds(self, bounds: Dict[str, float]) -> List[Dict[str, float]]:
        """
        Subdivide bounds into 4 smaller bounds
        """
        # Calculate midpoints
        mid_lat = (bounds["ne_lat"] + bounds["sw_lat"]) / 2
        mid_lng = (bounds["ne_lng"] + bounds["sw_lng"]) / 2
        
        # Create 4 smaller bounds
        return [
            # Northwest
            {
                "ne_lat": bounds["ne_lat"],
                "ne_lng": mid_lng,
                "sw_lat": mid_lat,
                "sw_lng": bounds["sw_lng"]
            },
            # Northeast
            {
                "ne_lat": bounds["ne_lat"],
                "ne_lng": bounds["ne_lng"],
                "sw_lat": mid_lat,
                "sw_lng": mid_lng
            },
            # Southwest
            {
                "ne_lat": mid_lat,
                "ne_lng": mid_lng,
                "sw_lat": bounds["sw_lat"],
                "sw_lng": bounds["sw_lng"]
            },
            # Southeast
            {
                "ne_lat": mid_lat,
                "ne_lng": bounds["ne_lng"],
                "sw_lat": bounds["sw_lat"],
                "sw_lng": mid_lng
            }
        ]
    
    async def process_bounds(self, bounds: Dict[str, float], depth: int = 0, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        Process bounds recursively
        """
        if depth > max_depth:
            logger.warning(f"Maximum recursion depth reached for bounds: {bounds}")
            return []
            
        try:
            # Fetch campgrounds
            campgrounds, too_many_results = await self.fetch_campgrounds(bounds)
            
            # If too many results, subdivide and process each
            if too_many_results and depth < max_depth:
                logger.info(f"Subdividing bounds at depth {depth}")
                subdivided_bounds = self.subdivide_bounds(bounds)
                
                # Process each subdivision
                all_campgrounds = []
                for sub_bounds in subdivided_bounds:
                    sub_campgrounds = await self.process_bounds(sub_bounds, depth + 1, max_depth)
                    all_campgrounds.extend(sub_campgrounds)
                    
                return all_campgrounds
            else:
                return campgrounds
        except Exception as e:
            logger.error(f"Error processing bounds {bounds}: {e}")
            return []
    
    async def parse_campground(self, camp_data: Dict[str, Any]) -> Campground:
        """
        Parse campground data into Pydantic model
        """
        # Extract attributes
        attrs = camp_data.get("attributes", {})
        
        # Get or calculate fields
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")
        
        # Get address (bonus)
        address = None
        if USE_GEOCODING and latitude and longitude:
            address = await self.get_address_from_coords(latitude, longitude)
        
        # Create Campground model
        campground = Campground(
            id=camp_data.get("id"),
            type=camp_data.get("type"),
            links={"self": camp_data.get("links", {}).get("self", "")},
            name=attrs.get("name", ""),
            latitude=latitude,
            longitude=longitude,
            region_name=attrs.get("region-name", ""),
            administrative_area=attrs.get("administrative-area"),
            nearest_city_name=attrs.get("nearest-city-name"),
            accommodation_type_names=attrs.get("accommodation-type-names", []),
            bookable=attrs.get("bookable", False),
            camper_types=attrs.get("camper-types", []),
            operator=attrs.get("operator"),
            photo_url=attrs.get("photo-url"),
            photo_urls=attrs.get("photo-urls", []),
            photos_count=attrs.get("photos-count", 0),
            rating=attrs.get("rating"),
            reviews_count=attrs.get("reviews-count", 0),
            slug=attrs.get("slug"),
            price_low=attrs.get("price-low"),
            price_high=attrs.get("price-high"),
            availability_updated_at=datetime.fromisoformat(attrs["availability-updated-at"]) if attrs.get("availability-updated-at") else None,
        )
        
        # Add address if available
        if address:
            setattr(campground, "address", address)
            
        return campground
    
    async def run(self) -> Dict[str, int]:
        """
        Run the scraper to fetch all campgrounds in the US
        """
        try:
            # Start with smaller bounds for testing
            test_bounds = {
               "sw_lng": -122.5, "sw_lat": 37.0,
               "ne_lng": -121.0, "ne_lat": 37.8
            }
            
            logger.info(f"Starting with test bounds: {test_bounds}")
            
            # Process test bounds first
            logger.info("Starting to scrape campgrounds in test area")
            raw_campgrounds = await self.process_bounds(test_bounds)
            
            # If test works, expand to full US
            if raw_campgrounds:
                logger.success(f"Test successful! Found {len(raw_campgrounds)} campgrounds")
                
                # Now try full US bounds
                us_bounds = {
                    "ne_lat": 49.38,  # Northern border
                    "ne_lng": -66.94,  # Eastern border
                    "sw_lat": 25.82,  # Southern border
                    "sw_lng": -124.39  # Western border
                }
                
                logger.info("Expanding to full US bounds")
                raw_campgrounds = await self.process_bounds(us_bounds)
            
            # Log stats
            logger.info(f"Raw campgrounds count: {len(raw_campgrounds)}")
            
            # Parse campgrounds into Pydantic models
            logger.info(f"Parsing {len(raw_campgrounds)} campgrounds")
            parsed_campgrounds = []
            for camp_data in raw_campgrounds:
                try:
                    campground = await self.parse_campground(camp_data)
                    parsed_campgrounds.append(campground)
                except Exception as e:
                    logger.error(f"Error parsing campground: {e}")
                    continue
            
            # Save to database
            logger.info(f"Saving {len(parsed_campgrounds)} campgrounds to database")
            result = await save_campgrounds(parsed_campgrounds)
            
            logger.success(f"Scraper completed. Added: {result['added']}, Updated: {result['updated']}")
            return result
        except Exception as e:
            logger.error(f"Error running scraper: {e}")
            raise
        finally:
            await self.close()


async def test_api_request():
    """Test API request to see response format"""
    logger.info("Running API test request...")
    
    # Test with a small area first
    test_params = {
        "filter[search][bbox]": "-122.5,37.0,-121.0,37.8",  # Bay Area
        "filter[search][drive_time]": "any",
        "filter[search][air_quality]": "any",
        "filter[search][electric_amperage]": "any",
        "filter[search][max_vehicle_length]": "any",
        "filter[search][price]": "any",
        "filter[search][rating]": "any",
        "sort": "recommended",
        "page[size]": 10,
        "page[number]": 1
    }
    
    # Headers that should work
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "application/vnd.api+json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://thedyrt.com/search",
        "Origin": "https://thedyrt.com"
    }
    
    # Test different API versions
    api_versions = [
        "https://thedyrt.com/api/v6/locations/search-results",
        "https://thedyrt.com/api/v5/locations/search-results", 
        "https://thedyrt.com/api/v4/locations/search-results",
        "https://thedyrt.com/api/v3/locations/search-results",
        "https://thedyrt.com/api/v2/search/campgrounds"
    ]
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # Get main page for cookies
        logger.info("Getting main website for cookies...")
        main_response = await client.get("https://thedyrt.com/search")
        logger.info(f"Main website status: {main_response.status_code}")
        
        # Test each API version
        for api_url in api_versions:
            logger.info(f"Testing API: {api_url}")
            
            try:
                response = await client.get(api_url, params=test_params)
                logger.info(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        camp_count = len(data.get('data', []))
                        logger.success(f"SUCCESS! Found {camp_count} campgrounds with {api_url}")
                        
                        if camp_count > 0:
                            logger.info("First campground structure:")
                            logger.info(json.dumps(data['data'][0], indent=2)[:500])
                        
                        return data
                    except json.JSONDecodeError:
                        logger.error("Response is not JSON")
                        logger.error(f"Response: {response.text[:200]}")
                else:
                    logger.error(f"Failed with status {response.status_code}")
                    logger.error(f"Response: {response.text[:200]}")
                    
            except Exception as e:
                logger.error(f"Exception with {api_url}: {e}")
    
    logger.error("All API endpoints failed")
    return None


if __name__ == "__main__":
    asyncio.run(test_api_request())
