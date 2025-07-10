import logging
import subprocess
from datetime import datetime
from typing import List, Dict, Optional

import re
import os
import json
import finnhub
import requests
from pathlib import Path

from app.alerts.notifier import send_notification
from app.utils.helper import load_config, MARKET_TIMEZONE


def _in_git_repo(path: Path) -> bool:
    """Return True if the given path is inside a git repository."""
    cur = path.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / '.git').exists():
            return True
    return False


PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'daily_prompt.txt'
BEST_PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'best_performers_prompt.txt'

config = load_config('config.yaml')
USER_IDS = {account['user_id'] for account in config['alertzy']['accounts']}

daily_recommendations: List[Dict[str, float]] = []
# commit hash of the prompt file used when generating today's recommendations
prompt_commit_id: str | None = None
best_prompt_commit_id: str | None = None


def _load_prompt() -> str:
    try:
        with open(PROMPT_PATH, 'r') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load prompt: {e}")
        return ""


PROMPT = _load_prompt()


def _load_best_prompt() -> str:
    try:
        with open(BEST_PROMPT_PATH, 'r') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load best performers prompt: {e}")
        return ""


BEST_PROMPT = _load_best_prompt()


def _get_prompt_commit_id() -> str:
    """Return the latest git commit hash for the prompt file."""
    if not _in_git_repo(PROMPT_PATH):
        return ""
    try:
        commit = subprocess.check_output(
            ['git', 'log', '-1', '--pretty=format:%H', str(PROMPT_PATH)]
        )
        return commit.decode().strip()
    except Exception as e:
        logging.error(f"Failed to get prompt commit id: {e}")
        return ""


def _get_best_prompt_commit_id() -> str:
    """Return commit hash for the best performers prompt file."""
    if not _in_git_repo(BEST_PROMPT_PATH):
        return ""
    try:
        commit = subprocess.check_output(
            ['git', 'log', '-1', '--pretty=format:%H', str(BEST_PROMPT_PATH)]
        )
        return commit.decode().strip()
    except Exception as e:
        logging.error(f"Failed to get best prompt commit id: {e}")
        return ""


def _get_market_pct(client: finnhub.Client) -> Optional[float]:
    """Return today's percentage change for the US market via SPY ETF."""
    try:
        quote = client.quote('SPY')
        open_price = quote.get('o')
        close_price = quote.get('c')
        if open_price:
            return (close_price - open_price) / open_price * 100
    except Exception as e:
        logging.error(f"Failed to fetch market performance: {e}")
    return None


def _is_weekday() -> bool:
    return datetime.now(MARKET_TIMEZONE).weekday() < 5


def _append_to_sheet(sheet_id: str | None, row: List[str], header: List[str] | None = None) -> None:
    """Append a row to Google Sheet with proper header handling and debug logging."""
    logging.debug('Function called with sheet_id=%s, row=%s', sheet_id, row)

    if not sheet_id:
        logging.debug('Sheet ID not provided')
        logging.info('Sheet logging disabled; no sheet id provided')
        return

    logging.debug('Sheet ID provided: %s', sheet_id)

    creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    if not creds_json:
        logging.debug('GOOGLE_SERVICE_ACCOUNT not found')
        logging.info('Sheet logging disabled; GOOGLE_SERVICE_ACCOUNT not set')
        return

    logging.debug('Credentials loaded from environment')

    try:
        import gspread
        logging.debug('Importing gspread library')

        creds = json.loads(creds_json)
        client = gspread.service_account_from_dict(creds)
        logging.debug('Initializing Google Sheets client')

        worksheet = client.open_by_key(sheet_id).sheet1
        logging.debug('Opened worksheet')

        if header is not None and not worksheet.row_values(1):
            worksheet.append_row(header, value_input_option='USER_ENTERED')
            logging.debug('Appending header row: %s', header)

        worksheet.append_row(row, value_input_option='USER_ENTERED', table_range='A1')
        logging.debug('Appending data row: %s', row)

    except Exception as e:
        logging.error(f'Failed to append to sheet {sheet_id}: {e}')
        logging.debug('Full exception traceback:', exc_info=True)


def _log_daily_performance(recs: List[Dict[str, float]], market_pct: Optional[float]) -> None:
    """Append daily performance data to Google Sheets."""
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    commit_id = prompt_commit_id or _get_prompt_commit_id()

    row: List[str] = [date_str, commit_id]
    actual_growth_values: List[float] = []

    # Include catalyst and predicted_growth for all 5 tickers
    for idx in range(5):
        rec = recs[idx] if idx < len(recs) else {}
        symbol = rec.get('symbol', '')
        actual_growth = rec.get('pct')  # This will be renamed in display
        catalyst = rec.get('catalyst', '')
        predicted_growth = rec.get('target', '')  # This comes from 'target' field

        row.extend([
            symbol,
            f"{actual_growth:+.2f}" if isinstance(actual_growth, float) else "",
            catalyst,
            predicted_growth
        ])

        if isinstance(actual_growth, float):
            actual_growth_values.append(actual_growth)

    avg_actual_growth = sum(actual_growth_values) / len(actual_growth_values) if actual_growth_values else None
    row.append(f"{avg_actual_growth:+.2f}" if isinstance(avg_actual_growth, float) else "")
    row.append(f"{market_pct:+.2f}" if isinstance(market_pct, float) else "")

    sheet_id = os.getenv('DAILY_PERF_SHEET_ID')
    # Updated header with new field names for all 5 tickers
    header = [
        'date', 'commit_id',
        'ticker1', 'actual_growth1', 'catalyst1', 'predicted_growth1',
        'ticker2', 'actual_growth2', 'catalyst2', 'predicted_growth2',
        'ticker3', 'actual_growth3', 'catalyst3', 'predicted_growth3',
        'ticker4', 'actual_growth4', 'catalyst4', 'predicted_growth4',
        'ticker5', 'actual_growth5', 'catalyst5', 'predicted_growth5',
        'average_actual_growth', 'market_growth'
    ]
    _append_to_sheet(sheet_id, row, header)


def _log_best_performers(recs: List[Dict[str, float]]) -> None:
    """Append end-of-day best performers data to Google Sheets."""
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    commit_id = best_prompt_commit_id or _get_best_prompt_commit_id()

    row: List[str] = [date_str, commit_id]
    for idx in range(5):
        rec = recs[idx] if idx < len(recs) else {}
        symbol = rec.get('symbol', '')
        pct = rec.get('pct')
        reason = rec.get('reason', '')
        row.extend([
            symbol,
            f"{pct:+.2f}" if isinstance(pct, float) else "",
            reason,
        ])

    sheet_id = os.getenv('BEST_PERF_SHEET_ID')
    header = [
        'date', 'commit_id',
        'ticker1', 'growth1', 'reason1',
        'ticker2', 'growth2', 'reason2',
        'ticker3', 'growth3', 'reason3',
        'ticker4', 'growth4', 'reason4',
        'ticker5', 'growth5', 'reason5',
    ]
    logging.info(
        'Logging best performers to sheet %s: %s',
        sheet_id or '<disabled>',
        row,
    )
    _append_to_sheet(sheet_id, row, header)


def _clean_output(text: str) -> str:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'^#+\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^-+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\*\s+.*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s+\n', '\n', text)
    return text.strip()


def parse_recommendations(text: str) -> List[Dict[str, str]]:
    text = _clean_output(text)
    recs = []
    for line in text.splitlines():
        m = re.match(r'^\$?([A-Z]{1,5}) \| (.+?) \| \+?([0-9]+(?:-[0-9]+)?%) \| (Low|Medium|High)$', line.strip())
        if m:
            symbol, catalyst, target, risk = m.groups()
            recs.append({
                'symbol': symbol,
                'catalyst': catalyst.strip(),
                'target': target,
                'risk': risk
            })
        if len(recs) == 5:
            break
    return recs


def query_perplexity(prompt: str) -> str:
    api_key = os.getenv('PERPLEXITY_API_KEY')
    model = os.getenv('PERPLEXITY_MODEL')
    if not api_key or not model:
        logging.error('PERPLEXITY_API_KEY or PERPLEXITY_MODEL not set')
        return ""
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': model,
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.2,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"Perplexity API request failed: {e}")
        return ""


def get_daily_recommendations(finnhub_client: finnhub.Client) -> None:
    if not _is_weekday():
        return
    logging.warning('Fetching daily stock recommendations from Perplexity')
    global prompt_commit_id
    prompt = PROMPT
    prompt_commit_id = _get_prompt_commit_id()
    text = query_perplexity(prompt)
    recs = parse_recommendations(text)

    daily_recommendations.clear()
    for rec in recs:
        try:
            quote = finnhub_client.quote(rec['symbol'])
            open_price = quote.get('o')
        except Exception as e:
            logging.error(f"Failed to fetch open price for {rec['symbol']}: {e}")
            open_price = None
        rec['open_price'] = open_price
        daily_recommendations.append(rec)

    if daily_recommendations:
        lines = [f"{r['symbol']} | {r['catalyst']} | {r['target']} | {r['risk']}" for r in daily_recommendations]
        message = "Today's picks:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)


def send_daily_performance(finnhub_client: finnhub.Client) -> None:
    if not _is_weekday() or not daily_recommendations:
        return
    lines = []
    for rec in daily_recommendations:
        try:
            quote = finnhub_client.quote(rec['symbol'])
            close_price = quote.get('c')
            open_price = rec.get('open_price')
            if open_price and close_price is not None:
                pct = (close_price - open_price) / open_price * 100
                rec['pct'] = pct
                rec['close_price'] = close_price
                target = rec.get('target', '')
                lines.append(f"{rec['symbol']}: Actual: {pct:+.2f}%  Predicted: {target}")
        except Exception as e:
            logging.error(f"Failed to fetch close price for {rec['symbol']}: {e}")
    if lines:
        message = "Performance of today's picks:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)
        market_pct = _get_market_pct(finnhub_client)
        try:
            _log_daily_performance(daily_recommendations, market_pct)
        except Exception as e:
            logging.error(f"Failed to log daily performance: {e}")


def get_best_daily_performers(finnhub_client: finnhub.Client) -> None:
    if not _is_weekday():
        return
    logging.warning('Fetching top daily performers from Perplexity')
    global best_prompt_commit_id
    best_prompt_commit_id = _get_best_prompt_commit_id()
    text = query_perplexity(BEST_PROMPT)
    recs = parse_recommendations(text)

    for rec in recs:
        if 'catalyst' in rec and 'reason' not in rec:
            rec['reason'] = rec['catalyst']

    for rec in recs:
        if 'pct' not in rec:
            try:
                quote = finnhub_client.quote(rec['symbol'])
                open_price = quote.get('o')
                close_price = quote.get('c')
                if open_price:
                    pct = (close_price - open_price) / open_price * 100
                    rec['pct'] = pct
            except Exception as e:
                logging.error(f"Failed to fetch performance for {rec['symbol']}: {e}")

    if recs:
        lines = []
        for r in recs:
            pct = r.get('pct')
            if isinstance(pct, float):
                lines.append(f"{r['symbol']}[{pct:+.2f}%]: {r['reason']}")
            else:
                lines.append(f"{r['symbol']}: {r['reason']}")
        message = "Today's best performers:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)
        _log_best_performers(recs)
