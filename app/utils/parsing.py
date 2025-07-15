import json
import re
from typing import Any, Optional, Union


def parse_json(text: str) -> Optional[Union[dict, list]]:
    if not isinstance(text, str):
        return None

    match = re.search(r'\{.*\}|\[.*\]', text, re.DOTALL)
    if not match:
        return None

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            repaired_str = re.sub(r',\s*([\}\]])', r'\1', json_str)

            repaired_str = repaired_str.replace('True', 'true')
            repaired_str = repaired_str.replace('False', 'false')
            repaired_str = repaired_str.replace('None', 'null')

            return json.loads(repaired_str)
        except json.JSONDecodeError:
            return None