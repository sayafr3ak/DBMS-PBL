"""Integrity Lab and database explorer."""
from flask import Blueprint, render_template, request

from ..auth import requires
from ..services import integrity_service as isvc

bp = Blueprint("admin", __name__)


@bp.route("/integrity", methods=["GET", "POST"])
@requires("integrity.run")
def integrity():
    results = {}
    if request.method == "GET" and request.args.get("run") == "all":   # read-only: every scenario is rolled back
        results = isvc.run_all()
    elif request.method == "POST":
        key = request.form.get("scenario")
        if key and key in isvc.SCENARIOS:
            results = {key: isvc.run_scenario(key)}
        else:
            results = isvc.run_all()
    grouped = {}
    for sc in isvc.SCENARIOS.values():
        grouped.setdefault(sc["rule"], []).append(sc)
    return render_template("admin/integrity.html", rules=isvc.RULES, grouped=grouped, results=results,
                           ran_all=len(results) > 1)


@bp.route("/explorer")
def explorer():
    return render_template("admin/explorer.html", s=isvc.schema_overview(), active=request.args.get("t"))
