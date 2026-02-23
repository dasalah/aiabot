"""Web authentication helpers."""
import os
from functools import wraps
from quart import session, redirect, url_for
from bot.config import WEB_ADMIN_PASSWORD


def check_password(password: str) -> bool:
    return password == WEB_ADMIN_PASSWORD


def login_required(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return await f(*args, **kwargs)
    return decorated
