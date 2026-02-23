"""Quart async admin panel web application."""
import os
import sys

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quart import Quart, render_template, request, redirect, url_for, session, flash
from bot.config import WEB_SECRET_KEY, get_settings
from web.auth import check_password, login_required
from web.routes.dashboard import dashboard_bp
from web.routes.events import events_bp
from web.routes.registrations import registrations_bp
from web.routes.broadcast import broadcast_bp
from web.routes.media import media_bp
from bot.api.internal_api import api_bp

app = Quart(__name__, template_folder="templates", static_folder="static")
app.secret_key = WEB_SECRET_KEY

# Register blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(events_bp)
app.register_blueprint(registrations_bp)
app.register_blueprint(broadcast_bp)
app.register_blueprint(media_bp)
app.register_blueprint(api_bp)


@app.route("/login", methods=["GET", "POST"])
async def login():
    if request.method == "POST":
        form = await request.form
        password = form.get("password", "")
        if check_password(password):
            session["logged_in"] = True
            return redirect(url_for("dashboard.index"))
        await flash("رمز عبور اشتباه است.", "error")
    return await render_template("login.html")


@app.route("/logout")
async def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    settings = get_settings()
    web_cfg = settings.get("web", {})
    host = web_cfg.get("host", "0.0.0.0")
    port = web_cfg.get("port", 8080)
    app.run(host=host, port=port)
