import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from queue import Queue
import os

from app.scheduler.job_scheduler import start_scheduler


class TestJobScheduler(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_db_manager = Mock()
        self.ticker_config = {
            'AAPL': [{'value': 5.0, 'users': ['user1']}],
            'GOOGL': [{'value': -3.0, 'users': ['user2']}]
        }
        self.user_notify_thresh = {'user1': 1.0, 'user2': 1.5}
        self.max_notifications = 100
        self.max_quote_calls_per_min = 60

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_basic_setup(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test basic scheduler setup and job addition."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        mock_finnhub_client_class.assert_called_once_with(api_key='test_api_key')
        mock_scheduler_class.assert_called_once()
        mock_scheduler.start.assert_called_once()
        
        # Check that jobs were added
        self.assertGreaterEqual(mock_scheduler.add_job.call_count, 5)  # At least 5 jobs should be added

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_stock_price_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that stock price checking job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the stock price checking job call
        stock_price_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'check_stock_price_change' in str(call):
                stock_price_job_call = call
                break
        
        self.assertIsNotNone(stock_price_job_call)
        
        # Check job configuration
        args, kwargs = stock_price_job_call
        self.assertEqual(kwargs['id'], 'job_check_stock_price_change')
        self.assertEqual(kwargs['max_instances'], 3)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_daily_recommendations_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that daily recommendations job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the daily recommendations job call
        daily_rec_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'get_daily_recommendations' in str(call):
                daily_rec_job_call = call
                break
        
        self.assertIsNotNone(daily_rec_job_call)
        
        # Check job configuration
        args, kwargs = daily_rec_job_call
        self.assertEqual(kwargs['id'], 'daily_recommendations')
        self.assertEqual(kwargs['max_instances'], 1)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_daily_performance_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that daily performance job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the daily performance job call
        daily_perf_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'send_daily_performance' in str(call):
                daily_perf_job_call = call
                break
        
        self.assertIsNotNone(daily_perf_job_call)
        
        # Check job configuration
        args, kwargs = daily_perf_job_call
        self.assertEqual(kwargs['id'], 'daily_performance')
        self.assertEqual(kwargs['max_instances'], 1)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_best_performers_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that best performers job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the best performers job call
        best_perf_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'get_best_daily_performers' in str(call):
                best_perf_job_call = call
                break
        
        self.assertIsNotNone(best_perf_job_call)
        
        # Check job configuration
        args, kwargs = best_perf_job_call
        self.assertEqual(kwargs['id'], 'best_daily_performers')
        self.assertEqual(kwargs['max_instances'], 1)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_reset_counters_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that reset daily counters job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the reset counters job call
        reset_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'reset_daily_counters' in str(call):
                reset_job_call = call
                break
        
        self.assertIsNotNone(reset_job_call)
        
        # Check job configuration
        args, kwargs = reset_job_call
        self.assertEqual(kwargs['id'], 'reset_daily_counters')
        self.assertEqual(kwargs['max_instances'], 3)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_upload_prompt_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that upload prompt job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the upload prompt job call
        upload_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'upload_prompt_to_sheets' in str(call):
                upload_job_call = call
                break
        
        self.assertIsNotNone(upload_job_call)
        
        # Check job configuration
        args, kwargs = upload_job_call
        self.assertEqual(kwargs['id'], 'upload_prompt_tracking')
        self.assertEqual(kwargs['max_instances'], 1)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_improve_prompt_job(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that improve prompt job is properly configured."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Find the improve prompt job call
        improve_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'improve_daily_prompt' in str(call):
                improve_job_call = call
                break
        
        self.assertIsNotNone(improve_job_call)
        
        # Check job configuration
        args, kwargs = improve_job_call
        self.assertEqual(kwargs['id'], 'improve_daily_prompt')
        self.assertEqual(kwargs['max_instances'], 1)
        self.assertTrue(kwargs['replace_existing'])

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_interval_calculation(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that interval calculation is correct for stock price checking."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        custom_max_calls = 30  # Should result in interval of 3 seconds (30//60 + 1)
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            custom_max_calls
        )
        
        # Assert
        # The interval should be calculated as (max_quote_calls_per_min // 60) + 1
        expected_interval = (custom_max_calls // 60) + 1  # Should be 1 second
        
        # Find the stock price checking job call and verify interval
        for call in mock_scheduler.add_job.call_args_list:
            if 'check_stock_price_change' in str(call):
                args, kwargs = call
                trigger = kwargs.get('trigger')
                # The trigger should be an IntervalTrigger with the correct seconds
                break

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {}, clear=True)
    def test_start_scheduler_missing_api_key(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test scheduler behavior when FINNHUB_API_KEY is missing."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        mock_finnhub_client_class.assert_called_once_with(api_key=None)

    @patch('app.scheduler.job_scheduler.BackgroundScheduler')
    @patch('app.scheduler.job_scheduler.finnhub.Client')
    @patch.dict(os.environ, {'FINNHUB_API_KEY': 'test_api_key'})
    def test_start_scheduler_ticker_queue_population(self, mock_finnhub_client_class, mock_scheduler_class):
        """Test that ticker queue is properly populated with symbols."""
        # Arrange
        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler
        mock_finnhub_client = Mock()
        mock_finnhub_client_class.return_value = mock_finnhub_client
        
        # Act
        start_scheduler(
            self.mock_db_manager,
            self.ticker_config,
            self.user_notify_thresh,
            self.max_notifications,
            self.max_quote_calls_per_min
        )
        
        # Assert
        # Check that the stock price job was called with proper arguments
        stock_price_job_call = None
        for call in mock_scheduler.add_job.call_args_list:
            if 'check_stock_price_change' in str(call):
                stock_price_job_call = call
                break
        
        self.assertIsNotNone(stock_price_job_call)
        args, kwargs = stock_price_job_call
        
        # The args should contain the ticker_queue as the third element
        job_args = kwargs['args']
        ticker_queue = job_args[2]  # Third argument should be the ticker_queue
        
        # Verify queue contains all tickers
        queue_contents = []
        while not ticker_queue.empty():
            queue_contents.append(ticker_queue.get())
        
        self.assertEqual(set(queue_contents), set(self.ticker_config.keys()))


if __name__ == '__main__':
    unittest.main()