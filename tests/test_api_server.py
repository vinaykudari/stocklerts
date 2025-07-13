import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from http.server import HTTPServer

from app.api_server import RequestHandler, start_server


class TestAPIServer(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.mock_finnhub_client = Mock()
        
    def create_request_handler(self, method='GET', path='/', body=None):
        """Helper method to create a RequestHandler instance for testing."""
        handler = RequestHandler(Mock(), ('127.0.0.1', 12345), Mock())
        handler.command = method
        handler.path = path
        handler.headers = {}
        
        if body:
            handler.rfile = Mock()
            handler.rfile.read.return_value = body.encode('utf-8')
            handler.headers['content-length'] = str(len(body))
        
        handler.wfile = Mock()
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        
        return handler

    def test_log_message_suppressed(self):
        """Test that log messages are suppressed."""
        # Arrange
        handler = self.create_request_handler()
        
        # Act & Assert
        # Should not raise any exception and should do nothing
        handler.log_message("Test message", "arg1", "arg2")

    def test_do_GET_health_endpoint(self):
        """Test GET request to /health endpoint."""
        # Arrange
        handler = self.create_request_handler('GET', '/health')
        
        # Act
        handler.do_GET()
        
        # Assert
        handler.send_response.assert_called_with(200)
        handler.send_header.assert_any_call('Content-type', 'application/json')
        handler.end_headers.assert_called_once()

    def test_do_GET_unknown_endpoint(self):
        """Test GET request to unknown endpoint returns 404."""
        # Arrange
        handler = self.create_request_handler('GET', '/unknown')
        
        # Act
        handler.do_GET()
        
        # Assert
        handler.send_response.assert_called_with(404)

    @patch('app.api_server.get_daily_recommendations')
    def test_do_POST_recommendations_endpoint(self, mock_get_recommendations):
        """Test POST request to /recommendations endpoint."""
        # Arrange
        mock_get_recommendations.return_value = {"message": "Test recommendations"}
        handler = self.create_request_handler('POST', '/recommendations')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        mock_get_recommendations.assert_called_once_with(self.mock_finnhub_client, api=True)
        handler.send_response.assert_called_with(200)

    @patch('app.api_server.send_daily_performance')
    def test_do_POST_daily_performance_endpoint(self, mock_send_performance):
        """Test POST request to /daily_performance endpoint."""
        # Arrange
        mock_send_performance.return_value = {"message": "Performance data"}
        handler = self.create_request_handler('POST', '/daily_performance')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        mock_send_performance.assert_called_once_with(self.mock_finnhub_client, api=True)
        handler.send_response.assert_called_with(200)

    @patch('app.api_server.get_best_daily_performers')
    def test_do_POST_best_performers_endpoint(self, mock_get_best_performers):
        """Test POST request to /best_performers endpoint."""
        # Arrange
        mock_get_best_performers.return_value = {"message": "Best performers"}
        handler = self.create_request_handler('POST', '/best_performers')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        mock_get_best_performers.assert_called_once_with(self.mock_finnhub_client, api=True)
        handler.send_response.assert_called_with(200)

    @patch('app.api_server.get_best_daily_performers')
    def test_do_POST_debug_best_performers_endpoint(self, mock_get_best_performers):
        """Test POST request to /debug_best_performers endpoint."""
        # Arrange
        mock_response = {"performers": [{"symbol": "AAPL", "pct": 5.0}]}
        mock_get_best_performers.return_value = mock_response
        handler = self.create_request_handler('POST', '/debug_best_performers')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        mock_get_best_performers.assert_called_once_with(self.mock_finnhub_client, api=True)
        handler.send_response.assert_called_with(200)

    @patch('app.api_server.upload_prompt_to_sheets')
    def test_do_POST_upload_prompt_endpoint(self, mock_upload_prompt):
        """Test POST request to /upload_prompt endpoint."""
        # Arrange
        mock_upload_prompt.return_value = {"status": "success"}
        handler = self.create_request_handler('POST', '/upload_prompt')
        
        # Act
        handler.do_POST()
        
        # Assert
        mock_upload_prompt.assert_called_once()
        handler.send_response.assert_called_with(200)

    @patch('app.api_server.improve_daily_prompt')
    def test_do_POST_improve_prompt_endpoint(self, mock_improve_prompt):
        """Test POST request to /improve_prompt endpoint."""
        # Arrange
        mock_improve_prompt.return_value = {"ok": True}
        handler = self.create_request_handler('POST', '/improve_prompt')
        
        # Act
        handler.do_POST()
        
        # Assert
        mock_improve_prompt.assert_called_once()
        handler.send_response.assert_called_with(200)

    def test_do_POST_unknown_endpoint(self):
        """Test POST request to unknown endpoint returns 404."""
        # Arrange
        handler = self.create_request_handler('POST', '/unknown')
        
        # Act
        handler.do_POST()
        
        # Assert
        handler.send_response.assert_called_with(404)

    @patch('app.api_server.get_daily_recommendations')
    def test_do_POST_exception_handling(self, mock_get_recommendations):
        """Test that exceptions in POST handlers are properly caught."""
        # Arrange
        mock_get_recommendations.side_effect = Exception("Test exception")
        handler = self.create_request_handler('POST', '/recommendations')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        handler.send_response.assert_called_with(500)

    @patch('app.api_server.get_daily_recommendations')
    def test_do_POST_json_response_writing(self, mock_get_recommendations):
        """Test that JSON responses are properly written."""
        # Arrange
        test_response = {"message": "Test response", "data": [1, 2, 3]}
        mock_get_recommendations.return_value = test_response
        handler = self.create_request_handler('POST', '/recommendations')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        handler.send_header.assert_any_call('Content-type', 'application/json')
        # Check that JSON was written to wfile
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list)
        parsed_response = json.loads(written_data.decode('utf-8'))
        self.assertEqual(parsed_response, test_response)

    @patch('app.api_server.threading.Thread')
    @patch('app.api_server.HTTPServer')
    def test_start_server_basic(self, mock_http_server_class, mock_thread_class):
        """Test basic server startup."""
        # Arrange
        mock_server = Mock()
        mock_http_server_class.return_value = mock_server
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        port = 8080
        
        # Act
        result = start_server(port, self.mock_finnhub_client)
        
        # Assert
        mock_http_server_class.assert_called_once_with(('', port), RequestHandler)
        self.assertEqual(mock_server.finnhub_client, self.mock_finnhub_client)
        mock_thread_class.assert_called_once()
        mock_thread.start.assert_called_once()
        self.assertEqual(result, mock_server)

    @patch('app.api_server.threading.Thread')
    @patch('app.api_server.HTTPServer')
    def test_start_server_default_port(self, mock_http_server_class, mock_thread_class):
        """Test server startup with default port."""
        # Arrange
        mock_server = Mock()
        mock_http_server_class.return_value = mock_server
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Act
        result = start_server(finnhub_client=self.mock_finnhub_client)
        
        # Assert
        mock_http_server_class.assert_called_once_with(('', 8000), RequestHandler)

    @patch('app.api_server.threading.Thread')
    @patch('app.api_server.HTTPServer')
    def test_start_server_no_finnhub_client(self, mock_http_server_class, mock_thread_class):
        """Test server startup without finnhub client."""
        # Arrange
        mock_server = Mock()
        mock_http_server_class.return_value = mock_server
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Act
        result = start_server()
        
        # Assert
        self.assertIsNone(mock_server.finnhub_client)

    @patch('app.api_server.threading.Thread')
    @patch('app.api_server.HTTPServer')
    def test_start_server_thread_configuration(self, mock_http_server_class, mock_thread_class):
        """Test that server thread is properly configured."""
        # Arrange
        mock_server = Mock()
        mock_http_server_class.return_value = mock_server
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Act
        start_server(8080, self.mock_finnhub_client)
        
        # Assert
        # Check thread configuration
        thread_call_args = mock_thread_class.call_args
        self.assertEqual(thread_call_args[1]['target'], mock_server.serve_forever)
        self.assertTrue(thread_call_args[1]['daemon'])

    def test_request_handler_server_attribute_access(self):
        """Test that RequestHandler can access server attributes."""
        # Arrange
        handler = self.create_request_handler('POST', '/recommendations')
        mock_server = Mock()
        mock_server.finnhub_client = self.mock_finnhub_client
        handler.server = mock_server
        
        # Act & Assert
        self.assertEqual(handler.server.finnhub_client, self.mock_finnhub_client)

    @patch('app.api_server.get_daily_recommendations')
    def test_do_POST_empty_response_handling(self, mock_get_recommendations):
        """Test handling of empty responses from service functions."""
        # Arrange
        mock_get_recommendations.return_value = {}
        handler = self.create_request_handler('POST', '/recommendations')
        handler.server = Mock()
        handler.server.finnhub_client = self.mock_finnhub_client
        
        # Act
        handler.do_POST()
        
        # Assert
        handler.send_response.assert_called_with(200)
        # Should still write empty JSON object
        written_data = b''.join(call[0][0] for call in handler.wfile.write.call_args_list)
        parsed_response = json.loads(written_data.decode('utf-8'))
        self.assertEqual(parsed_response, {})


if __name__ == '__main__':
    unittest.main()