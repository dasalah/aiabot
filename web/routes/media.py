"""Media upload management routes."""
import os
from quart import Blueprint, render_template, request, redirect, url_for, flash
from web.auth import login_required
from bot import database as db
from bot.config import get_settings, DATA_DIR

media_bp = Blueprint("media", __name__, url_prefix="/media")


@media_bp.route("/event/<int:event_id>")
@login_required
async def event_media(event_id: int):
    event = db.get_event(event_id)
    media_items = db.get_event_media(event_id)
    return await render_template("media.html", event=event, media_items=media_items)


@media_bp.route("/event/<int:event_id>/upload", methods=["POST"])
@login_required
async def upload_media(event_id: int):
    settings = get_settings()
    upload_path = settings.get("media", {}).get("upload_path", "data/media")
    if not os.path.isabs(upload_path):
        upload_path = os.path.join(DATA_DIR, os.path.basename(upload_path))
    os.makedirs(upload_path, exist_ok=True)

    files = await request.files
    form = await request.form
    caption = form.get("caption", "")

    uploaded_file = files.get("media_file")
    if not uploaded_file:
        await flash("فایلی انتخاب نشده.", "error")
        return redirect(url_for("media.event_media", event_id=event_id))

    filename = f"{event_id}_{uploaded_file.filename}"
    file_path = os.path.join(upload_path, filename)
    await uploaded_file.save(file_path)

    media_type = "photo"
    if uploaded_file.content_type:
        if "video" in uploaded_file.content_type:
            media_type = "video"
        elif "pdf" in uploaded_file.content_type:
            media_type = "document"

    existing = db.get_event_media(event_id)
    order = len(existing)
    db.add_event_media(event_id, media_type, None, file_path, caption, order, None)
    await flash("رسانه آپلود شد.", "success")
    return redirect(url_for("media.event_media", event_id=event_id))


@media_bp.route("/delete/<int:media_id>", methods=["POST"])
@login_required
async def delete_media(media_id: int):
    db.delete_media(media_id)
    await flash("رسانه حذف شد.", "success")
    form = await request.form
    event_id = form.get("event_id", 1)
    return redirect(url_for("media.event_media", event_id=event_id))
