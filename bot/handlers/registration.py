"""User registration flow handler (FSM-driven)."""
import logging
from telethon import events, Button

from bot import database as db
from bot import fsm
from bot.config import get_messages, get_settings
from bot.middlewares.membership import enforce_membership
from bot.utils.keyboards import (
    registration_confirm_keyboard, payment_type_keyboard, waitlist_keyboard
)
from bot.utils.validators import (
    validate_national_code, validate_email, validate_phone,
    validate_student_id, validate_full_name,
)
from bot.utils.persian import normalize_digits
from bot.utils.jalali import format_jalali_date

logger = logging.getLogger(__name__)

# Mapping from FSM state → field key (used for skip logic)
_STATE_TO_FIELD = {
    fsm.STATE_REG_FULL_NAME: "full_name",
    fsm.STATE_REG_STUDENT_ID: "student_id",
    fsm.STATE_REG_NATIONAL_CODE: "national_code",
    fsm.STATE_REG_EMAIL: "email",
    fsm.STATE_REG_PHONE: "phone",
}


def _build_confirm_text(data: dict, event: dict) -> str:
    msg = get_messages()
    settings = get_settings()
    reg_type = "رایگان" if data.get("registration_type") == "free" else "با گواهی"
    return msg["registration"]["confirm_info"].format(
        full_name=data.get("full_name") or "-",
        student_id=data.get("student_id") or "-",
        national_code=data.get("national_code") or "-",
        email=data.get("email") or "-",
        phone=data.get("phone") or "-",
        registration_type=reg_type,
    )


def register(client):

    @client.on(events.CallbackQuery(pattern=rb"^register:(\d+)$"))
    async def start_registration(event):
        if not await enforce_membership(client, event):
            return

        event_id = int(event.pattern_match.group(1))
        ev = db.get_event(event_id)
        if not ev:
            msg = get_messages()
            await event.answer(msg["errors"]["not_found"], alert=True)
            return

        sender = await event.get_sender()
        user = db.get_user(sender.id)
        if not user:
            db.upsert_user(sender.id, sender.username,
                           sender.first_name, sender.last_name)
            user = db.get_user(sender.id)

        if db.get_user_registration(user["id"], event_id):
            msg = get_messages()
            await event.answer(msg["events"]["already_registered"], alert=True)
            return

        msg = get_messages()

        # Check capacity
        if (ev.get("capacity", 0) > 0 and
                ev.get("current_registrations", 0) >= ev["capacity"]):
            if ev.get("waitlist_enabled"):
                await event.edit(
                    msg["events"]["waitlist_available"],
                    buttons=waitlist_keyboard(),
                )
                fsm.set_state(sender.id, fsm.STATE_IDLE,
                              {"event_id": event_id, "waitlist": True})
            else:
                await event.answer(msg["events"]["capacity_full"], alert=True)
            return

        # Start FSM
        fsm.set_state(sender.id, fsm.STATE_REG_FULL_NAME,
                      {"event_id": event_id})

        result = fsm.get_next_field(ev, {})
        if result:
            next_state, is_optional = result
            fsm.set_state(sender.id, next_state, {"event_id": event_id})
            await _ask_field(event, sender.id, next_state, is_optional, msg)
        else:
            # No fields needed – go straight to payment/confirm
            await _handle_payment_step(event, sender.id, ev, {}, msg)

    @client.on(events.CallbackQuery(data=b"waitlist_join"))
    async def join_waitlist(event):
        sender = await event.get_sender()
        state, data = fsm.get_state(sender.id)
        if not data.get("event_id"):
            return
        event_id = data["event_id"]
        user = db.get_user(sender.id)
        ev = db.get_event(event_id)
        if not user or not ev:
            return
        msg = get_messages()
        db.create_registration({
            "user_id": user["id"],
            "event_id": event_id,
            "registration_type": "waitlist",
            "is_waitlist": True,
        })
        fsm.clear_state(sender.id)
        await event.edit(msg["approval"]["waitlisted"])

    @client.on(events.CallbackQuery(data=b"waitlist_cancel"))
    async def cancel_waitlist(event):
        sender = await event.get_sender()
        fsm.clear_state(sender.id)
        msg = get_messages()
        await event.edit(msg["registration"]["cancelled"])

    @client.on(events.NewMessage(pattern=r"^/skip$"))
    async def skip_field(event):
        sender = await event.get_sender()
        if not sender:
            return
        state, data = fsm.get_state(sender.id)
        if state not in _STATE_TO_FIELD:
            return

        msg = get_messages()
        event_id = data.get("event_id")
        ev = db.get_event(event_id) if event_id else None
        if not ev:
            fsm.clear_state(sender.id)
            await event.respond(msg["errors"]["generic"])
            return

        # Check if this field is optional
        field_key = _STATE_TO_FIELD[state]
        optional = ev.get("optional_fields", [])
        if field_key not in optional:
            await event.respond(msg["registration"]["skip_not_allowed"])
            return

        # Skip: store None for this field, move to next
        data[field_key] = None
        result = fsm.get_next_field(ev, data)
        if result:
            next_state, is_optional = result
            fsm.set_state(sender.id, next_state, data)
            await _ask_field(event, sender.id, next_state, is_optional, msg)
        else:
            fsm.set_state(sender.id, state, data)
            await _handle_payment_step(event, sender.id, ev, data, msg)

    @client.on(events.NewMessage)
    async def handle_registration_input(event):
        if event.message.text and event.message.text.startswith("/"):
            return
        sender = await event.get_sender()
        if not sender:
            return

        state, data = fsm.get_state(sender.id)
        if state not in (
            fsm.STATE_REG_FULL_NAME, fsm.STATE_REG_STUDENT_ID,
            fsm.STATE_REG_NATIONAL_CODE, fsm.STATE_REG_EMAIL,
            fsm.STATE_REG_PHONE, fsm.STATE_REG_RECEIPT,
        ):
            return

        msg = get_messages()
        event_id = data.get("event_id")
        ev = db.get_event(event_id) if event_id else None
        if not ev:
            fsm.clear_state(sender.id)
            await event.respond(msg["errors"]["generic"])
            return

        text_input = event.message.text or ""
        text_input = normalize_digits(text_input.strip())
        photo = event.message.photo

        if state == fsm.STATE_REG_RECEIPT:
            if not photo:
                await event.respond(msg["registration"]["invalid_receipt"])
                return
            # Use the actual Telegram file_id from the photo
            receipt_file_id = photo.file_id if hasattr(photo, "file_id") else str(event.message.id)
            data["payment_receipt_file_id"] = receipt_file_id
            data["receipt_message_id"] = event.message.id
            # Move to confirm
            await _show_confirm(event, sender.id, ev, data, msg)
            return

        # Validate and store field
        valid, error_key, stored_key = _validate_field(state, text_input, msg)
        if not valid:
            await event.respond(error_key)
            return

        data[stored_key] = text_input
        fsm.set_state(sender.id, state, data)

        # Find next field
        result = fsm.get_next_field(ev, data)

        if result:
            next_state, is_optional = result
            fsm.set_state(sender.id, next_state, data)
            await _ask_field(event, sender.id, next_state, is_optional, msg)
        else:
            await _handle_payment_step(event, sender.id, ev, data, msg)

    @client.on(events.CallbackQuery(data=b"pay_free"))
    async def pay_free(event):
        sender = await event.get_sender()
        state, data = fsm.get_state(sender.id)
        data["registration_type"] = "free"
        data["payment_amount"] = 0
        ev = db.get_event(data.get("event_id"))
        msg = get_messages()
        if ev:
            await _show_confirm(event, sender.id, ev, data, msg)

    @client.on(events.CallbackQuery(data=b"pay_cert"))
    async def pay_cert(event):
        sender = await event.get_sender()
        state, data = fsm.get_state(sender.id)
        ev = db.get_event(data.get("event_id"))
        msg = get_messages()
        if not ev:
            return
        settings = get_settings()
        cert_fee = ev.get("certificate_fee", 0)
        data["registration_type"] = "cert"
        data["payment_amount"] = cert_fee
        fsm.set_state(sender.id, fsm.STATE_REG_RECEIPT, data)
        card_number = settings.get("payment", {}).get("card_number", "")
        card_holder = settings.get("payment", {}).get("card_holder", "")
        text = msg["payment"]["required"].format(
            amount=cert_fee,
            card_number=card_number,
            card_holder=card_holder,
        )
        await event.edit(text, parse_mode="markdown")

    @client.on(events.CallbackQuery(data=b"reg_confirm"))
    async def confirm_registration(event):
        sender = await event.get_sender()
        state, data = fsm.get_state(sender.id)
        msg = get_messages()
        event_id = data.get("event_id")
        ev = db.get_event(event_id)
        if not ev:
            await event.answer(msg["errors"]["generic"], alert=True)
            return

        user = db.get_user(sender.id)
        if not user:
            db.upsert_user(sender.id, sender.username,
                           sender.first_name, sender.last_name)
            user = db.get_user(sender.id)

        reg_id = db.create_registration({
            "user_id": user["id"],
            "event_id": event_id,
            "full_name": data.get("full_name"),
            "student_id": data.get("student_id"),
            "national_code": data.get("national_code"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "registration_type": data.get("registration_type", "free"),
            "payment_amount": data.get("payment_amount", 0),
            "payment_receipt_file_id": data.get("payment_receipt_file_id"),
            "payment_status": "pending" if data.get("payment_receipt_file_id") else "none",
        })
        if not data.get("is_waitlist"):
            db.increment_registration_count(event_id)

        fsm.clear_state(sender.id)
        await event.edit(msg["registration"]["submitted"])

        # Notify admins
        await _notify_admins_new_registration(client, reg_id, data, user, ev, msg)

    @client.on(events.CallbackQuery(data=b"reg_cancel"))
    async def cancel_registration(event):
        sender = await event.get_sender()
        fsm.clear_state(sender.id)
        msg = get_messages()
        await event.edit(msg["registration"]["cancelled"])


async def _ask_field(event, telegram_id: int, state: str,
                     is_optional: bool, msg: dict) -> None:
    prompts = {
        fsm.STATE_REG_FULL_NAME: msg["registration"]["ask_full_name"],
        fsm.STATE_REG_STUDENT_ID: msg["registration"]["ask_student_id"],
        fsm.STATE_REG_NATIONAL_CODE: msg["registration"]["ask_national_code"],
        fsm.STATE_REG_EMAIL: msg["registration"]["ask_email"],
        fsm.STATE_REG_PHONE: msg["registration"]["ask_phone"],
    }
    prompt = prompts.get(state, "")
    if is_optional and prompt:
        prompt = f"{prompt}\n\n{msg['registration']['optional_hint']}"
    if prompt:
        if hasattr(event, "edit"):
            try:
                await event.edit(prompt)
                return
            except Exception:
                pass
        await event.respond(prompt)


async def _handle_payment_step(event, telegram_id: int, ev: dict, data: dict, msg: dict) -> None:
    settings = get_settings()
    payment_enabled = settings.get("payment", {}).get("enabled", True)

    if ev.get("is_paid") and payment_enabled and ev.get("price"):
        # Main event price – show payment prompt
        card_number = settings.get("payment", {}).get("card_number", "")
        card_holder = settings.get("payment", {}).get("card_holder", "")
        text = msg["payment"]["required"].format(
            amount=ev["price"],
            card_number=card_number,
            card_holder=card_holder,
        )
        fsm.set_state(telegram_id, fsm.STATE_REG_RECEIPT, data)
        data["registration_type"] = "paid"
        data["payment_amount"] = ev["price"]
        if hasattr(event, "edit"):
            try:
                await event.edit(text, parse_mode="markdown")
                return
            except Exception:
                pass
        await event.respond(text, parse_mode="markdown")
    elif ev.get("certificate_fee"):
        # Optional certificate fee
        data["payment_amount"] = 0
        fsm.set_state(telegram_id, fsm.STATE_REG_CONFIRM, data)
        text = msg["registration"]["payment_type_select"]
        if hasattr(event, "edit"):
            try:
                await event.edit(text, buttons=payment_type_keyboard(ev["certificate_fee"]))
                return
            except Exception:
                pass
        await event.respond(text, buttons=payment_type_keyboard(ev["certificate_fee"]))
    else:
        data["registration_type"] = "free"
        data["payment_amount"] = 0
        fsm.set_state(telegram_id, fsm.STATE_REG_CONFIRM, data)
        await _show_confirm(event, telegram_id, ev, data, msg)


async def _show_confirm(event, telegram_id: int, ev: dict, data: dict, msg: dict) -> None:
    fsm.set_state(telegram_id, fsm.STATE_REG_CONFIRM, data)
    text = _build_confirm_text(data, ev)
    if hasattr(event, "edit"):
        try:
            await event.edit(text, buttons=registration_confirm_keyboard(),
                             parse_mode="markdown")
            return
        except Exception:
            pass
    await event.respond(text, buttons=registration_confirm_keyboard(),
                        parse_mode="markdown")


def _validate_field(state: str, value: str, msg: dict) -> tuple[bool, str, str]:
    """Returns (is_valid, error_message, field_key)."""
    if state == fsm.STATE_REG_FULL_NAME:
        if not validate_full_name(value):
            return False, msg["registration"]["invalid_name"], "full_name"
        return True, "", "full_name"
    if state == fsm.STATE_REG_STUDENT_ID:
        if not validate_student_id(value):
            return False, msg["registration"]["invalid_student_id"], "student_id"
        return True, "", "student_id"
    if state == fsm.STATE_REG_NATIONAL_CODE:
        if not validate_national_code(value):
            return False, msg["registration"]["invalid_national_code"], "national_code"
        return True, "", "national_code"
    if state == fsm.STATE_REG_EMAIL:
        if not validate_email(value):
            return False, msg["registration"]["invalid_email"], "email"
        return True, "", "email"
    if state == fsm.STATE_REG_PHONE:
        if not validate_phone(value):
            return False, msg["registration"]["invalid_phone"], "phone"
        return True, "", "phone"
    return False, msg["errors"]["generic"], ""


async def _notify_admins_new_registration(client, reg_id: int, data: dict,
                                           user: dict, ev: dict, msg: dict) -> None:
    from bot.utils.keyboards import admin_registration_keyboard
    admins = db.get_all_admins()
    from bot.config import SUPERADMIN_IDS
    admin_ids = set([a["telegram_id"] for a in admins] + SUPERADMIN_IDS)

    text = msg["admin"]["new_registration"].format(
        full_name=data.get("full_name") or "-",
        student_id=data.get("student_id") or "-",
        national_code=data.get("national_code") or "-",
        email=data.get("email") or "-",
        phone=data.get("phone") or "-",
        event_title=ev.get("title", "-"),
        registration_type=data.get("registration_type", "free"),
        payment_status="در انتظار" if data.get("payment_receipt_file_id") else "بدون پرداخت",
        username=user.get("username") or "-",
        user_id=user.get("telegram_id", "-"),
    )
    buttons = admin_registration_keyboard(reg_id)

    for admin_id in admin_ids:
        try:
            await client.send_message(admin_id, text, buttons=buttons, parse_mode="markdown")
        except Exception as e:
            logger.warning("Failed to notify admin %d: %s", admin_id, e)
