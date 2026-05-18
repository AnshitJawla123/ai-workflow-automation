"""Robust JSON extraction from messy LLM responses."""
import json
import re
from typing import Any, Optional

_JSON_BLOCK = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json(text: str) -> Optional[Any]:
    """Return the first valid JSON object/array found in text, else None."""
    if not text:
        return None
    text = text.strip()
    # Strip code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = _JSON_BLOCK.search(text)
    if not m:
        return None
    candidate = m.group(0)
    # Try shrinking by counting braces
    for end in range(len(candidate), 0, -1):
        try:
            return json.loads(candidate[:end])
        except Exception:
            continue
    return None
