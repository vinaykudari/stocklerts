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
