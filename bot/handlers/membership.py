"""Channel membership check handler."""
import logging
from telethon import events

from bot import database as db
from bot.config import get_messages
from bot.middlewares.membership import check_membership

logger = logging.getLogger(__name__)


def register(client):

    @client.on(events.CallbackQuery(data=b"check_membership"))
    async def check_membership_callback(event):
        sender = await event.get_sender()
        msg = get_messages()
        all_joined, missing = await check_membership(client, sender.id)
        if all_joined:
            from bot.utils.keyboards import main_menu_keyboard
            from bot.middlewares.auth import is_admin
            text = msg["membership"]["verified"]
            await event.edit(
                text,
                buttons=main_menu_keyboard(is_admin=is_admin(sender.id)),
            )
        else:
            await event.answer(msg["membership"]["not_verified"], alert=True)
