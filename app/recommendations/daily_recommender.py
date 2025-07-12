# Standard library imports
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Third-party imports
import finnhub
import requests

# Local application imports
from app.alerts.notifier import send_notification
from app.schemas.prompt_schemas import DAILY_SCHEMA, BEST_PERFORMERS_SCHEMA
from app.utils.helper import load_config, MARKET_TIMEZONE


DAILY_RECOMMENDATIONS_PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'daily_prompt.txt'
DAILY_BEST_PERFORMERS_PROMPT_PATH = Path(__file__).resolve().parents[2] / 'resources' / 'best_performers_prompt.txt'

config = load_config('config.yaml')
USER_IDS = {account['user_id'] for account in config['alertzy']['accounts']}

daily_recommendations: List[Dict[str, float]] = []
prompt_commit_id: str | None = None
best_prompt_commit_id: str | None = None


def _load_prompt(prompt_path) -> str:
    try:
        with open(prompt_path, 'r') as f:
            return f.read()
    except Exception as e:
        logging.error(f"Failed to load prompt: {e}")
        return ""


DAILY_RECOMMENDATIONS_PROMPT = _load_prompt(DAILY_RECOMMENDATIONS_PROMPT_PATH)
DAILY_BEST_PERFORMERS_PROMPT = _load_prompt(DAILY_BEST_PERFORMERS_PROMPT_PATH)


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


def _get_last_prompt_from_sheets(sheet_id: str) -> str:
    """Get the last uploaded prompt content from Google Sheets."""
    logging.debug('Getting last prompt from Google Sheets')

    creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    if not creds_json:
        logging.debug('GOOGLE_SERVICE_ACCOUNT not found')
        raise 

    try:
        import gspread
        logging.debug('Importing gspread library')

        creds = json.loads(creds_json)
        client = gspread.service_account_from_dict(creds)
        logging.debug('Initializing Google Sheets client')

        worksheet = client.open_by_key(sheet_id).sheet1
        logging.debug('Opened worksheet')

        records = worksheet.get_all_records()

        if not records:
            logging.debug('No records found in sheet')
            return ""

        last_record = records[-1]
        last_prompt = last_record.get('Prompt', '')

        logging.debug(f'Retrieved last prompt from sheet (length: {len(last_prompt)})')
        return last_prompt

    except Exception as e:
        logging.error(f'Failed to get last prompt from sheet {sheet_id}: {e}')
        logging.debug('Full exception traceback:', exc_info=True)
        raise e

def upload_prompt_to_sheets() -> None:
    print("Uploading prompt to Google Sheets...")
    """Upload daily_prompt.txt to Google Sheets if it has been updated."""
    logging.info('Checking if daily prompt needs to be uploaded to sheets')

    prompt_path = DAILY_RECOMMENDATIONS_PROMPT_PATH

    if not os.path.exists(prompt_path):
        logging.error(f'Prompt file not found: {prompt_path}')
        return

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            current_content = f.read().strip()
    except Exception as e:
        logging.error(f'Failed to read prompt file: {e}')
        return

    sheet_id = os.getenv('PROMPT_TRACKING_SHEET_ID')

    if not sheet_id:
        logging.info('Prompt tracking disabled; PROMPT_TRACKING_SHEET_ID not set')
        return

    last_content = _get_last_prompt_from_sheets(sheet_id).strip()
    if current_content == last_content and last_content != "":
        logging.info('Prompt file has not changed, skipping upload')
        return

    logging.info('Prompt content has changed, uploading to sheets')

    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = [date_str, current_content]
    header = ['Date', 'Prompt']

    logging.info(f'Uploading prompt to sheet {sheet_id}')

    _append_to_sheet(sheet_id, row, header)

    logging.info('Successfully uploaded prompt to sheets')

def _append_to_sheet(sheet_id: str | None, row: List[str], header: List[str] | None = None) -> None:
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
    date_str = datetime.now().strftime('%Y-%m-%d')

    row: List[str] = [date_str]
    actual_growth_values: List[float] = []

    for idx in range(5):
        rec = recs[idx] if idx < len(recs) else {}
        symbol = rec.get('symbol', '')
        actual_growth = rec.get('pct')
        catalyst = rec.get('catalyst', '')
        predicted_growth = rec.get('target', '')

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
    header = [
        'date',
        'ticker1', 'actual_growth1', 'catalyst1', 'predicted_growth1',
        'ticker2', 'actual_growth2', 'catalyst2', 'predicted_growth2',
        'ticker3', 'actual_growth3', 'catalyst3', 'predicted_growth3',
        'ticker4', 'actual_growth4', 'catalyst4', 'predicted_growth4',
        'ticker5', 'actual_growth5', 'catalyst5', 'predicted_growth5',
        'average_actual_growth', 'market_growth'
    ]
    _append_to_sheet(sheet_id, row, header)


def log_best_performers(recs: List[Dict[str, float]]) -> None:
    """Append end-of-day best performers data to Google Sheets."""
    date_str = datetime.now().strftime('%Y-%m-%d')

    row: List[str] = [date_str]
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



def query_perplexity(prompt: str, schema: dict = None) -> dict:
    api_key = os.getenv('PERPLEXITY_API_KEY')
    model = os.getenv('PERPLEXITY_MODEL')
    if not api_key or not model:
        logging.error('PERPLEXITY_API_KEY or PERPLEXITY_MODEL not set')
        return {}

    logging.info('Querying Perplexity API with provided prompt')

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
    if schema:
        payload['response_format'] = {
            'type': 'json_schema',
            'json_schema': {'schema': schema}
        }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=600)
        resp.raise_for_status()
        data = resp.json()
        content = data['choices'][0]['message']['content'].strip()
        
        if '<think>' in content and '</think>' in content:
            think_end = content.find('</think>') + len('</think>')
            content = content[think_end:].strip()
            content = content.replace('\n', ' ').strip()

        return json.loads(content)
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from Perplexity response: {e}")
        logging.error(f"Raw content: {content}")
        return {}
    except Exception as e:
        logging.error(f"Perplexity API request failed: {e}")
        return {}


def get_daily_recommendations(finnhub_client: finnhub.Client) -> None:
    if not _is_weekday():
        return {}
    logging.warning('Fetching daily stock recommendations from Perplexity')
    response = query_perplexity(DAILY_RECOMMENDATIONS_PROMPT, DAILY_SCHEMA)

    recs = response.get('recommendations', [])
    for rec in recs:
        try:
            quote = finnhub_client.quote(rec['symbol'])
            open_price = quote.get('o')
        except Exception as e:
            logging.error(f"Failed to fetch open price for {rec['symbol']}: {e}")
            open_price = None
        rec['open_price'] = open_price
        daily_recommendations.append(rec)

    logging.info(f"daily_recommendations: {daily_recommendations}")

    if daily_recommendations:
        lines = [f"{r['symbol']}[{r['catalyst']}] | Target: {r['target']} | Risk: {r['risk']}" for r in daily_recommendations]
        message = "Today's picks:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)
        return message

    return {}



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
        return {}
    logging.warning('Fetching top daily performers from Perplexity')
    response = query_perplexity(DAILY_BEST_PERFORMERS_PROMPT, BEST_PERFORMERS_SCHEMA)
    recs = response.get('performers', [])

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

    logging.info(f"performers: {recs}")

    if recs:
        lines = []
        for r in recs:
            pct = r.get('pct')
            if isinstance(pct, float):
                lines.append(f"{r['symbol']} [{pct:+.2f}%]: {r['reason']}")
            else:
                lines.append(f"{r['symbol']}: {r['reason']}")
        message = "Today's best performers:\n" + "\n".join(lines)
        send_notification(message, USER_IDS)
        log_best_performers(recs)
        return message

    return {}
