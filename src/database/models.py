#models.py
"""
Database models for the campground scraper.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Table, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.sql import func

Base = declarative_base()

# Association table for campground-camper_type many-to-many relationship
campground_camper_types = Table(
    'campground_camper_types',
    Base.metadata,
    Column('campground_id', String, ForeignKey('campgrounds.id', ondelete='CASCADE'), primary_key=True),
    Column('camper_type_id', Integer, ForeignKey('camper_types.id', ondelete='CASCADE'), primary_key=True)
)

# Association table for campground-accommodation_type many-to-many relationship
campground_accommodation_types = Table(
    'campground_accommodation_types',
    Base.metadata,
    Column('campground_id', String, ForeignKey('campgrounds.id', ondelete='CASCADE'), primary_key=True),
    Column('accommodation_type_id', Integer, ForeignKey('accommodation_types.id', ondelete='CASCADE'), primary_key=True)
)


class Campground(Base):
    """
    Campground model for database storage
    """
    __tablename__ = 'campgrounds'

    id = Column(String, primary_key=True)
    type = Column(String)
    links_self = Column(String)
    name = Column(String, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    region_name = Column(String)
    administrative_area = Column(String)
    nearest_city_name = Column(String)
    bookable = Column(Boolean, default=False)
    operator = Column(String)
    photo_url = Column(String)
    photos_count = Column(Integer, default=0)
    rating = Column(Float)
    reviews_count = Column(Integer, default=0)
    slug = Column(String)
    price_low = Column(Float)
    price_high = Column(Float)
    availability_updated_at = Column(DateTime)
    address = Column(String)  # Bonus field for geocoding
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    camper_types = relationship("CamperType", secondary=campground_camper_types, back_populates="campgrounds")
    accommodation_types = relationship("AccommodationType", secondary=campground_accommodation_types, back_populates="campgrounds")
    photo_urls = relationship("PhotoUrl", back_populates="campground", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Campground {self.name}>"


class CamperType(Base):
    """
    Camper Type model for database storage
    """
    __tablename__ = 'camper_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now())

    # Relationship
    campgrounds = relationship("Campground", secondary=campground_camper_types, back_populates="camper_types")

    def __repr__(self):
        return f"<CamperType {self.name}>"


class AccommodationType(Base):
    """
    Accommodation Type model for database storage
    """
    __tablename__ = 'accommodation_types'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, default=func.now())

    # Relationship
    campgrounds = relationship("Campground", secondary=campground_accommodation_types, back_populates="accommodation_types")

    def __repr__(self):
        return f"<AccommodationType {self.name}>"


class PhotoUrl(Base):
    """
    Photo URL model for database storage
    """
    __tablename__ = 'photo_urls'

    id = Column(Integer, primary_key=True, autoincrement=True)
    campground_id = Column(String, ForeignKey('campgrounds.id', ondelete='CASCADE'))
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())

    # Relationship
    campground = relationship("Campground", back_populates="photo_urls")

    def __repr__(self):
        return f"<PhotoUrl {self.url[:20]}...>"


class ScraperLog(Base):
    """
    Scraper Log model for database storage
    """
    __tablename__ = 'scraper_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    status = Column(String)  # running, success, failed
    records_processed = Column(Integer, default=0)
    records_added = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    errors = Column(JSON)

    def __repr__(self):
        return f"<ScraperLog {self.id} {self.status}>"