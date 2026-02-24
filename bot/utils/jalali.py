"""Jalali (Shamsi/Persian) calendar utilities."""
import re

try:
    import jdatetime
    _JDATETIME_AVAILABLE = True
except ImportError:
    _JDATETIME_AVAILABLE = False

PERSIAN_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر",
    "مرداد", "شهریور", "مهر", "آبان",
    "آذر", "دی", "بهمن", "اسفند",
]

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"


def _to_persian_digits(num: int) -> str:
    return "".join(PERSIAN_DIGITS[int(d)] for d in str(num))


def gregorian_to_jalali(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' Gregorian to 'YYYY/MM/DD' Jalali string."""
    if not date_str or not _JDATETIME_AVAILABLE:
        return date_str or ""
    try:
        parts = date_str.strip().split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        jd = jdatetime.date.fromgregorian(year=y, month=m, day=d)
        return f"{jd.year}/{jd.month:02d}/{jd.day:02d}"
    except Exception:
        return date_str


def jalali_to_gregorian(jalali_str: str) -> str:
    """Convert 'YYYY/MM/DD' or 'YYYY-MM-DD' Jalali to 'YYYY-MM-DD' Gregorian."""
    if not jalali_str or not _JDATETIME_AVAILABLE:
        return jalali_str or ""
    try:
        parts = re.split(r"[-/]", jalali_str.strip())
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        gd = jdatetime.date(y, m, d).togregorian()
        return gd.strftime("%Y-%m-%d")
    except Exception:
        return jalali_str


def format_jalali_date(date_str: str) -> str:
    """Format 'YYYY-MM-DD' Gregorian as pretty Jalali, e.g. '۵ اسفند ۱۴۰۴'."""
    if not date_str or not _JDATETIME_AVAILABLE:
        return date_str or ""
    try:
        parts = date_str.strip().split("-")
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        jd = jdatetime.date.fromgregorian(year=y, month=m, day=d)
        month_name = PERSIAN_MONTHS[jd.month - 1]
        return f"{_to_persian_digits(jd.day)} {month_name} {_to_persian_digits(jd.year)}"
    except Exception:
        return date_str
