"""Evidence register and chain of custody."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from ..auth import requires
from ..db import ValidationError, AppError, query
from ..services import evidence_service as es, officer_service as os_
from . import pagination, page_arg

bp = Blueprint("evidence", __name__, url_prefix="/evidence")
PER_PAGE = 12


@bp.route("/")
def index():
    filters = {k: request.args.get(k, "") for k in ("q", "status", "category", "holder")}
    page = page_arg(request)
    rows, total = es.list_evidence(filters, page, PER_PAGE)
    counts = {r["evidence_status"]: r["n"] for r in
              query("SELECT evidence_status, COUNT(*) AS n FROM v_evidence_location GROUP BY evidence_status")}
    return render_template("evidence/list.html", rows=rows, filters=filters, pg=pagination(total, page, PER_PAGE),
                           officers=os_.officers_for_select(active_only=False), counts=counts)


def _open_complaints():
    return query("""SELECT complaint_id, complaint_no, title FROM complaint WHERE status <> 'CLOSED'
                     ORDER BY registered_at DESC""")


@bp.route("/new", methods=["GET", "POST"])
@requires("evidence.create")
def new():
    form_state, status = None, 200
    if request.method == "POST":
        try:
            eid, number = es.register_evidence(request.form)
            flash(f"Evidence {number} registered and its chain of custody started.", "success")
            return redirect(url_for("evidence.detail", evidence_id=eid))
        except ValidationError as err:
            form_state, status = {"form": "evidence", "errors": err.errors, "data": request.form}, 422
        except AppError as err:
            flash(err.message, "error")
            form_state, status = {"form": "evidence", "errors": {}, "data": request.form}, 422
    return render_template("evidence/form.html", form_state=form_state, complaints=_open_complaints(),
                           officers=os_.officers_for_select(),
                           preselect=request.args.get("complaint", type=int)), status


@bp.route("/<int:evidence_id>")
def detail(evidence_id, form_state=None, status=200):
    try:
        ev = es.get_evidence(evidence_id)
    except AppError:
        abort(404)
    return render_template("evidence/detail.html", ev=ev, chain=es.custody_chain(evidence_id),
                           officers=os_.officers_for_select(), form_state=form_state), status


@bp.route("/<int:evidence_id>/transfer", methods=["POST"])
@requires("custody.transfer")
def transfer(evidence_id):
    try:
        es.transfer_custody(evidence_id, request.form)
        flash("Custody transferred. The chain of custody has been updated.", "success")
        return redirect(url_for("evidence.detail", evidence_id=evidence_id))
    except ValidationError as err:
        return detail(evidence_id, {"form": "transfer", "errors": err.errors, "data": request.form}, 422)
    except AppError as err:
        flash(err.message, "error")
        return detail(evidence_id, {"form": "transfer", "errors": {}, "data": request.form}, 422)


@bp.route("/<int:evidence_id>/edit", methods=["POST"])
@requires("evidence.create")
def edit(evidence_id):
    try:
        es.update_evidence(evidence_id, request.form)
        flash("Evidence details updated.", "success")
        return redirect(url_for("evidence.detail", evidence_id=evidence_id))
    except ValidationError as err:
        return detail(evidence_id, {"form": "edit", "errors": err.errors, "data": request.form}, 422)


@bp.route("/<int:evidence_id>/label")
def label(evidence_id):
    return render_template("evidence/label.html", ev=es.get_evidence(evidence_id), chain=es.custody_chain(evidence_id))
