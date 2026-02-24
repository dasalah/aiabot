"""Bot entry point: initializes DB, registers handlers, starts Telethon client."""
import asyncio
import logging
import logging.handlers
import os
import sys

from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.config import (
    API_ID, API_HASH, BOT_TOKEN, SUPERADMIN_IDS,
    get_settings, DATA_DIR,
)
from bot import database as db
from bot.handlers import start, events as events_handler, registration
from bot.handlers import archive, admin, membership
from bot.utils.notifications import notification_worker, broadcast_worker


def setup_logging():
    settings = get_settings()
    log_cfg = settings.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    log_file = log_cfg.get("file", "logs/bot.log")
    if not os.path.isabs(log_file):
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            log_file
        )
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(level)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=log_cfg.get("max_bytes", 10 * 1024 * 1024),
        backupCount=log_cfg.get("backup_count", 5),
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)


async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting AIA Bot...")

    # Initialize database
    db.init_db()

    # Ensure superadmins exist
    for sa_id in SUPERADMIN_IDS:
        db.upsert_admin(sa_id, None, f"Superadmin {sa_id}", role="superadmin")

    # Create required directories
    os.makedirs(os.path.join(DATA_DIR, "media"), exist_ok=True)

    settings = get_settings()
    session_name = settings.get("bot", {}).get("session_name", "aiabot")
    session_path = os.path.join(DATA_DIR, session_name)

    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    # Register all handlers
    start.register(client)
    events_handler.register(client)
    registration.register(client)
    archive.register(client)
    admin.register(client)
    membership.register(client)

    logger.info("All handlers registered.")

    # Start background tasks
    asyncio.create_task(notification_worker(client))
    asyncio.create_task(broadcast_worker(client))

    me = await client.get_me()
    logger.info("Bot started as @%s", me.username)

    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
