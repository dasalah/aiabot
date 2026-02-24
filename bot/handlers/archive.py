"""Past events archive handler with media browsing."""
import logging
import os
from telethon import events, Button

from bot import database as db
from bot.config import get_messages
from bot.middlewares.membership import enforce_membership
from bot.utils.keyboards import archive_events_keyboard, archive_media_keyboard
from bot.utils.jalali import format_jalali_date

logger = logging.getLogger(__name__)

MEDIA_PER_PAGE = 1


def register(client):

    @client.on(events.CallbackQuery(data=b"archive_list"))
    async def archive_list(event):
        if not await enforce_membership(client, event):
            return
        msg = get_messages()
        archived = db.get_archived_events()
        if not archived:
            await event.edit(
                msg["archive"]["no_archive"],
                buttons=[[Button.inline(msg["menu"]["back"], b"main_menu")]],
            )
            return
        await event.edit(
            msg["archive"]["header"],
            buttons=archive_events_keyboard(archived),
        )

    @client.on(events.CallbackQuery(pattern=rb"^archive_detail:(\d+)$"))
    async def archive_detail(event):
        if not await enforce_membership(client, event):
            return
        event_id = int(event.pattern_match.group(1))
        ev = db.get_event(event_id)
        msg = get_messages()
        if not ev:
            await event.answer(msg["errors"]["not_found"], alert=True)
            return

        text = msg["archive"]["event_detail"].format(
            title=ev.get("title", ""),
            event_date=format_jalali_date(ev.get("event_date", "")),
            location=ev.get("location", ""),
            description=ev.get("description", ""),
        )

        media = db.get_event_media(event_id)
        buttons = []
        if media:
            buttons.append([Button.inline(
                msg["archive"]["media_header"],
                f"archive_media:{event_id}:0".encode()
            )])
        buttons.append([Button.inline(msg["menu"]["back"], b"archive_list")])

        await event.edit(text, buttons=buttons, parse_mode="markdown")

    @client.on(events.CallbackQuery(pattern=rb"^archive_media:(\d+):(\d+)$"))
    async def archive_media(event):
        if not await enforce_membership(client, event):
            return
        event_id = int(event.pattern_match.group(1))
        page = int(event.pattern_match.group(2))

        msg = get_messages()
        media_items = db.get_event_media(event_id)
        if not media_items:
            await event.answer(msg["archive"]["no_media"], alert=True)
            return

        total_pages = len(media_items)
        if page >= total_pages:
            page = 0

        item = media_items[page]
        caption = item.get("caption") or ""
        page_info = msg["archive"]["page_info"].format(
            current=page + 1, total=total_pages
        )
        full_caption = f"{caption}\n\n{page_info}" if caption else page_info

        buttons = archive_media_keyboard(event_id, page, total_pages)

        try:
            file_id = item.get("file_id")
            file_path = item.get("file_path")
            chat = await event.get_input_chat()

            if file_id:
                await client.send_file(
                    chat,
                    file_id,
                    caption=full_caption,
                    buttons=buttons,
                )
                await event.answer()
            elif file_path and os.path.isfile(file_path):
                sent_msg = await client.send_file(
                    chat,
                    file_path,
                    caption=full_caption,
                    buttons=buttons,
                )
                await event.answer()
                # Cache the Telegram file_id for future sends.
                # pack_bot_file_id converts the media to a Bot API file_id string
                # that Telethon can use in subsequent send_file() calls.
                try:
                    from telethon.utils import pack_bot_file_id
                    cached_id = pack_bot_file_id(sent_msg.media)
                    db.update_media_file_id(item["id"], cached_id)
                except Exception:
                    pass
            else:
                await event.answer(msg["errors"]["not_found"], alert=True)
        except Exception as e:
            logger.error("Error sending archive media: %s", e)
            await event.answer(msg["errors"]["generic"], alert=True)
