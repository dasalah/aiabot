"""Dashboard and statistics route."""
from quart import Blueprint, render_template
from web.auth import login_required
from bot import database as db

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
async def index():
    stats = db.get_stats()
    recent_regs = db.get_pending_registrations()[:5]
    return await render_template("dashboard.html", stats=stats,
                                  recent_regs=recent_regs)
