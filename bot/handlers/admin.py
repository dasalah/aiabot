"""Admin commands handler."""
import logging
from telethon import events, Button

from bot import database as db
from bot import fsm
from bot.config import get_messages
from bot.middlewares.auth import is_admin, is_superadmin
from bot.utils.keyboards import admin_panel_keyboard

logger = logging.getLogger(__name__)


def register(client):

    @client.on(events.NewMessage(pattern=r"^/admin$"))
    async def admin_command(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.respond(msg["admin"]["not_authorized"])
            return
        msg = get_messages()
        text = msg["admin"]["panel_header"].format(
            admin_name=sender.first_name or "ادمین"
        )
        await event.respond(text, buttons=admin_panel_keyboard())

    @client.on(events.CallbackQuery(data=b"admin_panel"))
    async def admin_panel_callback(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.answer(msg["admin"]["not_authorized"], alert=True)
            return
        msg = get_messages()
        text = msg["admin"]["panel_header"].format(
            admin_name=sender.first_name or "ادمین"
        )
        await event.edit(text, buttons=admin_panel_keyboard())

    @client.on(events.CallbackQuery(data=b"admin_stats"))
    async def admin_stats(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.answer(msg["admin"]["not_authorized"], alert=True)
            return
        stats = db.get_stats()
        msg = get_messages()
        text = msg["admin"]["stats"].format(**stats)
        await event.edit(text, buttons=[[Button.inline(msg["menu"]["back"], b"admin_panel")]])

    @client.on(events.CallbackQuery(data=b"admin_pending"))
    async def admin_pending(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.answer(msg["admin"]["not_authorized"], alert=True)
            return
        pending = db.get_pending_registrations()
        msg = get_messages()
        if not pending:
            await event.edit(
                "هیچ ثبت‌نام در انتظاری وجود ندارد.",
                buttons=[[Button.inline(msg["menu"]["back"], b"admin_panel")]],
            )
            return
        # Show first pending
        reg = pending[0]
        from bot.utils.keyboards import admin_registration_keyboard
        text = msg["admin"]["new_registration"].format(
            full_name=reg.get("full_name", "-"),
            student_id=reg.get("student_id", "-"),
            national_code=reg.get("national_code", "-"),
            email=reg.get("email", "-"),
            phone=reg.get("phone", "-"),
            event_title=reg.get("event_title", "-"),
            registration_type=reg.get("registration_type", "-"),
            payment_status=reg.get("payment_status", "-"),
            username=reg.get("username") or "-",
            user_id=reg.get("telegram_id", "-"),
        )
        await event.edit(text, buttons=admin_registration_keyboard(reg["id"]),
                         parse_mode="markdown")

    @client.on(events.CallbackQuery(pattern=rb"^admin_approve:(\d+)$"))
    async def admin_approve(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.answer(msg["admin"]["not_authorized"], alert=True)
            return
        reg_id = int(event.pattern_match.group(1))
        reg = db.get_registration(reg_id)
        if not reg:
            msg = get_messages()
            await event.answer(msg["errors"]["not_found"], alert=True)
            return

        db.update_registration(reg_id, {
            "approval_status": "approved",
            "approved_by": sender.id,
        })

        msg = get_messages()
        await event.edit(msg["admin"]["registration_approved"])

        # Notify user
        user = _get_user_from_reg(reg_id)

        ev = db.get_event(reg["event_id"])
        if user and ev:
            user_msg = msg["approval"]["approved"].format(
                event_title=ev.get("title", ""),
                event_date=ev.get("event_date", ""),
                location=ev.get("location", ""),
                note="",
            )
            try:
                await client.send_message(user["telegram_id"], user_msg)
            except Exception as e:
                logger.warning("Failed to notify user %d: %s",
                               user.get("telegram_id"), e)

        # Schedule reminder
        try:
            from bot.utils.notifications import schedule_event_reminders
            await schedule_event_reminders(reg["event_id"])
        except Exception as e:
            logger.warning("Failed to schedule reminder: %s", e)

    @client.on(events.CallbackQuery(pattern=rb"^admin_reject:(\d+)$"))
    async def admin_reject_start(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.answer(msg["admin"]["not_authorized"], alert=True)
            return
        reg_id = int(event.pattern_match.group(1))
        msg = get_messages()
        fsm.set_state(sender.id, fsm.STATE_ADMIN_REJECT_REASON,
                      {"reg_id": reg_id})
        await event.edit(msg["admin"]["ask_reject_reason"])

    @client.on(events.NewMessage)
    async def admin_reject_reason(event):
        sender = await event.get_sender()
        if not sender:
            return
        state, data = fsm.get_state(sender.id)
        if state != fsm.STATE_ADMIN_REJECT_REASON:
            return
        reason = event.message.text or ""
        reg_id = data.get("reg_id")
        if not reg_id:
            fsm.clear_state(sender.id)
            return

        reg = db.get_registration(reg_id)
        if not reg:
            fsm.clear_state(sender.id)
            return

        db.update_registration(reg_id, {
            "approval_status": "rejected",
            "approved_by": sender.id,
            "approval_note": reason,
        })
        fsm.clear_state(sender.id)

        msg = get_messages()
        await event.respond(msg["admin"]["registration_rejected"])

        # Notify user
        user = _get_user_from_reg(reg_id)
        ev = db.get_event(reg["event_id"])
        if user and ev:
            user_msg = msg["approval"]["rejected"].format(
                event_title=ev.get("title", ""),
                reason=reason,
            )
            try:
                await client.send_message(user["telegram_id"], user_msg)
            except Exception as e:
                logger.warning("Failed to notify user: %s", e)

    @client.on(events.NewMessage(pattern=r"^/addadmin (\d+)$"))
    async def add_admin_command(event):
        sender = await event.get_sender()
        if not is_superadmin(sender.id):
            msg = get_messages()
            await event.respond(msg["admin"]["not_authorized"])
            return
        target_id = int(event.pattern_match.group(1))
        db.upsert_admin(target_id, None, str(target_id), role="admin")
        await event.respond(f"✅ کاربر {target_id} به عنوان ادمین اضافه شد.")

    @client.on(events.NewMessage(pattern=r"^/removeadmin (\d+)$"))
    async def remove_admin_command(event):
        sender = await event.get_sender()
        if not is_superadmin(sender.id):
            msg = get_messages()
            await event.respond(msg["admin"]["not_authorized"])
            return
        target_id = int(event.pattern_match.group(1))
        db.deactivate_admin(target_id)
        await event.respond(f"✅ ادمین {target_id} حذف شد.")

    @client.on(events.CallbackQuery(data=b"admin_events"))
    async def admin_events_list(event):
        sender = await event.get_sender()
        if not is_admin(sender.id):
            msg = get_messages()
            await event.answer(msg["admin"]["not_authorized"], alert=True)
            return
        all_events = db.get_all_events()
        msg = get_messages()
        if not all_events:
            await event.edit(
                "هیچ رویدادی وجود ندارد.",
                buttons=[[Button.inline(msg["menu"]["back"], b"admin_panel")]],
            )
            return
        buttons = []
        for ev in all_events[:10]:
            status_icon = {"draft": "📝", "active": "✅", "closed": "🔒",
                           "archived": "📂"}.get(ev["status"], "❓")
            label = f"{status_icon} {ev['title']}"
            buttons.append([Button.inline(label, f"admin_event:{ev['id']}".encode())])
        buttons.append([Button.inline(msg["menu"]["back"], b"admin_panel")])
        await event.edit("📅 **رویدادها:**", buttons=buttons)


def _get_user_from_reg(reg_id: int) -> dict | None:
    """Helper to get user from a registration record."""
    with db.get_cursor() as cur:
        cur.execute("""
            SELECT u.* FROM users u
            JOIN registrations r ON r.user_id=u.id
            WHERE r.id=?
        """, (reg_id,))
        row = cur.fetchone()
        return dict(row) if row else None
