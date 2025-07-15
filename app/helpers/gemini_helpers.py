import os
import json
import logging
from typing import List, Dict

from google.oauth2 import service_account
import google.genai as genai
from google.genai import types

from app.utils.parsing import parse_json


def query_gemini(prompt: str, schema: dict, model_name: str = "gemini-2.5-pro") -> dict | str | List[Dict]:
    project_id = os.getenv('GOOGLE_PROJECT_ID', 'doculoom-446020')
    location = os.getenv('GOOGLE_LOCATION', 'us-central1')
    model_name = os.getenv('GEMINI_MODEL', model_name)
    google_creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT')
    api_key = os.getenv('GOOGLE_API_KEY')

    if not all([project_id, model_name]):
        logging.error("Required Google Cloud environment variables are missing (GOOGLE_PROJECT_ID, GEMINI_MODEL)")
        return {}

    try:
        if api_key:
            client = genai.Client(api_key=api_key)

        elif google_creds_json:
            creds_info = json.loads(google_creds_json)
            scopes = [
                'https://www.googleapis.com/auth/cloud-platform',
                'https://www.googleapis.com/auth/generative-language.retriever',
                'https://www.googleapis.com/auth/generative-language.tuning'
            ]

            credentials = service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=scopes
            )

            client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
                credentials=credentials
            )
        else:
            logging.error("No valid authentication method found (GOOGLE_API_KEY or GOOGLE_SERVICE_ACCOUNT)")
            return {}

    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Failed to parse service account credentials: {e}")
        return {}
    except Exception as e:
        logging.error(f"Failed to initialize Google Gen AI client: {e}")
        return {}

    try:
        generation_config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_modalities=["TEXT"],
            max_output_tokens=5000,
            response_schema=schema
        )
        logging.info("Gemini is thinking...")
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=generation_config,
        )

        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if candidate.content and candidate.content.parts:
                response_text = candidate.content.parts[0].text
                if schema:
                    try:
                        return parse_json(response_text)
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to parse JSON response: {e}")
                        return {}
                else:
                    return response_text.strip()
            else:
                logging.error("No content in response")
                return {} if schema else ""
        else:
            logging.error("No candidates in response")
            return {} if schema else ""

    except Exception as e:
        logging.error(f"Google Gen AI request failed: {e}")
        return {} if schema else ""
