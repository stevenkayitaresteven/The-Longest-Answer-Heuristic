"""
parsing.py
==========
Defensive extraction of MCQ items from a (possibly messy) model response.

Tolerates code fences, leading prose, and trailing commentary; validates each
candidate against the item schema (k options, exactly-one valid 0-based answer
index, non-empty option strings). Items that fail validation are *dropped and
counted*, never silently coerced.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

_FENCE = re.compile(r"^```(?:json)?|```$", re.MULTILINE)
_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


@dataclass
class ParseResult:
    items: list[dict]
    n_valid: int
    n_rejected: int
    note: str = ""


def _coerce_array(text: str) -> list:
    text = _FENCE.sub("", text.strip()).strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, list) else [obj]
    except json.JSONDecodeError:
        m = _ARRAY.search(text)
        if not m:
            return []
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, list) else [obj]
        except json.JSONDecodeError:
            return []


def _valid_item(obj: object, k: int) -> bool:
    if not isinstance(obj, dict):
        return False
    opts = obj.get("options")
    ai = obj.get("answer_index")
    return (isinstance(opts, list) and len(opts) == k
            and all(isinstance(o, str) and o.strip() for o in opts)
            and isinstance(ai, bool) is False  # guard: bools are ints in Python
            and isinstance(ai, int) and 0 <= ai < k)


def parse_items(text: str, k: int) -> ParseResult:
    """Extract valid MCQ dicts (``stem``/``options``/``answer_index``) from ``text``.

    Returns a ``ParseResult`` carrying the kept items and the count of rejects so
    callers can record yield per cell rather than failing silently.
    """
    candidates = _coerce_array(text)
    kept, rejected = [], 0
    for obj in candidates:
        if _valid_item(obj, k):
            kept.append({
                "stem": str(obj.get("stem", "")).strip(),
                "options": [o.strip() for o in obj["options"]],
                "answer_index": int(obj["answer_index"]),
            })
        else:
            rejected += 1
    note = "" if candidates else "no JSON array found in response"
    return ParseResult(items=kept, n_valid=len(kept), n_rejected=rejected, note=note)
