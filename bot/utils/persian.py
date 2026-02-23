"""RTL and Persian text utilities."""

_FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_AR_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_EN_DIGITS = "0123456789"

_FA_TO_EN = str.maketrans(_FA_DIGITS, _EN_DIGITS)
_AR_TO_EN = str.maketrans(_AR_DIGITS, _EN_DIGITS)


def normalize_digits(text: str) -> str:
    """Convert Persian/Arabic digits to English digits."""
    return text.translate(_FA_TO_EN).translate(_AR_TO_EN)


def to_persian_digits(text: str) -> str:
    """Convert English digits to Persian digits."""
    en_to_fa = str.maketrans(_EN_DIGITS, _FA_DIGITS)
    return str(text).translate(en_to_fa)


def rtl_text(text: str) -> str:
    """Wrap text with RTL mark for proper display."""
    return "\u200f" + text


def format_number(n: int | float) -> str:
    """Format number with Persian-style thousands separator."""
    return f"{n:,}"
