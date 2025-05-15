#scheduler.py
"""
Scheduler for running the scraper at regular intervals
"""
import asyncio
import threading
from datetime import datetime, timedelta
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import SCHEDULE_INTERVAL, logger
from src.scraper.dyrt_scraper import DyrtScraper


def run_scraper():
    """
    Run the scraper as a background task
    """
    logger.info(f"Scheduled scraper running at {datetime.now()}")
    
    # Create an event loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Run the scraper
    scraper = DyrtScraper()
    try:
        result = loop.run_until_complete(scraper.run())
        logger.success(f"Scheduled scraper completed: {result}")
    except Exception as e:
        logger.error(f"Error in scheduled scraper: {e}")
    finally:
        loop.close()


def setup_scheduler():
    """
    Setup the background scheduler to run the scraper at regular intervals
    """
    scheduler = BackgroundScheduler()
    
    # Add job to run every X hours (from config)
    scheduler.add_job(
        run_scraper,
        IntervalTrigger(hours=SCHEDULE_INTERVAL),
        id='scraper_job',
        name='Run scraper at regular intervals',
        replace_existing=True,
        next_run_time=datetime.now()  # Run immediately when starting
    )
    
    # Start the scheduler
    scheduler.start()
    logger.info(f"Scheduler started. Will run every {SCHEDULE_INTERVAL} hours.")
    
    return scheduler


if __name__ == "__main__":
    # For testing the scheduler
    scheduler = setup_scheduler()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()