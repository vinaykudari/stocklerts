import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Optional
from functools import lru_cache

from app.constants import DAILY_RECOMMENDATIONS_PROMPT_PATH


@lru_cache(maxsize=1)
def get_gspread_client():
    """Get cached gspread client with service account authentication."""
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if not creds_json:
        logging.debug("GOOGLE_SERVICE_ACCOUNT environment variable not found")
        return None

    try:
        creds = json.loads(creds_json)
        import gspread
        client = gspread.service_account_from_dict(creds)
        logging.debug("Successfully created gspread client")
        return client
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse service account credentials: {e}")
        return None
    except ImportError as e:
        logging.error(f"Failed to import gspread: {e}")
        return None
    except Exception as e:
        logging.error(f"Failed to create gspread client: {e}")
        return None


def parse_date_value(value: str) -> Optional[datetime]:
    """Parse date value with multiple format attempts."""
    if not value or not str(value).strip():
        return None

    value_str = str(value).strip()

    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(value_str, fmt)
        except ValueError:
            continue

    # Try ISO format parsing as fallback
    try:
        return datetime.fromisoformat(value_str.replace('Z', '+00:00'))
    except ValueError:
        logging.debug(f"Could not parse date value: {value_str}")
        return None


def get_worksheet(sheet_id: str) -> Optional[object]:
    """Get worksheet object with error handling."""
    if not sheet_id:
        logging.error("Sheet ID not provided")
        return None

    client = get_gspread_client()
    if not client:
        return None

    try:
        worksheet = client.open_by_key(sheet_id).sheet1
        logging.debug(f"Successfully opened worksheet for sheet ID: {sheet_id}")
        return worksheet
    except Exception as e:
        logging.error(f"Failed to open worksheet {sheet_id}: {e}")
        return None


def get_last_prompt_from_sheets(sheet_id: str) -> str:
    """Get the last prompt from Google Sheets with improved error handling."""
    logging.debug("Getting last prompt from Google Sheets")

    if not sheet_id:
        logging.error("Sheet ID not provided")
        return ""

    worksheet = get_worksheet(sheet_id)
    if not worksheet:
        return ""

    try:
        records = worksheet.get_all_records()

        if not records:
            logging.debug("No records found in sheet")
            return ""

        last_record = records[-1]
        last_prompt = last_record.get('Prompt', '')

        logging.debug(f"Retrieved last prompt from sheet (length: {len(last_prompt)})")
        return last_prompt

    except Exception as e:
        logging.error(f"Failed to get last prompt from sheet {sheet_id}: {e}")
        return ""


def upload_prompt_to_sheets() -> None:
    """Upload daily prompt to sheets if content has changed."""
    logging.info("Checking if daily prompt needs to be uploaded to sheets")

    prompt_path = DAILY_RECOMMENDATIONS_PROMPT_PATH

    if not os.path.exists(prompt_path):
        logging.error(f"Prompt file not found: {prompt_path}")
        return

    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            current_content = f.read().strip()
    except Exception as e:
        logging.error(f"Failed to read prompt file: {e}")
        return

    sheet_id = os.getenv('PROMPT_TRACKING_SHEET_ID')

    if not sheet_id:
        logging.info("Prompt tracking disabled; PROMPT_TRACKING_SHEET_ID not set")
        return

    last_content = get_last_prompt_from_sheets(sheet_id).strip()
    if current_content == last_content and last_content != "":
        logging.info("Prompt file has not changed, skipping upload")
        return

    logging.info("Prompt content has changed, uploading to sheets")

    date_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    row = [date_str, current_content]
    header = ['Date', 'Prompt']

    logging.info(f"Uploading prompt to sheet {sheet_id}")

    success = append_to_sheet(sheet_id, row, header)
    if success:
        logging.info("Successfully uploaded prompt to sheets")
    else:
        logging.error("Failed to upload prompt to sheets")


def append_to_sheet(sheet_id: str | None, row: List[str], header: List[str] | None = None) -> bool:
    """Append row to Google Sheet with improved error handling."""
    logging.debug(f"Appending to sheet {sheet_id}: {row}")

    if not sheet_id:
        logging.info("Sheet logging disabled; no sheet ID provided")
        return False

    worksheet = get_worksheet(sheet_id)
    if not worksheet:
        logging.error(f"Could not access worksheet {sheet_id}")
        return False

    try:
        # Check if header needs to be added
        if header is not None:
            try:
                existing_headers = worksheet.row_values(1)
                if not existing_headers:
                    worksheet.append_row(header, value_input_option='USER_ENTERED')
                    logging.debug(f"Added header row: {header}")
            except Exception as e:
                logging.warning(f"Could not check/add header: {e}")

        # Append the data row
        worksheet.append_row(row, value_input_option='USER_ENTERED', table_range='A1')
        logging.debug(f"Successfully appended row: {row}")
        return True

    except Exception as e:
        logging.error(f"Failed to append to sheet {sheet_id}: {e}")
        return False


def get_last_prompt_date(sheet_id: str) -> Optional[datetime]:
    """Get the date of the last prompt from the sheet."""
    if not sheet_id:
        logging.debug("No sheet ID provided for last prompt date")
        return None

    worksheet = get_worksheet(sheet_id)
    if not worksheet:
        return None

    try:
        records = worksheet.get_all_records()
        if not records:
            logging.debug("No records found in sheet")
            return None

        last_record = records[-1]

        # Look for date column (case insensitive)
        date_value = None
        for key, value in last_record.items():
            if key.lower() == "date":
                date_value = value
                break

        if date_value:
            parsed_date = parse_date_value(str(date_value))
            if parsed_date:
                return parsed_date.date()

        logging.debug("No valid date found in last record")
        return None

    except Exception as e:
        logging.error(f"Failed to get last prompt date from sheet {sheet_id}: {e}")
        return None


def fetch_records_since(sheet_id: str | None, since: datetime | None) -> List[Dict]:
    """Fetch records from Google Sheets with optional date filtering."""
    if not sheet_id:
        logging.debug("No sheet ID provided")
        return []

    worksheet = get_worksheet(sheet_id)
    if not worksheet:
        return []

    try:
        records = worksheet.get_all_records()

        if since is None:
            logging.debug(f"Retrieved {len(records)} records without date filtering")
            return records

        # Convert since to date if it's datetime
        since_date = since.date() if isinstance(since, datetime) else since

        # Find date column
        date_column = None
        if records:
            for key in records[0].keys():
                if key.lower() in ['date', 'created', 'timestamp', 'created_at']:
                    date_column = key
                    break

        if not date_column:
            logging.warning(f"No date column found in sheet {sheet_id}")
            return records

        # Filter records by date
        filtered_records = []
        for record in records:
            date_value = record.get(date_column)
            if date_value:
                parsed_date = parse_date_value(str(date_value))
                if parsed_date and parsed_date.date() >= since_date:
                    filtered_records.append(record)

        logging.debug(f"Retrieved {len(filtered_records)} records filtered since {since_date}")
        return filtered_records

    except Exception as e:
        logging.error(f"Failed to fetch records from sheet {sheet_id}: {e}")
        return []


def log_daily_performance(recs: List[Dict[str, float]], market_pct: Optional[float]) -> None:
    """Log daily performance data to Google Sheets."""
    logging.info("Logging daily performance data")

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
            f"{actual_growth:+.2f}" if isinstance(actual_growth, (int, float)) else "",
            catalyst,
            str(predicted_growth) if predicted_growth else ""
        ])

        if isinstance(actual_growth, (int, float)):
            actual_growth_values.append(float(actual_growth))

    # Calculate average actual growth
    avg_actual_growth = sum(actual_growth_values) / len(actual_growth_values) if actual_growth_values else None
    row.append(f"{avg_actual_growth:+.2f}" if avg_actual_growth is not None else "")
    row.append(f"{market_pct:+.2f}" if isinstance(market_pct, (int, float)) else "")

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

    success = append_to_sheet(sheet_id, row, header)
    if success:
        logging.info("Successfully logged daily performance data")
    else:
        logging.error("Failed to log daily performance data")


def log_best_performers(recs: List[Dict[str, float]]) -> None:
    """Log best performers data to Google Sheets."""
    logging.info("Logging best performers data")

    date_str = datetime.now().strftime('%Y-%m-%d')

    row: List[str] = [date_str]
    for idx in range(5):
        rec = recs[idx] if idx < len(recs) else {}
        symbol = rec.get('symbol', '')
        pct = rec.get('pct')
        reason = rec.get('reason', '')

        row.extend([
            symbol,
            f"{pct:+.2f}" if isinstance(pct, (int, float)) else "",
            reason,
        ])

    sheet_id = os.getenv('BEST_PERF_SHEET_ID')
    header = [
        'date',
        'ticker1', 'growth1', 'reason1',
        'ticker2', 'growth2', 'reason2',
        'ticker3', 'growth3', 'reason3',
        'ticker4', 'growth4', 'reason4',
        'ticker5', 'growth5', 'reason5',
    ]

    logging.debug(f"Logging best performers to sheet {sheet_id or '<disabled>'}: {row}")

    success = append_to_sheet(sheet_id, row, header)
    if success:
        logging.info("Successfully logged best performers data")
    else:
        logging.error("Failed to log best performers data")


def log_recommended_prompt(analysis: str, new_prompt: str) -> None:
    """Log recommended prompt analysis to Google Sheets."""
    logging.info("Logging recommended prompt analysis")

    sheet_id = os.getenv("RECOMMENDED_PROMPT_SHEET_ID")
    row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), analysis, new_prompt]
    header = ["Date", "Analysis", "Prompt"]

    logging.debug(
        f"Logging recommended prompt to sheet {sheet_id or '<disabled>'}: {len(analysis)} chars analysis, {len(new_prompt)} chars prompt")

    success = append_to_sheet(sheet_id, row, header)
    if success:
        logging.info("Successfully logged recommended prompt analysis")
    else:
        logging.error("Failed to log recommended prompt analysis")