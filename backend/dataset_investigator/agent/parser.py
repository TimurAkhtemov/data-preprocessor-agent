import json

from .schemas import ACTION_ADAPTER


def parse_action(raw: str):
    if len(raw) > 32_000:
        raise ValueError("Model response exceeds the maximum action size.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The model did not return a JSON action.") from None
        value = json.loads(raw[start : end + 1])
    return ACTION_ADAPTER.validate_python(value)
