#main.py

import argparse

import asyncio

from src.config import logger
from src.database.db import init_db
from src.scraper.dyrt_scraper import DyrtScraper
from src.utils.scheduler import setup_scheduler
from src.api.endpoints import start_api


async def main():
    parser = argparse.ArgumentParser(description='The Dyrt Web Scraper')
    parser.add_argument('--scrape', action='store_true', help='Run scraper immediately')
    parser.add_argument('--schedule', action='store_true', help='Setup scheduled scraping')
    parser.add_argument('--api', action='store_true', help='Start API server')
    parser.add_argument('--test', action='store_true', help='Run API test')  # Test için yeni argüman
    args = parser.parse_args()

    # Initialize the database
    logger.info("Initializing database...")
    await init_db()
    
    if args.test:
        # Run API test
        logger.info("Running API test...")
        from src.scraper.dyrt_scraper import test_api_request
        await test_api_request()
        return
    
    if args.scrape:
        # Run scraper once
        logger.info("Starting scraper...")
        scraper = DyrtScraper()
        await scraper.run()
        
    if args.schedule:
        # Setup scheduled scraping
        logger.info("Setting up scheduler...")
        setup_scheduler()
        
    if args.api:
        # Start API server
        logger.info("Starting API server...")
        start_api()
    
    # If no arguments provided, run scraper once
    if not any(vars(args).values()):
        logger.info("No arguments provided. Running scraper once...")
        scraper = DyrtScraper()
        await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
