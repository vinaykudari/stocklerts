import logging
import os
import requests
from typing import List, Dict


def fetch_top_gainers_from_fmp(limit: int = 5) -> List[Dict]:
    fmp_api_key = os.getenv('FMP_API_KEY')
    if not fmp_api_key:
        raise ValueError("FMP_API_KEY environment variable not set")

    fmp_url = f"https://financialmodelingprep.com/api/v3/stock_market/gainers?apikey={fmp_api_key}"

    try:
        response = requests.get(fmp_url)
        response.raise_for_status()
        gainers_data = response.json()
        return gainers_data[:limit]
    except Exception as e:
        logging.error(f"Failed to fetch data from Financial Modeling Prep: {e}")
        raise
