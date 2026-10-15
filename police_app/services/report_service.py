"""Report catalogue. Each report is a parameterised SQL query (mostly over views)."""
import csv
import io
from collections import OrderedDict

from ..db import query, AppError

# column formats understood by templates/reports/view.html:
#   text, num, date, datetime, status, priority, evstatus, complaint (link), evidence (link), bool, days, purpose
REPORTS = OrderedDict()


def report(key, title, group, description, icon, params=(), chart=None):
    def deco(fn):
        REPORTS[key] = {"key": key, "title": title, "group": group, "description": description, "icon": icon,
                        "params": params, "chart": chart, "fn": fn}
        return fn
    return deco


def _int(args, name):
    try:
        return int(args.get(name)) if args.get(name) not in (None, "") else None
    except ValueError:
        raise AppError(f"Invalid value for {name}.")


# ----------------------------------------------------------------------
@report("pending-cases", "Pending Cases", "Case reports",
        "Every case that is not closed, oldest first, with lead officer and last activity.",
        "hourglass", params=("station", "priority", "min_days"))
def _pending(args):
    where, p = ["1=1"], []
    if args.get("station"):
        where.append("station_name = (SELECT station_name FROM station WHERE station_id = %s)")
        p.append(_int(args, "station"))
    if args.get("priority"):
        where.append("priority = %s")
        p.append(args["priority"])
    if args.get("min_days"):
        where.append("days_pending >= %s")
        p.append(_int(args, "min_days"))
    rows = query(f"SELECT * FROM v_pending_cases WHERE {' AND '.join(where)} ORDER BY days_pending DESC", p)
    cols = [("complaint_no", "Complaint", "complaint"), ("title", "Title", "text"), ("status", "Status", "status"),
            ("priority", "Priority", "priority"), ("station_name", "Station", "text"),
            ("lead_officer", "Lead officer", "text"), ("registered_on", "Registered", "date"),
            ("days_pending", "Days pending", "days"), ("last_activity", "Last activity", "datetime"),
            ("evidence_items", "Evidence", "num")]
    return cols, rows


@report("officer-load", "Officer Workload", "Officer reports",
        "Active cases, lead cases, recent activities and evidence in hand for every officer.",
        "users", params=("station",), chart=("full_name", "active_cases"))
def _load(args):
    where, p = ["is_active = 1"], []
    if args.get("station"):
        where.append("station_name = (SELECT station_name FROM station WHERE station_id = %s)")
        p.append(_int(args, "station"))
    rows = query(f"""SELECT * FROM v_officer_load WHERE {' AND '.join(where)}
                     ORDER BY active_cases DESC, lead_cases DESC, full_name""", p)
    cols = [("badge_no", "Badge", "mono"), ("full_name", "Officer", "officer"), ("officer_rank", "Rank", "text"),
            ("station_name", "Station", "text"), ("active_cases", "Active cases", "num"),
            ("lead_cases", "As lead", "num"), ("total_cases_handled", "Total handled", "num"),
            ("activities_30d", "Activities (30d)", "num"), ("evidence_in_hand", "Evidence held", "num")]
    return cols, rows


@report("evidence-location", "Evidence Location", "Evidence reports",
        "Current custodian, location and derived status of every evidence item.",
        "map-pin", params=("ev_status", "ev_category"), chart=("evidence_status", None))
def _location(args):
    where, p = ["1=1"], []
    if args.get("ev_status"):
        where.append("evidence_status = %s")
        p.append(args["ev_status"])
    if args.get("ev_category"):
        where.append("category = %s")
        p.append(args["ev_category"])
    rows = query(f"SELECT * FROM v_evidence_location WHERE {' AND '.join(where)} ORDER BY evidence_no", p)
    cols = [("evidence_no", "Evidence", "evidence"), ("complaint_no", "Complaint", "complaint"),
            ("description", "Description", "text"), ("evidence_status", "Status", "evstatus"),
            ("current_holder", "Current holder", "text"), ("current_location", "Location", "text"),
            ("held_since", "Since", "datetime"), ("days_at_location", "Days", "days"),
            ("transfer_count", "Transfers", "num")]
    return cols, rows


@report("custody-history", "Custody History", "Evidence reports",
        "Step-by-step chain of custody of an evidence item (or all items).",
        "link", params=("evidence",))
def _custody(args):
    where, p = ["1=1"], []
    if args.get("evidence"):
        where.append("evidence_id = %s")
        p.append(_int(args, "evidence"))
    rows = query(f"SELECT * FROM v_custody_history WHERE {' AND '.join(where)} ORDER BY evidence_no, step_no", p)
    cols = [("evidence_no", "Evidence", "evidence"), ("step_no", "Step", "num"),
            ("handed_over_by", "Handed over by", "text"), ("received_by", "Received by", "text"),
            ("location", "Location", "text"), ("purpose", "Purpose", "purpose"),
            ("received_at", "Received", "datetime"), ("released_at", "Released", "datetime"),
            ("hours_held", "Hours held", "num"), ("seal_intact", "Seal intact", "bool")]
    return cols, rows


@report("witnesses", "Witness Register", "Case reports",
        "Witness statements with recording officer; filter by complaint.",
        "message", params=("complaint",))
def _witnesses(args):
    where, p = ["1=1"], []
    if args.get("complaint"):
        where.append("complaint_id = %s")
        p.append(_int(args, "complaint"))
    rows = query(f"SELECT * FROM v_case_witnesses WHERE {' AND '.join(where)} ORDER BY complaint_no, statement_date", p)
    cols = [("complaint_no", "Complaint", "complaint"), ("witness_name", "Witness", "text"),
            ("witness_phone", "Phone", "mono"), ("statement", "Statement", "long"),
            ("statement_date", "Recorded", "datetime"), ("recorded_by", "Recorded by", "text"),
            ("is_protected", "Protected", "bool")]
    return cols, rows


@report("case-timeline", "Case Timeline", "Case reports",
        "Chronological stream of every event of a case: status, assignments, activities, evidence, custody, "
        "witnesses, charges and court.", "clock", params=("complaint_required",))
def _timeline(args):
    cid = _int(args, "complaint")
    if not cid:
        return [], []
    rows = query("""SELECT t.*, c.complaint_no FROM v_case_timeline t JOIN complaint c ON c.complaint_id = t.complaint_id
                     WHERE t.complaint_id = %s ORDER BY t.event_time, t.event_type""", (cid,))
    cols = [("event_time", "When", "datetime"), ("event_type", "Type", "evtype"), ("event_title", "Event", "text"),
            ("details", "Details", "long"), ("actor", "By", "text")]
    return cols, rows


@report("closures", "Case Closures", "Case reports",
        "Closed cases with closure type, days taken to close and court verdict.",
        "check-circle", params=("date_from", "date_to", "closure_type"), chart=("closure_type", None))
def _closures(args):
    where, p = ["1=1"], []
    if args.get("date_from"):
        where.append("closure_date >= %s")
        p.append(args["date_from"])
    if args.get("date_to"):
        where.append("closure_date <= %s")
        p.append(args["date_to"])
    if args.get("closure_type"):
        where.append("closure_type = %s")
        p.append(args["closure_type"])
    rows = query(f"SELECT * FROM v_closed_cases WHERE {' AND '.join(where)} ORDER BY closure_date DESC", p)
    cols = [("complaint_no", "Complaint", "complaint"), ("title", "Title", "text"), ("category", "Category", "label"),
            ("station_name", "Station", "text"), ("registered_on", "Registered", "date"),
            ("closure_date", "Closed", "date"), ("days_to_close", "Days to close", "days"),
            ("closure_type", "Closure type", "label"), ("closed_by", "Closed by", "text"),
            ("court_verdict", "Verdict", "label"), ("closure_remarks", "Remarks", "long")]
    return cols, rows


@report("station-summary", "Station Summary", "Analytics",
        "Cases per station broken down by status with closure rate (GROUP BY + conditional aggregation).",
        "building", chart=("station_name", "total"))
def _station(args):
    rows = query("""SELECT s.station_name, COUNT(c.complaint_id) AS total,
                           SUM(c.status = 'REGISTERED') AS registered,
                           SUM(c.status = 'UNDER_INVESTIGATION') AS under_investigation,
                           SUM(c.status IN ('CHARGE_SHEETED','IN_COURT')) AS charge_sheeted_or_court,
                           SUM(c.status = 'CLOSED') AS closed,
                           ROUND(100 * SUM(c.status = 'CLOSED') / NULLIF(COUNT(c.complaint_id), 0), 1) AS closure_rate
                      FROM station s LEFT JOIN complaint c ON c.station_id = s.station_id
                     GROUP BY s.station_id, s.station_name ORDER BY total DESC""")
    cols = [("station_name", "Station", "text"), ("total", "Total", "num"), ("registered", "Registered", "num"),
            ("under_investigation", "Investigating", "num"), ("charge_sheeted_or_court", "Charge-sheeted / court", "num"),
            ("closed", "Closed", "num"), ("closure_rate", "Closure rate %", "num")]
    return cols, rows


@report("category-analysis", "Crime Category Analysis", "Analytics",
        "Complaints per category with share of high-priority cases and average days to close.",
        "pie", chart=("category", "complaints"))
def _category(args):
    rows = query("""SELECT category, COUNT(*) AS complaints,
                           SUM(priority IN ('HIGH','CRITICAL')) AS urgent,
                           SUM(status <> 'CLOSED') AS open_cases,
                           ROUND(AVG(CASE WHEN status = 'CLOSED'
                                     THEN DATEDIFF(closure_date, DATE(registered_at)) END), 1) AS avg_days_to_close,
                           (SELECT COUNT(*) FROM evidence_item e JOIN complaint c2 ON c2.complaint_id = e.complaint_id
                             WHERE c2.category = c.category) AS evidence_items
                      FROM complaint c GROUP BY category ORDER BY complaints DESC""")
    cols = [("category", "Category", "label"), ("complaints", "Complaints", "num"), ("urgent", "High/Critical", "num"),
            ("open_cases", "Open", "num"), ("avg_days_to_close", "Avg days to close", "num"),
            ("evidence_items", "Evidence items", "num")]
    return cols, rows


@report("upcoming-hearings", "Upcoming Hearings", "Court reports",
        "Court hearings scheduled from today, nearest first.", "gavel")
def _hearings(args):
    rows = query("SELECT * FROM v_upcoming_hearings ORDER BY next_hearing_date")
    cols = [("next_hearing_date", "Hearing date", "date"), ("days_left", "Days left", "days"),
            ("court_case_no", "Court case", "mono"), ("court_name", "Court", "text"), ("case_stage", "Stage", "label"),
            ("complaint_no", "Complaint", "complaint"), ("title", "Title", "text")]
    return cols, rows


@report("stale-cases", "Stale Cases (no activity in 30 days)", "Case reports",
        "Open cases with no investigation activity logged in the last 30 days (NOT EXISTS sub-query).",
        "alert")
def _stale(args):
    rows = query("""SELECT c.complaint_id, c.complaint_no, c.title, c.status, c.priority,
                           (SELECT MAX(a.activity_time) FROM investigation_activity a
                             WHERE a.complaint_id = c.complaint_id) AS last_activity,
                           DATEDIFF(CURDATE(), DATE(c.registered_at)) AS age_days
                      FROM complaint c
                     WHERE c.status <> 'CLOSED'
                       AND NOT EXISTS (SELECT 1 FROM investigation_activity a WHERE a.complaint_id = c.complaint_id
                                        AND a.activity_time >= CURDATE() - INTERVAL 30 DAY)
                     ORDER BY last_activity IS NULL DESC, last_activity""")
    cols = [("complaint_no", "Complaint", "complaint"), ("title", "Title", "text"), ("status", "Status", "status"),
            ("priority", "Priority", "priority"), ("last_activity", "Last activity", "datetime"),
            ("age_days", "Age (days)", "days")]
    return cols, rows


@report("custody-audit", "Chain-of-Custody Integrity Audit", "Evidence reports",
        "Checks every custody hand-over with window functions (LAG): the receiver must take over exactly when the "
        "previous holder released the item, from that holder.", "shield")
def _audit(args):
    rows = query("""WITH chain AS (
                        SELECT evidence_id, custody_id, received_at, released_at, from_officer_id, to_officer_id, purpose,
                               LAG(released_at)   OVER (PARTITION BY evidence_id ORDER BY received_at) AS prev_released,
                               LAG(to_officer_id) OVER (PARTITION BY evidence_id ORDER BY received_at) AS prev_holder
                          FROM custody_log)
                    SELECT e.evidence_id, e.evidence_no, ch.custody_id, ch.purpose, ch.received_at, ch.prev_released,
                           CASE WHEN ch.prev_released IS NULL AND ch.from_officer_id IS NULL THEN 'OK - initial seizure'
                                WHEN ch.prev_released = ch.received_at AND ch.prev_holder = ch.from_officer_id THEN 'OK'
                                ELSE 'BROKEN CHAIN' END AS integrity
                      FROM chain ch JOIN evidence_item e ON e.evidence_id = ch.evidence_id
                     ORDER BY e.evidence_no, ch.received_at""")
    cols = [("evidence_no", "Evidence", "evidence"), ("custody_id", "Custody #", "num"), ("purpose", "Purpose", "purpose"),
            ("prev_released", "Previous released", "datetime"), ("received_at", "Received", "datetime"),
            ("integrity", "Integrity", "integrity")]
    return cols, rows


def run(key, args):
    rep = REPORTS.get(key)
    if not rep:
        raise AppError("Unknown report.")
    cols, rows = rep["fn"](args)
    return rep, cols, rows


def to_csv(cols, rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([c[1] for c in cols])
    for r in rows:
        w.writerow(["" if r.get(c[0]) is None else r.get(c[0]) for c in cols])
    return "﻿" + buf.getvalue()  # BOM so Excel opens UTF-8 correctly
