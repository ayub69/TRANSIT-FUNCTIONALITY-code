import json
import re
from pathlib import Path

_path = Path(__file__).parent / "stop_names_ur.json"
with open(_path, encoding="utf-8") as f:
    _STOP_UR = json.load(f)

_LINE_UR = {
    "red line": "ریڈ لائن",
    "green line": "گرین لائن",
    "pink line": "پنک لائن",
    "ev line": "ای وی لائن",
    "white line": "وائٹ لائن",
    "double decker": "ڈبل ڈیکر",
    "double decker line": "ڈبل ڈیکر لائن",
}

_ROUTE_UR = {
    # numbered routes
    "route 1": "روٹ ۱",
    "route 2": "روٹ ۲",
    "route 3": "روٹ ۳",
    "route 4": "روٹ ۴",
    "route 5": "روٹ ۵",
    "route 6": "روٹ ۶",
    "route 7": "روٹ ۷",
    "route 8": "روٹ ۸",
    "route 9": "روٹ ۹",
    "route 10": "روٹ ۱۰",
    "route 11": "روٹ ۱۱",
    "route 12": "روٹ ۱۲",
    "route 13": "روٹ ۱۳",
    "route 14": "روٹ ۱۴",
    "route 15": "روٹ ۱۵",
    # named routes
    "green route": "گرین روٹ",
    "red route": "ریڈ روٹ",
    "pink route": "پنک روٹ",
    "ev route": "ای وی روٹ",
    "ev1": "ای وی ۱",
    "ev2": "ای وی ۲",
    "ev3": "ای وی ۳",
    "ev4": "ای وی ۴",
    "ev5": "ای وی ۵",
}


def _stop(name: str) -> str:
    """Return Urdu stop name, fall back to English if not in map."""
    if not name:
        return name or ""
    return _STOP_UR.get(name.lower().strip(), name)


def _line(name: str) -> str:
    return _LINE_UR.get(name.lower().strip(), name)


def _route(name: str) -> str:
    return _ROUTE_UR.get(name.lower().strip(), name)


def _t(step: str) -> str:
    """Translate one English step string to Urdu."""

    # "Start at X."
    m = re.fullmatch(r"Start at (.+)\.", step)
    if m:
        return f"{_stop(m.group(1))} سے شروع کریں۔"

    # "Take LINE (ROUTE) from STOP."
    m = re.fullmatch(r"Take (.+) \((.+)\) from (.+)\.", step)
    if m:
        return f"{_stop(m.group(3))} سے {_line(m.group(1))} ({_route(m.group(2))}) میں سوار ہوں۔"

    # "Ride to X."
    m = re.fullmatch(r"Ride to (.+)\.", step)
    if m:
        return f"{_stop(m.group(1))} تک سواری کریں۔"

    # "Continue to X."
    m = re.fullmatch(r"Continue to (.+)\.", step)
    if m:
        return f"{_stop(m.group(1))} تک جاری رہیں۔"

    # "Transfer at STOP to LINE (ROUTE)."  ← check this BEFORE the "on" pattern
    m = re.fullmatch(r"Transfer at (.+) to (.+) \((.+)\)\.", step)
    if m:
        return f"{_stop(m.group(1))} پر {_line(m.group(2))} ({_route(m.group(3))}) میں تبدیل کریں۔"

    # "Transfer at STOP to ROUTE on LINE."
    m = re.fullmatch(r"Transfer at (.+) to (.+) on (.+)\.", step)
    if m:
        return f"{_stop(m.group(1))} پر {_line(m.group(3))} کی {_route(m.group(2))} میں تبدیل کریں۔"

    # "Arrive at X."
    m = re.fullmatch(r"Arrive at (.+)\.", step)
    if m:
        return f"{_stop(m.group(1))} پر پہنچیں۔"

    # "For female passengers: Pink bus is also available on ROUTE."
    m = re.fullmatch(r"For female passengers: Pink bus is also available on (.+)\.", step)
    if m:
        return f"خواتین مسافروں کے لیے: {_route(m.group(1))} پر پنک بس بھی دستیاب ہے۔"

    return step  # fallback: return unchanged


def translate_steps(english_steps: list) -> list:
    return [_t(s) for s in english_steps]

