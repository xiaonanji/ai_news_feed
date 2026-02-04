import re
from datetime import datetime
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Australia/Melbourne")


def now_local():
    return datetime.now(LOCAL_TZ)


def to_local(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ)


def normalize_whitespace(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()
