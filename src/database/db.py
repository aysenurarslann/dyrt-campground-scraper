#db.py
"""
Database connection and operations
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from sqlalchemy import create_engine, select, update, exists
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import sessionmaker

from src.config import DB_URL, logger
from src.database.models import Base, Campground, CamperType, AccommodationType, PhotoUrl, ScraperLog
from src.models.campground import Campground as CampgroundModel


# Create async engine
async_engine = create_async_engine(
    DB_URL.replace('postgresql://', 'postgresql+asyncpg://'),
    echo=False,
    future=True
)
async_session_factory = async_sessionmaker(async_engine, expire_on_commit=False)


async def init_db():
    """
    Initialize the database with the needed tables
    """
    try:
        # Create tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        logger.success("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def get_db_session() -> AsyncSession:
    """
    Get a database session
    """
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


async def save_campgrounds(campgrounds: List[CampgroundModel]) -> Dict[str, int]:
    """
    Save campgrounds to the database
    """
    session = async_session_factory()
    added_count = 0
    updated_count = 0
    scraper_log = None
    
    try:
        # Start a scraper log
        scraper_log = ScraperLog(
            start_time=datetime.utcnow(),
            status="running",
            records_processed=len(campgrounds)
        )
        session.add(scraper_log)
        await session.commit()
        await session.refresh(scraper_log)  # Refresh to get the ID
        
        for camp_model in campgrounds:
            # Check if campground already exists
            stmt = select(Campground).where(Campground.id == camp_model.id)
            result = await session.execute(stmt)
            existing_camp = result.scalars().first()
            
            if existing_camp:
                # Update existing campground
                existing_camp.name = camp_model.name
                existing_camp.latitude = camp_model.latitude
                existing_camp.longitude = camp_model.longitude
                existing_camp.region_name = camp_model.region_name
                existing_camp.administrative_area = camp_model.administrative_area
                existing_camp.nearest_city_name = camp_model.nearest_city_name
                existing_camp.bookable = camp_model.bookable
                existing_camp.operator = camp_model.operator
                existing_camp.photo_url = str(camp_model.photo_url) if camp_model.photo_url else None
                existing_camp.photos_count = camp_model.photos_count
                existing_camp.rating = camp_model.rating
                existing_camp.reviews_count = camp_model.reviews_count
                existing_camp.slug = camp_model.slug
                existing_camp.price_low = camp_model.price_low
                existing_camp.price_high = camp_model.price_high
                existing_camp.availability_updated_at = camp_model.availability_updated_at
                
                # Clear existing relationships before updating
                existing_camp.camper_types = []
                existing_camp.accommodation_types = []
                await session.commit()
                
                updated_count += 1
                camp_obj = existing_camp
            else:
                # Create new campground
                new_camp = Campground(
                    id=camp_model.id,
                    type=camp_model.type,
                    links_self=str(camp_model.links.get("self", "")),
                    name=camp_model.name,
                    latitude=camp_model.latitude,
                    longitude=camp_model.longitude,
                    region_name=camp_model.region_name,
                    administrative_area=camp_model.administrative_area,
                    nearest_city_name=camp_model.nearest_city_name,
                    bookable=camp_model.bookable,
                    operator=camp_model.operator,
                    photo_url=str(camp_model.photo_url) if camp_model.photo_url else None,
                    photos_count=camp_model.photos_count,
                    rating=camp_model.rating,
                    reviews_count=camp_model.reviews_count,
                    slug=camp_model.slug,
                    price_low=camp_model.price_low,
                    price_high=camp_model.price_high,
                    availability_updated_at=camp_model.availability_updated_at,
                )
                session.add(new_camp)
                await session.commit()
                await session.refresh(new_camp)  # Refresh to get the ID
                
                added_count += 1
                camp_obj = new_camp
            
            # Process camper types
            for camper_type_name in camp_model.camper_types:
                # Check if camper type exists
                stmt = select(CamperType).where(CamperType.name == camper_type_name)
                result = await session.execute(stmt)
                camper_type = result.scalars().first()
                
                if not camper_type:
                    camper_type = CamperType(name=camper_type_name)
                    session.add(camper_type)
                    await session.commit()
                    await session.refresh(camper_type)  # Refresh to get the ID
                
                # Add camper type to campground
                camp_obj.camper_types.append(camper_type)
            
            # Process accommodation types
            for acc_type_name in camp_model.accommodation_type_names:
                # Check if accommodation type exists
                stmt = select(AccommodationType).where(AccommodationType.name == acc_type_name)
                result = await session.execute(stmt)
                acc_type = result.scalars().first()
                
                if not acc_type:
                    acc_type = AccommodationType(name=acc_type_name)
                    session.add(acc_type)
                    await session.commit()
                    await session.refresh(acc_type)  # Refresh to get the ID
                
                # Add accommodation type to campground
                camp_obj.accommodation_types.append(acc_type)
            
            # Process photo URLs - Clear existing ones first
            # Delete existing photo URLs
            if camp_obj.photo_urls:
                for photo in camp_obj.photo_urls:
                    await session.delete(photo)
                await session.commit()
                
            # Add new photo URLs
            for photo_url in camp_model.photo_urls:
                photo = PhotoUrl(
                    campground_id=camp_obj.id,
                    url=str(photo_url)
                )
                session.add(photo)
            
            await session.commit()
        
        # Update scraper log
        if scraper_log:
            scraper_log.end_time = datetime.utcnow()
            scraper_log.status = "success"
            scraper_log.records_added = added_count
            scraper_log.records_updated = updated_count
            await session.commit()
        
        return {"added": added_count, "updated": updated_count}
    except Exception as e:
        logger.error(f"Error saving campgrounds: {e}")
        # Update scraper log if it exists
        if scraper_log:
            scraper_log.end_time = datetime.utcnow()
            scraper_log.status = "failed"
            scraper_log.errors = {"message": str(e)}
            await session.commit()
        raise
    finally:
        await session.close()


async def get_all_campgrounds() -> List[Dict[str, Any]]:
    """
    Get all campgrounds from the database
    """
    session = async_session_factory()
    try:
        stmt = select(Campground)
        result = await session.execute(stmt)
        campgrounds = result.scalars().all()
        
        # Convert to dict
        campgrounds_list = []
        for camp in campgrounds:
            campgrounds_list.append({
                "id": camp.id,
                "name": camp.name,
                "latitude": camp.latitude,
                "longitude": camp.longitude,
                "region_name": camp.region_name,
                "administrative_area": camp.administrative_area,
                "nearest_city_name": camp.nearest_city_name,
                "bookable": camp.bookable,
                "operator": camp.operator,
                "rating": camp.rating,
                "reviews_count": camp.reviews_count,
                "price_low": camp.price_low,
                "price_high": camp.price_high,
                "updated_at": camp.updated_at.isoformat() if camp.updated_at else None,
            })
        
        return campgrounds_list
    except Exception as e:
        logger.error(f"Error getting campgrounds: {e}")
        raise
    finally:
        await session.close()


async def get_campground_by_id(camp_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a campground by ID
    """
    session = async_session_factory()
    try:
        stmt = select(Campground).where(Campground.id == camp_id)
        result = await session.execute(stmt)
        camp = result.scalars().first()
        
        if not camp:
            return None
        
        # Get related data
        camper_types = [ct.name for ct in camp.camper_types]
        accommodation_types = [at.name for at in camp.accommodation_types]
        photo_urls = [pu.url for pu in camp.photo_urls]
        
        # Convert to dict
        camp_dict = {
            "id": camp.id,
            "type": camp.type,
            "links_self": camp.links_self,
            "name": camp.name,
            "latitude": camp.latitude,
            "longitude": camp.longitude,
            "region_name": camp.region_name,
            "administrative_area": camp.administrative_area,
            "nearest_city_name": camp.nearest_city_name,
            "bookable": camp.bookable,
            "operator": camp.operator,
            "photo_url": camp.photo_url,
            "photos_count": camp.photos_count,
            "rating": camp.rating,
            "reviews_count": camp.reviews_count,
            "slug": camp.slug,
            "price_low": camp.price_low,
            "price_high": camp.price_high,
            "availability_updated_at": camp.availability_updated_at.isoformat() if camp.availability_updated_at else None,
            "address": camp.address,
            "camper_types": camper_types,
            "accommodation_types": accommodation_types,
            "photo_urls": photo_urls,
            "created_at": camp.created_at.isoformat(),
            "updated_at": camp.updated_at.isoformat(),
        }
        
        return camp_dict
    except Exception as e:
        logger.error(f"Error getting campground by ID: {e}")
        raise
    finally:
        await session.close()


async def get_scraper_logs() -> List[Dict[str, Any]]:
    """
    Get all scraper logs
    """
    session = async_session_factory()
    try:
        stmt = select(ScraperLog).order_by(ScraperLog.start_time.desc())
        result = await session.execute(stmt)
        logs = result.scalars().all()
        
        # Convert to dict
        logs_list = []
        for log in logs:
            logs_list.append({
                "id": log.id,
                "start_time": log.start_time.isoformat(),
                "end_time": log.end_time.isoformat() if log.end_time else None,
                "status": log.status,
                "records_processed": log.records_processed,
                "records_added": log.records_added,
                "records_updated": log.records_updated,
                "errors": log.errors,
            })
        
        return logs_list
    except Exception as e:
        logger.error(f"Error getting scraper logs: {e}")
        raise
    finally:
        await session.close()