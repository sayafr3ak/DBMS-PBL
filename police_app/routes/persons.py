"""Person register (complainants, accused, witnesses) - full CRUD."""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort

from ..auth import requires
from ..db import ValidationError, AppError
from ..services import person_service as ps
from . import pagination, page_arg

bp = Blueprint("persons", __name__, url_prefix="/persons")
PER_PAGE = 15


@bp.route("/")
def index():
    q, role = request.args.get("q", ""), request.args.get("role", "")
    page = page_arg(request)
    rows, total = ps.list_persons(q, role, page, PER_PAGE)
    return render_template("persons/list.html", rows=rows, q=q, role=role, pg=pagination(total, page, PER_PAGE))


@bp.route("/new", methods=["GET", "POST"])
@requires("person.manage")
def new():
    if request.method == "POST":
        try:
            pid = ps.create_person(request.form)
            flash("Person registered.", "success")
            return redirect(url_for("persons.detail", person_id=pid))
        except (ValidationError, AppError) as err:
            if not isinstance(err, ValidationError):
                flash(err.message, "error")
            return render_template("persons/form.html", person=None, form_state={
                "form": "person", "errors": getattr(err, "errors", {}), "data": request.form}), 422
    return render_template("persons/form.html", person=None, form_state=None)


@bp.route("/<int:person_id>")
def detail(person_id):
    person = ps.get_person(person_id)
    if not person:
        abort(404)
    return render_template("persons/detail.html", p=person, involvement=ps.involvement(person_id))


@bp.route("/<int:person_id>/edit", methods=["GET", "POST"])
@requires("person.manage")
def edit(person_id):
    person = ps.get_person(person_id)
    if not person:
        abort(404)
    if request.method == "POST":
        try:
            ps.update_person(person_id, request.form)
            flash("Person details updated.", "success")
            return redirect(url_for("persons.detail", person_id=person_id))
        except (ValidationError, AppError) as err:
            if not isinstance(err, ValidationError):
                flash(err.message, "error")
            return render_template("persons/form.html", person=person, form_state={
                "form": "person", "errors": getattr(err, "errors", {}), "data": request.form}), 422
    return render_template("persons/form.html", person=person, form_state=None)


@bp.route("/<int:person_id>/delete", methods=["POST"])
@requires("person.delete")
def delete(person_id):
    try:
        ps.delete_person(person_id)
        flash("Person deleted.", "success")
        return redirect(url_for("persons.index"))
    except AppError as err:
        flash(err.message, "error")
        return redirect(url_for("persons.detail", person_id=person_id))
