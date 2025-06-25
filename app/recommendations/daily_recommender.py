import logging
import csv
import subprocess
from datetime import datetime
from typing import List, Dict, Optional

import re
import os
import finnhub
import requests
from pathlib import Path

from app.alerts.notifier import send_notification
from app.utils.helper import load_config, MARKET_TIMEZONE

PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'daily_prompt.txt'
BEST_PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'best_performers_prompt.txt'
PERF_LOG_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'daily_performance.csv'
BEST_PERF_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'best_daily_performers.csv'

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


def _log_daily_performance(recs: List[Dict[str, float]], market_pct: Optional[float]) -> None:
    """Append daily performance data to the CSV log and commit the change."""
    date_str = datetime.utcnow().strftime('%Y-%m-%d')
    commit_id = prompt_commit_id or _get_prompt_commit_id()

    row: List[str] = [date_str, commit_id]
    pct_values: List[float] = []
    for idx in range(5):
        rec = recs[idx] if idx < len(recs) else {}
        symbol = rec.get('symbol', '')
        pct = rec.get('pct')
        reason = rec.get('reason', '')
        row.extend([symbol, f"{pct:+.2f}" if isinstance(pct, float) else ""])
        if idx < 2:
            row.append(reason)
        if isinstance(pct, float):
            pct_values.append(pct)

    avg_pct = sum(pct_values) / len(pct_values) if pct_values else None
    row.append(f"{avg_pct:+.2f}" if isinstance(avg_pct, float) else "")
    row.append(f"{market_pct:+.2f}" if isinstance(market_pct, float) else "")

    file_exists = PERF_LOG_PATH.exists()
    try:
        with open(PERF_LOG_PATH, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                header = ['date', 'commit_id',
                          'ticker1', 'growth1', 'reason1',
                          'ticker2', 'growth2', 'reason2',
                          'ticker3', 'growth3',
                          'ticker4', 'growth4',
                          'ticker5', 'growth5',
                          'average_growth', 'market_growth']
                writer.writerow(header)
            writer.writerow(row)
    except Exception as e:
        logging.error(f"Failed to write performance log: {e}")
        return

    try:
        subprocess.run(['git', 'add', str(PERF_LOG_PATH)], check=True)
        subprocess.run(
            ['git', 'commit', '-m', f'Add daily performance {date_str}'],
            check=True,
        )
        subprocess.run(['git', 'push'], check=True)
    except Exception as e:
        logging.error(f"Failed to commit performance log: {e}")


def _log_best_performers(recs: List[Dict[str, float]]) -> None:
    """Append end-of-day best performers data to CSV and commit."""
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

    file_exists = BEST_PERF_PATH.exists()
    try:
        with open(BEST_PERF_PATH, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
                header = [
                    'date', 'commit_id',
                    'ticker1', 'growth1', 'reason1',
                    'ticker2', 'growth2', 'reason2',
                    'ticker3', 'growth3', 'reason3',
                    'ticker4', 'growth4', 'reason4',
                    'ticker5', 'growth5', 'reason5',
                ]
                writer.writerow(header)
            writer.writerow(row)
    except Exception as e:
        logging.error(f"Failed to write best performers log: {e}")
        return

    try:
        subprocess.run(['git', 'add', str(BEST_PERF_PATH)], check=True)
        subprocess.run(
            ['git', 'commit', '-m', f'Add best performers {date_str}'],
            check=True,
        )
        subprocess.run(['git', 'push'], check=True)
    except Exception as e:
        logging.error(f"Failed to commit best performers log: {e}")


def _clean_output(text: str) -> str:
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'\|[^|]*\|', '', text)
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
        m = re.match(r'^([A-Z]{1,5})\s*-\s*(.+)$', line.strip())
        if m:
            symbol, reason = m.groups()
            recs.append({'symbol': symbol, 'reason': reason.strip()})
        if len(recs) == 5:
            break
    return recs


def parse_best_performers(text: str) -> List[Dict[str, str]]:
    text = _clean_output(text)
    recs = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r'^([A-Z]{1,5})\s*-\s*(.+?)\s*-\s*([+-]?\d+(?:\.\d+)?)%$', line)
        if m:
            symbol, reason, pct = m.groups()
        else:
            m = re.match(r'^([A-Z]{1,5})\s+([+-]?\d+(?:\.\d+)?)%\s*-\s*(.+)$', line)
            if not m:
                continue
            symbol, pct, reason = m.groups()
        try:
            pct_val = float(pct)
        except Exception:
            continue
        recs.append({'symbol': symbol, 'reason': reason.strip(), 'pct': pct_val})
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
        lines = [f"{r['symbol']}: {r['reason']}" for r in daily_recommendations]
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
            if open_price:
                pct = (close_price - open_price) / open_price * 100
                rec['pct'] = pct
                rec['close_price'] = close_price
                lines.append(f"{rec['symbol']}: {pct:+.2f}%")
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

        try:
            get_best_daily_performers(finnhub_client)
        except Exception as e:
            logging.error(f"Failed to fetch best performers: {e}")


def get_best_daily_performers(finnhub_client: finnhub.Client) -> None:
    if not _is_weekday():
        return
    logging.warning('Fetching top daily performers from Perplexity')
    global best_prompt_commit_id
    best_prompt_commit_id = _get_best_prompt_commit_id()
    text = query_perplexity(BEST_PROMPT)
    recs = parse_best_performers(text)

    if recs:
        lines = [f"{r['symbol']}: {r['pct']:+.2f}% - {r['reason']}" for r in recs]
        message = "Today's best performers:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)
        _log_best_performers(recs)

