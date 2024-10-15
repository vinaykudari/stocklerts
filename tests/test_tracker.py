from queue import Queue
from unittest.mock import MagicMock

import pytest
from datetime import timedelta, date

from app.price_tracking.tracker import check_stock_price_change


@pytest.fixture
def mock_finnhub_client(mocker):
    return mocker.Mock()


@pytest.fixture
def mock_db_manager(mocker):
    return mocker.Mock()


@pytest.fixture
def mock_ticker_queue():
    queue_mock = MagicMock(spec=Queue)
    return queue_mock


@pytest.fixture
def mock_send_notification(mocker):
    return mocker.patch('app.price_tracking.tracker.send_notification')


def test_check_stock_price_change_threshold_met(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': 2.0, 'users': [1, 2]}]
    }
    user_notify_thresh = {1: 1}

    mock_ticker_queue.get.return_value = 'AAPL'
    mock_finnhub_client.quote.return_value = {'c': 150, 'pc': 140, 'dp': 7.14}
    mock_db_manager.get_user_notification_count.return_value = 0
    mock_db_manager.get_ticker_state.return_value = (False, None)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_ticker_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    assert mock_send_notification.call_count == 1
    assert mock_db_manager.set_ticker_alerted.call_count == 2
    assert mock_db_manager.increment_notification_count.call_count == 2


def test_check_stock_price_change_threshold_met_partially(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                          mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': 2.0, 'users': [1]},
                 {'value': 12.0, 'users': [2]}],
    }
    user_notify_thresh = {1: 1}

    mock_ticker_queue.get.return_value = 'AAPL'
    mock_finnhub_client.quote.return_value = {'c': 150, 'pc': 140, 'dp': 7.14}
    mock_db_manager.get_user_notification_count.return_value = 0
    mock_db_manager.get_ticker_state.return_value = (False, None)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_ticker_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    assert mock_send_notification.call_count == 1
    assert mock_db_manager.set_ticker_alerted.call_count == 1
    mock_db_manager.increment_notification_count.assert_any_call(1)


def test_check_stock_price_change_neg_threshold_met_partially(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                              mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': -5.0, 'users': [1]},
                 {'value': -7.0, 'users': [2, 3]}],
        'GOOGL': [{'value': -5.0, 'users': [1]},
                  {'value': -7.0, 'users': [2]}],
    }
    user_notify_thresh = {1: 1, 2: 1, 3: 1}

    mock_queue = MagicMock(spec=Queue)
    mock_queue.get.side_effect = ['GOOGL', 'AAPL']

    mock_finnhub_client = MagicMock()
    mock_finnhub_client.quote.side_effect = lambda ticker: {'dp': -5, 'c': 95, 'pc': 100} \
        if ticker == 'GOOGL' else {'dp': -10, 'c': 90, 'pc': 100}

    mock_db_manager = MagicMock()
    mock_db_manager.get_user_notification_count.return_value = 0
    mock_db_manager.get_ticker_state.return_value = (False, None)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    assert mock_send_notification.call_count == 1
    assert mock_db_manager.set_ticker_alerted.call_count == 1
    mock_db_manager.increment_notification_count.assert_any_call(1)
    mock_db_manager.get_ticker_state.return_value = (False, -5.5)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    assert mock_send_notification.call_count == 2
    assert mock_db_manager.set_ticker_alerted.call_count == 4
    mock_db_manager.increment_notification_count.assert_any_call(3)


def test_check_stock_price_change_threshold_not_met(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                    mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': 10.0, 'users': [1, 2]}]
    }
    user_notify_thresh = {1: 1}

    mock_ticker_queue.get.return_value = 'AAPL'
    mock_finnhub_client.quote.return_value = {'c': 150, 'pc': 140, 'dp': 7.14}
    mock_db_manager.get_user_notification_count.return_value = 0
    mock_db_manager.get_ticker_state.return_value = (False, None)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_ticker_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    mock_send_notification.assert_not_called()
    mock_db_manager.set_ticker_alerted.assert_not_called()
    mock_db_manager.increment_notification_count.assert_not_called()


def test_check_stock_price_change_less_than_notify_thresh(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                          mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': 2.0, 'users': [1]}]
    }
    user_notify_thresh = {1: 1}

    mock_ticker_queue.get.return_value = 'AAPL'
    mock_finnhub_client.quote.return_value = {'c': 150, 'pc': 140, 'dp': 3}
    mock_db_manager.get_user_notification_count.return_value = 0
    mock_db_manager.get_ticker_state.return_value = (True, 2.1)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_ticker_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    mock_send_notification.assert_not_called()
    mock_db_manager.set_ticker_alerted.assert_not_called()
    mock_db_manager.increment_notification_count.assert_not_called()


def test_check_stock_price_change_resets_after_exceeding_limit(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                               mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': 2.0, 'users': [1]}]
    }
    user_notify_thresh = {1: 1}

    mock_ticker_queue.get.return_value = 'AAPL'
    mock_finnhub_client.quote.return_value = {'c': 150, 'pc': 140, 'dp': 7.14}

    user = MagicMock()
    user.notification_count = 11
    user.last_notification_date = date.today() - timedelta(days=1)

    def reset_daily_count():
        if user.last_notification_date < date.today():
            user.notification_count = 0
            user.last_notification_date = date.today()

    user.reset_daily_count.side_effect = reset_daily_count

    mock_db_manager.get_user_notification_count.side_effect = lambda user_id: user.notification_count
    mock_db_manager.reset_daily_counters.side_effect = lambda: user.reset_daily_count()
    mock_db_manager.get_ticker_state.return_value = (False, 8.5)

    # simulating a new day
    user.reset_daily_count()

    assert user.notification_count == 0, "The user's notification count should be reset to 0."

    check_stock_price_change(ticker_config, user_notify_thresh, mock_ticker_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    mock_send_notification.assert_called_once()
    mock_db_manager.set_ticker_alerted.assert_called_once()
    mock_db_manager.increment_notification_count.assert_called_once()


def test_check_stock_price_change_more_than_notify_thresh(mock_finnhub_client, mock_db_manager, mock_ticker_queue,
                                                          mock_send_notification):
    ticker_config = {
        'AAPL': [{'value': 2.0, 'users': [1]}]
    }
    user_notify_thresh = {1: 1}

    mock_ticker_queue.get.return_value = 'AAPL'
    mock_finnhub_client.quote.return_value = {'c': 150, 'pc': 140, 'dp': 4.5}
    mock_db_manager.get_user_notification_count.return_value = 0
    mock_db_manager.get_ticker_state.return_value = (True, 3.5)

    check_stock_price_change(ticker_config, user_notify_thresh, mock_ticker_queue,
                             mock_finnhub_client, mock_db_manager, 10)

    assert mock_send_notification.call_count == 1
    assert mock_db_manager.set_ticker_alerted.call_count == 1
    mock_db_manager.increment_notification_count.assert_any_call(1)
