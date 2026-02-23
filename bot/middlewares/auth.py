"""Admin authentication middleware."""
from bot import database as db
from bot.config import SUPERADMIN_IDS


def is_admin(telegram_id: int) -> bool:
    """Check if the user is an active admin (including superadmin)."""
    if telegram_id in SUPERADMIN_IDS:
        return True
    return db.get_admin(telegram_id) is not None


def is_superadmin(telegram_id: int) -> bool:
    """Check if the user is a superadmin."""
    return telegram_id in SUPERADMIN_IDS


def require_admin(func):
    """Decorator that checks admin status before executing the handler."""
    from functools import wraps
    from bot.config import get_messages

    @wraps(func)
    async def wrapper(event, *args, **kwargs):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.respond(msg["admin"]["not_authorized"])
            return
        return await func(event, *args, **kwargs)
    return wrapper
