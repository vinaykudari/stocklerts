import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import finnhub
from queue import Queue
from app.database.db_manager import DBManager
import os

from app.price_tracking.tracker import check_stock_price_change
from app.recommendations.daily_recommender import (
    get_daily_recommendations,
    send_daily_performance,
    get_best_daily_performers,
    upload_prompt_to_sheets,
)


def start_scheduler(db_manager: DBManager, ticker_config: dict, user_notify_thresh: dict,
                    max_notifications: int = 100, max_quote_calls_per_min: int = 60) -> None:
    finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))
    scheduler = BackgroundScheduler()
    interval_seconds = (max_quote_calls_per_min // 60) + 1  # add some buffer

    ticker_queue = Queue()

    for symbol in ticker_config:
        ticker_queue.put(symbol)
        logging.warning(f'Added ticker to queue: {symbol}')

    scheduler.add_job(
        func=check_stock_price_change,
        trigger=IntervalTrigger(seconds=interval_seconds),
        args=[ticker_config, user_notify_thresh, ticker_queue, finnhub_client, db_manager, max_notifications],
        id=f'job_check_stock_price_change',
        max_instances=3,
        replace_existing=True
    )
    logging.warning(f'Stock price tracker scheduled')

    scheduler.add_job(
        func=db_manager.reset_daily_counters,
        trigger='cron',
        hour=0,
        minute=0,
        id='reset_daily_counters',
        max_instances=3,
        replace_existing=True
    )

    scheduler.add_job(
        func=get_daily_recommendations,
        trigger=CronTrigger(hour=9, minute=30, timezone='US/Eastern', day_of_week='mon-fri'),
        args=[finnhub_client],
        id='daily_recommendations',
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        func=send_daily_performance,
        trigger=CronTrigger(hour=16, minute=0, timezone='US/Eastern', day_of_week='mon-fri'),
        args=[finnhub_client],
        id='daily_performance',
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        func=get_best_daily_performers,
        trigger=CronTrigger(hour=16, minute=5, timezone='US/Eastern', day_of_week='mon-fri'),
        args=[finnhub_client],
        id='best_daily_performers',
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        func=upload_prompt_to_sheets,
        trigger=CronTrigger(hour=8, minute=0, timezone='US/Eastern'),
        id='upload_prompt_tracking',
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    logging.warning('Scheduler started.')
