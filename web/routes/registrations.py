"""Registration management routes."""
from quart import Blueprint, render_template, request, redirect, url_for, flash, send_file
import io
from web.auth import login_required
from bot import database as db
from bot.utils.excel_export import generate_registration_report

registrations_bp = Blueprint("registrations", __name__, url_prefix="/registrations")


@registrations_bp.route("/")
@login_required
async def list_registrations():
    pending = db.get_pending_registrations()
    return await render_template("registrations.html", registrations=pending)


@registrations_bp.route("/event/<int:event_id>")
@login_required
async def event_registrations(event_id: int):
    event = db.get_event(event_id)
    regs = db.get_event_registrations(event_id)
    return await render_template("registrations.html", registrations=regs, event=event)


@registrations_bp.route("/<int:reg_id>/approve", methods=["POST"])
@login_required
async def approve(reg_id: int):
    db.update_registration(reg_id, {"approval_status": "approved"})
    await flash("ثبت‌نام تأیید شد.", "success")
    return redirect(url_for("registrations.list_registrations"))


@registrations_bp.route("/<int:reg_id>/reject", methods=["POST"])
@login_required
async def reject(reg_id: int):
    form = await request.form
    note = form.get("note", "")
    db.update_registration(reg_id, {"approval_status": "rejected", "approval_note": note})
    await flash("ثبت‌نام رد شد.", "success")
    return redirect(url_for("registrations.list_registrations"))


@registrations_bp.route("/event/<int:event_id>/export")
@login_required
async def export_excel(event_id: int):
    event = db.get_event(event_id)
    if not event:
        await flash("رویداد یافت نشد.", "error")
        return redirect(url_for("registrations.list_registrations"))
    regs = db.get_event_registrations(event_id)
    data = generate_registration_report(event, regs)
    return await send_file(
        io.BytesIO(data),
        as_attachment=True,
        attachment_filename=f"registrations_event_{event_id}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
