"""Event browsing handler for users."""
import logging
from telethon import events, Button

from bot import database as db
from bot.config import get_messages
from bot.middlewares.membership import enforce_membership
from bot.utils.keyboards import events_keyboard, event_detail_keyboard
from bot.utils.jalali import format_jalali_date

logger = logging.getLogger(__name__)


def register(client):
    @client.on(events.CallbackQuery(data=b"events_list"))
    async def events_list(event):
        if not await enforce_membership(client, event):
            return
        msg = get_messages()
        active_events = db.get_active_events()
        if not active_events:
            await event.edit(
                msg["events"]["no_events"],
                buttons=[[Button.inline(msg["menu"]["back"], b"main_menu")]],
            )
            return
        text = msg["events"]["list_header"]
        await event.edit(text, buttons=events_keyboard(active_events))

    @client.on(events.CallbackQuery(pattern=rb"^event_detail:(\d+)$"))
    async def event_detail(event):
        if not await enforce_membership(client, event):
            return
        event_id = int(event.pattern_match.group(1))
        ev = db.get_event(event_id)
        if not ev:
            msg = get_messages()
            await event.answer(msg["errors"]["not_found"], alert=True)
            return

        msg = get_messages()
        ev_msg = msg["events"]
        price_info = ""
        if ev.get("is_paid") and ev.get("price"):
            price_info = ev_msg["price_info"].format(price=ev["price"])
        cert_info = ""
        if ev.get("certificate_fee"):
            cert_info = ev_msg["cert_info"].format(cert_fee=ev["certificate_fee"])

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

        sender = await event.get_sender()
        user = db.get_user(sender.id)
        already_registered = False
        if user:
            reg = db.get_user_registration(user["id"], event_id)
            already_registered = reg is not None

        await event.edit(
            text,
            buttons=event_detail_keyboard(ev, already_registered=already_registered),
            parse_mode="markdown",
        )
