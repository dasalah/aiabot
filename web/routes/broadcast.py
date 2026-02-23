"""Broadcast message routes."""
from quart import Blueprint, render_template, request, redirect, url_for, flash
from web.auth import login_required
from bot import database as db

broadcast_bp = Blueprint("broadcast", __name__, url_prefix="/broadcast")


@broadcast_bp.route("/", methods=["GET", "POST"])
@login_required
async def broadcast():
    if request.method == "POST":
        form = await request.form
        message_text = form.get("message_text", "")
        target = form.get("target", "all")
        if not message_text:
            await flash("متن پیام نمی‌تواند خالی باشد.", "error")
            return redirect(url_for("broadcast.broadcast"))
        # Store broadcast record (actual sending is done via bot process)
        db.create_broadcast(
            message_text=message_text,
            target=target,
            event_id=None,
            media_file_id=None,
            media_type=None,
            sent_count=0,
            failed_count=0,
            sent_by=None,
        )
        await flash("پیام برادکست در صف ارسال قرار گرفت.", "success")
        return redirect(url_for("broadcast.broadcast"))
    return await render_template("broadcast.html")
