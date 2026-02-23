"""Channel membership enforcement middleware."""
import logging
from telethon.errors import UserNotParticipantError, ChannelPrivateError
from bot import database as db
from bot.config import get_messages, get_channels
from bot.utils.keyboards import membership_keyboard

logger = logging.getLogger(__name__)


async def check_membership(client, telegram_id: int) -> tuple[bool, list[dict]]:
    """
    Check if the user is member of all required channels.
    Returns (all_joined, list_of_missing_channels).
    """
    # Channels from DB take priority; fall back to config file
    db_channels = db.get_required_channels()
    if not db_channels:
        cfg = get_channels()
        db_channels = cfg.get("required_channels", [])

    missing = []
    for ch in db_channels:
        username = ch.get("channel_username") or ch.get("username", "")
        if not username:
            continue
        try:
            participant = await client.get_permissions(f"@{username}", telegram_id)
            if not participant.is_member and not participant.is_admin:
                missing.append(ch)
        except UserNotParticipantError:
            missing.append(ch)
        except ChannelPrivateError:
            # Can't check private channel – skip check
            pass
        except Exception as e:
            logger.warning("Error checking membership for @%s: %s", username, e)

    return len(missing) == 0, missing


async def enforce_membership(client, event) -> bool:
    """
    Check membership and send join prompt if needed.
    Returns True if user has access, False if blocked.
    """
    sender = await event.get_sender()
    if sender is None:
        return False

    all_joined, missing = await check_membership(client, sender.id)
    if all_joined:
        return True

    msg = get_messages()
    channel_list = "\n".join(
        f"• [{ch.get('channel_title', ch.get('title', ''))}](https://t.me/{ch.get('channel_username', ch.get('username', ''))})"
        for ch in missing
    )
    text = msg["membership"]["not_member"].format(channel_list=channel_list)
    await event.respond(
        text,
        buttons=membership_keyboard(missing),
        parse_mode="markdown",
        link_preview=False,
    )
    return False
