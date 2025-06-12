import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


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

    def log_message(self, format: str, *args) -> None:  # noqa: D401
        """Silence default logging."""
        return


def start_health_server(port: int = 8000) -> HTTPServer:
    """Start a background HTTP server exposing the /health endpoint."""
    server = HTTPServer(('0.0.0.0', port), HealthRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
