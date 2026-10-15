"""Acting user, role-based access control and CSRF protection.

There is no login page: the app opens directly as the default user
(config.ini -> [app] default_user, 'admin' if not set). The "Acting as"
switcher in the sidebar changes the active user/role, so role-based
permissions and the audit trail (which officer did what) still work.
"""
import secrets
from functools import wraps

from flask import Blueprint, request, redirect, url_for, session, flash, g, abort

from .db import query_one
from .constants import PERMISSIONS
from .config import load_app_config

bp = Blueprint("auth", __name__)

USER_SQL = """SELECT u.user_id, u.username, u.user_role, u.officer_id, u.is_active,
                     o.full_name, o.badge_no, o.officer_rank, o.station_id, s.station_name, s.station_code
                FROM app_user u
                LEFT JOIN officer o ON o.officer_id = u.officer_id
                LEFT JOIN station s ON s.station_id = o.station_id
               WHERE {cond} AND u.is_active = 1"""


def load_user():
    """Set g.user from the session, falling back to the configured default user."""
    g.user = None
    uid = session.get("user_id")
    if uid:
        g.user = query_one(USER_SQL.format(cond="u.user_id = %s"), (uid,))
    if not g.user:
        g.user = query_one(USER_SQL.format(cond="u.username = %s"), (load_app_config()["default_user"],))
        if g.user:
            session["user_id"] = g.user["user_id"]


def switch_to(username):
    user = query_one(USER_SQL.format(cond="u.username = %s"), (username,))
    if user:
        session["user_id"] = user["user_id"]
    return user


def can(permission):
    user = g.get("user")
    return bool(user) and user["user_role"] in PERMISSIONS.get(permission, set())


def requires(permission):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not can(permission):
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return deco


# ---------------- CSRF ----------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def check_csrf():
    if request.method == "POST":
        token = request.form.get("_csrf") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("_csrf"):
            abort(400, description="Your session expired or the form is invalid. Please reload the page and try again.")


# ---------------- routes ----------------
@bp.route("/switch-user", methods=["POST"])
def switch_user():
    user = switch_to((request.form.get("username") or "").strip().lower())
    if user:
        flash(f"Now acting as {user['full_name'] or user['username']} ({user['user_role']}).", "info")
    else:
        flash("Unknown or inactive user.", "error")
    nxt = request.form.get("next") or ""
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = url_for("main.dashboard")
    return redirect(nxt)
