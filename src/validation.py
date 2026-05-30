"""Data validation helpers for the ingestion pipeline."""
import re
from typing import Optional
from datetime import datetime


# RFC 5322-ish simplified pattern. Good enough for sanity checks,
# not a full spec implementation (which is a nightmare).
EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

def is_valid_email(value: Optional[str]) -> bool:
    """Returns True if value looks like a valid email, False otherwise."""
    if not value or not isinstance(value, str):
        return False
    return bool(EMAIL_REGEX.match(value.strip()))


def clean_string(value: Optional[str]) -> Optional[str]:
    """Strips whitespace, converts empty strings to None."""
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    return cleaned if cleaned else None

def is_valid_date(value: Optional[str]) -> bool:
    """Returns True if value parses as YYYY-MM-DD, False otherwise."""
    if not value or not isinstance(value, str):
        return False
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False