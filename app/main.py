import logging

from app.scheduler.job_scheduler import start_scheduler
from app.database.db_manager import DBManager
from app.utils.helper import load_config, setup_logging
from app.health_server import start_health_server


def main() -> None:
    config = load_config('config.yaml')
    accounts = config['alertzy']['accounts']
    user_notify_thresh = {}

    for account in accounts:
        user_id = account['user_id']
        thresh = account['notify_thresh']
        user_notify_thresh[user_id] = thresh

    setup_logging('logs/app.log')

    db_manager = DBManager()

    max_quote_calls_per_min = config['defaults'].get('max_quote_calls_per_min', 60)
    max_notifications = config['defaults'].get('max_notifications_per_day', 100)

    ticker_config = {}
    for item in config['tickers']:
        symbol = item['symbol']
        ticker_config[symbol] = item['threshold']

    logging.info('Starting Stock Price Alert Tracker.')
    start_scheduler(
        db_manager,
        ticker_config,
        user_notify_thresh,
        max_notifications,
        max_quote_calls_per_min
    )
    # Start lightweight health check server in the background
    start_health_server()

    try:
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logging.info('Shutting down Stock Price Alert Tracker.')


if __name__ == '__main__':
    main()
