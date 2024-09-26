import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import finnhub
from queue import Queue
from app.database.db_manager import DBManager
import os

from app.stocks.tracker import check_stock_price_change


def start_scheduler(db_manager: DBManager, ticker_config: dict,
                    cooldown_minutes: int = 60, max_notifications: int = 100,
                    max_quote_calls_per_min: int = 60) -> None:
    finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))
    scheduler = BackgroundScheduler()
    interval_seconds = max_quote_calls_per_min // 60

    ticker_queue = Queue()

    for symbol in ticker_config:
        ticker_queue.put(symbol)
        logging.info(f'Added ticker to queue: {symbol}')

    scheduler.add_job(
        func=check_stock_price_change,
        trigger=IntervalTrigger(seconds=interval_seconds),
        args=[ticker_config, ticker_queue, finnhub_client, db_manager, cooldown_minutes, max_notifications],
        id=f'job_check_stock_price_change',
        replace_existing=True
    )
    logging.info(f'Stock price tracker scheduled')

    scheduler.add_job(
        func=db_manager.reset_daily_counters,
        trigger='cron',
        hour=0,
        minute=0,
        id='reset_daily_counters',
        replace_existing=True
    )

    scheduler.start()
    logging.info('Scheduler started.')
