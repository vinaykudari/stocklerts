import os
from functools import wraps

import logging
import pytz
from datetime import datetime, time

import requests
import yaml

MARKET_OPEN_TIME = time(9, 30)
MARKET_CLOSE_TIME = time(16, 0)
MARKET_TIMEZONE = pytz.timezone('US/Eastern')


def load_config(config_path: str) -> dict:
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)


def setup_logging(log_file: str) -> None:
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )


def is_market_open():
    now = datetime.now(MARKET_TIMEZONE)
    current_time = now.time()
    current_weekday = now.weekday()

    if current_weekday >= 5:
        return False

    if MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME:
        return True
    return False


def state_tracker(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.previous_state = getattr(wrapper, 'previous_state', None)
        current_state = is_market_open()

        if wrapper.previous_state != current_state:
            if current_state:
                logging.warning('Market is now OPEN. Starting stock price checks.')
            else:
                logging.warning('Market is now CLOSED. Stopping stock price checks.')
            wrapper.previous_state = current_state

        return func(*args, **kwargs)

    return wrapper


def heartbeat(url: str):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    logging.debug(f'Heartbeat sent successfully to {url}')
                else:
                    logging.error(f'Failed to send heartbeat to {url}. Status Code: {response.status_code}')
            except Exception as e:
                logging.error(f'Exception occurred while sending heartbeat: {e}')

            return func(*args, **kwargs)

        return wrapper

    return decorator