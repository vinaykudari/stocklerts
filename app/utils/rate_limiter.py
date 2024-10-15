from functools import wraps

import logging
import pytz
from datetime import datetime, time

MARKET_OPEN_TIME = time(9, 30)
MARKET_CLOSE_TIME = time(16, 0)
MARKET_TIMEZONE = pytz.timezone('US/Eastern')


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
                logging.warning("Market is now OPEN. Starting stock price checks.")
            else:
                logging.warning("Market is now CLOSED. Stopping stock price checks.")
            wrapper.previous_state = current_state

        return func(*args, **kwargs)

    return wrapper
