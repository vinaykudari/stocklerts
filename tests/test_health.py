import requests
from app.health_server import start_health_server


def test_health_endpoint(tmp_path):
    server = start_health_server(port=0)
    port = server.server_address[1]
    try:
        resp = requests.get(f'http://127.0.0.1:{port}/health')
        assert resp.status_code == 200
        assert resp.json() == {"status": "OK"}
    finally:
        server.shutdown()


def test_recommendations_endpoint(mocker):
    mock_func = mocker.patch('app.health_server.get_daily_recommendations')
    dummy_client = object()
    server = start_health_server(port=0, finnhub_client=dummy_client)
    port = server.server_address[1]
    try:
        resp = requests.post(f'http://127.0.0.1:{port}/recommendations')
        assert resp.status_code == 200
        assert resp.json() == {"status": "OK"}
        mock_func.assert_called_once_with(dummy_client)
    finally:
        server.shutdown()
