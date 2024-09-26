import logging
import yaml
from app.scheduler.job_scheduler import start_scheduler
from app.database.db_manager import DBManager


def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def setup_logging(log_file: str) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def main() -> None:
    config = load_config('config.yaml')
    setup_logging('logs/app.log')

    db_manager = DBManager()

    max_quote_calls_per_min = config['defaults'].get('max_quote_calls_per_min', 60)
    cooldown_minutes = config['defaults'].get('cooldown_period_minutes', 60)
    max_notifications = config['defaults'].get('max_notifications_per_day', 100)

    ticker_config = {}
    for item in config['tickers']:
        symbol = item['symbol']
        ticker_config[symbol] = item['threshold']

    logging.info('Starting Stock Price Alert Tracker.')
    start_scheduler(
        db_manager,
        ticker_config,
        cooldown_minutes,
        max_notifications,
        max_quote_calls_per_min
    )

    try:
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logging.info('Shutting down Stock Price Alert Tracker.')


if __name__ == '__main__':
    main()
