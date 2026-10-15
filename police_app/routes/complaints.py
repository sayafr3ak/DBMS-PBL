"""Complaint registration, case file and all case-level actions."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, abort

from ..auth import requires, can
from ..db import ValidationError, AppError, query
from ..services import complaint_service as cs, officer_service as os_, evidence_service
from . import pagination, page_arg

bp = Blueprint("complaints", __name__, url_prefix="/complaints")

PER_PAGE = 12


def _officer_id():
    return g.user["officer_id"] if g.user else None


@bp.route("/")
def index():
    filters = {k: request.args.get(k, "") for k in
               ("q", "status", "category", "priority", "station", "officer", "date_from", "date_to", "sort",
                "open", "unassigned")}
    page = page_arg(request)
    rows, total = cs.list_complaints(filters, page, PER_PAGE)
    return render_template("complaints/list.html", rows=rows, filters=filters,
                           pg=pagination(total, page, PER_PAGE), stations=os_.stations(),
                           officers=os_.officers_for_select())


def _form_page(template, form_state=None, complaint=None, status=200):
    return render_template(template, form_state=form_state, complaint=complaint, stations=os_.stations(),
                           officers=os_.officers_for_select()), status


@bp.route("/new", methods=["GET", "POST"])
@requires("complaint.create")
def new():
    if request.method == "POST":
        try:
            cid, number = cs.register_complaint(request.form, _officer_id())
            flash(f"Complaint {number} registered successfully.", "success")
            return redirect(url_for("complaints.detail", complaint_id=cid))
        except ValidationError as err:
            return _form_page("complaints/form.html", {"form": "complaint", "errors": err.errors,
                                                       "data": request.form}, status=422)
        except AppError as err:
            flash(err.message, "error")
            return _form_page("complaints/form.html", {"form": "complaint", "errors": {}, "data": request.form},
                              status=422)
    return _form_page("complaints/form.html")


@bp.route("/<int:complaint_id>/edit", methods=["GET", "POST"])
@requires("complaint.edit")
def edit(complaint_id):
    complaint = cs.get_complaint(complaint_id)
    if complaint["status"] == "CLOSED":
        flash("A closed case cannot be edited. Re-open it first.", "error")
        return redirect(url_for("complaints.detail", complaint_id=complaint_id))
    if request.method == "POST":
        try:
            cs.update_complaint(complaint_id, request.form)
            flash("Complaint details updated.", "success")
            return redirect(url_for("complaints.detail", complaint_id=complaint_id))
        except ValidationError as err:
            return _form_page("complaints/form.html", {"form": "complaint", "errors": err.errors,
                                                       "data": request.form}, complaint, status=422)
    return _form_page("complaints/form.html", complaint=complaint)


@bp.route("/<int:complaint_id>")
def detail(complaint_id, form_state=None, tab=None, status=200):
    try:
        complaint = cs.get_complaint(complaint_id)
    except AppError:
        abort(404)
    ctx = dict(
        c=complaint,
        assignments=cs.assignments(complaint_id),
        activities=cs.activities(complaint_id),
        witnesses=cs.witnesses(complaint_id),
        accused=cs.accused(complaint_id),
        charges=cs.charges(complaint_id),
        courts=cs.court_refs(complaint_id),
        history=cs.status_history(complaint_id),
        timeline=cs.timeline(complaint_id),
        evidence=cs.evidence(complaint_id),
        transitions=cs.allowed_transitions(complaint["status"]),
        officers=os_.officers_for_select(),
        form_state=form_state,
        tab=tab or request.args.get("tab", "overview"),
    )
    ctx["active_officers"] = [a for a in ctx["assignments"] if not a["relieved_at"]]
    return render_template("complaints/detail.html", **ctx), status


@bp.route("/<int:complaint_id>/print")
def print_case(complaint_id):
    complaint = cs.get_complaint(complaint_id)
    return render_template("complaints/print.html", c=complaint, assignments=cs.assignments(complaint_id),
                           activities=cs.activities(complaint_id), witnesses=cs.witnesses(complaint_id),
                           accused=cs.accused(complaint_id), charges=cs.charges(complaint_id),
                           courts=cs.court_refs(complaint_id), timeline=cs.timeline(complaint_id),
                           evidence=cs.evidence(complaint_id))


def _case_action(complaint_id, form_name, tab, fn, success_msg):
    """Run a case-level action; on validation error re-render the case page with the modal open."""
    try:
        fn()
        flash(success_msg, "success")
        return redirect(url_for("complaints.detail", complaint_id=complaint_id, tab=tab))
    except ValidationError as err:
        return detail(complaint_id, {"form": form_name, "errors": err.errors, "data": request.form}, tab, 422)
    except AppError as err:
        flash(err.message, "error")
        return detail(complaint_id, {"form": form_name, "errors": {}, "data": request.form}, tab, 422)


@bp.route("/<int:complaint_id>/status", methods=["POST"])
@requires("complaint.status")
def change_status(complaint_id):
    if request.form.get("new_status") == "CLOSED" and not can("complaint.close"):
        abort(403)
    return _case_action(complaint_id, "status", "overview",
                        lambda: cs.update_status(complaint_id, request.form, _officer_id()),
                        "Case status updated and recorded in the audit trail.")


@bp.route("/<int:complaint_id>/assign", methods=["POST"])
@requires("complaint.assign")
def assign(complaint_id):
    return _case_action(complaint_id, "assign", "officers",
                        lambda: cs.assign_officer(complaint_id, request.form, _officer_id()),
                        "Officer assigned to the case.")


@bp.route("/<int:complaint_id>/assignments/<int:assignment_id>/relieve", methods=["POST"])
@requires("complaint.assign")
def relieve(complaint_id, assignment_id):
    cs.relieve_assignment(complaint_id, assignment_id)
    flash("Officer relieved from the case.", "success")
    return redirect(url_for("complaints.detail", complaint_id=complaint_id, tab="officers"))


@bp.route("/<int:complaint_id>/activities", methods=["POST"])
@requires("activity.log")
def add_activity(complaint_id):
    return _case_action(complaint_id, "activity", "activities",
                        lambda: cs.log_activity(complaint_id, request.form), "Investigation activity logged.")


@bp.route("/<int:complaint_id>/witnesses", methods=["POST"])
@requires("witness.manage")
def add_witness(complaint_id):
    return _case_action(complaint_id, "witness", "people",
                        lambda: cs.add_witness(complaint_id, request.form), "Witness statement recorded.")


@bp.route("/<int:complaint_id>/witnesses/<int:witness_id>/delete", methods=["POST"])
@requires("witness.manage")
def delete_witness(complaint_id, witness_id):
    cs.remove_witness(complaint_id, witness_id)
    flash("Witness removed from the case.", "success")
    return redirect(url_for("complaints.detail", complaint_id=complaint_id, tab="people"))


@bp.route("/<int:complaint_id>/accused", methods=["POST"])
@requires("accused.manage")
def add_accused(complaint_id):
    return _case_action(complaint_id, "accused", "people",
                        lambda: cs.add_accused(complaint_id, request.form), "Accused added to the case.")


@bp.route("/<int:complaint_id>/accused/<int:person_id>/status", methods=["POST"])
@requires("accused.manage")
def accused_status(complaint_id, person_id):
    cs.update_accused_status(complaint_id, person_id, request.form)
    flash("Accused status updated.", "success")
    return redirect(url_for("complaints.detail", complaint_id=complaint_id, tab="people"))


@bp.route("/<int:complaint_id>/accused/<int:person_id>/delete", methods=["POST"])
@requires("accused.manage")
def delete_accused(complaint_id, person_id):
    cs.remove_accused(complaint_id, person_id)
    flash("Accused removed from the case.", "success")
    return redirect(url_for("complaints.detail", complaint_id=complaint_id, tab="people"))


@bp.route("/<int:complaint_id>/charges", methods=["POST"])
@requires("charge.manage")
def add_charge(complaint_id):
    return _case_action(complaint_id, "charge", "legal",
                        lambda: cs.add_charge(complaint_id, request.form, _officer_id()), "Charge framed.")


@bp.route("/<int:complaint_id>/charges/<int:charge_id>/delete", methods=["POST"])
@requires("charge.manage")
def delete_charge(complaint_id, charge_id):
    cs.delete_charge(complaint_id, charge_id)
    flash("Charge withdrawn.", "success")
    return redirect(url_for("complaints.detail", complaint_id=complaint_id, tab="legal"))


@bp.route("/<int:complaint_id>/court", methods=["POST"])
@requires("court.manage")
def add_court(complaint_id):
    return _case_action(complaint_id, "court", "legal",
                        lambda: cs.add_court_ref(complaint_id, request.form), "Court reference added.")


@bp.route("/<int:complaint_id>/court/<int:court_ref_id>", methods=["POST"])
@requires("court.manage")
def update_court(complaint_id, court_ref_id):
    return _case_action(complaint_id, f"court-{court_ref_id}", "legal",
                        lambda: cs.update_court_ref(complaint_id, court_ref_id, request.form),
                        "Court reference updated.")
