"""Officers and stations."""
import re

from ..db import query, query_one, execute, scalar, AppError
from ..validators import Form
from .. import constants as C


def stations():
    return query("SELECT * FROM station ORDER BY station_name")


def officers_for_select(active_only=True):
    sql = """SELECT o.officer_id, o.full_name, o.badge_no, o.officer_rank, s.station_code
               FROM officer o JOIN station s ON s.station_id = o.station_id"""
    if active_only:
        sql += " WHERE o.is_active = 1"
    return query(sql + " ORDER BY s.station_code, o.full_name")


def list_officers(q=None, station=None, active=None):
    where, params = ["1=1"], []
    if q:
        like = f"%{q}%"
        where.append("(v.full_name LIKE %s OR v.badge_no LIKE %s OR v.officer_rank LIKE %s)")
        params += [like, like, like]
    if station:
        where.append("o.station_id = %s")
        params.append(station)
    if active in ("0", "1"):
        where.append("v.is_active = %s")
        params.append(int(active))
    return query(f"""SELECT v.*, o.station_id, o.phone, o.email, o.date_joined,
                            (SELECT u.username FROM app_user u WHERE u.officer_id = o.officer_id) AS username,
                            (SELECT u.user_role FROM app_user u WHERE u.officer_id = o.officer_id) AS user_role
                       FROM v_officer_load v JOIN officer o ON o.officer_id = v.officer_id
                      WHERE {' AND '.join(where)}
                      ORDER BY v.is_active DESC, v.active_cases DESC, v.full_name""", params)


def get_officer(officer_id):
    row = query_one("""SELECT o.*, s.station_name, s.station_code, v.active_cases, v.lead_cases,
                              v.total_cases_handled, v.activities_30d, v.evidence_in_hand
                         FROM officer o JOIN station s ON s.station_id = o.station_id
                         JOIN v_officer_load v ON v.officer_id = o.officer_id
                        WHERE o.officer_id = %s""", (officer_id,))
    if not row:
        raise AppError("Officer not found.")
    return row


def officer_cases(officer_id):
    return query("""SELECT a.assignment_role, a.assigned_at, a.relieved_at, c.complaint_id, c.complaint_no, c.title,
                           c.status, c.priority
                      FROM assignment a JOIN complaint c ON c.complaint_id = a.complaint_id
                     WHERE a.officer_id = %s ORDER BY a.relieved_at IS NOT NULL, a.assigned_at DESC""", (officer_id,))


def officer_evidence(officer_id):
    return query("""SELECT * FROM v_evidence_location WHERE holder_id = %s
                     AND evidence_status NOT IN ('RETURNED','DISPOSED') ORDER BY held_since""", (officer_id,))


def officer_activities(officer_id, limit=10):
    return query("""SELECT a.*, c.complaint_no FROM investigation_activity a
                      JOIN complaint c ON c.complaint_id = a.complaint_id
                     WHERE a.officer_id = %s ORDER BY a.activity_time DESC LIMIT %s""", (officer_id, limit))


def _validate(data):
    f = Form(data)
    badge = f.text("badge_no", "Badge number", max_len=12)
    if badge:
        f.clean["badge_no"] = badge = badge.upper()
        if not re.match(r"^MH[0-9]{2}-[0-9]{4}$", badge):
            f.error("badge_no", "Badge number must look like MH12-1234.")
    f.text("full_name", "Full name", min_len=3, max_len=100)
    f.choice("officer_rank", "Rank", C.RANKS)
    f.integer("station_id", "Station", min_value=1)
    f.phone("phone", "Phone", required=True)
    f.email("email", "Email")
    f.date("date_joined", "Date joined", not_future=True)
    return f.raise_if_invalid()


def create_officer(data):
    c = _validate(data)
    return execute("""INSERT INTO officer (badge_no, full_name, officer_rank, station_id, phone, email, date_joined)
                      VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                   (c["badge_no"], c["full_name"], c["officer_rank"], c["station_id"], c["phone"], c["email"],
                    c["date_joined"]))


def update_officer(officer_id, data):
    c = _validate(data)
    execute("""UPDATE officer SET badge_no=%s, full_name=%s, officer_rank=%s, station_id=%s, phone=%s, email=%s,
                      date_joined=%s WHERE officer_id=%s""",
            (c["badge_no"], c["full_name"], c["officer_rank"], c["station_id"], c["phone"], c["email"],
             c["date_joined"], officer_id))


def set_active(officer_id, active):
    off = get_officer(officer_id)
    if not active:
        if off["active_cases"]:
            raise AppError(f"{off['full_name']} still has {off['active_cases']} active case(s). Relieve them first.")
        if off["evidence_in_hand"]:
            raise AppError(f"{off['full_name']} still holds {off['evidence_in_hand']} evidence item(s). "
                           "Transfer custody first.")
    execute("UPDATE officer SET is_active = %s WHERE officer_id = %s", (1 if active else 0, officer_id))
    execute("UPDATE app_user SET is_active = %s WHERE officer_id = %s", (1 if active else 0, officer_id))


def delete_officer(officer_id):
    get_officer(officer_id)
    execute("DELETE FROM officer WHERE officer_id = %s", (officer_id,))


def station_stats():
    return query("""SELECT s.station_id, s.station_code, s.station_name, s.district,
                           COUNT(c.complaint_id) AS total,
                           SUM(c.status <> 'CLOSED') AS open_cases,
                           SUM(c.status = 'CLOSED') AS closed_cases,
                           (SELECT COUNT(*) FROM officer o WHERE o.station_id = s.station_id AND o.is_active = 1) AS officers
                      FROM station s LEFT JOIN complaint c ON c.station_id = s.station_id
                     GROUP BY s.station_id, s.station_code, s.station_name, s.district
                     ORDER BY s.station_name""")
