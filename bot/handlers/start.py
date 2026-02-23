"""/start command and main menu handler."""
import logging
from telethon import events

from bot import database as db
from bot.config import get_messages
from bot.middlewares.auth import is_admin
from bot.utils.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


def register(client):
    @client.on(events.NewMessage(pattern=r"^/start$"))
    async def start_handler(event):
        sender = await event.get_sender()
        user_id = db.upsert_user(
            telegram_id=sender.id,
            username=sender.username,
            first_name=sender.first_name,
            last_name=sender.last_name,
        )
        first_name = sender.first_name or "کاربر"
        msg = get_messages()

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
            buttons=[[__import__("telethon").Button.inline(
                msg["menu"]["back"], b"main_menu"
            )]],
            parse_mode="markdown",
        )
