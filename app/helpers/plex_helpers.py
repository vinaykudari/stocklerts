import json
import logging
import os
import requests


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
        return {}
    except Exception as e:
        logging.error(f"Perplexity API request failed: {e}")
        return {}
