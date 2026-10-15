"""Flask application factory."""
import logging
import os
from datetime import datetime, date, timedelta

from flask import Flask, g, request, redirect, url_for, flash, render_template, session

from . import constants as C
from .auth import bp as auth_bp, load_user, switch_to, can, csrf_token, check_csrf
from .config import load_app_config, ROOT
from .db import init_pool, close_conn, refresh_session_vars, AppError

def create_app(database=None, testing=False):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    cfg = load_app_config()
    app.config.update(SECRET_KEY=cfg["secret_key"], TESTING=testing,
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
    _setup_logging(app)
    init_pool(database)

    app.teardown_appcontext(close_conn)

    @app.before_request
    def _before():
        if request.endpoint == "static":
            return None
        if request.args.get("as"):          # ?as=<username> switches the acting user (used for screenshots/demo)
            switch_to(request.args["as"])
        load_user()
        refresh_session_vars()
        if not app.config.get("WTF_CSRF_DISABLED"):
            check_csrf()

    @app.context_processor
    def _inject():
        return {"C": C, "can": can, "csrf_token": csrf_token, "now": datetime.now(), "today": date.today(),
                "officer_opts": _officer_opts, "opts": lambda mapping: list(mapping.items()),
                "seq_opts": lambda seq: [(v, v) for v in seq],
                "station_opts": lambda stations: [(s["station_id"], s["station_name"]) for s in stations],
                "all_users": _all_users}

    _register_filters(app)
    _register_errors(app)

    from .routes import main, complaints, evidence, persons, officers, reports, admin
    for bp in (auth_bp, main.bp, complaints.bp, evidence.bp, persons.bp, officers.bp, reports.bp, admin.bp):
        app.register_blueprint(bp)
    return app


def _all_users():
    from .db import query
    return query("""SELECT u.username, u.user_role, o.full_name FROM app_user u
                     LEFT JOIN officer o ON o.officer_id = u.officer_id WHERE u.is_active = 1
                     ORDER BY FIELD(u.user_role, 'ADMIN', 'SHO', 'IO', 'CUSTODIAN'), u.username""")


def _officer_opts(officers):
    return [(o["officer_id"], f"{o['full_name']} · {o['officer_rank']} · {o['station_code']}") for o in officers]


def _setup_logging(app):
    log_dir = os.path.join(ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    handler = logging.FileHandler(os.path.join(log_dir, "app.log"), encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _register_filters(app):
    @app.template_filter("dt")
    def fmt_dt(value, fmt="%d %b %Y, %H:%M"):
        if not value:
            return "—"
        return value.strftime(fmt) if hasattr(value, "strftime") else str(value)

    @app.template_filter("d")
    def fmt_d(value, fmt="%d %b %Y"):
        if not value:
            return "—"
        return value.strftime(fmt) if hasattr(value, "strftime") else str(value)

    @app.template_filter("dtlocal")
    def fmt_dtlocal(value):
        if not value:
            return ""
        return value.strftime("%Y-%m-%dT%H:%M") if hasattr(value, "strftime") else str(value)

    @app.template_filter("label")
    def fmt_label(value):
        if value is None:
            return "—"
        for mapping in (C.STATUSES, C.CATEGORIES, C.CLOSURE_TYPES, C.ACTIVITY_TYPES, C.EVIDENCE_CATEGORIES,
                        C.CUSTODY_PURPOSES, C.EVIDENCE_STATUSES, C.ACCUSED_STATUSES, C.ASSIGNMENT_ROLES,
                        C.COURT_TYPES, C.CASE_STAGES, C.VERDICTS, C.USER_ROLES, C.PRIORITIES, C.CONDITIONS):
            if value in mapping:
                return mapping[value]
        return str(value).replace("_", " ").title()

    @app.template_filter("initials")
    def fmt_initials(name):
        parts = [p for p in (name or "?").split() if p[0].isalpha()]
        return "".join(p[0] for p in parts[:2]).upper() or "?"

    @app.template_filter("ago")
    def fmt_ago(value):
        if not value:
            return "—"
        if isinstance(value, datetime):
            delta = datetime.now() - value
        else:
            delta = datetime.now() - datetime.combine(value, datetime.min.time())
        secs = int(delta.total_seconds())
        if secs < 0:
            days = -secs // 86400
            return "today" if days == 0 else f"in {days} day{'s' if days != 1 else ''}"
        if secs < 3600:
            return f"{max(secs // 60, 1)} min ago"
        if secs < 86400:
            return f"{secs // 3600} h ago"
        days = secs // 86400
        if days < 31:
            return f"{days} day{'s' if days != 1 else ''} ago"
        if days < 365:
            return f"{days // 30} mo ago"
        return f"{days // 365} y ago"

    @app.template_filter("inr")
    def fmt_num(value):
        try:
            return f"{int(value):,}"
        except (TypeError, ValueError):
            return value or 0


def _register_errors(app):
    @app.errorhandler(AppError)
    def _app_error(err):
        flash(err.message, "error")
        return redirect(request.referrer or url_for("main.dashboard"))

    @app.errorhandler(400)
    def _bad(err):
        return render_template("error.html", code=400, title="Bad request",
                               message=getattr(err, "description", "The request could not be processed.")), 400

    @app.errorhandler(403)
    def _forbidden(err):
        return render_template("error.html", code=403, title="Access denied",
                               message="Your role does not have permission to perform this action."), 403

    @app.errorhandler(404)
    def _not_found(err):
        return render_template("error.html", code=404, title="Page not found",
                               message="The page or record you are looking for does not exist."), 404

    @app.errorhandler(500)
    def _server_error(err):
        app.logger.exception("Unhandled error: %s", err)
        return render_template("error.html", code=500, title="Something went wrong",
                               message="An unexpected error occurred. It has been logged."), 500

    @app.errorhandler(Exception)
    def _unhandled(err):
        from werkzeug.exceptions import HTTPException
        if isinstance(err, HTTPException):
            return err
        import mysql.connector
        app.logger.exception("Unhandled exception")
        if isinstance(err, mysql.connector.Error) and getattr(err, "errno", None) in (2003, 2005, 2013, 1045, 1049, 2055):
            return render_template("error.html", code=503, title="Database unavailable",
                                   message="Cannot connect to MySQL. Make sure the MySQL service is running and "
                                           "the credentials in config.ini are correct, then run setup_db.py."), 503
        return render_template("error.html", code=500, title="Something went wrong",
                               message=str(err) if app.debug else "An unexpected error occurred. It has been logged."), 500
