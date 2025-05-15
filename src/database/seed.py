"""
Database migration script for initializing the database and adding test data
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database.db import init_db, async_session_factory
from src.database.models import Campground, CamperType, AccommodationType, PhotoUrl, ScraperLog
from src.config import logger

# Example seed data for testing
SEED_CAMPGROUNDS = [
    {
        "id": "sample-campground-1",
        "type": "campground",
        "links_self": "https://thedyrt.com/api/v6/campgrounds/sample-campground-1",
        "name": "Pine Valley Campground",
        "latitude": 39.5678,
        "longitude": -105.3456,
        "region_name": "Colorado",
        "administrative_area": "Jefferson County",
        "nearest_city_name": "Denver",
        "bookable": True,
        "operator": "National Park Service",
        "photo_url": "https://example.com/photos/sample1.jpg",
        "photos_count": 5,
        "rating": 4.7,
        "reviews_count": 42,
        "slug": "pine-valley",
        "price_low": 20.0,
        "price_high": 35.0,
        "camper_types": ["RV", "Tent", "Van"],
        "accommodation_types": ["Campsite", "RV Site"],
        "photo_urls": [
            "https://example.com/photos/sample1.jpg",
            "https://example.com/photos/sample2.jpg",
            "https://example.com/photos/sample3.jpg"
        ]
    },
    {
        "id": "sample-campground-2",
        "type": "campground",
        "links_self": "https://thedyrt.com/api/v6/campgrounds/sample-campground-2",
        "name": "Mountain View Retreat",
        "latitude": 40.1234,
        "longitude": -106.7890,
        "region_name": "Colorado",
        "administrative_area": "Summit County",
        "nearest_city_name": "Breckenridge",
        "bookable": False,
        "operator": "Forest Service",
        "photo_url": "https://example.com/photos/mountain1.jpg",
        "photos_count": 3,
        "rating": 4.2,
        "reviews_count": 18,
        "slug": "mountain-view",
        "price_low": 0.0,
        "price_high": 0.0,
        "camper_types": ["Tent", "Hammock"],
        "accommodation_types": ["Campsite", "Primitive"],
        "photo_urls": [
            "https://example.com/photos/mountain1.jpg",
            "https://example.com/photos/mountain2.jpg"
        ]
    }
]

async def seed_database():
    """
    Initialize the database and seed it with test data
    """
    logger.info("Initializing database schema...")
    await init_db()
    
    # Create a session
    async with async_session_factory() as session:
        logger.info("Seeding database with test data...")
        
        # Create a test scraper log
        scraper_log = ScraperLog(
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            status="success",
            records_processed=len(SEED_CAMPGROUNDS),
            records_added=len(SEED_CAMPGROUNDS),
            records_updated=0
        )
        session.add(scraper_log)
        
        # Process each test campground
        for camp_data in SEED_CAMPGROUNDS:
            # Create campground
            campground = Campground(
                id=camp_data["id"],
                type=camp_data["type"],
                links_self=camp_data["links_self"],
                name=camp_data["name"],
                latitude=camp_data["latitude"],
                longitude=camp_data["longitude"],
                region_name=camp_data["region_name"],
                administrative_area=camp_data["administrative_area"],
                nearest_city_name=camp_data["nearest_city_name"],
                bookable=camp_data["bookable"],
                operator=camp_data["operator"],
                photo_url=camp_data["photo_url"],
                photos_count=camp_data["photos_count"],
                rating=camp_data["rating"],
                reviews_count=camp_data["reviews_count"],
                slug=camp_data["slug"],
                price_low=camp_data["price_low"],
                price_high=camp_data["price_high"]
            )
            session.add(campground)
            await session.flush()
            
            # Process camper types
            for ct_name in camp_data["camper_types"]:
                # Check if camper type exists
                ct = await session.execute(
                    f"SELECT id FROM camper_types WHERE name = '{ct_name}'"
                )
                ct_id = ct.scalar()
                
                if not ct_id:
                    # Create new camper type
                    camper_type = CamperType(name=ct_name)
                    session.add(camper_type)
                    await session.flush()
                    ct_id = camper_type.id
                
                # Add relationship
                await session.execute(
                    f"INSERT INTO campground_camper_types (campground_id, camper_type_id) VALUES ('{campground.id}', {ct_id})"
                )
            
            # Process accommodation types
            for at_name in camp_data["accommodation_types"]:
                # Check if accommodation type exists
                at = await session.execute(
                    f"SELECT id FROM accommodation_types WHERE name = '{at_name}'"
                )
                at_id = at.scalar()
                
                if not at_id:
                    # Create new accommodation type
                    acc_type = AccommodationType(name=at_name)
                    session.add(acc_type)
                    await session.flush()
                    at_id = acc_type.id
                
                # Add relationship
                await session.execute(
                    f"INSERT INTO campground_accommodation_types (campground_id, accommodation_type_id) VALUES ('{campground.id}', {at_id})"
                )
            
            # Add photo URLs
            for url in camp_data["photo_urls"]:
                photo = PhotoUrl(
                    campground_id=campground.id,
                    url=url
                )
                session.add(photo)
        
        # Commit all changes
        await session.commit()
        
        logger.success(f"Successfully seeded database with {len(SEED_CAMPGROUNDS)} campgrounds.")

if __name__ == "__main__":
    asyncio.run(seed_database())