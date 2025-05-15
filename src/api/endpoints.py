#endpoint.py
"""
API endpoints for controlling the scraper
"""
import asyncio
import threading
from typing import Dict, List, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.config import API_HOST, API_PORT, logger
from src.scraper.dyrt_scraper import DyrtScraper
from src.database.db import get_all_campgrounds, get_campground_by_id, get_scraper_logs
from src.utils.scheduler import setup_scheduler

app = FastAPI(
    title="The Dyrt Scraper API",
    description="API for controlling The Dyrt web scraper",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store scheduler instance
scheduler = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "The Dyrt Scraper API"}


@app.post("/scraper/run", status_code=202)
async def run_scraper(background_tasks: BackgroundTasks):
    """
    Run the scraper in the background
    """
    # Run in background task
    background_tasks.add_task(run_scraper_task)
    
    return {"message": "Scraper started in the background"}


async def run_scraper_task():
    """Background task for running the scraper"""
    logger.info("Starting scraper from API request")
    scraper = DyrtScraper()
    try:
        result = await scraper.run()
        logger.success(f"Scraper completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        raise


@app.get("/scraper/status")
async def get_status():
    """
    Get the status of the scraper
    """
    # Get the latest scraper log
    logs = await get_scraper_logs()
    if not logs:
        return {"status": "Never run"}
    
    latest_log = logs[0]
    return {
        "status": latest_log["status"],
        "last_run": latest_log["start_time"],
        "records_processed": latest_log["records_processed"],
        "records_added": latest_log["records_added"],
        "records_updated": latest_log["records_updated"],
    }


@app.post("/scheduler/start")
async def start_scheduler():
    """
    Start the scheduler
    """
    global scheduler
    if scheduler:
        return {"message": "Scheduler already running"}
    
    scheduler = setup_scheduler()
    return {"message": "Scheduler started"}


@app.post("/scheduler/stop")
async def stop_scheduler():
    """
    Stop the scheduler
    """
    global scheduler
    if not scheduler:
        return {"message": "Scheduler not running"}
    
    scheduler.shutdown()
    scheduler = None
    return {"message": "Scheduler stopped"}


@app.get("/campgrounds")
async def get_campgrounds():
    """
    Get all campgrounds
    """
    campgrounds = await get_all_campgrounds()
    return {"campgrounds": campgrounds, "count": len(campgrounds)}


@app.get("/campgrounds/{campground_id}")
async def get_campground(campground_id: str):
    """
    Get a campground by ID
    """
    campground = await get_campground_by_id(campground_id)
    if not campground:
        raise HTTPException(status_code=404, detail="Campground not found")
    
    return campground


@app.get("/logs")
async def get_logs():
    """
    Get all scraper logs
    """
    logs = await get_scraper_logs()
    return {"logs": logs, "count": len(logs)}


def start_api():
    """
    Start the API server
    """
    # Run in a separate thread
    threading.Thread(
        target=lambda: uvicorn.run(app, host=API_HOST, port=API_PORT, log_level="info"),
        daemon=True
    ).start()
    
    logger.info(f"API server started at http://{API_HOST}:{API_PORT}")