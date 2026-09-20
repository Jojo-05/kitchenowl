from __future__ import annotations

import gzip
import json
import re
from typing import Any


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_id(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).lower().replace("-", "").strip()


def normalize_instruction_step(value: Any) -> str:
    text = normalize_text(value)
    if not text:
        return ""
    return re.sub(r"^(?:\d+\s*[\.)]\s+)+", "", text)


def normalize_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    match = re.search(r"\d+", str(value))
    if match:
        try:
            return int(match.group(0))
        except (TypeError, ValueError):
            return None
    return None


def _parse_minutes(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(value))

    s = str(value).strip()
    if not s:
        return None

    # Check ISO 8601 format: PT1H30M, PT2H, PT45M, P0DT1H30M, etc.
    iso_match = re.match(
        r"^P(?:.*?T)?(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?$",
        s,
        re.IGNORECASE,
    )
    if iso_match and (iso_match.group(1) or iso_match.group(2) or iso_match.group(3)):
        hours = float(iso_match.group(1)) if iso_match.group(1) else 0.0
        minutes = float(iso_match.group(2)) if iso_match.group(2) else 0.0
        seconds = float(iso_match.group(3)) if iso_match.group(3) else 0.0
        total = int(round(hours * 60 + minutes + seconds / 60))
        if total > 0:
            return total

    # Check natural language: e.g. "1 hr 30 min", "2 hours", "1h 30m"
    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", s, re.IGNORECASE)
    minutes_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)\b", s, re.IGNORECASE
    )
    if hours_match or minutes_match:
        hours = float(hours_match.group(1)) if hours_match else 0.0
        minutes = float(minutes_match.group(1)) if minutes_match else 0.0
        total = int(round(hours * 60 + minutes))
        if total > 0:
            return total

    # Fallback to pure digits
    match = re.search(r"\d+", s)
    if match:
        return int(match.group(0))
    return None


def parse_time(payload: dict[str, Any], *keys: str) -> int | None:
    for k in keys:
        val = payload.get(k)
        if val is not None and val != "":
            res = _parse_minutes(val)
            if res is not None:
                return res
    return None


def normalize_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        value = [line.strip() for line in value.split("\n") if line.strip()]
    elif not isinstance(value, list):
        return []

    items: list[dict[str, Any]] = []
    for entry in value:
        if isinstance(entry, dict):
            name = normalize_text(
                entry.get("name")
                or entry.get("item")
                or entry.get("ingredient")
                or entry.get("recipeIngredient")
            )
            if not name:
                continue

            quantity = normalize_text(entry.get("quantity") or entry.get("amount"))
            note = normalize_text(entry.get("note"))
            desc = " ".join([p for p in (quantity, note) if p]).strip()

            items.append(
                {
                    "name": name,
                    "description": desc,
                    "optional": bool(entry.get("optional", False)),
                }
            )
        else:
            name = normalize_text(entry)
            if name:
                items.append(
                    {
                        "name": name,
                        "description": "",
                        "optional": False,
                    }
                )
    return items


def _is_gzip_bytes(data: bytes) -> bool:
    return len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B


def _load_json_bytes(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))


def maybe_decode_json_payload(data: bytes) -> Any | None:
    if _is_gzip_bytes(data):
        try:
            data = gzip.decompress(data)
        except Exception:
            return None
    try:
        return _load_json_bytes(data)
    except Exception:
        return None
