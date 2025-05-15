"""
The Dyrt website scraper - Modified version
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
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Check if we have any cookies set
            cookies = self.client.cookies
            logger.info(f"Got cookies: {cookies}")
            
            # Check if any authentication-related cookies exist
            auth_cookies = [cookie for cookie in cookies.jar if cookie.name in ('ab', 'ab-test-info', '_ga', '_gcl_au')]

            if auth_cookies:
                logger.info(f"Found session cookies: {auth_cookies}")
                return True
            else:
                logger.warning("No session cookies found. This might cause issues.")
                return False
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
        
        # Calculate center and build bbox parameter
        lat_center = (bounds['ne_lat'] + bounds['sw_lat']) / 2
        lng_center = (bounds['ne_lng'] + bounds['sw_lng']) / 2
        
        # Using bbox parameter as seen in the actual request headers
        bbox_value = f"{bounds['sw_lng']},{bounds['sw_lat']},{bounds['ne_lng']},{bounds['ne_lat']}"
        
        # Build params according to the actual API format from headers
        params = {
            "filter[search][bbox]": bbox_value,
            "filter[search][drive_time]": "any",
            "filter[search][air_quality]": "any",
            "filter[search][electric_amperage]": "any",
            "filter[search][max_vehicle_length]": "any",
            "filter[search][price]": "any",
            "filter[search][rating]": "any",
            "sort": "recommended",
            "page[size]": 500,
            "page[number]": 1
        }
        
        try:
            # Log full request details
            logger.debug(f"Making API request to: {DYRT_API_URL}")
            logger.debug(f"With params: {params}")
            logger.debug(f"Using headers: {self.client.headers}")
            
            # Make API request
            response = await self.client.get(DYRT_API_URL, params=params)
            
            # Log detailed response info
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Log response data if it's an error
            if response.status_code >= 400:
                logger.error(f"API Error: Status {response.status_code}")
                logger.error(f"Response: {response.text[:1000]}")  # Log the first 1000 chars of error
            
            response.raise_for_status()
    
            # Parse JSON response
            data = response.json()
            
            logger.debug(f"API returned keys: {data.keys()}")
            logger.debug(f"Meta: {data.get('meta')}")
            
            # Check if too many results
            meta = data.get("meta", {})
            record_count = meta.get("record-count", 0)
            too_many_results = record_count > 500  # Increased from 100 to match page size
    
            if too_many_results:
                logger.info(f"Too many results ({record_count}) for bounds: {bounds}. Need to subdivide.")
    
            # Extract campgrounds
            campgrounds = data.get("data", [])
            logger.info(f"Retrieved {len(campgrounds)} campgrounds")
    
            # Log first campground structure if available
            if campgrounds and len(campgrounds) > 0:
                logger.debug(f"First campground keys: {campgrounds[0].keys()}")
                logger.debug(f"First campground attributes: {campgrounds[0].get('attributes', {}).keys()}")
    
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
    
    async def process_bounds(self, bounds: Dict[str, float], depth: int = 0, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Process bounds recursively
        """
        if depth > max_depth:
            logger.warning(f"Maximum recursion depth reached for bounds: {bounds}")
            return []
            
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
            # US bounds (approximately)
            us_bounds = {
                "ne_lat": 49.38,  # Northern border
                "ne_lng": -66.94,  # Eastern border
                "sw_lat": 25.82,  # Southern border
                "sw_lng": -124.39  # Western border
            }
            
            # Log bounds
            logger.info(f"US bounds: {us_bounds}")
            
            # Process US bounds
            logger.info("Starting to scrape campgrounds in the US")
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
    import httpx
    import json
    from urllib.parse import urlencode
    
    logger.info("Running API test request...")
    # TheDyrt API URL
    api_url = "https://thedyrt.com/api/v6/locations/search-results"
    
    # Test locations
    test_locations = [
        # Yellowstone with proper bbox format
        {
            "name": "Yellowstone",
            "params": {
                "filter[search][bbox]": "-111.0885,44.1280,-110.0885,44.7280",
                "filter[search][drive_time]": "any",
                "filter[search][air_quality]": "any",
                "filter[search][electric_amperage]": "any",
                "filter[search][max_vehicle_length]": "any",
                "filter[search][price]": "any",
                "filter[search][rating]": "any",
                "sort": "recommended",
                "page[size]": 500,
                "page[number]": 1
            }
        },
        # Grand Canyon with proper bbox format
        {
            "name": "Grand Canyon",
            "params": {
                "filter[search][bbox]": "-112.3129,35.9069,-111.9129,36.3069",
                "filter[search][drive_time]": "any",
                "filter[search][air_quality]": "any",
                "filter[search][electric_amperage]": "any",
                "filter[search][max_vehicle_length]": "any",
                "filter[search][price]": "any",
                "filter[search][rating]": "any",
                "sort": "recommended",
                "page[size]": 500,
                "page[number]": 1
            }
        }
    ]
    
    # Headers that match those from the successful request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "application/vnd.api+json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://thedyrt.com/search",
        "Origin": "https://thedyrt.com",
        "Content-Type": "application/vnd.api+json"
    }
    
    # Make request
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        # First get website to get cookies
        logger.info("Getting main website for cookies...")
        main_response = await client.get("https://thedyrt.com/search")
        logger.info(f"Main website status: {main_response.status_code}")
        logger.info(f"Cookies received: {client.cookies}")
        
        # Test each location
        for location in test_locations:
            # Construct URL with query parameters
            url = f"{api_url}?{urlencode(location['params'])}"
            logger.info(f"Testing {location['name']} URL: {url}")
            
            # Make request
            response = await client.get(url)
            logger.info(f"{location['name']} Status code: {response.status_code}")
            
            # Try to parse JSON
            try:
                data = response.json()
                camp_count = len(data.get('data', []))
                meta_count = data.get('meta', {}).get('record-count', 0)
                logger.info(f"{location['name']} found {camp_count} campgrounds (meta says {meta_count})")
                
                if camp_count > 0:
                    logger.info(f"Success! Found data for {location['name']}")
                    logger.info(f"First campground: {json.dumps(data['data'][0], indent=2)[:500]}...")
                    
                    # Save this successful query for future reference
                    logger.info(f"WORKING QUERY: {location['name']} with bbox parameters")
                    return data
                else:
                    logger.warning(f"No campgrounds found for {location['name']}")
            except Exception as e:
                logger.error(f"Error with {location['name']}: {e}")
                logger.error(f"Response text: {response.text[:500]}...")
    
    logger.error("All test locations failed to return campground data")
    return None

# Run test
if __name__ == "__main__":
    asyncio.run(test_api_request())