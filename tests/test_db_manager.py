import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from sqlalchemy.orm import sessionmaker

from app.database.db_manager import DBManager, User, TickerState


class TestDBManager(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Use in-memory SQLite database for testing
        self.db_manager = DBManager('sqlite:///:memory:')
        self.test_user_id = 'test_user_123'
        self.test_ticker = 'AAPL'

    def test_get_user_notification_count_new_user(self):
        """Test getting notification count for a new user."""
        # Act
        count = self.db_manager.get_user_notification_count(self.test_user_id)
        
        # Assert
        self.assertEqual(count, 0)

    def test_get_user_notification_count_existing_user(self):
        """Test getting notification count for an existing user."""
        # Arrange - Create user and increment count
        self.db_manager.increment_notification_count(self.test_user_id)
        self.db_manager.increment_notification_count(self.test_user_id)
        
        # Act
        count = self.db_manager.get_user_notification_count(self.test_user_id)
        
        # Assert
        self.assertEqual(count, 2)

    def test_increment_notification_count(self):
        """Test incrementing notification count."""
        # Arrange
        initial_count = self.db_manager.get_user_notification_count(self.test_user_id)
        
        # Act
        self.db_manager.increment_notification_count(self.test_user_id)
        
        # Assert
        new_count = self.db_manager.get_user_notification_count(self.test_user_id)
        self.assertEqual(new_count, initial_count + 1)

    def test_increment_notification_count_nonexistent_user(self):
        """Test incrementing notification count for non-existent user."""
        # Act
        self.db_manager.increment_notification_count('nonexistent_user')
        
        # Assert
        # Should not raise an error, but also shouldn't create the user
        count = self.db_manager.get_user_notification_count('nonexistent_user')
        self.assertEqual(count, 0)  # New user created with 0 count

    def test_get_ticker_state_new_ticker(self):
        """Test getting ticker state for a new ticker."""
        # Act
        alerted, last_alert_thresh = self.db_manager.get_ticker_state(self.test_user_id, self.test_ticker)
        
        # Assert
        self.assertFalse(alerted)
        self.assertIsNone(last_alert_thresh)

    def test_set_ticker_alerted(self):
        """Test setting ticker as alerted."""
        # Arrange
        threshold = 5.5
        
        # Act
        self.db_manager.set_ticker_alerted(self.test_user_id, self.test_ticker, threshold)
        
        # Assert
        alerted, last_alert_thresh = self.db_manager.get_ticker_state(self.test_user_id, self.test_ticker)
        self.assertTrue(alerted)
        self.assertEqual(last_alert_thresh, threshold)

    def test_reset_ticker_alerted(self):
        """Test resetting ticker alert state."""
        # Arrange - First set ticker as alerted
        self.db_manager.set_ticker_alerted(self.test_user_id, self.test_ticker, 5.5)
        
        # Act
        self.db_manager.reset_ticker_alerted(self.test_user_id, self.test_ticker)
        
        # Assert
        alerted, last_alert_thresh = self.db_manager.get_ticker_state(self.test_user_id, self.test_ticker)
        self.assertFalse(alerted)
        self.assertIsNone(last_alert_thresh)

    def test_reset_daily_counters(self):
        """Test resetting daily counters for all users."""
        # Arrange - Create multiple users with notification counts
        user_ids = ['user1', 'user2', 'user3']
        for user_id in user_ids:
            self.db_manager.increment_notification_count(user_id)
            self.db_manager.increment_notification_count(user_id)
        
        # Act
        self.db_manager.reset_daily_counters()
        
        # Assert
        for user_id in user_ids:
            count = self.db_manager.get_user_notification_count(user_id)
            self.assertEqual(count, 0)

    def test_multiple_tickers_same_user(self):
        """Test handling multiple tickers for the same user."""
        # Arrange
        tickers = ['AAPL', 'GOOGL', 'TSLA']
        thresholds = [5.0, 3.5, 8.2]
        
        # Act - Set different tickers as alerted
        for ticker, threshold in zip(tickers, thresholds):
            self.db_manager.set_ticker_alerted(self.test_user_id, ticker, threshold)
        
        # Assert
        for ticker, expected_threshold in zip(tickers, thresholds):
            alerted, last_alert_thresh = self.db_manager.get_ticker_state(self.test_user_id, ticker)
            self.assertTrue(alerted)
            self.assertEqual(last_alert_thresh, expected_threshold)

    def test_same_ticker_multiple_users(self):
        """Test handling same ticker for multiple users."""
        # Arrange
        user_ids = ['user1', 'user2', 'user3']
        thresholds = [5.0, 3.5, 8.2]
        
        # Act - Set same ticker for different users
        for user_id, threshold in zip(user_ids, thresholds):
            self.db_manager.set_ticker_alerted(user_id, self.test_ticker, threshold)
        
        # Assert
        for user_id, expected_threshold in zip(user_ids, thresholds):
            alerted, last_alert_thresh = self.db_manager.get_ticker_state(user_id, self.test_ticker)
            self.assertTrue(alerted)
            self.assertEqual(last_alert_thresh, expected_threshold)

    def test_database_persistence(self):
        """Test that data persists across database manager instances."""
        # Arrange - Use file-based database for persistence test
        db_path = 'test_persistence.db'
        db_manager1 = DBManager(f'sqlite:///{db_path}')
        
        # Act - Set some data
        db_manager1.increment_notification_count(self.test_user_id)
        db_manager1.set_ticker_alerted(self.test_user_id, self.test_ticker, 5.5)
        
        # Create new instance
        db_manager2 = DBManager(f'sqlite:///{db_path}')
        
        # Assert - Data should persist
        count = db_manager2.get_user_notification_count(self.test_user_id)
        alerted, threshold = db_manager2.get_ticker_state(self.test_user_id, self.test_ticker)
        
        self.assertEqual(count, 1)
        self.assertTrue(alerted)
        self.assertEqual(threshold, 5.5)
        
        # Cleanup
        import os
        if os.path.exists(db_path):
            os.remove(db_path)


class TestUserModel(unittest.TestCase):
    
    def test_user_reset_daily_count_no_previous_date(self):
        """Test resetting daily count when no previous notification date."""
        # Arrange
        user = User()
        user.notification_count = 5
        user.last_notification_date = None
        
        # Act
        user.reset_daily_count()
        
        # Assert
        self.assertEqual(user.notification_count, 0)
        self.assertEqual(user.last_notification_date, date.today())

    def test_user_reset_daily_count_old_date(self):
        """Test resetting daily count when last notification was on a previous date."""
        # Arrange
        user = User()
        user.notification_count = 10
        user.last_notification_date = date(2024, 1, 1)  # Old date
        
        # Act
        user.reset_daily_count()
        
        # Assert
        self.assertEqual(user.notification_count, 0)
        self.assertEqual(user.last_notification_date, date.today())

    def test_user_reset_daily_count_same_date(self):
        """Test that daily count is not reset when last notification was today."""
        # Arrange
        user = User()
        user.notification_count = 5
        user.last_notification_date = date.today()
        
        # Act
        user.reset_daily_count()
        
        # Assert
        self.assertEqual(user.notification_count, 5)  # Should not be reset
        self.assertEqual(user.last_notification_date, date.today())

    def test_user_reset_daily_count_datetime_object(self):
        """Test resetting daily count when last_notification_date is a datetime object."""
        # Arrange
        user = User()
        user.notification_count = 8
        user.last_notification_date = datetime(2024, 1, 1, 10, 30, 0)  # Old datetime
        
        # Act
        user.reset_daily_count()
        
        # Assert
        self.assertEqual(user.notification_count, 0)
        self.assertEqual(user.last_notification_date, date.today())

    def test_user_repr(self):
        """Test User model string representation."""
        # Arrange
        user = User()
        user.id = 'test_user_123'
        
        # Act
        repr_str = repr(user)
        
        # Assert
        self.assertEqual(repr_str, "<User(name='test_user_123')>")


class TestTickerStateModel(unittest.TestCase):
    
    def test_ticker_state_creation(self):
        """Test TickerState model creation."""
        # Arrange & Act
        ticker_state = TickerState()
        ticker_state.user_id = 'test_user'
        ticker_state.ticker = 'AAPL'
        ticker_state.alerted = True
        ticker_state.last_alert_thresh = 5.5
        
        # Assert
        self.assertEqual(ticker_state.user_id, 'test_user')
        self.assertEqual(ticker_state.ticker, 'AAPL')
        self.assertTrue(ticker_state.alerted)
        self.assertEqual(ticker_state.last_alert_thresh, 5.5)

    def test_ticker_state_defaults(self):
        """Test TickerState model default values."""
        # Arrange & Act
        ticker_state = TickerState()
        
        # Assert
        self.assertFalse(ticker_state.alerted)  # Default should be False
        self.assertIsNone(ticker_state.last_alert_thresh)  # Default should be None


if __name__ == '__main__':
    unittest.main()