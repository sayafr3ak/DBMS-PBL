"""Complaints and everything attached to them: assignments, activities, witnesses,
accused, charges, court references and status changes."""
from datetime import datetime, date

from ..db import query, query_one, execute, scalar, transaction, AppError, ValidationError
from ..validators import Form
from .. import constants as C
from . import person_service

SORTS = {
    "newest": "registered_at DESC",
    "oldest": "registered_at ASC",
    "priority": "FIELD(priority,'CRITICAL','HIGH','MEDIUM','LOW'), registered_at DESC",
    "status": "FIELD(status,'REGISTERED','UNDER_INVESTIGATION','CHARGE_SHEETED','IN_COURT','CLOSED'), registered_at DESC",
    "age": "age_days DESC",
}


# ----------------------------------------------------------------------
# Search / read
# ----------------------------------------------------------------------
def list_complaints(filters, page=1, per_page=12):
    where, params = ["1=1"], []
    q = (filters.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        where.append("(complaint_no LIKE %s OR title LIKE %s OR complainant_name LIKE %s "
                     "OR incident_location LIKE %s OR lead_officer_name LIKE %s)")
        params += [like] * 5
    for key in ("status", "category", "priority"):
        if filters.get(key):
            where.append(f"{key} = %s")
            params.append(filters[key])
    if filters.get("open") == "1":
        where.append("status <> 'CLOSED'")
    if filters.get("station"):
        where.append("station_id = %s")
        params.append(filters["station"])
    if filters.get("officer"):
        where.append("complaint_id IN (SELECT complaint_id FROM assignment WHERE officer_id = %s AND relieved_at IS NULL)")
        params.append(filters["officer"])
    if filters.get("date_from"):
        where.append("DATE(registered_at) >= %s")
        params.append(filters["date_from"])
    if filters.get("date_to"):
        where.append("DATE(registered_at) <= %s")
        params.append(filters["date_to"])
    if filters.get("unassigned") == "1":
        where.append("lead_officer_id IS NULL AND status <> 'CLOSED'")
    where_sql = " AND ".join(where)
    order = SORTS.get(filters.get("sort"), SORTS["newest"])
    total = scalar(f"SELECT COUNT(*) FROM v_case_summary WHERE {where_sql}", params)
    rows = query(f"SELECT * FROM v_case_summary WHERE {where_sql} ORDER BY {order} LIMIT %s OFFSET %s",
                 params + [per_page, (page - 1) * per_page])
    return rows, total


def get_complaint(complaint_id):
    row = query_one(
        """SELECT c.*, s.station_name, s.station_code, s.district,
                  p.full_name AS complainant_name, p.phone AS complainant_phone, p.address AS complainant_address,
                  p.gender AS complainant_gender, p.id_proof_type, p.id_proof_no,
                  rb.full_name AS registered_by_name, cb.full_name AS closed_by_name,
                  DATEDIFF(COALESCE(c.closure_date, CURDATE()), DATE(c.registered_at)) AS age_days
             FROM complaint c
             JOIN station s ON s.station_id = c.station_id
             JOIN person  p ON p.person_id  = c.complainant_id
             LEFT JOIN officer rb ON rb.officer_id = c.registered_by
             LEFT JOIN officer cb ON cb.officer_id = c.closed_by
            WHERE c.complaint_id = %s""", (complaint_id,))
    if not row:
        raise AppError("Complaint not found.")
    return row


def find_by_number(complaint_no):
    return query_one("SELECT complaint_id FROM complaint WHERE complaint_no = %s", (complaint_no,))


def assignments(complaint_id):
    return query(
        """SELECT a.*, o.full_name, o.badge_no, o.officer_rank, s.station_code, ab.full_name AS assigned_by_name
             FROM assignment a
             JOIN officer o ON o.officer_id = a.officer_id
             JOIN station s ON s.station_id = o.station_id
             LEFT JOIN officer ab ON ab.officer_id = a.assigned_by
            WHERE a.complaint_id = %s
            ORDER BY a.relieved_at IS NOT NULL, FIELD(a.assignment_role,'LEAD','SUPPORT','FORENSIC','SURVEILLANCE'),
                     a.assigned_at""", (complaint_id,))


def activities(complaint_id):
    return query(
        """SELECT a.*, o.full_name, o.badge_no FROM investigation_activity a
             JOIN officer o ON o.officer_id = a.officer_id
            WHERE a.complaint_id = %s ORDER BY a.activity_time DESC""", (complaint_id,))


def witnesses(complaint_id):
    return query("SELECT * FROM v_case_witnesses WHERE complaint_id = %s ORDER BY statement_date", (complaint_id,))


def accused(complaint_id):
    return query(
        """SELECT ca.*, p.full_name, p.phone, p.address, p.gender, p.date_of_birth,
                  (SELECT COUNT(*) FROM charge ch WHERE ch.complaint_id = ca.complaint_id
                      AND ch.accused_person_id = ca.person_id) AS charge_count
             FROM complaint_accused ca JOIN person p ON p.person_id = ca.person_id
            WHERE ca.complaint_id = %s ORDER BY ca.added_at""", (complaint_id,))


def charges(complaint_id):
    return query(
        """SELECT ch.*, p.full_name AS accused_name, o.full_name AS charged_by_name
             FROM charge ch
             JOIN person p ON p.person_id = ch.accused_person_id
             JOIN officer o ON o.officer_id = ch.charged_by
            WHERE ch.complaint_id = %s ORDER BY ch.charged_on, ch.charge_id""", (complaint_id,))


def court_refs(complaint_id):
    return query("SELECT * FROM court_reference WHERE complaint_id = %s ORDER BY filing_date", (complaint_id,))


def status_history(complaint_id):
    return query(
        """SELECT sh.*, o.full_name AS changed_by_name FROM status_history sh
             LEFT JOIN officer o ON o.officer_id = sh.changed_by
            WHERE sh.complaint_id = %s ORDER BY sh.changed_at, sh.history_id""", (complaint_id,))


def timeline(complaint_id):
    return query("SELECT * FROM v_case_timeline WHERE complaint_id = %s ORDER BY event_time, event_type",
                 (complaint_id,))


def evidence(complaint_id):
    return query(
        """SELECT e.*, v.current_holder, v.current_location, v.evidence_status, v.held_since, v.transfer_count
             FROM evidence_item e LEFT JOIN v_evidence_location v ON v.evidence_id = e.evidence_id
            WHERE e.complaint_id = %s ORDER BY e.collected_at""", (complaint_id,))


def allowed_transitions(status):
    return C.TRANSITIONS.get(status, [])


def _require_open(complaint):
    if complaint["status"] == "CLOSED":
        raise AppError("This case is closed. Re-open it before making changes.")


# ----------------------------------------------------------------------
# Complaint registration / editing
# ----------------------------------------------------------------------
def _validate_complaint_fields(f):
    f.integer("station_id", "Police station", min_value=1)
    f.text("title", "Title", min_len=5, max_len=150)
    f.text("description", "Description", min_len=15, max_len=5000)
    f.choice("category", "Category", C.CATEGORIES)
    f.choice("priority", "Priority", C.PRIORITIES)
    f.datetime("incident_datetime", "Incident date/time", not_future=True)
    f.text("incident_location", "Incident location", min_len=3, max_len=255)


def register_complaint(data, registered_by):
    """Registers a complaint in ONE transaction:
       (new complainant) -> complaint -> (optional lead assignment + status change)."""
    f = Form(data)
    _validate_complaint_fields(f)
    lead = f.integer("lead_officer_id", "Lead officer", required=False)
    errors = dict(f.errors)
    if (data.get("complainant_mode") or "existing") == "new":
        errors.update(person_service.validate_person(data, prefix="p_").errors)
    if errors:
        raise ValidationError(errors)
    clean = f.clean

    with transaction(remarks="Investigation started on registration") as conn:
        complainant_id = person_service.resolve_person(data, "complainant_mode", "complainant_id", "p_", conn)
        complaint_id = execute(
            """INSERT INTO complaint (station_id, complainant_id, title, description, category, priority,
                                      incident_datetime, incident_location, registered_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (clean["station_id"], complainant_id, clean["title"], clean["description"], clean["category"],
             clean["priority"], clean["incident_datetime"], clean["incident_location"], registered_by), conn=conn)
        if lead:
            execute("""INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_by, remarks)
                       VALUES (%s, %s, 'LEAD', %s, 'Assigned at registration')""",
                    (complaint_id, lead, registered_by), conn=conn)
            execute("UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = %s",
                    (complaint_id,), conn=conn)
        number = scalar("SELECT complaint_no FROM complaint WHERE complaint_id = %s", (complaint_id,), conn=conn)
    return complaint_id, number


def update_complaint(complaint_id, data):
    complaint = get_complaint(complaint_id)
    _require_open(complaint)
    f = Form(data)
    _validate_complaint_fields(f)
    clean = f.raise_if_invalid()
    if clean["incident_datetime"] > complaint["registered_at"]:
        raise ValidationError({"incident_datetime": "Incident cannot be after the registration time."})
    execute(
        """UPDATE complaint SET station_id=%s, title=%s, description=%s, category=%s, priority=%s,
                  incident_datetime=%s, incident_location=%s WHERE complaint_id=%s""",
        (clean["station_id"], clean["title"], clean["description"], clean["category"], clean["priority"],
         clean["incident_datetime"], clean["incident_location"], complaint_id))


# ----------------------------------------------------------------------
# Status workflow
# ----------------------------------------------------------------------
def update_status(complaint_id, data, acting_officer_id):
    complaint = get_complaint(complaint_id)
    f = Form(data)
    new_status = f.choice("new_status", "New status", C.STATUSES)
    remarks = f.text("remarks", "Remarks", required=new_status != "CLOSED", min_len=3, max_len=500)
    if new_status and new_status not in allowed_transitions(complaint["status"]):
        f.error("new_status", f"A case in {C.STATUSES[complaint['status']]} cannot move to "
                              f"{C.STATUSES.get(new_status, new_status)}.")
    closure = {}
    if new_status == "CLOSED":
        closure["closure_type"] = f.choice("closure_type", "Closure type", C.CLOSURE_TYPES)
        closure["closure_date"] = f.date("closure_date", "Closure date", not_future=True,
                                         not_before=complaint["registered_at"].date())
        closure["closure_remarks"] = f.text("closure_remarks", "Closure remarks", min_len=10, max_len=500)
        closure["closed_by"] = f.integer("closed_by", "Closing officer", min_value=1)
    f.raise_if_invalid()

    with transaction(remarks=remarks) as conn:
        # lock the row so two users cannot change the status at the same time
        current = scalar("SELECT status FROM complaint WHERE complaint_id = %s FOR UPDATE", (complaint_id,), conn=conn)
        if current != complaint["status"]:
            raise AppError("The case status was changed by someone else. Reload and try again.")
        if new_status == "CLOSED":
            execute("""UPDATE complaint SET status='CLOSED', closure_date=%s, closure_type=%s,
                              closure_remarks=%s, closed_by=%s WHERE complaint_id=%s""",
                    (closure["closure_date"], closure["closure_type"], closure["closure_remarks"],
                     closure["closed_by"], complaint_id), conn=conn)
            execute("""UPDATE assignment SET relieved_at = GREATEST(NOW(), assigned_at)
                        WHERE complaint_id = %s AND relieved_at IS NULL""", (complaint_id,), conn=conn)
        elif complaint["status"] == "CLOSED":  # re-open
            execute("""UPDATE complaint SET status=%s, closure_date=NULL, closure_type=NULL,
                              closure_remarks=NULL, closed_by=NULL WHERE complaint_id=%s""",
                    (new_status, complaint_id), conn=conn)
        else:
            execute("UPDATE complaint SET status=%s WHERE complaint_id=%s", (new_status, complaint_id), conn=conn)
    return new_status


# ----------------------------------------------------------------------
# Officer assignment
# ----------------------------------------------------------------------
def assign_officer(complaint_id, data, assigned_by):
    complaint = get_complaint(complaint_id)
    _require_open(complaint)
    f = Form(data)
    officer_id = f.integer("officer_id", "Officer", min_value=1)
    role = f.choice("assignment_role", "Role", C.ASSIGNMENT_ROLES)
    f.text("remarks", "Remarks", required=False, max_len=300)
    replace_lead = f.boolean("replace_lead")
    clean = f.raise_if_invalid()

    with transaction() as conn:
        if role == "LEAD":
            current_lead = query_one("""SELECT assignment_id, officer_id FROM assignment WHERE complaint_id=%s
                                         AND assignment_role='LEAD' AND relieved_at IS NULL FOR UPDATE""",
                                     (complaint_id,), conn=conn)
            if current_lead and current_lead["officer_id"] != officer_id:
                if not replace_lead:
                    raise AppError("This case already has an active LEAD officer. Tick 'Replace current lead' "
                                   "to hand over the case.")
                execute("UPDATE assignment SET relieved_at = NOW(), remarks = CONCAT_WS(' | ', remarks, 'Replaced as lead') "
                        "WHERE assignment_id = %s", (current_lead["assignment_id"],), conn=conn)
        # if the officer already has an active assignment with a different role, relieve it (role change)
        existing = query_one("""SELECT assignment_id, assignment_role FROM assignment WHERE complaint_id=%s
                                 AND officer_id=%s AND relieved_at IS NULL""", (complaint_id, officer_id), conn=conn)
        if existing:
            if existing["assignment_role"] == role:
                raise AppError("This officer is already assigned to the case with the same role.")
            execute("UPDATE assignment SET relieved_at = NOW() WHERE assignment_id = %s",
                    (existing["assignment_id"],), conn=conn)
        execute("""INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_by, remarks)
                   VALUES (%s, %s, %s, %s, %s)""",
                (complaint_id, officer_id, role, assigned_by, clean["remarks"]), conn=conn)


def relieve_assignment(complaint_id, assignment_id):
    row = query_one("SELECT * FROM assignment WHERE assignment_id = %s AND complaint_id = %s",
                    (assignment_id, complaint_id))
    if not row:
        raise AppError("Assignment not found.")
    if row["relieved_at"]:
        raise AppError("This officer has already been relieved.")
    execute("UPDATE assignment SET relieved_at = GREATEST(NOW(), assigned_at) WHERE assignment_id = %s",
            (assignment_id,))


# ----------------------------------------------------------------------
# Investigation activity
# ----------------------------------------------------------------------
def log_activity(complaint_id, data):
    complaint = get_complaint(complaint_id)
    _require_open(complaint)
    f = Form(data)
    f.integer("officer_id", "Officer", min_value=1)
    f.choice("activity_type", "Activity type", C.ACTIVITY_TYPES)
    f.datetime("activity_time", "Activity time", not_future=True, not_before=complaint["registered_at"])
    f.text("location", "Location", required=False, max_len=255)
    f.text("description", "Description", min_len=5, max_len=1000)
    f.text("outcome", "Outcome", required=False, max_len=500)
    clean = f.raise_if_invalid()
    return execute(
        """INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location,
                                               description, outcome) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (complaint_id, clean["officer_id"], clean["activity_type"], clean["activity_time"], clean["location"],
         clean["description"], clean["outcome"]))


# ----------------------------------------------------------------------
# Witnesses
# ----------------------------------------------------------------------
def add_witness(complaint_id, data):
    complaint = get_complaint(complaint_id)
    _require_open(complaint)
    f = Form(data)
    f.text("statement", "Statement", min_len=10, max_len=5000)
    f.datetime("statement_date", "Statement date/time", not_future=True, not_before=complaint["registered_at"])
    f.integer("recorded_by", "Recording officer", min_value=1)
    f.boolean("is_protected")
    errors = dict(f.errors)
    if (data.get("witness_mode") or "existing") == "new":
        errors.update(person_service.validate_person(data, prefix="w_").errors)
    if errors:
        raise ValidationError(errors)
    clean = f.clean
    with transaction() as conn:
        person_id = person_service.resolve_person(data, "witness_mode", "witness_person_id", "w_", conn)
        execute("""INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (complaint_id, person_id, clean["statement"], clean["statement_date"], clean["recorded_by"],
                 clean["is_protected"]), conn=conn)


def remove_witness(complaint_id, witness_id):
    _require_open(get_complaint(complaint_id))
    if not execute("DELETE FROM witness WHERE witness_id = %s AND complaint_id = %s", (witness_id, complaint_id)):
        raise AppError("Witness record not found.")


# ----------------------------------------------------------------------
# Accused & charges
# ----------------------------------------------------------------------
def add_accused(complaint_id, data):
    complaint = get_complaint(complaint_id)
    _require_open(complaint)
    f = Form(data)
    f.choice("accused_status", "Accused status", C.ACCUSED_STATUSES)
    f.text("accused_remarks", "Remarks", required=False, max_len=300)
    errors = dict(f.errors)
    if (data.get("accused_mode") or "existing") == "new":
        errors.update(person_service.validate_person(data, prefix="a_").errors)
    if errors:
        raise ValidationError(errors)
    clean = f.clean
    with transaction() as conn:
        person_id = person_service.resolve_person(data, "accused_mode", "accused_person_id", "a_", conn)
        execute("""INSERT INTO complaint_accused (complaint_id, person_id, accused_status, remarks)
                   VALUES (%s, %s, %s, %s)""",
                (complaint_id, person_id, clean["accused_status"], clean["accused_remarks"]), conn=conn)


def update_accused_status(complaint_id, person_id, data):
    f = Form(data)
    status = f.choice("accused_status", "Accused status", C.ACCUSED_STATUSES)
    f.raise_if_invalid()
    if not execute("UPDATE complaint_accused SET accused_status = %s WHERE complaint_id = %s AND person_id = %s",
                   (status, complaint_id, person_id)):
        raise AppError("Accused record not found or unchanged.")


def remove_accused(complaint_id, person_id):
    _require_open(get_complaint(complaint_id))
    if not execute("DELETE FROM complaint_accused WHERE complaint_id = %s AND person_id = %s",
                   (complaint_id, person_id)):
        raise AppError("Accused record not found.")


def add_charge(complaint_id, data, charged_by_default):
    complaint = get_complaint(complaint_id)
    _require_open(complaint)
    f = Form(data)
    f.integer("accused_person_id", "Accused", min_value=1)
    f.choice("act_name", "Act", C.ACTS)
    sec = f.text("section_code", "Section", max_len=20)
    if sec and not sec[0].isdigit():
        f.error("section_code", "Section must start with a number, e.g. 303(2).")
    f.text("offence_description", "Offence description", min_len=3, max_len=255)
    f.date("charged_on", "Charged on", not_future=True, not_before=complaint["registered_at"].date())
    f.integer("charged_by", "Charging officer", required=False)
    clean = f.raise_if_invalid()
    execute("""INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description,
                                   charged_on, charged_by) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (complaint_id, clean["accused_person_id"], clean["act_name"], clean["section_code"],
             clean["offence_description"], clean["charged_on"], clean["charged_by"] or charged_by_default))


def delete_charge(complaint_id, charge_id):
    complaint = get_complaint(complaint_id)
    if complaint["status"] not in ("UNDER_INVESTIGATION",):
        raise AppError("Charges can only be withdrawn before the case is charge-sheeted.")
    if not execute("DELETE FROM charge WHERE charge_id = %s AND complaint_id = %s", (charge_id, complaint_id)):
        raise AppError("Charge not found.")


# ----------------------------------------------------------------------
# Court references
# ----------------------------------------------------------------------
def _validate_court(f, filing_required=True):
    f.text("court_name", "Court name", min_len=3, max_len=150)
    f.choice("court_type", "Court type", C.COURT_TYPES)
    f.date("filing_date", "Filing date", required=filing_required, not_future=True)
    f.date("next_hearing_date", "Next hearing date", required=False)
    f.text("judge_name", "Judge", required=False, max_len=100)
    stage = f.choice("case_stage", "Stage", C.CASE_STAGES)
    verdict = f.choice("verdict", "Verdict", C.VERDICTS)
    if stage and verdict:
        if stage == "DISPOSED" and verdict == "PENDING":
            f.error("verdict", "Record the verdict for a disposed case.")
        if stage != "DISPOSED" and verdict != "PENDING":
            f.error("verdict", "A verdict can only be recorded when the stage is Disposed.")
    fd, nh = f.clean.get("filing_date"), f.clean.get("next_hearing_date")
    if fd and nh and nh < fd:
        f.error("next_hearing_date", "Next hearing cannot be before the filing date.")


def add_court_ref(complaint_id, data):
    complaint = get_complaint(complaint_id)
    f = Form(data)
    f.text("court_case_no", "Court case number", min_len=3, max_len=30)
    _validate_court(f)
    if f.clean.get("filing_date") and f.clean["filing_date"] < complaint["registered_at"].date():
        f.error("filing_date", "Filing date cannot be before the complaint registration.")
    clean = f.raise_if_invalid()
    execute("""INSERT INTO court_reference (complaint_id, court_case_no, court_name, court_type, filing_date,
                                            next_hearing_date, judge_name, case_stage, verdict)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (complaint_id, clean["court_case_no"].upper(), clean["court_name"], clean["court_type"],
             clean["filing_date"], clean["next_hearing_date"], clean["judge_name"], clean["case_stage"],
             clean["verdict"]))


def update_court_ref(complaint_id, court_ref_id, data):
    existing = query_one("SELECT * FROM court_reference WHERE court_ref_id=%s AND complaint_id=%s",
                         (court_ref_id, complaint_id))
    if not existing:
        raise AppError("Court reference not found.")
    data = dict(data)
    data.setdefault("filing_date", existing["filing_date"].isoformat())
    f = Form(data)
    _validate_court(f)
    clean = f.raise_if_invalid()
    execute("""UPDATE court_reference SET court_name=%s, court_type=%s, next_hearing_date=%s, judge_name=%s,
                      case_stage=%s, verdict=%s WHERE court_ref_id=%s""",
            (clean["court_name"], clean["court_type"], clean["next_hearing_date"], clean["judge_name"],
             clean["case_stage"], clean["verdict"], court_ref_id))
