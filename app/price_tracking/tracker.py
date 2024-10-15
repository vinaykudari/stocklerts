import logging
from collections import defaultdict
from queue import Queue
from typing import Any

from datetime import datetime, timedelta
from app.alerts.notifier import send_notification
from app.database.db_manager import DBManager


def fetch_quote(ticker: str, finnhub_client) -> dict[Any, Any] | Any:
    try:
        quote = finnhub_client.quote(ticker)
        return quote
    except Exception as e:
        logging.error(f'Error fetching price for {ticker}: {e}')
        return defaultdict(int)


def check_stock_price_change(ticker_config: dict, user_notify_thresh: dict, ticker_queue: Queue,
                             finnhub_client, db_manager: DBManager, max_notifications: int) -> None:
    ticker = ticker_queue.get()
    quote = fetch_quote(ticker, finnhub_client)
    current_price, prev_close, percentage_change = quote['c'], quote['pc'], quote['dp']

    logging.debug(
        f"Ticker: {ticker}, Current Price: {current_price}, "
        f"Previous close: {prev_close}, Percentage Change: {percentage_change}%"
    )
    logging.debug(f'ticker_config[{ticker}] = {ticker_config[ticker]}')

    users_to_notify = set()

    for threshold_config in ticker_config[ticker]:
        threshold, users = threshold_config['value'], threshold_config['users']

        # positive: stock price below the threshold
        if threshold >= 0 and threshold > percentage_change:
            continue

        # negative: stock price above the threshold
        if threshold < 0 and threshold < percentage_change:
            continue

        for user_id in users:
            user_notification_count = db_manager.get_user_notification_count(user_id)

            if user_notification_count == 0.9 * max_notifications:
                message = f'User {user_id} has almost reached the daily notification limit.'
                logging.info(message)
                send_notification(message, {user_id})

            # notification count check: alertz limitation
            if user_notification_count >= max_notifications:
                logging.warning(f'User {user_id} has reached the daily notification limit.')
                continue

            # cooldown notifications
            alerted, last_alert_thresh = db_manager.get_ticker_state(user_id, ticker)
            if alerted:
                if last_alert_thresh:
                    if threshold < 0:
                        if percentage_change > last_alert_thresh - user_notify_thresh[user_id]:
                            continue
                    else:
                        if percentage_change < last_alert_thresh + user_notify_thresh[user_id]:
                            continue

            users_to_notify.add(user_id)

    if len(users_to_notify) > 0:
        message = f"{ticker} price has changed by {percentage_change:.2f}% ({prev_close} to {current_price})"
        logging.debug(message)
        logging.info(f'For {ticker} notifying {list(users_to_notify)}')
        if send_notification(message, users_to_notify):
            for user_id in users_to_notify:
                db_manager.set_ticker_alerted(user_id, ticker, percentage_change)
                db_manager.increment_notification_count(user_id)

    logging.debug(f'Putting ticker {ticker} back in queue')
    ticker_queue.put(ticker)
