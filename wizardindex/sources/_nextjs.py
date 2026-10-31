"""Helpers for pulling the data that Next.js App Router pages embed in their HTML."""

import json
import re

_PUSH = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')


def flight_payload(html: str) -> str:
    """Concatenate the React Server Components payload chunks into one string."""
    return "".join(json.loads('"' + chunk + '"') for chunk in _PUSH.findall(html))


def extract_json(payload: str, key: str):
    """Decode the JSON value that follows the first occurrence of `"key":`."""
    marker = f'"{key}":'
    i = payload.find(marker)
    if i < 0:
        raise ValueError(f"key {key!r} not found in page payload")
    value, _ = json.JSONDecoder().raw_decode(payload, i + len(marker))
    return value
