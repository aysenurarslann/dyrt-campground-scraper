#main.py
"""
Main entrypoint for The Dyrt web scraper case study.

Usage:
    The scraper can be run directly (`python main.py`) or via Docker Compose (`docker compose up`).

If you have any questions in mind you can connect to me directly via info@smart-maple.com
"""
import argparse
import asyncio

from src.config import logger
from src.database.db import init_db
from src.scraper.dyrt_scraper import DyrtScraper
from src.utils.scheduler import setup_scheduler


async def async_main():
    """Async main function for scraper operations"""
    parser = argparse.ArgumentParser(description='The Dyrt Web Scraper')
    parser.add_argument('--scrape', action='store_true', help='Run scraper immediately')
    parser.add_argument('--schedule', action='store_true', help='Setup scheduled scraping')
    parser.add_argument('--api', action='store_true', help='Start API server')
    parser.add_argument('--test', action='store_true', help='Run API test')
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
        
    # If no arguments provided, run scraper once
    if not any(vars(args).values()):
        logger.info("No arguments provided. Running scraper once...")
        scraper = DyrtScraper()
        await scraper.run()


def main():
    """Main function - handles API vs async operations"""
    parser = argparse.ArgumentParser(description='The Dyrt Web Scraper')
    parser.add_argument('--scrape', action='store_true', help='Run scraper immediately')
    parser.add_argument('--schedule', action='store_true', help='Setup scheduled scraping')
    parser.add_argument('--api', action='store_true', help='Start API server')
    parser.add_argument('--test', action='store_true', help='Run API test')
    args = parser.parse_args()
    
    if args.api:
        # Start API server synchronously
        logger.info("Starting API server...")
        from src.api.endpoints import start_api
        start_api()
    else:
        # Run async operations
        asyncio.run(async_main())


if __name__ == "__main__":
    main()
