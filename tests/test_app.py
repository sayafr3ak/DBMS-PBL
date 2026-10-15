"""
PCETS automated test-suite (functional + integrity + transaction tests).

Runs against a SEPARATE database `police_evidence_test` that is rebuilt from
the SQL scripts on every run, so the demo database is never touched.

    python -m unittest -v tests.test_app
"""
import os
import re
import sys
import unittest
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import setup_db                                   # noqa: E402
from police_app.app import create_app              # noqa: E402
from police_app.db import query, query_one, scalar  # noqa: E402
from police_app.services import integrity_service  # noqa: E402

TEST_DB = "police_evidence_test"
# PCETS_TEST_HOSTED=1 drops all triggers/functions after loading, to test "hosted mode"
# (MySQL services such as Clever Cloud DEV that refuse CREATE TRIGGER)
HOSTED = os.environ.get("PCETS_TEST_HOSTED") == "1"


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M")


class PCETSTestCase(unittest.TestCase):
    """Tests are numbered and run in order; later tests build on records created earlier."""

    @classmethod
    def setUpClass(cls):
        setup_db.setup(TEST_DB, quiet=True)
        if HOSTED:
            import mysql.connector
            from police_app.config import load_db_config
            cfg = dict(load_db_config(), database=TEST_DB)
            cn = mysql.connector.connect(**cfg, autocommit=True)
            cur = cn.cursor()
            cur.execute("SELECT trigger_name FROM information_schema.triggers WHERE trigger_schema=%s", (TEST_DB,))
            for (t,) in cur.fetchall():
                cur.execute(f"DROP TRIGGER `{t}`")
            cur.execute("SELECT routine_name FROM information_schema.routines WHERE routine_schema=%s "
                        "AND routine_type='FUNCTION'", (TEST_DB,))
            for (f,) in cur.fetchall():
                cur.execute(f"DROP FUNCTION `{f}`")
            cn.close()
        cls.app = create_app(database=TEST_DB, testing=True)
        cls.app.config["WTF_CSRF_DISABLED"] = True
        cls.state = {}

    # ---------------- helpers ----------------
    def client(self, user="vikram"):
        c = self.app.test_client()
        r = c.post("/switch-user", data={"username": user})
        self.assertEqual(r.status_code, 302)
        return c

    def q(self, sql, params=None):
        with self.app.test_request_context():
            return query(sql, params)

    def q1(self, sql, params=None):
        with self.app.test_request_context():
            return query_one(sql, params)

    def val(self, sql, params=None):
        with self.app.test_request_context():
            return scalar(sql, params)

    def why(self, c, r):
        """Readable failure context: flashed messages + field errors rendered on the page."""
        import html as _h
        page = r.data.decode(errors="ignore")
        found = re.findall(r'<div class="msg">(.*?)</div>', page, re.S)
        found += re.findall(r'<span class="err">.*?</svg>(.*?)</span>', page, re.S)
        return self.flashes(c) + " | " + " | ".join(_h.unescape(x.strip()) for x in found)

    def flashes(self, c):
        with c.session_transaction() as s:
            return " | ".join(m for _, m in s.get("_flashes", []))

    # =============== ACTING USER & SECURITY ===============
    def test_01_opens_without_login(self):
        r = self.app.test_client().get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Acting as", r.data)
        self.assertNotIn(b"Sign in", r.data)

    def test_02_default_user_is_admin(self):
        c = self.app.test_client()
        c.get("/")
        with c.session_transaction() as s:
            uid = s["user_id"]
        self.assertEqual(self.val("SELECT username FROM app_user WHERE user_id=%s", (uid,)), "admin")

    def test_03_switch_user_changes_role(self):
        c = self.client("anjali")
        self.assertIn(b"Anjali Kulkarni", c.get("/").data)
        r = c.post("/switch-user", data={"username": "nobody"})
        self.assertIn("Unknown or inactive user", self.flashes(c))

    def test_04_role_based_access(self):
        c = self.client("suresh")  # custodian
        self.assertEqual(c.get("/complaints/new").status_code, 403)
        self.assertEqual(c.get("/evidence/new").status_code, 200)
        self.assertEqual(c.get("/officers/new").status_code, 403)

    def test_05_csrf_protection(self):
        self.app.config["WTF_CSRF_DISABLED"] = False
        try:
            c = self.app.test_client()
            r = c.post("/switch-user", data={"username": "vikram"})
            self.assertEqual(r.status_code, 400)
        finally:
            self.app.config["WTF_CSRF_DISABLED"] = True

    # =============== COMPLAINT REGISTRATION ===============
    def test_06_register_complaint_new_person(self):
        c = self.client()
        persons_before = self.val("SELECT COUNT(*) FROM person")
        r = c.post("/complaints/new", data={
            "complainant_mode": "new", "p_full_name": "Test Complainant", "p_gender": "F", "p_phone": "9876500011",
            "p_address": "12 Test Lane, Pune", "p_id_proof_type": "AADHAAR", "p_id_proof_no": "234567890123",
            "title": "Laptop stolen from car", "description": "Car window smashed and laptop bag stolen from rear seat.",
            "category": "THEFT", "priority": "MEDIUM", "incident_datetime": fmt(datetime.now() - timedelta(hours=5)),
            "station_id": "1", "incident_location": "JM Road parking"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        cid = int(r.location.rstrip("/").split("/")[-1])
        row = self.q1("SELECT * FROM complaint WHERE complaint_id = %s", (cid,))
        self.assertRegex(row["complaint_no"], r"^CMP-\d{4}-\d{5}$")
        self.assertEqual(row["status"], "REGISTERED")
        self.assertEqual(self.val("SELECT COUNT(*) FROM person"), persons_before + 1)
        self.assertEqual(self.val("SELECT COUNT(*) FROM status_history WHERE complaint_id=%s", (cid,)), 1)
        self.state["cid"] = cid

    def test_07_register_with_lead_starts_investigation(self):
        c = self.client()
        r = c.post("/complaints/new", data={
            "complainant_mode": "existing", "complainant_id": "3", "title": "Cheque fraud at bank",
            "description": "Forged signature used to encash a cheque of Rs 40,000.", "category": "FRAUD",
            "priority": "HIGH", "incident_datetime": fmt(datetime.now() - timedelta(days=1)), "station_id": "1",
            "incident_location": "SBI branch, FC Road", "lead_officer_id": "2"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        cid = int(r.location.split("/")[-1])
        self.assertEqual(self.val("SELECT status FROM complaint WHERE complaint_id=%s", (cid,)), "UNDER_INVESTIGATION")
        self.assertEqual(self.val("SELECT COUNT(*) FROM assignment WHERE complaint_id=%s AND assignment_role='LEAD'", (cid,)), 1)
        self.assertEqual(self.val("SELECT COUNT(*) FROM status_history WHERE complaint_id=%s", (cid,)), 2)
        self.state["cid2"] = cid

    def test_08_registration_validation_errors(self):
        c = self.client()
        before = self.val("SELECT COUNT(*) FROM complaint")
        r = c.post("/complaints/new", data={"complainant_mode": "existing", "complainant_id": "1", "title": "",
                                            "description": "short", "category": "INVALID", "priority": "LOW",
                                            "incident_datetime": fmt(datetime.now() + timedelta(days=2)),
                                            "station_id": "1", "incident_location": "x"})
        self.assertEqual(r.status_code, 422)
        for msg in (b"Title is required", b"cannot be in the future", b"Invalid category"):
            self.assertIn(msg, r.data)
        self.assertEqual(self.val("SELECT COUNT(*) FROM complaint"), before)

    def test_09_invalid_phone_and_id_proof(self):
        c = self.client()
        r = c.post("/complaints/new", data={
            "complainant_mode": "new", "p_full_name": "Bad Phone", "p_gender": "M", "p_phone": "12345",
            "p_address": "Somewhere in Pune", "p_id_proof_type": "PAN", "p_id_proof_no": "1234",
            "title": "Test title here", "description": "A valid long description for the test.", "category": "THEFT",
            "priority": "LOW", "incident_datetime": fmt(datetime.now()), "station_id": "1", "incident_location": "Pune"})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"10-digit mobile", r.data)
        self.assertIn(b"Invalid Pan number", r.data)

    def test_10_transaction_rollback_on_failure(self):
        """New person is valid, but the complaint fails at the DB (unknown station) -> person must NOT be saved."""
        c = self.client()
        persons_before = self.val("SELECT COUNT(*) FROM person")
        r = c.post("/complaints/new", data={
            "complainant_mode": "new", "p_full_name": "Rollback Person", "p_gender": "M", "p_phone": "9876500099",
            "p_address": "Rollback Street, Pune", "title": "Rollback test complaint",
            "description": "This complaint references a station that does not exist.", "category": "OTHER",
            "priority": "LOW", "incident_datetime": fmt(datetime.now()), "station_id": "999", "incident_location": "Pune"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.val("SELECT COUNT(*) FROM person"), persons_before)
        self.assertIsNone(self.q1("SELECT person_id FROM person WHERE full_name = 'Rollback Person'"))

    # =============== OFFICER ASSIGNMENT ===============
    def test_11_assign_lead_and_support(self):
        c = self.client()
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/assign", data={"officer_id": "3", "assignment_role": "LEAD"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        r = c.post(f"/complaints/{cid}/assign", data={"officer_id": "15", "assignment_role": "FORENSIC"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.val("SELECT COUNT(*) FROM assignment WHERE complaint_id=%s AND relieved_at IS NULL", (cid,)), 2)

    def test_12_second_lead_rejected(self):
        c = self.client()
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/assign", data={"officer_id": "2", "assignment_role": "LEAD"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("already has an active LEAD", self.flashes(c) + r.data.decode())

    def test_13_replace_lead_in_one_transaction(self):
        c = self.client()
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/assign", data={"officer_id": "2", "assignment_role": "LEAD", "replace_lead": "1"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        leads = self.q("SELECT officer_id FROM assignment WHERE complaint_id=%s AND assignment_role='LEAD' AND relieved_at IS NULL", (cid,))
        self.assertEqual([l["officer_id"] for l in leads], [2])
        self.assertIsNotNone(self.val("SELECT relieved_at FROM assignment WHERE complaint_id=%s AND officer_id=3", (cid,)))

    def test_14_inactive_officer_rejected(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid']}/assign", data={"officer_id": "16", "assignment_role": "SUPPORT"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("Inactive officers cannot be assigned", r.data.decode() + self.flashes(c))

    # =============== STATUS + ACTIVITY ===============
    def test_15_start_investigation_and_log_activity(self):
        c = self.client()
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/status", data={"new_status": "UNDER_INVESTIGATION", "remarks": "Investigation started"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        r = c.post(f"/complaints/{cid}/activities", data={
            "officer_id": "2", "activity_type": "SITE_VISIT", "activity_time": fmt(datetime.now()),
            "location": "JM Road", "description": "Visited the parking lot and spoke to the attendant."})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        self.assertEqual(self.val("SELECT COUNT(*) FROM investigation_activity WHERE complaint_id=%s", (cid,)), 1)
        hist = self.q("SELECT changed_by, remarks FROM status_history WHERE complaint_id=%s ORDER BY history_id DESC LIMIT 1", (cid,))[0]
        self.assertEqual(hist["changed_by"], 1)          # vikram's officer id recorded in the audit trail
        self.assertEqual(hist["remarks"], "Investigation started")

    def test_16_activity_by_unassigned_officer_rejected(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid']}/activities", data={
            "officer_id": "9", "activity_type": "RAID", "activity_time": fmt(datetime.now()),
            "description": "Officer not on this case tries to log."})
        self.assertEqual(r.status_code, 422)
        self.assertIn("Only an officer assigned to this case", r.data.decode() + self.flashes(c))

    def test_17_activity_future_time_rejected(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid']}/activities", data={
            "officer_id": "2", "activity_type": "OTHER", "activity_time": fmt(datetime.now() + timedelta(days=1)),
            "description": "Future dated activity"})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"cannot be in the future", r.data)

    # =============== EVIDENCE & CUSTODY ===============
    def test_18_register_evidence_with_deposit(self):
        c = self.client("anjali")
        t0 = datetime.now() - timedelta(hours=2)
        r = c.post("/evidence/new", data={
            "complaint_id": str(self.state["cid"]), "category": "ELECTRONIC", "description": "Broken car window glass and laptop sleeve",
            "quantity": "2", "item_condition": "DAMAGED", "seal_no": "SL-TEST-0001", "collected_at": fmt(t0),
            "collected_by": "2", "collected_from": "JM Road parking", "deposit_now": "1", "custodian_id": "4",
            "deposit_at": fmt(t0 + timedelta(hours=1)), "storage_location": "Malkhana, Shivajinagar PS"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        eid = int(r.location.split("/")[-1])
        ev = self.q1("SELECT * FROM evidence_item WHERE evidence_id=%s", (eid,))
        self.assertRegex(ev["evidence_no"], r"^EVD-\d{4}-\d{5}$")
        chain = self.q("SELECT * FROM custody_log WHERE evidence_id=%s ORDER BY received_at", (eid,))
        self.assertEqual([x["purpose"] for x in chain], ["INITIAL_SEIZURE", "STORAGE"])
        self.assertEqual(chain[0]["released_at"], chain[1]["received_at"])     # no gap
        self.assertEqual(self.val("SELECT holder_id FROM v_evidence_location WHERE evidence_id=%s", (eid,)), 4)
        self.state["eid"] = eid

    def test_19_duplicate_seal_rejected(self):
        c = self.client("anjali")
        r = c.post("/evidence/new", data={
            "complaint_id": str(self.state["cid"]), "category": "OTHER", "description": "Another item same seal",
            "quantity": "1", "item_condition": "INTACT", "seal_no": "SL-TEST-0001", "collected_at": fmt(datetime.now()),
            "collected_by": "2", "collected_from": "JM Road"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("seal number is already used", r.data.decode() + self.flashes(c))

    def test_20_custody_transfer(self):
        c = self.client("suresh")
        eid = self.state["eid"]
        r = c.post(f"/evidence/{eid}/transfer", data={
            "to_officer_id": "15", "location": "RFSL Pune", "purpose": "FORENSIC_ANALYSIS",
            "transfer_at": fmt(datetime.now() - timedelta(minutes=10)), "seal_intact": "1", "remarks": "Letter 45/2026"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        chain = self.q("SELECT * FROM custody_log WHERE evidence_id=%s ORDER BY received_at", (eid,))
        self.assertEqual(len(chain), 3)
        self.assertEqual(chain[2]["from_officer_id"], 4)
        self.assertEqual(chain[1]["released_at"], chain[2]["received_at"])
        self.assertEqual(self.val("SELECT evidence_status FROM v_evidence_location WHERE evidence_id=%s", (eid,)), "IN_LAB")

    def test_21_transfer_backdated_rejected(self):
        c = self.client("suresh")
        r = c.post(f"/evidence/{self.state['eid']}/transfer", data={
            "to_officer_id": "4", "location": "Malkhana", "purpose": "STORAGE",
            "transfer_at": fmt(datetime.now() - timedelta(days=3)), "seal_intact": "1"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("Transfer time must be after", r.data.decode() + self.flashes(c))
        self.assertEqual(self.val("SELECT COUNT(*) FROM custody_log WHERE evidence_id=%s", (self.state["eid"],)), 3)

    def test_22_broken_seal_requires_remarks(self):
        c = self.client("suresh")
        r = c.post(f"/evidence/{self.state['eid']}/transfer", data={
            "to_officer_id": "4", "location": "Malkhana", "purpose": "STORAGE", "transfer_at": fmt(datetime.now())})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"remarks are mandatory when the seal is broken", r.data)

    def test_23_no_transfer_after_return(self):
        c = self.client("admin")
        r = c.post("/evidence/1/transfer", data={"to_officer_id": "4", "location": "Malkhana", "purpose": "STORAGE",
                                                  "transfer_at": fmt(datetime.now()), "seal_intact": "1"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("already been returned/disposed", r.data.decode() + self.flashes(c))

    @unittest.skipIf(HOSTED, "trigger-based rules are enforced by the app in hosted mode")
    def test_24_database_enforces_every_rule(self):
        with self.app.test_request_context():
            results = integrity_service.run_all()
        failed = [k for k, v in results.items() if not v["passed"]]
        self.assertEqual(failed, [], f"Rules not enforced: {failed}")
        self.assertGreaterEqual(len(results), 25)

    # =============== PEOPLE, CHARGES, COURT, CLOSURE ===============
    def test_25_add_witness_new_person(self):
        c = self.client("anjali")
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/witnesses", data={
            "witness_mode": "new", "w_full_name": "Parking Attendant", "w_gender": "M", "w_address": "JM Road, Pune",
            "statement": "I saw a man in a red cap break the window and run.", "statement_date": fmt(datetime.now()),
            "recorded_by": "2", "is_protected": "1"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        w = self.q1("SELECT * FROM v_case_witnesses WHERE complaint_id=%s", (cid,))
        self.assertEqual(w["witness_name"], "Parking Attendant")
        self.assertEqual(w["is_protected"], 1)
        self.state["witness_pid"] = w["person_id"]

    def test_26_witness_cannot_be_accused(self):
        c = self.client("anjali")
        r = c.post(f"/complaints/{self.state['cid']}/accused", data={
            "accused_mode": "existing", "accused_person_id": str(self.state["witness_pid"]), "accused_status": "SUSPECT"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("A witness cannot be accused", r.data.decode() + self.flashes(c))

    def test_27_add_accused_and_frame_charge(self):
        c = self.client("anjali")
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/accused", data={"accused_mode": "existing", "accused_person_id": "23",
                                                       "accused_status": "ARRESTED"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        r = c.post(f"/complaints/{cid}/charges", data={"accused_person_id": "23", "act_name": "BNS", "section_code": "303(2)",
                                                      "offence_description": "Theft from vehicle",
                                                      "charged_on": datetime.now().strftime("%Y-%m-%d"), "charged_by": "2"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        self.assertEqual(self.val("SELECT COUNT(*) FROM charge WHERE complaint_id=%s", (cid,)), 1)

    def test_28_charge_sheet_rules(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid2']}/status", data={"new_status": "CHARGE_SHEETED", "remarks": "test"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("without at least one charge", r.data.decode() + self.flashes(c))
        r = c.post(f"/complaints/{self.state['cid']}/status", data={"new_status": "CHARGE_SHEETED", "remarks": "Charge-sheet filed"})
        self.assertEqual(r.status_code, 302, self.why(c, r))

    def test_29_invalid_transition_rejected(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid']}/status", data={"new_status": "REGISTERED", "remarks": "go back"})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"cannot move to", r.data)

    def test_30_court_reference_and_in_court(self):
        c = self.client()
        cid = self.state["cid"]
        today = datetime.now().strftime("%Y-%m-%d")
        r = c.post(f"/complaints/{cid}/court", data={"court_case_no": "RCC-TEST-2026", "court_name": "JMFC Shivajinagar",
                                                    "court_type": "MAGISTRATE", "filing_date": today,
                                                    "case_stage": "FILED", "verdict": "PENDING"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        r = c.post(f"/complaints/{cid}/status", data={"new_status": "IN_COURT", "remarks": "Trial begins"})
        self.assertEqual(r.status_code, 302, self.why(c, r))

    def test_31_verdict_requires_disposed_stage(self):
        c = self.client()
        cid = self.state["cid"]
        ref = self.val("SELECT court_ref_id FROM court_reference WHERE complaint_id=%s", (cid,))
        r = c.post(f"/complaints/{cid}/court/{ref}", data={"court_name": "JMFC Shivajinagar", "court_type": "MAGISTRATE",
                                                          "case_stage": "HEARING", "verdict": "CONVICTED"})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"only be recorded when the stage is Disposed", r.data)

    def test_32_close_without_details_rejected(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid']}/status", data={"new_status": "CLOSED"})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"Select closure type", r.data)
        self.assertEqual(self.val("SELECT status FROM complaint WHERE complaint_id=%s", (self.state["cid"],)), "IN_COURT")

    def test_33_io_cannot_close(self):
        c = self.client("anjali")
        r = c.post(f"/complaints/{self.state['cid']}/status", data={"new_status": "CLOSED"})
        self.assertEqual(r.status_code, 403)

    def test_34_close_case_relieves_officers(self):
        c = self.client()
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/status", data={
            "new_status": "CLOSED", "closure_type": "CONVICTED", "closure_date": datetime.now().strftime("%Y-%m-%d"),
            "closure_remarks": "Accused convicted, sentenced to 1 year.", "closed_by": "1"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        row = self.q1("SELECT * FROM complaint WHERE complaint_id=%s", (cid,))
        self.assertEqual(row["status"], "CLOSED")
        self.assertEqual(row["closure_type"], "CONVICTED")
        self.assertEqual(self.val("SELECT COUNT(*) FROM assignment WHERE complaint_id=%s AND relieved_at IS NULL", (cid,)), 0)
        self.assertIn(cid, [r["complaint_id"] for r in self.q("SELECT complaint_id FROM v_closed_cases")])

    def test_35_no_activity_on_closed_case(self):
        c = self.client()
        r = c.post(f"/complaints/{self.state['cid']}/activities", data={
            "officer_id": "2", "activity_type": "OTHER", "activity_time": fmt(datetime.now()), "description": "After closure"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("closed", (r.data.decode() + self.flashes(c)).lower())

    def test_36_reopen_clears_closure(self):
        c = self.client()
        cid = self.state["cid"]
        r = c.post(f"/complaints/{cid}/status", data={"new_status": "UNDER_INVESTIGATION", "remarks": "New evidence surfaced"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        row = self.q1("SELECT status, closure_type, closed_by FROM complaint WHERE complaint_id=%s", (cid,))
        self.assertEqual((row["status"], row["closure_type"], row["closed_by"]), ("UNDER_INVESTIGATION", None, None))
        statuses = [h["new_status"] for h in self.q("SELECT new_status FROM status_history WHERE complaint_id=%s ORDER BY history_id", (cid,))]
        self.assertEqual(statuses, ["REGISTERED", "UNDER_INVESTIGATION", "CHARGE_SHEETED", "IN_COURT", "CLOSED", "UNDER_INVESTIGATION"])

    # =============== PERSONS & OFFICERS CRUD ===============
    def test_37_person_crud(self):
        c = self.client()
        r = c.post("/persons/new", data={"full_name": "Crud Person", "gender": "O", "address": "Baner, Pune",
                                         "phone": "9123456780", "id_proof_type": "PASSPORT", "id_proof_no": "z1234567"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        pid = int(r.location.split("/")[-1])
        self.assertEqual(self.val("SELECT id_proof_no FROM person WHERE person_id=%s", (pid,)), "Z1234567")
        r = c.post(f"/persons/{pid}/edit", data={"full_name": "Crud Person Updated", "gender": "O", "address": "Aundh, Pune"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.val("SELECT full_name FROM person WHERE person_id=%s", (pid,)), "Crud Person Updated")
        r = c.post(f"/persons/{pid}/delete")
        self.assertEqual(r.status_code, 302)
        self.assertIsNone(self.q1("SELECT person_id FROM person WHERE person_id=%s", (pid,)))

    def test_38_delete_referenced_person_blocked(self):
        c = self.client()
        c.post("/persons/1/delete")
        self.assertIn("referenced by other records", self.flashes(c))
        self.assertIsNotNone(self.q1("SELECT person_id FROM person WHERE person_id=1"))

    def test_39_officer_crud_and_rules(self):
        c = self.client("admin")
        r = c.post("/officers/new", data={"full_name": "New Officer", "badge_no": "BAD", "officer_rank": "Constable",
                                          "station_id": "1", "phone": "9000000001", "date_joined": "2020-01-01"})
        self.assertEqual(r.status_code, 422)
        self.assertIn(b"MH12-1234", r.data)
        r = c.post("/officers/new", data={"full_name": "New Officer", "badge_no": "mh12-7777", "officer_rank": "Constable",
                                          "station_id": "1", "phone": "9000000001", "date_joined": "2020-01-01"})
        self.assertEqual(r.status_code, 302, self.why(c, r))
        c.post("/officers/2/toggle")  # Anjali has active cases -> must be refused
        self.assertIn("still has", self.flashes(c))
        self.assertEqual(self.val("SELECT is_active FROM officer WHERE officer_id=2"), 1)

    # =============== SEARCH & REPORTS ===============
    def test_40_search(self):
        c = self.client()
        r = c.get("/search?q=CMP-2026-00004")
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.location.endswith("/complaints/4"))
        r = c.get("/search?q=Rahul")
        self.assertIn(b"Rahul Mehta", r.data)
        r = c.get("/complaints/?q=chain&status=UNDER_INVESTIGATION")
        self.assertIn(b"Gold chain snatched", r.data)

    def test_41_all_reports_and_csv(self):
        from police_app.services.report_service import REPORTS
        c = self.client()
        for key in REPORTS:
            self.assertEqual(c.get(f"/reports/{key}").status_code, 200, key)
            csv = c.get(f"/reports/{key}.csv")
            self.assertEqual(csv.status_code, 200)
            self.assertEqual(csv.mimetype, "text/csv")
        r = c.get("/reports/custody-history?evidence=1")
        self.assertIn(b"Return to owner", r.data)

    def test_42_pending_report_excludes_closed(self):
        pending = {r["complaint_no"] for r in self.q("SELECT complaint_no FROM v_pending_cases")}
        closed = {r["complaint_no"] for r in self.q("SELECT complaint_no FROM complaint WHERE status='CLOSED'")}
        self.assertTrue(pending.isdisjoint(closed))

    def test_43_custody_chain_integrity_audit(self):
        rows = self.q("""WITH chain AS (SELECT evidence_id, received_at, from_officer_id,
                              LAG(released_at) OVER (PARTITION BY evidence_id ORDER BY received_at) AS prev_rel,
                              LAG(to_officer_id) OVER (PARTITION BY evidence_id ORDER BY received_at) AS prev_to
                         FROM custody_log)
                         SELECT COUNT(*) AS broken FROM chain
                          WHERE NOT ((prev_rel IS NULL AND from_officer_id IS NULL)
                                     OR (prev_rel = received_at AND prev_to = from_officer_id))""")
        self.assertEqual(rows[0]["broken"], 0)

    @classmethod
    def tearDownClass(cls):
        pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
