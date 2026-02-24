"""Finite State Machine for user registration flow."""
from bot import database as db

# State names
STATE_IDLE = "idle"
STATE_REG_FULL_NAME = "reg_full_name"
STATE_REG_STUDENT_ID = "reg_student_id"
STATE_REG_NATIONAL_CODE = "reg_national_code"
STATE_REG_EMAIL = "reg_email"
STATE_REG_PHONE = "reg_phone"
STATE_REG_PAYMENT_TYPE = "reg_payment_type"
STATE_REG_RECEIPT = "reg_receipt"
STATE_REG_CONFIRM = "reg_confirm"
STATE_ADMIN_REJECT_REASON = "admin_reject_reason"
STATE_ADMIN_BROADCAST_TEXT = "admin_broadcast_text"
STATE_ADMIN_BROADCAST_TARGET = "admin_broadcast_target"


def get_state(telegram_id: int) -> tuple[str, dict]:
    row = db.get_user_state(telegram_id)
    if row is None:
        return STATE_IDLE, {}
    return row["state"], row["state_data"]


def set_state(telegram_id: int, state: str, data: dict | None = None) -> None:
    db.set_user_state(telegram_id, state, data or {})


def update_state_data(telegram_id: int, updates: dict) -> None:
    state, data = get_state(telegram_id)
    data.update(updates)
    set_state(telegram_id, state, data)


def clear_state(telegram_id: int) -> None:
    db.clear_user_state(telegram_id)


def get_next_field(event: dict, current_data: dict) -> tuple[str, bool] | None:
    """Return (next_state, is_optional) for the next uncollected field, or None."""
    required = event.get("required_fields", [])
    optional = event.get("optional_fields", [])
    field_states = {
        "full_name": STATE_REG_FULL_NAME,
        "student_id": STATE_REG_STUDENT_ID,
        "national_code": STATE_REG_NATIONAL_CODE,
        "email": STATE_REG_EMAIL,
        "phone": STATE_REG_PHONE,
    }
    for field in required:
        if field in field_states and field not in current_data:
            return field_states[field], False
    for field in optional:
        if field in field_states and field not in current_data:
            return field_states[field], True
    return None
