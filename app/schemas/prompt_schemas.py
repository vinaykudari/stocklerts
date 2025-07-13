DAILY_SCHEMA = {
    "type": "object",
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "catalyst": {"type": "string"},
                    "target": {"type": "string"},
                    "risk": {"type": "string"}
                },
                "required": ["symbol", "catalyst", "target", "risk"]
            },
            "minItems": 5,
            "maxItems": 5
        }
    },
    "required": ["recommendations"]
}

BEST_PERFORMERS_SCHEMA = {
    "type": "object",
    "properties": {
        "performers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "pct": {"type": "number"},
                    "reason": {"type": "string"}
                },
                "required": ["symbol", "pct", "reason"]
            },
            "minItems": 5,
            "maxItems": 5
        }
    },
    "required": ["performers"]
}

IMPROVE_SCHEMA = {
    "type": "object",
    "properties": {"new_prompt": {"type": "string"}, "analysis": {"type": "string"}},
    "required": ["new_prompt", "analysis"],
}