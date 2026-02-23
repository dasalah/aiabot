"""Internal REST API (Quart blueprint) for future website/mini-app integration."""
from quart import Blueprint, jsonify, request
from bot import database as db

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


@api_bp.route("/events", methods=["GET"])
async def get_events():
    """List all active events."""
    events = db.get_active_events()
    return jsonify([{
        "id": e["id"],
        "title": e["title"],
        "description": e.get("description"),
        "event_date": e.get("event_date"),
        "event_time": e.get("event_time"),
        "location": e.get("location"),
        "capacity": e.get("capacity"),
        "current_registrations": e.get("current_registrations"),
        "is_paid": bool(e.get("is_paid")),
        "price": e.get("price"),
        "status": e.get("status"),
    } for e in events])


@api_bp.route("/events/<int:event_id>", methods=["GET"])
async def get_event_detail(event_id: int):
    """Get details of a specific event."""
    event = db.get_event(event_id)
    if not event:
        return jsonify({"error": "not_found"}), 404
    return jsonify({
        "id": event["id"],
        "title": event["title"],
        "description": event.get("description"),
        "event_date": event.get("event_date"),
        "event_time": event.get("event_time"),
        "location": event.get("location"),
        "capacity": event.get("capacity"),
        "current_registrations": event.get("current_registrations"),
        "is_paid": bool(event.get("is_paid")),
        "price": event.get("price"),
        "certificate_fee": event.get("certificate_fee"),
        "is_university_only": bool(event.get("is_university_only")),
        "required_fields": event.get("required_fields", []),
        "optional_fields": event.get("optional_fields", []),
        "status": event.get("status"),
        "reg_token": event.get("reg_token"),
    })


@api_bp.route("/registration_status", methods=["GET"])
async def get_registration_status():
    """Check registration status for a user and event."""
    user_telegram_id = request.args.get("user_id", type=int)
    event_id = request.args.get("event_id", type=int)
    if not user_telegram_id or not event_id:
        return jsonify({"error": "missing_params"}), 400
    user = db.get_user(user_telegram_id)
    if not user:
        return jsonify({"status": "not_registered"})
    reg = db.get_user_registration(user["id"], event_id)
    if not reg:
        return jsonify({"status": "not_registered"})
    return jsonify({
        "status": reg.get("approval_status"),
        "payment_status": reg.get("payment_status"),
        "registration_type": reg.get("registration_type"),
        "is_waitlist": bool(reg.get("is_waitlist")),
    })
