import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
from typing import Dict

from app.services.improve_prompt_service import improve_daily_prompt


class TestImprovePromptService(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_sheet_id = "test_sheet_id"
        self.mock_daily_perf_sheet_id = "daily_perf_sheet_id"
        self.mock_best_perf_sheet_id = "best_perf_sheet_id"

    @patch.dict(os.environ, {}, clear=True)
    def test_improve_daily_prompt_no_sheet_id(self):
        """Test when PROMPT_TRACKING_SHEET_ID is not set."""
        # Act
        result = improve_daily_prompt()
        
        # Assert
        self.assertEqual(result, {"ok": False})

    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id',
        'BEST_PERF_SHEET_ID': 'best_perf_sheet_id'
    })
    def test_improve_daily_prompt_no_new_data(self, mock_fetch_records, mock_get_last_date):
        """Test when no new data is found for prompt improvement."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.return_value = []
        
        # Act
        result = improve_daily_prompt()
        
        # Assert
        self.assertEqual(result, {"ok": False})
        self.assertEqual(mock_fetch_records.call_count, 2)  # Called for both daily and best sheets

    @patch('app.services.improve_prompt_service.log_recommended_prompt')
    @patch('app.services.improve_prompt_service.send_notification')
    @patch('app.services.improve_prompt_service.query_gemini')
    @patch('app.services.improve_prompt_service.fmt')
    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id',
        'BEST_PERF_SHEET_ID': 'best_perf_sheet_id'
    })
    def test_improve_daily_prompt_success(self, mock_fetch_records, mock_get_last_date, 
                                        mock_fmt, mock_query_gemini, mock_send_notification,
                                        mock_log_recommended_prompt):
        """Test successful prompt improvement."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.side_effect = [
            [{'symbol': 'AAPL', 'pct': 3.5}],  # daily_rows
            [{'symbol': 'TSLA', 'pct': 8.2}]   # best_rows
        ]
        mock_fmt.side_effect = ["formatted_daily", "formatted_best"]
        
        mock_gemini_response = {
            "new_prompt": "Improved prompt text",
            "analysis": "This prompt is better because..."
        }
        mock_query_gemini.return_value = mock_gemini_response
        mock_send_notification.return_value = True
        
        # Act
        result = improve_daily_prompt()
        
        # Assert
        self.assertEqual(result, {"ok": True})
        mock_query_gemini.assert_called_once()
        mock_log_recommended_prompt.assert_called_once_with(
            analysis=mock_gemini_response['analysis'],
            new_prompt=mock_gemini_response['new_prompt']
        )
        mock_send_notification.assert_called_once_with("Daily prompt is updated", admin=True)

    @patch('app.services.improve_prompt_service.query_gemini')
    @patch('app.services.improve_prompt_service.fmt')
    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id',
        'BEST_PERF_SHEET_ID': 'best_perf_sheet_id'
    })
    def test_improve_daily_prompt_gemini_no_response(self, mock_fetch_records, mock_get_last_date, 
                                                   mock_fmt, mock_query_gemini):
        """Test when Gemini doesn't return a proper response."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.side_effect = [
            [{'symbol': 'AAPL', 'pct': 3.5}],  # daily_rows
            [{'symbol': 'TSLA', 'pct': 8.2}]   # best_rows
        ]
        mock_fmt.side_effect = ["formatted_daily", "formatted_best"]
        mock_query_gemini.return_value = None
        
        # Act
        result = improve_daily_prompt()
        
        # Assert
        self.assertEqual(result, {"ok": False})

    @patch('app.services.improve_prompt_service.query_gemini')
    @patch('app.services.improve_prompt_service.fmt')
    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id',
        'BEST_PERF_SHEET_ID': 'best_perf_sheet_id'
    })
    def test_improve_daily_prompt_gemini_invalid_response(self, mock_fetch_records, mock_get_last_date, 
                                                        mock_fmt, mock_query_gemini):
        """Test when Gemini returns invalid response format."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.side_effect = [
            [{'symbol': 'AAPL', 'pct': 3.5}],  # daily_rows
            [{'symbol': 'TSLA', 'pct': 8.2}]   # best_rows
        ]
        mock_fmt.side_effect = ["formatted_daily", "formatted_best"]
        mock_query_gemini.return_value = {"analysis": "Good analysis"}  # Missing new_prompt
        
        # Act
        result = improve_daily_prompt()
        
        # Assert
        self.assertEqual(result, {"ok": False})

    @patch('app.services.improve_prompt_service.query_gemini')
    @patch('app.services.improve_prompt_service.fmt')
    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id',
        'BEST_PERF_SHEET_ID': 'best_perf_sheet_id'
    })
    def test_improve_daily_prompt_gemini_string_response(self, mock_fetch_records, mock_get_last_date, 
                                                       mock_fmt, mock_query_gemini):
        """Test when Gemini returns a string instead of dict."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.side_effect = [
            [{'symbol': 'AAPL', 'pct': 3.5}],  # daily_rows
            [{'symbol': 'TSLA', 'pct': 8.2}]   # best_rows
        ]
        mock_fmt.side_effect = ["formatted_daily", "formatted_best"]
        mock_query_gemini.return_value = "Invalid string response"
        
        # Act
        result = improve_daily_prompt()
        
        # Assert
        self.assertEqual(result, {"ok": False})

    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id'
        # Missing BEST_PERF_SHEET_ID
    })
    def test_improve_daily_prompt_missing_best_sheet_id(self, mock_fetch_records, mock_get_last_date):
        """Test when BEST_PERF_SHEET_ID is missing."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.side_effect = [
            [{'symbol': 'AAPL', 'pct': 3.5}],  # daily_rows
            []  # best_rows (empty due to None sheet_id)
        ]
        
        # Act
        result = improve_daily_prompt()
        
        # Assert
        # Should still work with only daily data
        self.assertEqual(mock_fetch_records.call_count, 2)
        mock_fetch_records.assert_any_call('daily_perf_sheet_id', '2024-01-01')
        mock_fetch_records.assert_any_call(None, '2024-01-01')

    @patch('app.services.improve_prompt_service.IMPROVE_PROMPT', 'Test prompt: {current_prompt} Daily: {daily_rows} Best: {best_rows}')
    @patch('app.services.improve_prompt_service.DAILY_RECOMMENDATIONS_PROMPT', 'Current daily prompt')
    @patch('app.services.improve_prompt_service.query_gemini')
    @patch('app.services.improve_prompt_service.fmt')
    @patch('app.services.improve_prompt_service.get_last_prompt_date')
    @patch('app.services.improve_prompt_service.fetch_records_since')
    @patch.dict(os.environ, {
        'PROMPT_TRACKING_SHEET_ID': 'test_sheet_id',
        'DAILY_PERF_SHEET_ID': 'daily_perf_sheet_id',
        'BEST_PERF_SHEET_ID': 'best_perf_sheet_id'
    })
    def test_improve_daily_prompt_formatting(self, mock_fetch_records, mock_get_last_date, 
                                           mock_fmt, mock_query_gemini):
        """Test that the prompt is properly formatted with data."""
        # Arrange
        mock_get_last_date.return_value = "2024-01-01"
        mock_fetch_records.side_effect = [
            [{'symbol': 'AAPL', 'pct': 3.5}],  # daily_rows
            [{'symbol': 'TSLA', 'pct': 8.2}]   # best_rows
        ]
        mock_fmt.side_effect = ["formatted_daily_data", "formatted_best_data"]
        
        mock_gemini_response = {
            "new_prompt": "Improved prompt",
            "analysis": "Analysis"
        }
        mock_query_gemini.return_value = mock_gemini_response
        
        # Act
        improve_daily_prompt()
        
        # Assert
        # Check that query_gemini was called with properly formatted prompt
        call_args = mock_query_gemini.call_args[0]
        expected_prompt = "Test prompt: Current daily prompt Daily: formatted_daily_data Best: formatted_best_data"
        self.assertEqual(call_args[0], expected_prompt)


if __name__ == '__main__':
    unittest.main()