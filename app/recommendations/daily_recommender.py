import logging
from typing import List, Dict

import re
import os
import finnhub
import requests
from pathlib import Path

from app.alerts.notifier import send_notification
from app.utils.helper import load_config

PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'daily_prompt.txt'

config = load_config('config.yaml')
USER_IDS = {account['user_id'] for account in config['alertzy']['accounts']}

daily_recommendations: List[Dict[str, float]] = []


def _load_prompt() -> str:
    try:
        with open(PROMPT_PATH, 'r') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load prompt: {e}")
        return ""


PROMPT = _load_prompt()


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
    logging.warning('Fetching daily stock recommendations from Perplexity')
    prompt = PROMPT
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
    if not daily_recommendations:
        return
    lines = []
    for rec in daily_recommendations:
        try:
            quote = finnhub_client.quote(rec['symbol'])
            close_price = quote.get('c')
            open_price = rec.get('open_price')
            if open_price:
                pct = (close_price - open_price) / open_price * 100
                lines.append(f"{rec['symbol']}: {pct:+.2f}%")
        except Exception as e:
            logging.error(f"Failed to fetch close price for {rec['symbol']}: {e}")
    if lines:
        message = "Performance of today's picks:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)
