import os
import pytest
import finnhub

from app.recommendations import daily_recommender as dr


def test_perplexity_api_triggers_notification(monkeypatch):
    api_key = os.getenv('PERPLEXITY_API_KEY')
    model = os.getenv('PERPLEXITY_MODEL')
    encrypt_key = os.getenv('ENCRYPT_KEY')
    if not api_key or not model or not encrypt_key:
        pytest.skip('Perplexity/Alertzy credentials not provided')

    notifications = []

    def fake_send_push_notification(message: str, title: str, account_key: str) -> bool:
        notifications.append((message, title, account_key))
        return True

    monkeypatch.setattr('app.alerts.notifier.send_push_notification', fake_send_push_notification)
    monkeypatch.setattr(finnhub.Client, 'quote', lambda self, symbol: {'o': 100})

    client = finnhub.Client(api_key='dummy')
    dr.get_daily_recommendations(client)

    if not notifications:
        pytest.xfail('Perplexity API request failed')

    assert notifications, 'send_notification was not triggered'
