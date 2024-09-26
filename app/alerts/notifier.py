import logging
import os

import requests
import yaml

from app.utils.crypto import decrypt


def send_push_notification(message: str, title: str, account_key: str) -> bool:
    url = 'https://alertzy.app/send'
    payload = {
        'accountKey': account_key,
        'title': title,
        'message': message
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logging.debug(f'Notification sent successfully')
            return True
        else:
            logging.error(
                f'Failed to send notification. Status Code: {response.status_code}, Response: {response.text}')
            return False
    except Exception as e:
        logging.error(f'Error sending notification: {e}')

    return False


def send_notification(message: str, users: set) -> bool:
    config = load_config()
    accounts = config['alertzy']['accounts']
    title = 'Stocklert'
    account_ids = []

    for account in accounts:
        user_id = account['user_id']
        if user_id in users:
            account_ids.append(decrypt(account['account_id'], os.getenv('ENCRYPT_KEY')))

    account_key = '_'.join(account_ids)
    status = send_push_notification(message, title, account_key)
    return status


def load_config() -> dict:
    with open('config.yaml', 'r') as file:
        return yaml.safe_load(file)
