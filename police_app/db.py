"""
Database access layer.

* One pooled MySQL connection per request (stored on flask.g)
* query()/query_one()/execute() helpers - always parameterised (no SQL injection)
* transaction() context manager: COMMIT on success, ROLLBACK on any error
* translate_db_error(): converts MySQL error codes into friendly messages
"""
import re
from contextlib import contextmanager

import mysql.connector
from mysql.connector import errorcode, pooling
from flask import g, has_request_context

from .config import load_db_config, db_pool_size

_pool = None


class AppError(Exception):
    """An error whose message is safe to show to the user."""

    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


class ValidationError(AppError):
    def __init__(self, errors):
        self.errors = errors if isinstance(errors, dict) else {"_": errors}
        super().__init__("Please correct the highlighted fields.")


_direct_cfg = None   # set when pooling is disabled (PCETS_DB_POOL_SIZE=0)


def init_pool(database=None):
    """Create the connection pool. Pool size 0 = open one connection per request instead
    (used on hosts with a tiny per-user connection limit, e.g. Clever Cloud DEV: 5)."""
    global _pool, _direct_cfg
    cfg = load_db_config()
    if database:
        cfg["database"] = database
    common = dict(charset="utf8mb4", collation="utf8mb4_0900_ai_ci", time_zone="+05:30", autocommit=True, **cfg)
    size = db_pool_size()
    if size <= 0:
        _pool, _direct_cfg = None, common
        return None
    _direct_cfg = None
    _pool = pooling.MySQLConnectionPool(pool_name="pcets", pool_size=size, pool_reset_session=True, **common)
    return _pool


def _new_connection():
    if _pool is None and _direct_cfg is None:
        init_pool()
    if _direct_cfg is not None:
        return mysql.connector.connect(**_direct_cfg)
    return _pool.get_connection()          # autocommit=True is part of the pool config


def get_conn():
    if has_request_context():
        if "db" not in g:
            g.db = _new_connection()
            _set_session_vars(g.db)
        return g.db
    return _new_connection()


def _set_session_vars(conn):
    officer_id = None
    if has_request_context():
        user = g.get("user")
        officer_id = user["officer_id"] if user else None
    cur = conn.cursor()
    cur.execute("SET @current_officer_id = %s, @audit_time = NULL, @status_remarks = NULL", (officer_id,))
    cur.close()


def refresh_session_vars():
    """Re-apply @current_officer_id after the logged-in user is known."""
    if has_request_context() and "db" in g:
        _set_session_vars(g.db)


def close_conn(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        try:
            if conn.in_transaction:
                conn.rollback()
        finally:
            conn.close()


def query(sql, params=None, conn=None):
    conn = conn or get_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    except mysql.connector.Error as err:
        raise translate_db_error(err) from err
    finally:
        cur.close()


def query_one(sql, params=None, conn=None):
    rows = query(sql, params, conn)
    return rows[0] if rows else None


def scalar(sql, params=None, conn=None):
    row = query_one(sql, params, conn)
    return next(iter(row.values())) if row else None


def execute(sql, params=None, conn=None):
    """Run an INSERT/UPDATE/DELETE. Returns lastrowid (or rowcount when no id)."""
    conn = conn or get_conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        return cur.lastrowid if cur.lastrowid else cur.rowcount
    except mysql.connector.Error as err:
        raise translate_db_error(err) from err
    finally:
        cur.close()


@contextmanager
def transaction(remarks=None):
    """
    Groups several statements into one atomic unit of work.

        with transaction() as conn:
            execute("UPDATE ...", conn=conn)
            execute("INSERT ...", conn=conn)
    """
    conn = get_conn()
    if conn.in_transaction:          # never nest - discard anything left open
        conn.rollback()
    try:
        # explicit START TRANSACTION ... COMMIT (autocommit stays on outside the block)
        conn.start_transaction(isolation_level="READ COMMITTED")
        if remarks is not None:
            execute("SET @status_remarks = %s", (remarks,), conn=conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if remarks is not None:
            cur = conn.cursor()
            cur.execute("SET @status_remarks = NULL")
            cur.close()


# ----------------------------------------------------------------------
# Error translation
# ----------------------------------------------------------------------
_CONSTRAINT_MESSAGES = {
    "uq_complaint_no": "This complaint number already exists.",
    "uq_evidence_no": "This evidence number already exists.",
    "uq_evidence_seal": "This seal number is already used by another evidence item.",
    "uq_station_code": "A station with this code already exists.",
    "uq_officer_badge": "An officer with this badge number already exists.",
    "uq_officer_phone": "Another officer already uses this phone number.",
    "uq_officer_email": "Another officer already uses this email address.",
    "uq_person_idproof": "A person with this ID proof is already registered.",
    "uq_assignment_active": "This officer is already actively assigned to the case.",
    "uq_assignment_one_lead": "The case already has an active LEAD officer. Relieve them first.",
    "uq_custody_one_open": "This evidence item already has a current custodian (overlapping custody).",
    "uq_witness_case": "This person is already recorded as a witness in this case.",
    "uq_charge": "This charge is already framed against the accused.",
    "uq_court_case_no": "This court case number already exists.",
    "uq_app_username": "This username is taken.",
    "PRIMARY": "This record already exists.",
    "chk_complaint_status": "Invalid case status.",
    "chk_complaint_closure": "Closure date, type, remarks and closing officer are required to close a case "
                             "(and must be empty for open cases).",
    "chk_complaint_closuredate": "Closure date cannot be before the registration date.",
    "chk_complaint_incident": "Incident time cannot be after the registration time.",
    "chk_complaint_no": "Complaint number must look like CMP-2026-00001.",
    "chk_custody_from": "Every transfer must name the handing officer (complete custody transfer).",
    "chk_custody_self": "An officer cannot transfer custody to themselves.",
    "chk_custody_period": "Release time must be after the receive time.",
    "chk_custody_location": "Custody location is required.",
    "chk_person_phone": "Phone must be a valid 10-digit Indian mobile number.",
    "chk_officer_phone": "Phone must be a valid 10-digit Indian mobile number.",
    "chk_person_idformat": "ID proof number does not match the format of the selected ID type.",
    "chk_person_idpair": "Provide both ID proof type and number, or neither.",
    "chk_officer_badge": "Badge number must look like MH12-1234.",
    "chk_assignment_dates": "Relieve time cannot be before the assignment time.",
    "chk_court_hearing": "Next hearing date cannot be before the filing date.",
    "chk_court_verdict_stage": "A verdict can only be recorded when the court case is DISPOSED "
                               "(and must be PENDING otherwise).",
    "chk_charge_section": "Section must start with a number, e.g. 303(2).",
    "chk_activity_desc": "Activity description is too short.",
    "chk_witness_statement": "Witness statement must be at least 10 characters.",
    "chk_evidence_qty": "Quantity must be at least 1.",
}

_FK_MESSAGES = {
    "fk_charge_accused": "Charges can only be framed against a person listed as accused in this case.",
}


def translate_db_error(err):
    """Map a mysql.connector.Error onto an AppError with a readable message."""
    msg = getattr(err, "msg", str(err))
    code = getattr(err, "errno", None)

    if code == 1644:  # SIGNAL from a trigger / procedure - already human readable
        return AppError(msg)
    if code == errorcode.ER_DUP_ENTRY:  # 1062
        m = re.search(r"for key '(?:[\w]+\.)?([\w]+)'", msg)
        return AppError(_CONSTRAINT_MESSAGES.get(m.group(1) if m else "", "Duplicate value: " + msg))
    if code == 3819:  # CHECK constraint violated
        m = re.search(r"constraint '([\w]+)'", msg)
        key = m.group(1) if m else ""
        return AppError(_CONSTRAINT_MESSAGES.get(key, f"Validation rule '{key}' was violated."))
    if code in (1451,):  # parent row referenced
        return AppError("This record is referenced by other records (e.g. complaints, evidence or "
                        "statements) and cannot be deleted.")
    if code in (1452,):
        m = re.search(r"CONSTRAINT `([\w]+)`", msg)
        return AppError(_FK_MESSAGES.get(m.group(1) if m else "", "A referenced record does not exist."))
    if code == 1048:
        m = re.search(r"Column '([\w]+)'", msg)
        return AppError(f"'{(m.group(1) if m else 'value').replace('_', ' ')}' is required.")
    if code in (1406,):
        m = re.search(r"column '([\w]+)'", msg)
        return AppError(f"'{(m.group(1) if m else 'value').replace('_', ' ')}' is too long.")
    if code in (1292, 1366):
        return AppError("One of the values has an invalid format (date, time or number).")
    if code in (2003, 2005, 2013, 2055, 1045, 1049):
        return AppError("Cannot reach the MySQL database. Check that the server is running and config.ini is correct.")
    return AppError(f"Database error ({code}): {msg}")
