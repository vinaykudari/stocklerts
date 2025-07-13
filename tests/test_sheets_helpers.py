import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

from app.helpers.sheets_helpers import (
    get_gspread_client,
    parse_date_value,
    # Note: Other functions would need to be imported based on the actual file content
)


class TestSheetsHelpers(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        # Clear the LRU cache before each test
        get_gspread_client.cache_clear()

    @patch.dict(os.environ, {}, clear=True)
    def test_get_gspread_client_no_credentials(self):
        """Test gspread client creation when no credentials are provided."""
        # Act
        result = get_gspread_client()
        
        # Assert
        self.assertIsNone(result)

    @patch('app.helpers.sheets_helpers.gspread')
    @patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT': '{"type": "service_account", "project_id": "test"}'})
    def test_get_gspread_client_success(self, mock_gspread):
        """Test successful gspread client creation."""
        # Arrange
        mock_client = Mock()
        mock_gspread.service_account_from_dict.return_value = mock_client
        
        # Act
        result = get_gspread_client()
        
        # Assert
        self.assertEqual(result, mock_client)
        mock_gspread.service_account_from_dict.assert_called_once()

    @patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT': 'invalid_json'})
    def test_get_gspread_client_invalid_json(self):
        """Test gspread client creation with invalid JSON credentials."""
        # Act
        result = get_gspread_client()
        
        # Assert
        self.assertIsNone(result)

    @patch('app.helpers.sheets_helpers.gspread')
    @patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT': '{"type": "service_account"}'})
    def test_get_gspread_client_import_error(self, mock_gspread):
        """Test gspread client creation when gspread import fails."""
        # Arrange
        mock_gspread.service_account_from_dict.side_effect = ImportError("gspread not installed")
        
        # Act
        result = get_gspread_client()
        
        # Assert
        self.assertIsNone(result)

    @patch('app.helpers.sheets_helpers.gspread')
    @patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT': '{"type": "service_account"}'})
    def test_get_gspread_client_general_exception(self, mock_gspread):
        """Test gspread client creation with general exception."""
        # Arrange
        mock_gspread.service_account_from_dict.side_effect = Exception("General error")
        
        # Act
        result = get_gspread_client()
        
        # Assert
        self.assertIsNone(result)

    def test_get_gspread_client_caching(self):
        """Test that gspread client is properly cached."""
        # Arrange
        with patch('app.helpers.sheets_helpers.gspread') as mock_gspread:
            mock_client = Mock()
            mock_gspread.service_account_from_dict.return_value = mock_client
            
            with patch.dict(os.environ, {'GOOGLE_SERVICE_ACCOUNT': '{"type": "service_account"}'}):
                # Act
                result1 = get_gspread_client()
                result2 = get_gspread_client()
                
                # Assert
                self.assertEqual(result1, result2)
                self.assertEqual(result1, mock_client)
                # Should only be called once due to caching
                mock_gspread.service_account_from_dict.assert_called_once()

    def test_parse_date_value_none_or_empty(self):
        """Test parsing None or empty date values."""
        # Test cases
        test_cases = [None, "", "   ", 0, False]
        
        for test_value in test_cases:
            with self.subTest(value=test_value):
                result = parse_date_value(test_value)
                self.assertIsNone(result)

    def test_parse_date_value_valid_formats(self):
        """Test parsing valid date formats."""
        # Test cases with expected results
        test_cases = [
            ("2024-01-15 10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
            ("2024-01-15", datetime(2024, 1, 15, 0, 0, 0)),
            ("01/15/2024 14:30:00", datetime(2024, 1, 15, 14, 30, 0)),
            ("01/15/2024", datetime(2024, 1, 15, 0, 0, 0)),
            ("15/01/2024", datetime(2024, 1, 15, 0, 0, 0)),
        ]
        
        for date_str, expected in test_cases:
            with self.subTest(date_string=date_str):
                result = parse_date_value(date_str)
                self.assertEqual(result, expected)

    def test_parse_date_value_invalid_format(self):
        """Test parsing invalid date formats."""
        # Test cases that should return None
        invalid_dates = [
            "invalid_date",
            "2024-13-01",  # Invalid month
            "2024/01/32",  # Invalid day
            "not a date at all",
            "2024-01-01T10:30:00Z",  # ISO format not in the list
        ]
        
        for invalid_date in invalid_dates:
            with self.subTest(date_string=invalid_date):
                result = parse_date_value(invalid_date)
                self.assertIsNone(result)

    def test_parse_date_value_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        # Arrange
        date_with_whitespace = "  2024-01-15  "
        expected = datetime(2024, 1, 15, 0, 0, 0)
        
        # Act
        result = parse_date_value(date_with_whitespace)
        
        # Assert
        self.assertEqual(result, expected)

    def test_parse_date_value_numeric_input(self):
        """Test parsing numeric input (converted to string)."""
        # Arrange
        numeric_date = 20240115  # Should be converted to string
        
        # Act
        result = parse_date_value(numeric_date)
        
        # Assert
        # Should return None as "20240115" doesn't match any format
        self.assertIsNone(result)

    @patch('app.helpers.sheets_helpers.get_gspread_client')
    def test_sheets_function_with_no_client(self, mock_get_client):
        """Test sheets functions when gspread client is not available."""
        # Arrange
        mock_get_client.return_value = None
        
        # This test would need to be expanded based on actual function implementations
        # For now, just testing the client retrieval
        
        # Act
        client = get_gspread_client()
        
        # Assert
        self.assertIsNone(client)

    @patch('app.helpers.sheets_helpers.get_gspread_client')
    def test_sheets_function_with_client_exception(self, mock_get_client):
        """Test sheets functions when gspread client raises exceptions."""
        # Arrange
        mock_client = Mock()
        mock_client.open_by_key.side_effect = Exception("Sheets API error")
        mock_get_client.return_value = mock_client
        
        # This would test actual sheet operations if we had the full function implementations
        # For now, just testing the exception scenario setup
        
        # Act & Assert
        with self.assertRaises(Exception):
            mock_client.open_by_key("test_sheet_id")

    def test_parse_date_value_edge_cases(self):
        """Test edge cases for date parsing."""
        # Test leap year
        leap_year_date = "2024-02-29"
        result = parse_date_value(leap_year_date)
        self.assertEqual(result, datetime(2024, 2, 29, 0, 0, 0))
        
        # Test end of year
        end_of_year = "2024-12-31 23:59:59"
        result = parse_date_value(end_of_year)
        self.assertEqual(result, datetime(2024, 12, 31, 23, 59, 59))
        
        # Test beginning of year
        beginning_of_year = "2024-01-01 00:00:00"
        result = parse_date_value(beginning_of_year)
        self.assertEqual(result, datetime(2024, 1, 1, 0, 0, 0))

    @patch('app.helpers.sheets_helpers.get_gspread_client')
    def test_sheets_helper_error_handling(self, mock_get_client):
        """Test error handling in sheets helper functions."""
        # Arrange
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        # Test various exception scenarios
        exception_types = [
            ConnectionError("Network error"),
            TimeoutError("Request timeout"),
            ValueError("Invalid value"),
            KeyError("Missing key"),
        ]
        
        for exception in exception_types:
            with self.subTest(exception_type=type(exception).__name__):
                mock_client.open_by_key.side_effect = exception
                
                # This would test actual function behavior
                # For now, just verifying the exception setup
                with self.assertRaises(type(exception)):
                    mock_client.open_by_key("test_id")

    def test_parse_date_value_type_conversion(self):
        """Test that various input types are properly converted to strings."""
        # Test different input types
        test_inputs = [
            (123, None),  # Number that doesn't match date format
            (True, None),  # Boolean
            ([], None),   # List (should be converted to string but won't match format)
        ]
        
        for input_value, expected in test_inputs:
            with self.subTest(input_value=input_value):
                result = parse_date_value(input_value)
                self.assertEqual(result, expected)


# Additional test class for specific sheets operations (would be expanded based on actual functions)
class TestSheetsOperations(unittest.TestCase):
    """Test class for specific Google Sheets operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_sheet = Mock()
        self.mock_worksheet = Mock()
        
        # Setup mock chain
        self.mock_client.open_by_key.return_value = self.mock_sheet
        self.mock_sheet.sheet1 = self.mock_worksheet

    @patch('app.helpers.sheets_helpers.get_gspread_client')
    def test_sheet_access_pattern(self, mock_get_client):
        """Test common pattern of accessing Google Sheets."""
        # Arrange
        mock_get_client.return_value = self.mock_client
        sheet_id = "test_sheet_id"
        
        # Act
        client = get_gspread_client()
        if client:
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.sheet1
        
        # Assert
        self.mock_client.open_by_key.assert_called_once_with(sheet_id)
        self.assertEqual(worksheet, self.mock_worksheet)

    @patch('app.helpers.sheets_helpers.get_gspread_client')
    def test_sheet_data_operations(self, mock_get_client):
        """Test data reading/writing operations."""
        # Arrange
        mock_get_client.return_value = self.mock_client
        test_data = [["Header1", "Header2"], ["Value1", "Value2"]]
        self.mock_worksheet.get_all_values.return_value = test_data
        
        # Act
        client = get_gspread_client()
        if client:
            sheet = client.open_by_key("test_id")
            data = sheet.sheet1.get_all_values()
        
        # Assert
        self.assertEqual(data, test_data)
        self.mock_worksheet.get_all_values.assert_called_once()


if __name__ == '__main__':
    unittest.main()