"""Event CRUD routes."""
import json
from quart import Blueprint, render_template, request, redirect, url_for, flash
from web.auth import login_required
from bot import database as db
from bot.config import BOT_USERNAME

events_bp = Blueprint("events", __name__, url_prefix="/events")


@events_bp.route("/")
@login_required
async def list_events():
    all_events = db.get_all_events()
    return await render_template("events.html", events=all_events)


@events_bp.route("/new", methods=["GET", "POST"])
@login_required
async def new_event():
    if request.method == "POST":
        form = await request.form
        required_fields = form.getlist("required_fields")
        optional_fields = form.getlist("optional_fields")
        slug = form.get("slug", "").strip() or None
        data = {
            "title": form.get("title", ""),
            "description": form.get("description", ""),
            "event_date": form.get("event_date", ""),
            "event_time": form.get("event_time", ""),
            "location": form.get("location", ""),
            "capacity": int(form.get("capacity", 0)),
            "price": int(form.get("price", 0)),
            "certificate_fee": int(form.get("certificate_fee", 0)),
            "is_paid": bool(form.get("is_paid")),
            "is_university_only": bool(form.get("is_university_only")),
            "waitlist_enabled": bool(form.get("waitlist_enabled")),
            "max_waitlist": int(form.get("max_waitlist", 0)),
            "required_fields": required_fields,
            "optional_fields": optional_fields,
            "status": form.get("status", "draft"),
            "registration_open": bool(form.get("registration_open")),
            "slug": slug,
        }
        event_id = db.create_event(data)
        await flash("رویداد با موفقیت ایجاد شد.", "success")
        if slug and BOT_USERNAME:
            deep_link = f"https://t.me/{BOT_USERNAME}?start=event_{slug}"
            await flash(f"لینک دیپ‌لینک رویداد: {deep_link}", "info")
        return redirect(url_for("events.list_events"))
    return await render_template("event_form.html", event=None)


@events_bp.route("/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
async def edit_event(event_id: int):
    event = db.get_event(event_id)
    if not event:
        await flash("رویداد یافت نشد.", "error")
        return redirect(url_for("events.list_events"))
    if request.method == "POST":
        form = await request.form
        required_fields = form.getlist("required_fields")
        optional_fields = form.getlist("optional_fields")
        slug = form.get("slug", "").strip() or None
        data = {
            "title": form.get("title", ""),
            "description": form.get("description", ""),
            "event_date": form.get("event_date", ""),
            "event_time": form.get("event_time", ""),
            "location": form.get("location", ""),
            "capacity": int(form.get("capacity", 0)),
            "price": int(form.get("price", 0)),
            "certificate_fee": int(form.get("certificate_fee", 0)),
            "is_paid": 1 if form.get("is_paid") else 0,
            "is_university_only": 1 if form.get("is_university_only") else 0,
            "waitlist_enabled": 1 if form.get("waitlist_enabled") else 0,
            "max_waitlist": int(form.get("max_waitlist", 0)),
            "required_fields": required_fields,
            "optional_fields": optional_fields,
            "status": form.get("status", "draft"),
            "registration_open": 1 if form.get("registration_open") else 0,
            "slug": slug,
        }
        db.update_event(event_id, data)
        await flash("رویداد با موفقیت ویرایش شد.", "success")
        return redirect(url_for("events.list_events"))
    return await render_template("event_form.html", event=event)


@events_bp.route("/<int:event_id>/delete", methods=["POST"])
@login_required
async def delete_event(event_id: int):
    db.delete_event(event_id)
    await flash("رویداد حذف شد.", "success")
    return redirect(url_for("events.list_events"))
