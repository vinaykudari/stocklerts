import logging
from typing import List, Dict, Optional

import finnhub

from app.alerts.notifier import send_notification
from app.constants import DAILY_RECOMMENDATIONS_PROMPT_PATH, DAILY_BEST_PERFORMERS_PROMPT_PATH
from app.helpers.plex_helpers import query_perplexity
from app.helpers.sheets_helpers import log_daily_performance, log_best_performers
from app.schemas.prompt_schemas import DAILY_SCHEMA, BEST_PERFORMERS_SCHEMA
from app.utils.basic import is_weekday, load_prompt

daily_recommendations: List[Dict[str, float]] = []

DAILY_RECOMMENDATIONS_PROMPT = load_prompt(DAILY_RECOMMENDATIONS_PROMPT_PATH)
DAILY_BEST_PERFORMERS_PROMPT = load_prompt(DAILY_BEST_PERFORMERS_PROMPT_PATH)


def get_market_pct(client: finnhub.Client) -> Optional[float]:
    try:
        quote = client.quote('SPY')
        open_price = quote.get('o')
        close_price = quote.get('c')
        if open_price:
            return (close_price - open_price) / open_price * 100
    except Exception as e:
        logging.error(f"Failed to fetch market performance: {e}")
    return None


def get_daily_recommendations(finnhub_client: finnhub.Client, api=False) -> Dict:
    if not api and not is_weekday():
        return {}
    logging.info('Fetching daily stock recommendations from Perplexity')
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
        lines = [f"{r['symbol']}: {r['catalyst']} Target: {r['target']} Risk: {r['risk']}" for r in
                 daily_recommendations]
        message = "Perplexity read the news and recommends:\n" + "\n".join(lines)
        send_notification(message, admin=api)
        return {"message": message}

    return {}


def send_daily_performance(finnhub_client: finnhub.Client, api=False) -> Dict:
    if (not api and not is_weekday()) or not daily_recommendations:
        return {}
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
        send_notification(message, admin=api)
        market_pct = get_market_pct(finnhub_client)
        try:
            log_daily_performance(daily_recommendations, market_pct)
        except Exception as e:
            logging.error(f"Failed to log daily performance: {e}")

        return {"message": message}

    return {}


def get_best_daily_performers(finnhub_client: finnhub.Client, api=False) -> Dict:
    if not api and not is_weekday():
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
        send_notification(message, admin=api)
        log_best_performers(recs)
        return {"message": message}

    return {}
