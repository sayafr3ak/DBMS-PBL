"""Reports hub, report viewer and CSV export."""
from datetime import datetime

from flask import Blueprint, render_template, request, Response, abort

from ..db import query
from ..services import report_service as rs, officer_service as os_

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
def index():
    groups = {}
    for rep in rs.REPORTS.values():
        groups.setdefault(rep["group"], []).append(rep)
    return render_template("reports/index.html", groups=groups)


def _pickers():
    return {
        "stations": os_.stations(),
        "complaints": query("SELECT complaint_id, complaint_no, title FROM complaint ORDER BY registered_at DESC"),
        "evidence_items": query("SELECT evidence_id, evidence_no, description FROM evidence_item ORDER BY evidence_no"),
    }


@bp.route("/<key>")
def view(key):
    if key not in rs.REPORTS:
        abort(404)
    rep, cols, rows = rs.run(key, request.args)
    chart = None
    if rep["chart"] and rows:
        label_col, value_col = rep["chart"]
        if value_col:
            chart = [(r[label_col], r[value_col] or 0) for r in rows][:12]
        else:  # count rows per label
            counts = {}
            for r in rows:
                counts[r[label_col]] = counts.get(r[label_col], 0) + 1
            chart = sorted(counts.items(), key=lambda kv: -kv[1])
    return render_template("reports/view.html", rep=rep, cols=cols, rows=rows, args=request.args, chart=chart,
                           generated=datetime.now(), **_pickers())


@bp.route("/<key>.csv")
def export(key):
    if key not in rs.REPORTS:
        abort(404)
    rep, cols, rows = rs.run(key, request.args)
    filename = f"{key}-{datetime.now():%Y%m%d-%H%M}.csv"
    return Response(rs.to_csv(cols, rows), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})
