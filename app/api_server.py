import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import finnhub

from app.helpers.sheets_helpers import log_best_performers, upload_prompt_to_sheets
from app.services.daily_recommender_service import (
    get_daily_recommendations,
    get_best_daily_performers, send_daily_performance,
)
from app.services.improve_prompt_service import improve_daily_prompt


class RequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress health check logs
        if '/health' in args[0]:
            return
        super().log_message(format, *args)

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

            res = get_daily_recommendations(client, api=True)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
        elif self.path == '/daily_performance':
            client = getattr(self.server, 'finnhub_client', None)
            if client is None:
                api_key = os.getenv('FINNHUB_API_KEY')
                client = finnhub.Client(api_key=api_key) if api_key else None

            if client is None:
                self.send_response(500)
                self.end_headers()
                return

            res = send_daily_performance(client, api=True)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
        elif self.path == '/best_performers':
            client = getattr(self.server, 'finnhub_client', None)
            if client is None:
                api_key = os.getenv('FINNHUB_API_KEY')
                client = finnhub.Client(api_key=api_key) if api_key else None

            if client is None:
                self.send_response(500)
                self.end_headers()
                return

            res = get_best_daily_performers(client, api=True)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
        elif self.path == '/debug_best_performers':
            dummy_data = [
                {'symbol': 'AAPL', 'pct': 5.0, 'reason': 'debug'},
                {'symbol': 'MSFT', 'pct': 3.0, 'reason': 'debug'},
            ]
            log_best_performers(dummy_data)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'OK'}).encode())
        elif self.path == '/upload_prompt':
            try:
                upload_prompt_to_sheets()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'OK', 'message': 'Prompt uploaded successfully'}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ERROR', 'message': str(e)}).encode())
        elif self.path == '/improve_prompt':
            try:
                improve_daily_prompt()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'OK'}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'ERROR', 'message': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()


def start_server(port: int = 8000, finnhub_client: finnhub.Client | None = None) -> HTTPServer:
    server = HTTPServer(('0.0.0.0', port), RequestHandler)
    server.finnhub_client = finnhub_client  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
