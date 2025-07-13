import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from queue import Queue
from collections import defaultdict

# Import the actual service functions
from app.services.price_tracker_service import (
    fetch_quote,
    check_stock_price_change
)


class TestPriceTrackerService(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_finnhub_client = Mock()
        self.mock_db_manager = Mock()
        self.ticker_queue = Queue()
        self.ticker_config = {
            'AAPL': {'positive_threshold': 3.0, 'negative_threshold': -3.0},
            'GOOGL': {'positive_threshold': 2.5, 'negative_threshold': -2.5}
        }
        self.user_notify_threshold = 5
        self.max_notifications = 10

        # Add test tickers to queue
        self.ticker_queue.put('AAPL')
        self.ticker_queue.put('GOOGL')

    def test_fetch_quote_success(self):
        """Test successful quote fetching."""
        # Arrange
        expected_quote = {
            'c': 150.0,  # current price
            'pc': 145.0,  # previous close
            'o': 148.0,   # open price
            'h': 152.0,   # high
            'l': 147.0    # low
        }
        self.mock_finnhub_client.quote.return_value = expected_quote

        # Act
        result = fetch_quote('AAPL', self.mock_finnhub_client)

        # Assert
        self.assertEqual(result, expected_quote)
        self.mock_finnhub_client.quote.assert_called_once_with('AAPL')

    def test_fetch_quote_exception(self):
        """Test quote fetching with an exception."""
        # Arrange
        self.mock_finnhub_client.quote.side_effect = Exception("API Error")

        # Act
        result = fetch_quote('AAPL', self.mock_finnhub_client)

        # Assert
        self.assertIsInstance(result, defaultdict)
        self.assertEqual(result['c'], 0)  # defaultdict returns 0 for missing keys

    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_market_closed(self, mock_is_market_open):
        """Test the function returns early when the market is closed."""
        # Arrange
        mock_is_market_open.return_value = False

        # Act
        result = check_stock_price_change(
            self.ticker_queue,
            self.mock_finnhub_client,
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_threshold,
            self.max_notifications
        )

        # Assert
        self.assertIsNone(result)
        mock_is_market_open.assert_called_once()

    @patch('app.services.price_tracker_service.send_notification')
    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_positive_threshold_triggered(self, mock_is_market_open, mock_send_notification):
        """Test positive threshold triggering notification."""
        # Arrange
        mock_is_market_open.return_value = True
        mock_send_notification.return_value = True
        
        # Mock quote data - 6% increase triggers 5% threshold
        quote_data = {'c': 150.0, 'pc': 141.5, 'dp': 6.0}
        self.mock_finnhub_client.quote.return_value = quote_data
        
        # Mock database responses
        self.mock_db_manager.get_user_notification_count.return_value = 5
        self.mock_db_manager.get_ticker_state.return_value = (False, None)
        
        # Act
        check_stock_price_change(
            self.ticker_config, self.user_notify_thresh, self.ticker_queue,
            self.mock_finnhub_client, self.mock_db_manager, self.max_notifications
        )
        
        # Assert
        mock_send_notification.assert_called_once()
        self.mock_db_manager.set_ticker_alerted.assert_called()
        self.mock_db_manager.increment_notification_count.assert_called()

    @patch('app.services.price_tracker_service.send_notification')
    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_negative_threshold_triggered(self, mock_is_market_open, mock_send_notification):
        """Test negative threshold triggering notification."""
        # Arrange
        mock_is_market_open.return_value = True
        mock_send_notification.return_value = True
        
        # Mock quote data - -4% decrease triggers -3% threshold
        quote_data = {'c': 140.0, 'pc': 145.8, 'dp': -4.0}
        self.mock_finnhub_client.quote.return_value = quote_data
        
        # Mock database responses
        self.mock_db_manager.get_user_notification_count.return_value = 5
        self.mock_db_manager.get_ticker_state.return_value = (False, None)
        
        # Act
        check_stock_price_change(
            self.ticker_config, self.user_notify_thresh, self.ticker_queue,
            self.mock_finnhub_client, self.mock_db_manager, self.max_notifications
        )
        
        # Assert
        mock_send_notification.assert_called_once()
        self.mock_db_manager.set_ticker_alerted.assert_called()

    @patch('app.services.price_tracker_service.send_notification')
    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_threshold_not_triggered(self, mock_is_market_open, mock_send_notification):
        """Test when thresholds are not triggered."""
        # Arrange
        mock_is_market_open.return_value = True
        
        # Mock quote data - 2% increase doesn't trigger 5% threshold
        quote_data = {'c': 148.0, 'pc': 145.0, 'dp': 2.0}
        self.mock_finnhub_client.quote.return_value = quote_data
        
        # Act
        check_stock_price_change(
            self.ticker_config, self.user_notify_thresh, self.ticker_queue,
            self.mock_finnhub_client, self.mock_db_manager, self.max_notifications
        )
        
        # Assert
        mock_send_notification.assert_not_called()

    @patch('app.services.price_tracker_service.send_notification')
    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_max_notifications_reached(self, mock_is_market_open, mock_send_notification):
        """Test when user has reached max notifications."""
        # Arrange
        mock_is_market_open.return_value = True
        
        # Mock quote data that would trigger threshold
        quote_data = {'c': 150.0, 'pc': 141.5, 'dp': 6.0}
        self.mock_finnhub_client.quote.return_value = quote_data
        
        # Mock database responses - user has reached max notifications
        self.mock_db_manager.get_user_notification_count.return_value = self.max_notifications
        self.mock_db_manager.get_ticker_state.return_value = (False, None)
        
        # Act
        check_stock_price_change(
            self.ticker_config, self.user_notify_thresh, self.ticker_queue,
            self.mock_finnhub_client, self.mock_db_manager, self.max_notifications
        )
        
        # Assert
        mock_send_notification.assert_not_called()

    @patch('app.services.price_tracker_service.send_notification')
    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_cooldown_active(self, mock_is_market_open, mock_send_notification):
        """Test when cooldown is active for a ticker."""
        # Arrange
        mock_is_market_open.return_value = True
        
        # Mock quote data
        quote_data = {'c': 150.0, 'pc': 141.5, 'dp': 6.0}
        self.mock_finnhub_client.quote.return_value = quote_data
        
        # Mock database responses - ticker already alerted with similar threshold
        self.mock_db_manager.get_user_notification_count.return_value = 5
        self.mock_db_manager.get_ticker_state.return_value = (True, 5.5)  # Already alerted at 5.5%
        
        # Act
        check_stock_price_change(
            self.ticker_config, self.user_notify_thresh, self.ticker_queue,
            self.mock_finnhub_client, self.mock_db_manager, self.max_notifications
        )
        
        # Assert
        mock_send_notification.assert_not_called()

    @patch('app.services.price_tracker_service.is_market_open')
    def test_ticker_queue_management(self, mock_is_market_open):
        """Test that the ticker is put back in the queue after processing."""
        # Arrange
        mock_is_market_open.return_value = True

        # Mock quote
        quote = {
            'c': 147.0,   # current price
            'pc': 145.0,  # previous close
        }
        self.mock_finnhub_client.quote.return_value = quote

        initial_queue_size = self.ticker_queue.qsize()

        # Act
        check_stock_price_change(
            self.ticker_queue,
            self.mock_finnhub_client,
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_threshold,
            self.max_notifications
        )

        # Assert
        # Queue should have the same size (ticker put back)
        self.assertEqual(self.ticker_queue.qsize(), initial_queue_size)

    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_empty_queue(self, mock_is_market_open):
        """Test behavior when queue is empty."""
        # Arrange
        mock_is_market_open.return_value = True
        empty_queue = Queue()

        # Act
        result = check_stock_price_change(
            empty_queue,
            self.mock_finnhub_client,
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_threshold,
            self.max_notifications
        )

        # Assert
        self.assertIsNone(result)

    @patch('app.services.price_tracker_service.is_market_open')
    def test_check_stock_price_change_invalid_ticker_config(self, mock_is_market_open):
        """Test behavior with invalid ticker configuration."""
        # Arrange
        mock_is_market_open.return_value = True

        # Mock quote
        quote = {
            'c': 150.0,   # current price
            'pc': 145.0,  # previous close
        }
        self.mock_finnhub_client.quote.return_value = quote

        # Use empty ticker config
        empty_config = {}

        # Act
        check_stock_price_change(
            self.ticker_queue,
            self.mock_finnhub_client,
            self.mock_db_manager,
            empty_config,  # Empty config
            self.user_notify_threshold,
            self.max_notifications
        )

        # Assert - should handle gracefully without crashing
        # The ticker should still be put back in the queue
        self.assertGreater(self.ticker_queue.qsize(), 0)


if __name__ == '__main__':
    unittest.main()