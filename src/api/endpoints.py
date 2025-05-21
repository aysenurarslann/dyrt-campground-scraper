# src/api/endpoints.py - Düzeltilmiş versiyon
"""
FastAPI endpoints for The Dyrt scraper
"""
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

from src.config import logger
from src.database.db import get_campgrounds_from_db, get_campground_by_id
from src.models.campground import Campground

# Initialize FastAPI app
app = FastAPI(
    title="The Dyrt Scraper API",
    description="API for accessing scraped campground data",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "The Dyrt Scraper API", "version": "1.0.0"}

@app.get("/campgrounds", response_model=List[Campground])
async def get_campgrounds(
    limit: int = Query(default=100, le=1000, description="Maximum number of campgrounds to return"),
    offset: int = Query(default=0, ge=0, description="Number of campgrounds to skip"),
    state: Optional[str] = Query(default=None, description="Filter by state/administrative area"),
    min_rating: Optional[float] = Query(default=None, ge=0, le=5, description="Minimum rating filter")
):
    """
    Get campgrounds with optional filtering
    """
    try:
        campgrounds = await get_campgrounds_from_db(
            limit=limit, 
            offset=offset, 
            state=state, 
            min_rating=min_rating
        )
        return campgrounds
    except Exception as e:
        logger.error(f"Error fetching campgrounds: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/campgrounds/{campground_id}", response_model=Campground)
async def get_campground(campground_id: str):
    """
    Get a specific campground by ID
    """
    try:
        campground = await get_campground_by_id(campground_id)
        if not campground:
            raise HTTPException(status_code=404, detail="Campground not found")
        return campground
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching campground {campground_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "message": "API is running"}

def start_api():
    """
    Start the API server - DÜZELTILMIŞ VERSİYON
    """
    # Environment variables
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting API server at {API_HOST}:{API_PORT}")
    
    # DÜZELTME: asyncio.run kullanmak yerine direkt uvicorn.run
    uvicorn.run(
        "src.api.endpoints:app",  # Module path to app
        host=API_HOST, 
        port=API_PORT,
        reload=False,  # Production'da False olmalı
        log_level="info"
    )

# Alternative async version (if needed)
async def start_api_async():
    """
    Async version of API starter
    """
    import uvicorn
    
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting API server at {API_HOST}:{API_PORT}")
    
    config = uvicorn.Config(
        app=app,
        host=API_HOST,
        port=API_PORT,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    start_api()
