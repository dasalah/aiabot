"""Inline keyboard builders for Telethon."""
from telethon import Button
from bot.config import get_messages


def main_menu_keyboard(is_admin: bool = False) -> list:
    msg = get_messages()
    menu = msg["menu"]
    buttons = [
        [Button.inline(menu["events"], b"events_list")],
        [Button.inline(menu["archive"], b"archive_list")],
        [Button.inline(menu["about"], b"about")],
    ]
    if is_admin:
        buttons.append([Button.inline(menu["admin_panel"], b"admin_panel")])
    return buttons


def events_keyboard(events: list) -> list:
    buttons = []
    for event in events:
        label = event["title"]
        callback = f"event_detail:{event['id']}".encode()
        buttons.append([Button.inline(label, callback)])
    msg = get_messages()
    buttons.append([Button.inline(msg["menu"]["back"], b"main_menu")])
    return buttons


def event_detail_keyboard(event: dict, already_registered: bool = False) -> list:
    msg = get_messages()
    buttons = []
    if not already_registered and event.get("registration_open"):
        buttons.append([Button.inline(
            msg["events"]["register_button"],
            f"register:{event['id']}".encode()
        )])
    buttons.append([Button.inline(msg["menu"]["back"], b"events_list")])
    return buttons


def registration_confirm_keyboard() -> list:
    msg = get_messages()
    return [[
        Button.inline(msg["registration"]["confirm_button"], b"reg_confirm"),
        Button.inline(msg["registration"]["cancel_button"], b"reg_cancel"),
    ]]


def waitlist_keyboard() -> list:
    msg = get_messages()
    return [[
        Button.inline(msg["events"]["waitlist_join"], b"waitlist_join"),
        Button.inline(msg["events"]["waitlist_cancel"], b"waitlist_cancel"),
    ]]


def payment_type_keyboard(cert_fee: int) -> list:
    msg = get_messages()
    free_label = msg["registration"]["free_registration"]
    cert_label = msg["registration"]["paid_registration"].format(cert_fee=cert_fee)
    return [[
        Button.inline(free_label, b"pay_free"),
        Button.inline(cert_label, b"pay_cert"),
    ]]


def membership_keyboard(channels: list) -> list:
    msg = get_messages()
    buttons = []
    for ch in channels:
        username = ch.get("channel_username", "")
        title = ch.get("channel_title", username)
        url = f"https://t.me/{username}"
        buttons.append([Button.url(f"📢 {title}", url)])
    buttons.append([Button.inline(msg["membership"]["check_button"], b"check_membership")])
    return buttons


def admin_registration_keyboard(reg_id: int) -> list:
    msg = get_messages()
    return [[
        Button.inline(
            msg["approval"]["approve_button"],
            f"admin_approve:{reg_id}".encode()
        ),
        Button.inline(
            msg["approval"]["reject_button"],
            f"admin_reject:{reg_id}".encode()
        ),
    ]]


def archive_events_keyboard(events: list) -> list:
    buttons = []
    for event in events:
        label = f"📂 {event['title']}"
        callback = f"archive_detail:{event['id']}".encode()
        buttons.append([Button.inline(label, callback)])
    msg = get_messages()
    buttons.append([Button.inline(msg["menu"]["back"], b"main_menu")])
    return buttons


def archive_media_keyboard(event_id: int, page: int, total_pages: int) -> list:
    msg = get_messages()
    archive_msg = msg["archive"]
    nav_row = []
    if page > 0:
        nav_row.append(Button.inline(
            archive_msg["prev_page"],
            f"archive_media:{event_id}:{page - 1}".encode()
        ))
    if page < total_pages - 1:
        nav_row.append(Button.inline(
            archive_msg["next_page"],
            f"archive_media:{event_id}:{page + 1}".encode()
        ))
    buttons = []
    if nav_row:
        buttons.append(nav_row)
    buttons.append([Button.inline(msg["menu"]["back"], f"archive_detail:{event_id}".encode())])
    return buttons


def admin_panel_keyboard() -> list:
    return [
        [Button.inline("📅 مدیریت رویدادها", b"admin_events")],
        [Button.inline("📝 ثبت‌نام‌های در انتظار", b"admin_pending")],
        [Button.inline("📊 آمار", b"admin_stats")],
        [Button.inline("🏠 منوی اصلی", b"main_menu")],
    ]
