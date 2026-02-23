"""Scheduled notification sender background task."""
import asyncio
import logging
from datetime import datetime, timedelta

from bot import database as db
from bot.config import get_settings, get_messages

logger = logging.getLogger(__name__)


async def schedule_event_reminders(event_id: int) -> None:
    """Schedule reminder notifications for all approved registrations of an event."""
    settings = get_settings()
    hours_before = settings.get("notifications", {}).get("reminder_hours_before", 24)
    event = db.get_event(event_id)
    if not event or not event.get("event_date"):
        return

    try:
        event_dt_str = f"{event['event_date']} {event.get('event_time', '08:00')}"
        event_dt = datetime.strptime(event_dt_str, "%Y-%m-%d %H:%M")
        scheduled_at = event_dt - timedelta(hours=hours_before)
    except ValueError:
        logger.warning("Invalid event date format for event %d", event_id)
        return

    registrations = db.get_event_registrations(event_id)
    msg_template = get_messages()["notifications"]["event_reminder"]

    for reg in registrations:
        if reg.get("approval_status") != "approved":
            continue
        message = msg_template.format(
            event_title=event["title"],
            hours=hours_before,
            event_date=event.get("event_date", ""),
            event_time=event.get("event_time", ""),
            location=event.get("location", ""),
        )
        db.create_notification(
            user_id=reg["user_id"],
            event_id=event_id,
            message=message,
            notification_type="reminder",
            scheduled_at=scheduled_at.strftime("%Y-%m-%d %H:%M:%S"),
        )


async def notification_worker(client) -> None:
    """Background task: check for due notifications and send them."""
    settings = get_settings()
    interval = settings.get("notifications", {}).get("check_interval_seconds", 3600)
    logger.info("Notification worker started, interval=%ds", interval)

    while True:
        try:
            pending = db.get_pending_notifications()
            for notif in pending:
                try:
                    await client.send_message(notif["telegram_id"], notif["message"])
                    db.mark_notification_sent(notif["id"])
                except Exception as e:
                    logger.warning("Failed to send notification %d: %s", notif["id"], e)
        except Exception as e:
            logger.error("Notification worker error: %s", e)
        await asyncio.sleep(interval)
