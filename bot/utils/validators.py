"""Validators for Iranian national code, email, phone, student ID."""
import re
from bot.utils.persian import normalize_digits


def validate_national_code(code: str) -> bool:
    """Validate Iranian national code (10 digits) using check-digit algorithm."""
    code = normalize_digits(code.strip())
    if not code.isdigit() or len(code) != 10:
        return False
    # All same digits are invalid
    if len(set(code)) == 1:
        return False
    total = sum(int(code[i]) * (10 - i) for i in range(9))
    remainder = total % 11
    check = int(code[9])
    if remainder < 2:
        return check == remainder
    return check == (11 - remainder)


def validate_email(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Validate Iranian mobile phone number (09xxxxxxxxx)."""
    phone = normalize_digits(phone.strip())
    return bool(re.match(r'^09[0-9]{9}$', phone))


def validate_student_id(student_id: str) -> bool:
    """Validate student ID (basic check: numeric, 5-15 digits)."""
    sid = normalize_digits(student_id.strip())
    return sid.isdigit() and 5 <= len(sid) <= 15


def validate_full_name(name: str) -> bool:
    """Validate full name: at least two words, letters only (Persian or Latin)."""
    name = name.strip()
    if len(name) < 3:
        return False
    parts = name.split()
    return len(parts) >= 2
