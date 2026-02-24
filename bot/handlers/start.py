"""/start command and main menu handler."""
import logging
from telethon import events, Button

from bot import database as db
from bot.config import get_messages
from bot.middlewares.auth import is_admin
from bot.utils.keyboards import main_menu_keyboard, event_detail_keyboard

logger = logging.getLogger(__name__)


def register(client):
    @client.on(events.NewMessage(pattern=r"^/start(.*)$"))
    async def start_handler(event):
        sender = await event.get_sender()
        db.upsert_user(
            telegram_id=sender.id,
            username=sender.username,
            first_name=sender.first_name,
            last_name=sender.last_name,
        )
        first_name = sender.first_name or "کاربر"
        msg = get_messages()

        # Handle deep link payload
        payload = event.pattern_match.group(1).strip()
        if payload.startswith("event_"):
            slug = payload[len("event_"):]
            ev = db.get_event_by_slug(slug)
            if ev:
                from bot.middlewares.membership import enforce_membership
                if not await enforce_membership(client, event):
                    return
                ev_msg = msg["events"]
                price_info = ""
                if ev.get("is_paid") and ev.get("price"):
                    price_info = ev_msg["price_info"].format(price=ev["price"])
                cert_info = ""
                if ev.get("certificate_fee"):
                    cert_info = ev_msg["cert_info"].format(
                        cert_fee=ev["certificate_fee"])
                from bot.utils.jalali import format_jalali_date
                text = ev_msg["detail"].format(
                    title=ev["title"],
                    description=ev.get("description", ""),
                    event_date=format_jalali_date(ev.get("event_date", "")),
                    event_time=ev.get("event_time", ""),
                    location=ev.get("location", ""),
                    capacity=ev.get("capacity", 0),
                    current_registrations=ev.get("current_registrations", 0),
                    price_info=price_info,
                    cert_info=cert_info,
                )
                user = db.get_user(sender.id)
                already_registered = False
                if user:
                    reg = db.get_user_registration(user["id"], ev["id"])
                    already_registered = reg is not None
                await event.respond(
                    text,
                    buttons=event_detail_keyboard(ev, already_registered=already_registered),
                    parse_mode="markdown",
                )
                return

        user = db.get_user(sender.id)
        if user and user.get("last_active"):
            text = msg["start"]["welcome_back"].format(first_name=first_name)
        else:
            text = msg["start"]["welcome"].format(first_name=first_name)

        admin = is_admin(sender.id)
        await event.respond(
            text,
            buttons=main_menu_keyboard(is_admin=admin),
        )

    @client.on(events.CallbackQuery(data=b"main_menu"))
    async def main_menu_callback(event):
        sender = await event.get_sender()
        msg = get_messages()
        first_name = sender.first_name or "کاربر"
        text = msg["start"]["welcome_back"].format(first_name=first_name)
        admin = is_admin(sender.id)
        await event.edit(text, buttons=main_menu_keyboard(is_admin=admin))

    @client.on(events.CallbackQuery(data=b"about"))
    async def about_callback(event):
        msg = get_messages()
        text = msg["about"]["text"]
        await event.edit(
            text,
            buttons=[[Button.inline(msg["menu"]["back"], b"main_menu")]],
            parse_mode="markdown",
        )
