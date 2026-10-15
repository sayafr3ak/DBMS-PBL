"""Dashboard, global search and small JSON endpoints used by pickers."""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for

from ..db import query
from ..services import dashboard_service as dash, person_service

bp = Blueprint("main", __name__)


@bp.route("/")
def dashboard():
    return render_template("dashboard.html",
                           k=dash.kpis(), statuses=dash.status_breakdown(), monthly=dash.monthly(),
                           categories=dash.category_breakdown(), officers=dash.top_officers(),
                           events=dash.recent_events(), attention=dash.attention())


@bp.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return redirect(url_for("main.dashboard"))
    upper = q.upper()
    # exact ID hit -> jump straight to the record
    if upper.startswith("CMP-"):
        row = query("SELECT complaint_id FROM complaint WHERE complaint_no = %s", (upper,))
        if row:
            return redirect(url_for("complaints.detail", complaint_id=row[0]["complaint_id"]))
    if upper.startswith("EVD-"):
        row = query("SELECT evidence_id FROM evidence_item WHERE evidence_no = %s", (upper,))
        if row:
            return redirect(url_for("evidence.detail", evidence_id=row[0]["evidence_id"]))
    like = f"%{q}%"
    complaints = query("""SELECT complaint_id, complaint_no, title, status, priority, complainant_name, registered_at
                            FROM v_case_summary
                           WHERE complaint_no LIKE %s OR title LIKE %s OR complainant_name LIKE %s
                              OR incident_location LIKE %s
                           ORDER BY registered_at DESC LIMIT 20""", (like, like, like, like))
    evidence = query("""SELECT evidence_id, evidence_no, description, evidence_status, current_holder, complaint_no
                          FROM v_evidence_location
                         WHERE evidence_no LIKE %s OR description LIKE %s OR seal_no LIKE %s
                         ORDER BY evidence_no DESC LIMIT 20""", (like, like, like))
    persons = query("""SELECT person_id, full_name, phone, address FROM person
                        WHERE full_name LIKE %s OR phone LIKE %s OR id_proof_no LIKE %s
                        ORDER BY full_name LIMIT 20""", (like, like, like))
    officers = query("""SELECT o.officer_id, o.full_name, o.badge_no, o.officer_rank, s.station_code FROM officer o
                          JOIN station s ON s.station_id = o.station_id
                         WHERE o.full_name LIKE %s OR o.badge_no LIKE %s ORDER BY o.full_name LIMIT 20""", (like, like))
    return render_template("search.html", q=q, complaints=complaints, evidence=evidence, persons=persons,
                           officers=officers)


@bp.route("/api/persons")
def api_persons():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    return jsonify([{"id": p["person_id"], "name": p["full_name"], "phone": p["phone"],
                     "address": p["address"], "proof": (p["id_proof_type"] or "") + " " + (p["id_proof_no"] or "")}
                    for p in person_service.search_persons(q)])


@bp.route("/api/complaints")
def api_complaints():
    q = (request.args.get("q") or "").strip()
    like = f"%{q}%"
    rows = query("""SELECT complaint_id, complaint_no, title, status FROM complaint
                     WHERE (complaint_no LIKE %s OR title LIKE %s) ORDER BY registered_at DESC LIMIT 10""", (like, like))
    return jsonify([{"id": r["complaint_id"], "no": r["complaint_no"], "title": r["title"], "status": r["status"]}
                    for r in rows])
