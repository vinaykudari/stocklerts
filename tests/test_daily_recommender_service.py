import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from typing import List, Dict

# Import the actual service functions
from app.services.daily_recommender_service import (
    get_market_pct,
    get_daily_recommendations,
    send_daily_performance,
    get_best_daily_performers,
    daily_recommendations
)


class TestDailyRecommenderService(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_finnhub_client = Mock()
        # Clear the global daily_recommendations list before each test
        daily_recommendations.clear()

    def test_get_market_pct_success(self):
        """Test successful market percentage calculation."""
        # Arrange
        spy_quote = {
            'c': 450.0,   # current price
            'o': 440.0,   # open price
        }
        self.mock_finnhub_client.quote.return_value = spy_quote

        # Act
        result = get_market_pct(self.mock_finnhub_client)

        # Assert
        expected_pct = ((450.0 - 440.0) / 440.0) * 100  # ~2.27%
        self.assertAlmostEqual(result, expected_pct, places=2)
        self.mock_finnhub_client.quote.assert_called_once_with('SPY')

    def test_get_market_pct_no_open_price(self):
        """Test market percentage when open price is missing."""
        # Arrange
        mock_quote = {'o': None, 'c': 420.0}
        self.mock_finnhub_client.quote.return_value = mock_quote
        
        # Act
        result = get_market_pct(self.mock_finnhub_client)
        
        # Assert
        self.assertIsNone(result)

    def test_get_market_pct_exception(self):
        """Test market percentage calculation with exception."""
        # Arrange
        self.mock_finnhub_client.quote.side_effect = Exception("API Error")
        
        # Act
        result = get_market_pct(self.mock_finnhub_client)
        
        # Assert
        self.assertIsNone(result)

    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_daily_recommendations_not_weekday(self, mock_is_weekday):
        """Test that function returns empty dict on non-weekdays when not API call."""
        # Arrange
        mock_is_weekday.return_value = False
        
        # Act
        result = get_daily_recommendations(self.mock_finnhub_client, api=False)
        
        # Assert
        self.assertEqual(result, {})

    @patch('app.services.daily_recommender_service.query_perplexity')
    @patch('app.services.daily_recommender_service.get_market_pct')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_daily_recommendations_success(self, mock_is_weekday, mock_get_market_pct, mock_query_perplexity):
        """Test successful daily recommendations retrieval."""
        # Arrange
        mock_is_weekday.return_value = True
        mock_get_market_pct.return_value = 2.5

        mock_recommendations = {
            "recommendations": [
                {
                    "symbol": "AAPL",
                    "catalyst": "Strong earnings report",
                    "target": "3%",
                    "risk": "Medium"
                },
                {
                    "symbol": "GOOGL",
                    "catalyst": "AI breakthrough",
                    "target": "5%",
                    "risk": "High"
                },
                {
                    "symbol": "MSFT",
                    "catalyst": "Cloud growth",
                    "target": "2%",
                    "risk": "Low"
                },
                {
                    "symbol": "TSLA",
                    "catalyst": "Delivery numbers",
                    "target": "8%",
                    "risk": "High"
                },
                {
                    "symbol": "NVDA",
                    "catalyst": "GPU demand",
                    "target": "6%",
                    "risk": "Medium"
                }
            ]
        }
        mock_query_perplexity.return_value = mock_recommendations

        # Act
        result = get_daily_recommendations(self.mock_finnhub_client, api=True)

        # Assert
        self.assertEqual(result, mock_recommendations)
        mock_query_perplexity.assert_called_once()

    @patch('app.services.daily_recommender_service.query_perplexity')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_daily_recommendations_no_recommendations(self, mock_is_weekday, mock_query_perplexity):
        """Test when no recommendations are returned."""
        # Arrange
        mock_is_weekday.return_value = True
        mock_query_perplexity.return_value = {'recommendations': []}
        
        # Act
        result = get_daily_recommendations(self.mock_finnhub_client, api=True)
        
        # Assert
        self.assertEqual(result, {})

    @patch('app.services.daily_recommender_service.query_perplexity')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_daily_recommendations_finnhub_error(self, mock_is_weekday, mock_query_perplexity):
        """Test handling of Finnhub API errors."""
        # Arrange
        mock_is_weekday.return_value = True
        mock_perplexity_response = {
            'recommendations': [
                {
                    'symbol': 'AAPL',
                    'catalyst': 'Strong earnings',
                    'target': '3%',
                    'risk': 'Medium'
                }
            ]
        }
        mock_query_perplexity.return_value = mock_perplexity_response
        self.mock_finnhub_client.quote.side_effect = Exception("API Error")
        
        # Act
        result = get_daily_recommendations(self.mock_finnhub_client, api=True)
        
        # Assert
        self.assertEqual(len(daily_recommendations), 1)
        self.assertIsNone(daily_recommendations[0]['open_price'])

    @patch('app.services.daily_recommender_service.is_weekday')
    def test_send_daily_performance_not_weekday(self, mock_is_weekday):
        """Test that function returns empty dict on non-weekdays when not API call."""
        # Arrange
        mock_is_weekday.return_value = False
        
        # Act
        result = send_daily_performance(self.mock_finnhub_client, api=False)
        
        # Assert
        self.assertEqual(result, {})

    @patch('app.services.daily_recommender_service.is_weekday')
    def test_send_daily_performance_no_recommendations(self, mock_is_weekday):
        """Test when no daily recommendations exist."""
        # Arrange
        mock_is_weekday.return_value = True
        daily_recommendations.clear()
        
        # Act
        result = send_daily_performance(self.mock_finnhub_client, api=True)
        
        # Assert
        self.assertEqual(result, {})

    @patch('app.services.daily_recommender_service.log_daily_performance')
    @patch('app.services.daily_recommender_service.send_notification')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_send_daily_performance_success(self, mock_is_weekday, mock_send_notification, mock_log_daily_performance):
        """Test successful daily performance sending."""
        # Arrange
        mock_is_weekday.return_value = True

        # Add test recommendations
        test_recommendations = [
            {"symbol": "AAPL", "target": "3%"},
            {"symbol": "GOOGL", "target": "5%"}
        ]
        daily_recommendations.extend(test_recommendations)

        # Mock quote responses
        def mock_quote_side_effect(symbol):
            quotes = {
                'AAPL': {'c': 150.0, 'pc': 145.0},  # 3.45% gain
                'GOOGL': {'c': 2800.0, 'pc': 2750.0}  # 1.82% gain
            }
            return quotes.get(symbol, {'c': 100.0, 'pc': 100.0})

        self.mock_finnhub_client.quote.side_effect = mock_quote_side_effect

        # Act
        result = send_daily_performance(self.mock_finnhub_client, api=True)

        # Assert
        self.assertIn("message", result)
        mock_send_notification.assert_called()
        mock_log_daily_performance.assert_called()

    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_best_daily_performers_not_weekday(self, mock_is_weekday):
        """Test that function returns empty dict on non-weekdays when not API call."""
        # Arrange
        mock_is_weekday.return_value = False
        
        # Act
        result = get_best_daily_performers(self.mock_finnhub_client, api=False)
        
        # Assert
        self.assertEqual(result, {})

    @patch('app.services.daily_recommender_service.query_perplexity')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_best_daily_performers_success(self, mock_is_weekday, mock_query_perplexity):
        """Test successful best daily performers retrieval."""
        # Arrange
        mock_is_weekday.return_value = True

        mock_performers = {
            "performers": [
                {
                    "symbol": "TSLA",
                    "pct": 8.5,
                    "reason": "Strong delivery numbers"
                },
                {
                    "symbol": "NVDA",
                    "pct": 6.2,
                    "reason": "AI chip demand"
                },
                {
                    "symbol": "AMD",
                    "pct": 5.8,
                    "reason": "Data center growth"
                },
                {
                    "symbol": "AAPL",
                    "pct": 4.1,
                    "reason": "iPhone sales beat"
                },
                {
                    "symbol": "GOOGL",
                    "pct": 3.9,
                    "reason": "Search revenue growth"
                }
            ]
        }
        mock_query_perplexity.return_value = mock_performers

        # Act
        result = get_best_daily_performers(self.mock_finnhub_client, api=True)

        # Assert
        self.assertEqual(result, mock_performers)
        mock_query_perplexity.assert_called_once()

    @patch('app.services.daily_recommender_service.query_perplexity')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_best_daily_performers_no_performers(self, mock_is_weekday, mock_query_perplexity):
        """Test when no performers are returned."""
        # Arrange
        mock_is_weekday.return_value = True
        mock_query_perplexity.return_value = {'performers': []}
        
        # Act
        result = get_best_daily_performers(self.mock_finnhub_client, api=True)
        
        # Assert
        self.assertEqual(result, {})

    @patch('app.services.daily_recommender_service.query_perplexity')
    @patch('app.services.daily_recommender_service.is_weekday')
    def test_get_best_daily_performers_finnhub_error(self, mock_is_weekday, mock_query_perplexity):
        """Test handling of Finnhub API errors in best performers."""
        # Arrange
        mock_is_weekday.return_value = True
        mock_perplexity_response = {
            'performers': [
                {
                    'symbol': 'TSLA',
                    'reason': 'Strong delivery numbers'
                }
            ]
        }
        mock_query_perplexity.return_value = mock_perplexity_response
        self.mock_finnhub_client.quote.side_effect = Exception("API Error")
        
        # Act
        result = get_best_daily_performers(self.mock_finnhub_client, api=True)
        
        # Assert
        performers = mock_query_perplexity.return_value['performers']
        self.assertNotIn('pct', performers[0])


if __name__ == '__main__':
    unittest.main()