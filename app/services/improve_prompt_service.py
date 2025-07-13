import logging
import os
from typing import Dict

from app.alerts.notifier import send_notification
from app.constants import DAILY_RECOMMENDATIONS_PROMPT_PATH, IMPROVE_PROMPT_PATH
from app.helpers.gemini_helpers import query_gemini
from app.helpers.sheets_helpers import fetch_records_since, get_last_prompt_date, log_recommended_prompt
from app.schemas.prompt_schemas import IMPROVE_SCHEMA
from app.utils.basic import load_prompt, fmt

IMPROVE_PROMPT = load_prompt(IMPROVE_PROMPT_PATH)
DAILY_RECOMMENDATIONS_PROMPT = load_prompt(DAILY_RECOMMENDATIONS_PROMPT_PATH)


def improve_daily_prompt() -> Dict:
    sheet_id = os.getenv("PROMPT_TRACKING_SHEET_ID")
    if not sheet_id:
        logging.info("Prompt improvement disabled; PROMPT_TRACKING_SHEET_ID not set")
        return {"ok": False}

    last_date = get_last_prompt_date(sheet_id)

    daily_rows = fetch_records_since(os.getenv("DAILY_PERF_SHEET_ID"), last_date)
    best_rows = fetch_records_since(os.getenv("BEST_PERF_SHEET_ID"), last_date)

    if not daily_rows and not best_rows:
        logging.warning("No new data found for prompt improvement")
        return {"ok": False}

    prompt = IMPROVE_PROMPT.format(
        current_prompt=DAILY_RECOMMENDATIONS_PROMPT,
        daily_rows=fmt(daily_rows),
        best_rows=fmt(best_rows),
    )

    resp = query_gemini(prompt, IMPROVE_SCHEMA)
    new_prompt = resp.get("new_prompt") if isinstance(resp, dict) else None
    if not new_prompt:
        logging.error("Gemini did not return improved prompt")
        return {"ok": False}

    log_recommended_prompt(analysis=resp['analysis'], new_prompt=resp['new_prompt'])
    send_notification("Daily prompt is updated", admin=True)
    return {"ok": True}


