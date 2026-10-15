"""Officer register - CRUD + workload profile."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from ..auth import requires
from ..db import ValidationError, AppError
from ..services import officer_service as os_

bp = Blueprint("officers", __name__, url_prefix="/officers")


@bp.route("/")
def index():
    q, station, active = request.args.get("q", ""), request.args.get("station", ""), request.args.get("active", "1")
    return render_template("officers/list.html", rows=os_.list_officers(q, station, active), q=q, station=station,
                           active=active, stations=os_.stations(), station_stats=os_.station_stats())


@bp.route("/new", methods=["GET", "POST"])
@requires("officer.manage")
def new():
    if request.method == "POST":
        try:
            oid = os_.create_officer(request.form)
            flash("Officer added.", "success")
            return redirect(url_for("officers.detail", officer_id=oid))
        except (ValidationError, AppError) as err:
            if not isinstance(err, ValidationError):
                flash(err.message, "error")
            return render_template("officers/form.html", officer=None, stations=os_.stations(), form_state={
                "form": "officer", "errors": getattr(err, "errors", {}), "data": request.form}), 422
    return render_template("officers/form.html", officer=None, stations=os_.stations(), form_state=None)


@bp.route("/<int:officer_id>")
def detail(officer_id):
    return render_template("officers/detail.html", o=os_.get_officer(officer_id), cases=os_.officer_cases(officer_id),
                           evidence=os_.officer_evidence(officer_id), activities=os_.officer_activities(officer_id))


@bp.route("/<int:officer_id>/edit", methods=["GET", "POST"])
@requires("officer.manage")
def edit(officer_id):
    officer = os_.get_officer(officer_id)
    if request.method == "POST":
        try:
            os_.update_officer(officer_id, request.form)
            flash("Officer details updated.", "success")
            return redirect(url_for("officers.detail", officer_id=officer_id))
        except (ValidationError, AppError) as err:
            if not isinstance(err, ValidationError):
                flash(err.message, "error")
            return render_template("officers/form.html", officer=officer, stations=os_.stations(), form_state={
                "form": "officer", "errors": getattr(err, "errors", {}), "data": request.form}), 422
    return render_template("officers/form.html", officer=officer, stations=os_.stations(), form_state=None)


@bp.route("/<int:officer_id>/toggle", methods=["POST"])
@requires("officer.manage")
def toggle(officer_id):
    officer = os_.get_officer(officer_id)
    os_.set_active(officer_id, not officer["is_active"])
    flash(f"{officer['full_name']} has been {'deactivated' if officer['is_active'] else 'reactivated'}.", "success")
    return redirect(url_for("officers.detail", officer_id=officer_id))


@bp.route("/<int:officer_id>/delete", methods=["POST"])
@requires("officer.manage")
def delete(officer_id):
    try:
        os_.delete_officer(officer_id)
        flash("Officer record deleted.", "success")
        return redirect(url_for("officers.index"))
    except AppError as err:
        flash(err.message + " Deactivate the officer instead.", "error")
        return redirect(url_for("officers.detail", officer_id=officer_id))
