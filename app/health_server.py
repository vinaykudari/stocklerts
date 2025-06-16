import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import finnhub

from app.recommendations.daily_recommender import get_daily_recommendations


class HealthRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # type: ignore[override]
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'OK'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:  # type: ignore[override]
        if self.path == '/recommendations':
            client = getattr(self.server, 'finnhub_client', None)
            if client is None:
                api_key = os.getenv('FINNHUB_API_KEY')
                client = finnhub.Client(api_key=api_key) if api_key else None

            if client is None:
                self.send_response(500)
                self.end_headers()
                return

            get_daily_recommendations(client)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'OK'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:  # noqa: D401
        """Silence default logging."""
        return


def start_health_server(port: int = 8000, finnhub_client: finnhub.Client | None = None) -> HTTPServer:
    """Start a background HTTP server exposing the /health endpoint."""
    server = HTTPServer(('0.0.0.0', port), HealthRequestHandler)
    server.finnhub_client = finnhub_client  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
