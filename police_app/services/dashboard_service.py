"""Dashboard metrics."""
from datetime import date

from ..db import query, query_one


def kpis():
    return query_one("""
        SELECT (SELECT COUNT(*) FROM complaint)                                          AS total_cases,
               (SELECT COUNT(*) FROM complaint WHERE status <> 'CLOSED')                 AS open_cases,
               (SELECT COUNT(*) FROM complaint WHERE status = 'CLOSED')                  AS closed_cases,
               (SELECT COUNT(*) FROM complaint WHERE status = 'REGISTERED')              AS unassigned_cases,
               (SELECT COUNT(*) FROM complaint WHERE priority = 'CRITICAL' AND status <> 'CLOSED') AS critical_open,
               (SELECT COUNT(*) FROM complaint WHERE registered_at >= CURDATE() - INTERVAL 30 DAY) AS new_30d,
               (SELECT COUNT(*) FROM evidence_item)                                      AS evidence_total,
               (SELECT COUNT(*) FROM v_evidence_location WHERE evidence_status = 'IN_LAB')   AS evidence_in_lab,
               (SELECT COUNT(*) FROM v_evidence_location WHERE evidence_status NOT IN ('RETURNED','DISPOSED')) AS evidence_active,
               (SELECT COUNT(*) FROM custody_log WHERE received_at >= CURDATE() - INTERVAL 30 DAY
                                                   AND purpose <> 'INITIAL_SEIZURE')   AS transfers_30d,
               (SELECT COUNT(*) FROM v_upcoming_hearings WHERE days_left <= 30)          AS hearings_30d,
               (SELECT COUNT(*) FROM officer WHERE is_active = 1)                        AS active_officers,
               (SELECT ROUND(AVG(DATEDIFF(closure_date, DATE(registered_at))), 0)
                  FROM complaint WHERE status = 'CLOSED')                                AS avg_days_to_close
    """)


def status_breakdown():
    return query("""SELECT status, COUNT(*) AS n FROM complaint GROUP BY status
                    ORDER BY FIELD(status,'REGISTERED','UNDER_INVESTIGATION','CHARGE_SHEETED','IN_COURT','CLOSED')""")


def monthly(months=8):
    """Registrations and closures for the last `months` calendar months (zero-filled)."""
    today = date.today()
    keys = []
    y, mth = today.year, today.month
    for _ in range(months):
        keys.append((y, mth))
        y, mth = (y, mth - 1) if mth > 1 else (y - 1, 12)
    keys.reverse()
    start = date(keys[0][0], keys[0][1], 1)
    reg = {(r["y"], r["m"]): r["n"] for r in query(
        """SELECT YEAR(registered_at) AS y, MONTH(registered_at) AS m, COUNT(*) AS n FROM complaint
            WHERE registered_at >= %s GROUP BY y, m""", (start,))}
    closed = {(r["y"], r["m"]): r["n"] for r in query(
        """SELECT YEAR(closure_date) AS y, MONTH(closure_date) AS m, COUNT(*) AS n FROM complaint
            WHERE closure_date >= %s GROUP BY y, m""", (start,))}
    return [{"label": date(yy, mm, 1).strftime("%b"), "registered": reg.get((yy, mm), 0),
             "closed": closed.get((yy, mm), 0)} for yy, mm in keys]


def category_breakdown():
    return query("SELECT category, COUNT(*) AS n FROM complaint GROUP BY category ORDER BY n DESC")


def top_officers(limit=6):
    return query("""SELECT officer_id, full_name, officer_rank, station_name, active_cases, lead_cases, evidence_in_hand
                      FROM v_officer_load WHERE is_active = 1 ORDER BY active_cases DESC, lead_cases DESC LIMIT %s""",
                 (limit,))


def recent_events(limit=8):
    return query("""SELECT t.*, c.complaint_no FROM v_case_timeline t JOIN complaint c ON c.complaint_id = t.complaint_id
                     WHERE t.event_time <= NOW() ORDER BY t.event_time DESC LIMIT %s""", (limit,))


def attention():
    """Items that need action."""
    return {
        "unassigned": query("""SELECT complaint_id, complaint_no, title, priority, DATEDIFF(CURDATE(), DATE(registered_at)) AS age
                                 FROM complaint WHERE status = 'REGISTERED' ORDER BY FIELD(priority,'CRITICAL','HIGH','MEDIUM','LOW'),
                                 registered_at LIMIT 5"""),
        "long_lab": query("""SELECT evidence_id, evidence_no, description, days_at_location FROM v_evidence_location
                              WHERE evidence_status = 'IN_LAB' ORDER BY days_at_location DESC LIMIT 5"""),
        "hearings": query("SELECT * FROM v_upcoming_hearings ORDER BY next_hearing_date LIMIT 5"),
    }
