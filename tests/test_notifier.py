import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import os
from typing import Set

from app.alerts.notifier import send_push_notification, send_notification


class TestNotifier(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.test_message = "Test notification message"
        self.test_title = "Test Title"
        self.test_account_key = "test_account_key"

    @patch('app.alerts.notifier.requests.post')
    def test_send_push_notification_success(self, mock_post):
        """Test successful push notification sending."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Act
        result = send_push_notification(self.test_message, self.test_title, self.test_account_key)
        
        # Assert
        self.assertTrue(result)
        mock_post.assert_called_once_with(
            'https://alertzy.app/send',
            json={
                'accountKey': self.test_account_key,
                'title': self.test_title,
                'message': self.test_message
            }
        )

    @patch('app.alerts.notifier.requests.post')
    def test_send_push_notification_failure(self, mock_post):
        """Test push notification sending failure."""
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        # Act
        result = send_push_notification(self.test_message, self.test_title, self.test_account_key)
        
        # Assert
        self.assertFalse(result)

    @patch('app.alerts.notifier.requests.post')
    def test_send_push_notification_exception(self, mock_post):
        """Test push notification sending with exception."""
        # Arrange
        mock_post.side_effect = Exception("Network error")
        
        # Act
        result = send_push_notification(self.test_message, self.test_title, self.test_account_key)
        
        # Assert
        self.assertFalse(result)

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.decrypt')
    @patch('app.alerts.notifier.load_config')
    @patch.dict(os.environ, {'ENCRYPT_KEY': 'test_encrypt_key'})
    def test_send_notification_admin_only(self, mock_load_config, mock_decrypt, mock_send_push):
        """Test sending notification to admin users only."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_account_1',
                        'is_admin': True
                    },
                    {
                        'user_id': 'user2',
                        'account_id': 'encrypted_account_2',
                        'is_admin': False
                    },
                    {
                        'user_id': 'user3',
                        'account_id': 'encrypted_account_3',
                        'is_admin': True
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_decrypt.side_effect = ['decrypted_1', 'decrypted_3']
        mock_send_push.return_value = True
        
        # Act
        result = send_notification(self.test_message, admin=True)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_decrypt.call_count, 2)  # Only admin accounts
        mock_send_push.assert_called_once_with(
            self.test_message,
            'Stocklert',
            'decrypted_1_decrypted_3'
        )

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.decrypt')
    @patch('app.alerts.notifier.load_config')
    @patch.dict(os.environ, {'ENCRYPT_KEY': 'test_encrypt_key'})
    def test_send_notification_specific_users(self, mock_load_config, mock_decrypt, mock_send_push):
        """Test sending notification to specific users."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_account_1',
                        'is_admin': False
                    },
                    {
                        'user_id': 'user2',
                        'account_id': 'encrypted_account_2',
                        'is_admin': False
                    },
                    {
                        'user_id': 'user3',
                        'account_id': 'encrypted_account_3',
                        'is_admin': False
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_decrypt.side_effect = ['decrypted_1', 'decrypted_3']
        mock_send_push.return_value = True
        
        target_users = {'user1', 'user3'}
        
        # Act
        result = send_notification(self.test_message, users=target_users, admin=False)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_decrypt.call_count, 2)  # Only specified users
        mock_send_push.assert_called_once_with(
            self.test_message,
            'Stocklert',
            'decrypted_1_decrypted_3'
        )

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.decrypt')
    @patch('app.alerts.notifier.load_config')
    @patch.dict(os.environ, {'ENCRYPT_KEY': 'test_encrypt_key'})
    def test_send_notification_all_users(self, mock_load_config, mock_decrypt, mock_send_push):
        """Test sending notification to all users when no specific users provided."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_account_1',
                        'is_admin': False
                    },
                    {
                        'user_id': 'user2',
                        'account_id': 'encrypted_account_2',
                        'is_admin': False
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_decrypt.side_effect = ['decrypted_1', 'decrypted_2']
        mock_send_push.return_value = True
        
        # Act
        result = send_notification(self.test_message, admin=False)
        
        # Assert
        self.assertTrue(result)
        self.assertEqual(mock_decrypt.call_count, 2)  # All non-admin users
        mock_send_push.assert_called_once_with(
            self.test_message,
            'Stocklert',
            'decrypted_1_decrypted_2'
        )

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.decrypt')
    @patch('app.alerts.notifier.load_config')
    @patch.dict(os.environ, {'ENCRYPT_KEY': 'test_encrypt_key'})
    def test_send_notification_no_matching_users(self, mock_load_config, mock_decrypt, mock_send_push):
        """Test sending notification when no users match criteria."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_account_1',
                        'is_admin': False
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_send_push.return_value = True
        
        target_users = {'user2', 'user3'}  # Users not in config
        
        # Act
        result = send_notification(self.test_message, users=target_users, admin=False)
        
        # Assert
        self.assertTrue(result)
        mock_decrypt.assert_not_called()
        mock_send_push.assert_called_once_with(
            self.test_message,
            'Stocklert',
            ''  # Empty account key
        )

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.decrypt')
    @patch('app.alerts.notifier.load_config')
    @patch.dict(os.environ, {'ENCRYPT_KEY': 'test_encrypt_key'})
    def test_send_notification_mixed_admin_and_regular(self, mock_load_config, mock_decrypt, mock_send_push):
        """Test notification handling with mixed admin and regular users."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'admin1',
                        'account_id': 'encrypted_admin_1',
                        'is_admin': True
                    },
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_user_1',
                        'is_admin': False
                    },
                    {
                        'user_id': 'admin2',
                        'account_id': 'encrypted_admin_2',
                        'is_admin': True
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_decrypt.return_value = 'decrypted_account'
        mock_send_push.return_value = True
        
        target_users = {'admin1', 'user1'}  # Mix of admin and regular user
        
        # Act
        result = send_notification(self.test_message, users=target_users, admin=False)
        
        # Assert
        self.assertTrue(result)
        # Should include both admin1 and user1 since admin=False and they're in target_users
        self.assertEqual(mock_decrypt.call_count, 2)

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.load_config')
    def test_send_notification_missing_encrypt_key(self, mock_load_config, mock_send_push):
        """Test notification when ENCRYPT_KEY is missing."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_account_1',
                        'is_admin': True
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_send_push.return_value = True
        
        # Act (without ENCRYPT_KEY in environment)
        with patch.dict(os.environ, {}, clear=True):
            result = send_notification(self.test_message, admin=True)
        
        # Assert
        # Should still call send_push_notification but with None as decrypt key
        self.assertTrue(result)

    @patch('app.alerts.notifier.send_push_notification')
    @patch('app.alerts.notifier.decrypt')
    @patch('app.alerts.notifier.load_config')
    def test_send_notification_push_failure(self, mock_load_config, mock_decrypt, mock_send_push):
        """Test when push notification sending fails."""
        # Arrange
        mock_config = {
            'alertzy': {
                'accounts': [
                    {
                        'user_id': 'user1',
                        'account_id': 'encrypted_account_1',
                        'is_admin': False
                    }
                ]
            }
        }
        mock_load_config.return_value = mock_config
        mock_decrypt.return_value = 'decrypted_account'
        mock_send_push.return_value = False  # Push notification fails
        
        # Act
        result = send_notification(self.test_message, admin=False)
        
        # Assert
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()