"""
Hosted mode — for MySQL services that refuse CREATE TRIGGER / CREATE FUNCTION
(e.g. Clever Cloud's shared DEV plan: binary logging on, no SUPER privilege).

When the connected database has no triggers, the application performs what the
triggers normally do: issuing CMP/EVD numbers and writing the status history.
The rule checks the triggers perform are ALSO done by the services in every
mode (so the rules hold either way); on a database with triggers the database
remains the final authority.
"""
from datetime import datetime

from .db import query_one, scalar, execute, AppError

_cache = {}


def has_triggers(conn=None):
    """True when the PCETS triggers are installed in the connected database (cached per database)."""
    db = scalar("SELECT DATABASE()", conn=conn)
    if db not in _cache:
        _cache[db] = (scalar("""SELECT COUNT(*) FROM information_schema.triggers
                                 WHERE trigger_schema = DATABASE() AND trigger_name = 'trg_complaint_bi'""",
                             conn=conn) or 0) > 0
    return _cache[db]


def now_minute():
    """Forms work at minute precision; stored timestamps are truncated to the minute."""
    return datetime.now().replace(second=0, microsecond=0)


def next_number(conn, table, column, prefix, year):
    """Next CMP-YYYY-NNNNN / EVD-YYYY-NNNNN number (rows locked; UNIQUE key guards any race)."""
    seq = scalar(f"""SELECT COALESCE(MAX(CAST(SUBSTRING({column}, 10) AS UNSIGNED)), 0) + 1 FROM {table}
                      WHERE {column} LIKE %s FOR UPDATE""", (f"{prefix}-{year}-%",), conn=conn)
    return f"{prefix}-{year}-{int(seq):05d}"


def log_status(conn, complaint_id, old_status, new_status, changed_by, remarks, changed_at=None):
    execute("""INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, changed_at, remarks)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (complaint_id, old_status, new_status, changed_by, changed_at or datetime.now(), remarks), conn=conn)


# ---------------- rule checks (mirror the triggers) ----------------
def require_active_officer(conn, officer_id, message):
    row = query_one("SELECT is_active FROM officer WHERE officer_id = %s", (officer_id,), conn=conn)
    if not row:
        raise AppError("Selected officer does not exist.")
    if not row["is_active"]:
        raise AppError(message)


def require_status_preconditions(conn, complaint_id, old_status, new_status):
    if old_status == "REGISTERED" and new_status == "UNDER_INVESTIGATION":
        if not scalar("SELECT COUNT(*) FROM assignment WHERE complaint_id=%s AND relieved_at IS NULL",
                      (complaint_id,), conn=conn):
            raise AppError("Assign at least one officer before starting the investigation.")
    if new_status == "CHARGE_SHEETED":
        if not scalar("SELECT COUNT(*) FROM charge WHERE complaint_id=%s", (complaint_id,), conn=conn):
            raise AppError("A case cannot be charge-sheeted without at least one charge.")
    if new_status == "IN_COURT":
        if not scalar("SELECT COUNT(*) FROM court_reference WHERE complaint_id=%s", (complaint_id,), conn=conn):
            raise AppError("Add a court reference before moving the case to IN_COURT.")


def require_assigned_at(conn, complaint_id, officer_id, when):
    if not scalar("""SELECT COUNT(*) FROM assignment WHERE complaint_id=%s AND officer_id=%s AND assigned_at <= %s
                      AND (relieved_at IS NULL OR relieved_at >= %s)""",
                  (complaint_id, officer_id, when, when), conn=conn):
        raise AppError("Only an officer assigned to this case (at that time) can log an activity.")


def require_not_accused(conn, complaint_id, person_id):
    if scalar("SELECT COUNT(*) FROM complaint_accused WHERE complaint_id=%s AND person_id=%s",
              (complaint_id, person_id), conn=conn):
        raise AppError("An accused person cannot be a witness in the same case.")


def require_can_be_accused(conn, complaint_id, person_id):
    if scalar("SELECT COUNT(*) FROM complaint WHERE complaint_id=%s AND complainant_id=%s",
              (complaint_id, person_id), conn=conn):
        raise AppError("The complainant cannot be accused in the same complaint.")
    if scalar("SELECT COUNT(*) FROM witness WHERE complaint_id=%s AND person_id=%s", (complaint_id, person_id), conn=conn):
        raise AppError("A witness cannot be accused in the same case.")
