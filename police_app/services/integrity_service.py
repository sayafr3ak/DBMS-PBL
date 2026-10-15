"""
Integrity Lab - live demonstration that the DATABASE (not just the app)
enforces the business rules. Each scenario runs deliberately invalid SQL
inside a transaction that is ALWAYS rolled back, and reports the error the
database raised.
"""
from collections import OrderedDict

import mysql.connector

from ..db import get_conn, query

SCENARIOS = OrderedDict()


def scenario(key, rule, title, explanation, statements, mechanism):
    SCENARIOS[key] = {"key": key, "rule": rule, "title": title, "explanation": explanation,
                      "statements": statements, "mechanism": mechanism}


RULES = OrderedDict([
    ("R1", "Unique complaint / evidence IDs"),
    ("R2", "Complete custody transfer"),
    ("R3", "Valid case status"),
    ("R4", "No overlapping custody"),
    ("R5", "Closure details required"),
    ("R6", "Other integrity rules"),
])

scenario("dup-complaint", "R1", "Duplicate complaint number",
         "Insert a complaint re-using CMP-2026-00001.",
         ["INSERT INTO complaint (complaint_no, station_id, complainant_id, title, description, category, "
          "incident_datetime, incident_location) VALUES ('CMP-2026-00001', 1, 1, 'Duplicate', "
          "'Duplicate number test', 'THEFT', '2026-10-01 10:00', 'Pune')"],
         "UNIQUE uq_complaint_no")
scenario("dup-evidence", "R1", "Duplicate evidence number",
         "Register an evidence item re-using EVD-2026-00001.",
         ["INSERT INTO evidence_item (evidence_no, complaint_id, category, description, collected_at, collected_by, "
          "collected_from) VALUES ('EVD-2026-00001', 5, 'OTHER', 'Duplicate evidence id', '2026-10-01 10:00', 10, 'Test')"],
         "UNIQUE uq_evidence_no")
scenario("bad-number", "R1", "Malformed complaint number",
         "Insert a complaint numbered 'FIR-12'.",
         ["INSERT INTO complaint (complaint_no, station_id, complainant_id, title, description, category, "
          "incident_datetime, incident_location) VALUES ('FIR-12', 1, 1, 'Bad', 'Bad number test', 'THEFT', "
          "'2026-10-01 10:00', 'Pune')"],
         "CHECK chk_complaint_no (REGEXP)")

scenario("transfer-no-from", "R2", "Transfer without handing officer",
         "Release EVD-2026-00009 and open a new STORAGE period with from_officer_id = NULL.",
         ["UPDATE custody_log SET released_at = NOW() - INTERVAL 1 MINUTE WHERE evidence_id = 9 AND released_at IS NULL",
          "INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at) "
          "VALUES (9, NULL, 11, 'Malkhana', 'STORAGE', NOW() - INTERVAL 1 MINUTE)"],
         "Trigger trg_custody_bi + CHECK chk_custody_from")
scenario("transfer-wrong-holder", "R2", "Handing officer is not the current custodian",
         "EVD-2026-00009 is held by Sneha Bhosale; try to transfer it 'from' Anjali Kulkarni.",
         ["UPDATE custody_log SET released_at = NOW() - INTERVAL 1 MINUTE WHERE evidence_id = 9 AND released_at IS NULL",
          "INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at) "
          "VALUES (9, 2, 11, 'Malkhana', 'STORAGE', NOW() - INTERVAL 1 MINUTE)"],
         "Trigger trg_custody_bi")
scenario("transfer-not-released", "R2", "New custody while current holder has not released",
         "Insert a new custody period for EVD-2026-00009 without closing the current one.",
         ["INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at) "
          "VALUES (9, 10, 11, 'Malkhana', 'STORAGE', NOW())"],
         "Trigger trg_custody_bi")
scenario("transfer-after-return", "R2", "Transfer after evidence returned to owner",
         "EVD-2026-00001 was returned to its owner; try to move it back to storage.",
         ["INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at) "
          "VALUES (1, 2, 4, 'Malkhana', 'STORAGE', NOW())"],
         "Trigger trg_custody_bi")

scenario("status-invalid", "R3", "Unknown status value",
         "Set the status of CMP-2026-00017 to 'PENDING'.",
         ["UPDATE complaint SET status = 'PENDING' WHERE complaint_id = 17"],
         "Trigger trg_complaint_bu + CHECK chk_complaint_status")
scenario("status-jump", "R3", "Illegal workflow jump",
         "Move CMP-2026-00017 directly from REGISTERED to IN_COURT.",
         ["UPDATE complaint SET status = 'IN_COURT' WHERE complaint_id = 17"],
         "Trigger trg_complaint_bu")
scenario("status-no-officer", "R3", "Investigate without an officer",
         "Start investigation on CMP-2026-00017, which has no assigned officer.",
         ["UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 17"],
         "Trigger trg_complaint_bu")
scenario("status-no-charge", "R3", "Charge-sheet without charges",
         "Mark CMP-2026-00005 CHARGE_SHEETED although no charge has been framed.",
         ["UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 5"],
         "Trigger trg_complaint_bu")

scenario("overlap-open", "R4", "Two current custodians",
         "Add a second open custody period for EVD-2026-00022 without closing the first.",
         ["INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at) "
          "VALUES (22, 13, 14, 'Cyber PS', 'INVESTIGATION', NOW())"],
         "Trigger trg_custody_bi + UNIQUE uq_custody_one_open")
scenario("overlap-backdated", "R4", "Back-dated overlapping period",
         "Insert a custody period for EVD-2026-00002 inside an already recorded period (March 2026).",
         ["UPDATE custody_log SET released_at = NOW() - INTERVAL 1 MINUTE WHERE evidence_id = 2 AND released_at IS NULL",
          "INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at) "
          "VALUES (2, 4, 3, 'FC Road', 'INVESTIGATION', '2026-03-05 15:00', '2026-03-05 15:30')"],
         "Trigger trg_custody_bi (interval overlap check)")
scenario("tamper-custody", "R4", "Tamper with a closed custody record",
         "Change the receiving officer of an already closed custody period.",
         ["UPDATE custody_log SET to_officer_id = 3 WHERE custody_id = 1"],
         "Trigger trg_custody_bu (append-only log)")
scenario("delete-custody", "R4", "Delete chain-of-custody records",
         "Delete the custody history of EVD-2026-00001.",
         ["DELETE FROM custody_log WHERE evidence_id = 1"],
         "Trigger trg_custody_bd")

scenario("close-no-details", "R5", "Close without closure details",
         "Set CMP-2026-00005 to CLOSED with no closure date/type/remarks/officer.",
         ["UPDATE complaint SET status = 'CLOSED' WHERE complaint_id = 5"],
         "CHECK chk_complaint_closure")
scenario("open-with-details", "R5", "Closure details on an open case",
         "Add a closure type to CMP-2026-00005 while it is still under investigation.",
         ["UPDATE complaint SET closure_type = 'SOLVED' WHERE complaint_id = 5"],
         "CHECK chk_complaint_closure")
scenario("close-before-reg", "R5", "Closure date before registration",
         "Close CMP-2026-00005 with closure date 01-01-2026.",
         ["UPDATE complaint SET status = 'CLOSED', closure_date = '2026-01-01', closure_type = 'SOLVED', "
          "closure_remarks = 'test', closed_by = 10 WHERE complaint_id = 5"],
         "CHECK chk_complaint_closuredate")

scenario("activity-unassigned", "R6", "Activity by an unassigned officer",
         "Anjali Kulkarni logs an activity on CMP-2026-00005 where she is not assigned.",
         ["INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, description) "
          "VALUES (5, 2, 'SITE_VISIT', NOW(), 'Unassigned officer visit')"],
         "Trigger trg_activity_bi")
scenario("assign-inactive", "R6", "Assign an inactive officer",
         "Assign retired constable Sandeep Kale to CMP-2026-00017.",
         ["INSERT INTO assignment (complaint_id, officer_id, assignment_role) VALUES (17, 16, 'SUPPORT')"],
         "Trigger trg_assignment_bi")
scenario("two-leads", "R6", "Two active LEAD officers",
         "Add Rajesh Pawar as a second LEAD on CMP-2026-00005.",
         ["INSERT INTO assignment (complaint_id, officer_id, assignment_role) VALUES (5, 9, 'LEAD')"],
         "UNIQUE uq_assignment_one_lead (generated column)")
scenario("charge-non-accused", "R6", "Charge a person who is not accused",
         "Frame a BNS 303 charge against the complainant of CMP-2026-00005.",
         ["INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, "
          "charged_on, charged_by) VALUES (5, 5, 'BNS', '303', 'Theft', CURDATE(), 10)"],
         "Composite FOREIGN KEY fk_charge_accused")
scenario("bad-aadhaar", "R6", "Invalid Aadhaar number",
         "Register a person with Aadhaar '12345'.",
         ["INSERT INTO person (full_name, gender, address, id_proof_type, id_proof_no) "
          "VALUES ('Test Person', 'M', 'Pune', 'AADHAAR', '12345')"],
         "CHECK chk_person_idformat")
scenario("delete-complaint", "R6", "Delete a complaint",
         "Delete CMP-2026-00020.",
         ["DELETE FROM complaint WHERE complaint_id = 20"],
         "Trigger trg_complaint_bd")
scenario("tamper-history", "R6", "Tamper with the status audit trail",
         "Edit a status history row.",
         ["UPDATE status_history SET remarks = 'tampered' WHERE history_id = 1"],
         "Trigger trg_history_bu")
scenario("delete-person", "R6", "Delete a person referenced by a complaint",
         "Delete complainant Rahul Mehta.",
         ["DELETE FROM person WHERE person_id = 1"],
         "FOREIGN KEY fk_complaint_complainant")


def run_scenario(key):
    sc = SCENARIOS[key]
    conn = get_conn()
    cur = conn.cursor()
    result = {"key": key, "passed": False, "error": None, "code": None}
    if conn.in_transaction:
        conn.rollback()
    try:
        conn.start_transaction()
        for stmt in sc["statements"]:
            cur.execute(stmt)
        result["error"] = "No error raised - the rule was NOT enforced!"
    except mysql.connector.Error as err:
        result.update(passed=True, error=err.msg, code=err.errno)
    finally:
        conn.rollback()           # never keep any change
        cur.close()
    return result


def run_all():
    return {k: run_scenario(k) for k in SCENARIOS}


# ----------------------------------------------------------------------
# Database explorer (information_schema)
# ----------------------------------------------------------------------
def schema_overview():
    db = query("SELECT DATABASE() AS db")[0]["db"]
    tables = query("""SELECT t.table_name AS name, t.table_comment AS comment,
                             (SELECT COUNT(*) FROM information_schema.columns c
                               WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS columns_count
                        FROM information_schema.tables t
                       WHERE t.table_schema = %s AND t.table_type = 'BASE TABLE' ORDER BY t.table_name""", (db,))
    for t in tables:
        t["rows"] = query(f"SELECT COUNT(*) AS n FROM `{t['name']}`")[0]["n"]
    columns = query("""SELECT table_name AS table_name, column_name AS column_name, column_type AS column_type,
                              is_nullable AS is_nullable, column_key AS column_key, column_default AS column_default,
                              extra AS extra
                         FROM information_schema.columns WHERE table_schema = %s
                        ORDER BY table_name, ordinal_position""", (db,))
    constraints = query("""SELECT tc.table_name AS table_name, tc.constraint_name AS constraint_name,
                                  tc.constraint_type AS constraint_type, cc.check_clause AS check_clause
                             FROM information_schema.table_constraints tc
                             LEFT JOIN information_schema.check_constraints cc
                               ON cc.constraint_schema = tc.constraint_schema AND cc.constraint_name = tc.constraint_name
                            WHERE tc.table_schema = %s
                            ORDER BY tc.table_name, FIELD(tc.constraint_type,'PRIMARY KEY','UNIQUE','FOREIGN KEY','CHECK'),
                                     tc.constraint_name""", (db,))
    fks = query("""SELECT table_name AS table_name, constraint_name AS constraint_name,
                          GROUP_CONCAT(column_name ORDER BY ordinal_position) AS cols,
                          referenced_table_name AS referenced_table_name, GROUP_CONCAT(referenced_column_name ORDER BY ordinal_position) AS ref_cols
                     FROM information_schema.key_column_usage
                    WHERE table_schema = %s AND referenced_table_name IS NOT NULL
                    GROUP BY table_name, constraint_name, referenced_table_name""", (db,))
    triggers = query("""SELECT trigger_name AS trigger_name, event_manipulation AS event_manipulation,
                                 event_object_table AS event_object_table, action_timing AS action_timing
                          FROM information_schema.triggers WHERE trigger_schema = %s
                         ORDER BY event_object_table, action_timing, event_manipulation""", (db,))
    views = query("""SELECT table_name AS name FROM information_schema.views WHERE table_schema = %s
                      ORDER BY table_name""", (db,))
    routines = query("""SELECT routine_name AS routine_name, routine_type AS routine_type FROM information_schema.routines WHERE routine_schema = %s
                         ORDER BY routine_type, routine_name""", (db,))
    indexes = query("""SELECT table_name AS table_name, index_name AS index_name, GROUP_CONCAT(column_name ORDER BY seq_in_index) AS cols,
                              MAX(non_unique) AS non_unique, MAX(index_type) AS index_type
                         FROM information_schema.statistics WHERE table_schema = %s
                        GROUP BY table_name, index_name ORDER BY table_name, index_name""", (db,))
    return {"db": db, "tables": tables, "columns": columns, "constraints": constraints, "fks": fks,
            "triggers": triggers, "views": views, "routines": routines, "indexes": indexes}
