import requests
from app.api_server import start_health_server


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


def test_best_performers_endpoint(mocker):
    mock_func = mocker.patch('app.health_server.get_best_daily_performers')
    dummy_client = object()
    server = start_health_server(port=0, finnhub_client=dummy_client)
    port = server.server_address[1]
    try:
        resp = requests.post(f'http://127.0.0.1:{port}/best_performers')
        assert resp.status_code == 200
        assert resp.json() == {"status": "OK"}
        mock_func.assert_called_once_with(dummy_client)
    finally:
        server.shutdown()


def test_best_performers_endpoint_appends_sheet(monkeypatch, mocker):
    rows: list[list[str]] = []

    class DummyWorksheet:
        def __init__(self):
            self.data = []

        def get_all_values(self):
            return list(self.data)

        def row_values(self, idx):
            return self.data[idx - 1] if len(self.data) >= idx else []

        def append_row(self, row, value_input_option='USER_ENTERED', **kwargs):
            self.data.append(row)
            rows.append(row)

    dummy_ws = DummyWorksheet()

    class DummyClient:
        def open_by_key(self, key):
            return type('S', (), {'sheet1': dummy_ws})

    def service_account_from_dict(creds):
        return DummyClient()

    import types, sys

    gspread_dummy = types.SimpleNamespace(service_account_from_dict=service_account_from_dict)
    monkeypatch.setitem(sys.modules, 'gspread', gspread_dummy)
    monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT', '{}')
    monkeypatch.setenv('BEST_PERF_SHEET_ID', 'sheetid')

    monkeypatch.setattr(
        'app.recommendations.daily_recommender.query_perplexity',
        lambda prompt: '$AAPL | good | +2% | Low\n$MSFT | nice | +3% | Medium'
    )
    monkeypatch.setattr('app.recommendations.daily_recommender._is_weekday', lambda: True)
    monkeypatch.setattr('app.recommendations.daily_recommender._get_best_prompt_commit_id', lambda: 'abc')
    monkeypatch.setattr('app.recommendations.daily_recommender.send_notification', lambda msg, ids: None)

    dummy_client = mocker.Mock()
    dummy_client.quote.return_value = {'o': 10, 'c': 11}

    server = start_health_server(port=0, finnhub_client=dummy_client)
    port = server.server_address[1]
    try:
        resp = requests.post(f'http://127.0.0.1:{port}/best_performers')
        assert resp.status_code == 200
    finally:
        server.shutdown()

    assert rows[0][0] == 'date'
    assert len(rows) == 2


def test_debug_best_performers_endpoint(monkeypatch):
    rows: list[list[str]] = []

    class DummyWorksheet:
        def __init__(self):
            self.data = []

        def get_all_values(self):
            return list(self.data)

        def row_values(self, idx):
            return self.data[idx - 1] if len(self.data) >= idx else []

        def append_row(self, row, value_input_option='USER_ENTERED', **kwargs):
            self.data.append(row)
            rows.append(row)

    dummy_ws = DummyWorksheet()

    class DummyClient:
        def open_by_key(self, key):
            return type('S', (), {'sheet1': dummy_ws})

    def service_account_from_dict(creds):
        return DummyClient()

    import types, sys

    gspread_dummy = types.SimpleNamespace(service_account_from_dict=service_account_from_dict)
    monkeypatch.setitem(sys.modules, 'gspread', gspread_dummy)
    monkeypatch.setenv('GOOGLE_SERVICE_ACCOUNT', '{}')
    monkeypatch.setenv('BEST_PERF_SHEET_ID', 'sheetid')

    server = start_health_server(port=0)
    port = server.server_address[1]
    try:
        resp = requests.post(f'http://127.0.0.1:{port}/debug_best_performers')
        assert resp.status_code == 200
    finally:
        server.shutdown()

    assert len(rows) == 2
