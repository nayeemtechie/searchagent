# src/utils/dates.py
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

ISO_FORMATS = (
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%d",
)

def parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    for fmt in ISO_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None

def within_days(dt: Optional[datetime], days: int, now: Optional[datetime] = None) -> bool:
    if not dt:
        return False
    now = now or datetime.now(timezone.utc)
    return dt >= (now - timedelta(days=days))

def fmt_short_date(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    # Asia/Kolkata = UTC+5:30 (no DST)
    ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
    return ist.strftime("%d %b %Y")
