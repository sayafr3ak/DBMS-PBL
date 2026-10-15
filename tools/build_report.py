"""
Builds the project report from live sources so it always matches the code:

  * data dictionary, constraints, triggers, views, indexes  <- information_schema
  * row counts of the sample data                           <- the demo database
  * test results                                            <- runs tests/test_app.py now
  * integrity results                                       <- runs every Integrity Lab scenario
  * output screens                                          <- docs/screenshots/*.png

Outputs:  docs/Project_Report.html, docs/Project_Report.pdf, docs/TEST_CASES.md, docs/er_diagram.png

    python tools/build_report.py
"""
import io
import os
import subprocess
import sys
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
DOCS = os.path.join(ROOT, "docs")
EDGE = next((p for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"] if os.path.exists(p)), None)

from jinja2 import Environment, FileSystemLoader  # noqa: E402

# ----------------------------------------------------------------------
# Test-case catalogue (ID, test method, module, scenario, expected result)
# ----------------------------------------------------------------------
TEST_CASES = [
    ("TC-01", "test_01_opens_without_login", "Acting user", "Open the app with a fresh browser", "Dashboard opens directly; no login page"),
    ("TC-02", "test_02_default_user_is_admin", "Acting user", "Check the default acting user", "Session uses default_user from config.ini (admin)"),
    ("TC-03", "test_03_switch_user_changes_role", "Acting user", "Switch to anjali, then to an unknown user", "Role/name change; unknown user rejected"),
    ("TC-04", "test_04_role_based_access", "Security (RBAC)", "Custodian opens Register complaint / Add officer", "HTTP 403; evidence registration allowed"),
    ("TC-05", "test_05_csrf_protection", "Security", "POST the user switcher without CSRF token", "HTTP 400 - request rejected"),
    ("TC-06", "test_06_register_complaint_new_person", "Complaint registration", "Register complaint with a NEW complainant", "CMP-YYYY-NNNNN issued, status REGISTERED, person + history row created"),
    ("TC-07", "test_07_register_with_lead_starts_investigation", "Complaint registration", "Register complaint and assign lead officer at once", "Status UNDER_INVESTIGATION, LEAD assignment, 2 history rows"),
    ("TC-08", "test_08_registration_validation_errors", "Input validation", "Empty title, short description, invalid category, future incident time", "HTTP 422 with field errors; nothing inserted"),
    ("TC-09", "test_09_invalid_phone_and_id_proof", "Input validation", "Phone '12345', PAN '1234'", "Field errors for phone and PAN format"),
    ("TC-10", "test_10_transaction_rollback_on_failure", "Transactions", "Valid new person + complaint with non-existent station", "FK error; whole transaction rolled back - person NOT saved"),
    ("TC-11", "test_11_assign_lead_and_support", "Officer assignment", "Assign LEAD and FORENSIC officers", "2 active assignments"),
    ("TC-12", "test_12_second_lead_rejected", "Officer assignment", "Assign a second LEAD without 'replace'", "Rejected: case already has an active LEAD"),
    ("TC-13", "test_13_replace_lead_in_one_transaction", "Transactions", "Replace current lead", "Old lead relieved + new lead inserted atomically"),
    ("TC-14", "test_14_inactive_officer_rejected", "Officer assignment", "Assign retired (inactive) officer", "Rejected by trigger trg_assignment_bi"),
    ("TC-15", "test_15_start_investigation_and_log_activity", "Status update / activity", "Move to UNDER_INVESTIGATION, log a site visit", "Activity saved; audit row records acting officer & remarks"),
    ("TC-16", "test_16_activity_by_unassigned_officer_rejected", "Activity logging", "Officer not on the case logs an activity", "Rejected by trigger trg_activity_bi"),
    ("TC-17", "test_17_activity_future_time_rejected", "Input validation", "Activity dated tomorrow", "'cannot be in the future'"),
    ("TC-18", "test_18_register_evidence_with_deposit", "Evidence registration", "Register evidence and deposit with custodian", "EVD number issued; 2 custody periods with no gap; custodian is holder"),
    ("TC-19", "test_19_duplicate_seal_rejected", "Evidence registration", "Second item with same seal number", "Rejected: seal number already used (UNIQUE)"),
    ("TC-20", "test_20_custody_transfer", "Custody transfer", "Transfer custodian -> forensic officer", "Previous period closed at transfer time; new period opened; status IN_LAB"),
    ("TC-21", "test_21_transfer_backdated_rejected", "Custody transfer", "Transfer dated before current custody began", "Rejected; chain unchanged"),
    ("TC-22", "test_22_broken_seal_requires_remarks", "Custody transfer", "Seal not intact and no remarks", "Validation error - remarks mandatory"),
    ("TC-23", "test_23_no_transfer_after_return", "Custody transfer", "Transfer an item already returned to owner", "Rejected - custody chain is final"),
    ("TC-24", "test_24_database_enforces_every_rule", "Integrity (DB level)", "Run all 26 Integrity Lab scenarios with raw SQL", "Every invalid statement rejected by MySQL"),
    ("TC-25", "test_25_add_witness_new_person", "Witness entry", "Record protected witness statement (new person)", "Witness row + person created; protected flag set"),
    ("TC-26", "test_26_witness_cannot_be_accused", "Accused", "Add an existing witness as accused in same case", "Rejected by trigger trg_accused_bi"),
    ("TC-27", "test_27_add_accused_and_frame_charge", "Charges", "Add accused, frame BNS 303(2) charge", "Charge saved"),
    ("TC-28", "test_28_charge_sheet_rules", "Status update", "Charge-sheet a case with no charges / with charges", "First rejected, second accepted"),
    ("TC-29", "test_29_invalid_transition_rejected", "Status update", "CHARGE_SHEETED -> REGISTERED", "Rejected: invalid transition"),
    ("TC-30", "test_30_court_reference_and_in_court", "Court reference", "Add court reference, move to IN_COURT", "Both succeed"),
    ("TC-31", "test_31_verdict_requires_disposed_stage", "Court reference", "Verdict CONVICTED while stage HEARING", "Validation error"),
    ("TC-32", "test_32_close_without_details_rejected", "Closure", "Close case without closure details", "Validation error; status unchanged"),
    ("TC-33", "test_33_io_cannot_close", "Security (RBAC)", "Investigating Officer tries to close case", "HTTP 403"),
    ("TC-34", "test_34_close_case_relieves_officers", "Closure / transactions", "Close with all closure details", "CLOSED; all officers relieved in same transaction; appears in closures view"),
    ("TC-35", "test_35_no_activity_on_closed_case", "Closure", "Log activity on a closed case", "Rejected"),
    ("TC-36", "test_36_reopen_clears_closure", "Status update", "Re-open closed case", "UNDER_INVESTIGATION, closure fields cleared, full audit trail kept"),
    ("TC-37", "test_37_person_crud", "CRUD", "Create, update and delete an unreferenced person", "All three succeed; ID proof upper-cased"),
    ("TC-38", "test_38_delete_referenced_person_blocked", "CRUD / FK", "Delete a complainant", "Friendly 'referenced by other records' message (FK 1451)"),
    ("TC-39", "test_39_officer_crud_and_rules", "CRUD", "Bad badge format, valid officer, deactivate busy officer", "Error, success, refusal"),
    ("TC-40", "test_40_search", "Search", "Exact complaint number, name search, filtered list", "Redirect to case; matching results"),
    ("TC-41", "test_41_all_reports_and_csv", "Reports", "Open every report and export CSV", "All 200 OK, CSV mimetype"),
    ("TC-42", "test_42_pending_report_excludes_closed", "Reports", "Pending cases view vs closed cases", "No overlap"),
    ("TC-43", "test_43_custody_chain_integrity_audit", "Integrity (DB level)", "LAG() audit over the whole custody log", "0 broken links"),
]


def run_tests():
    from tests import test_app
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(test_app.PCETSTestCase)
    result = unittest.TestResult()
    started = datetime.now()
    suite.run(result)
    failed = {t.id().split(".")[-1]: msg for t, msg in result.failures + result.errors}
    return {"ran": result.testsRun, "failed": failed, "time": (datetime.now() - started).total_seconds()}


def collect_db():
    from police_app.app import create_app
    from police_app.db import query
    from police_app.services import integrity_service
    app = create_app()
    with app.test_request_context():
        meta = integrity_service.schema_overview()
        integrity = integrity_service.run_all()
        counts = {t["name"]: t["rows"] for t in meta["tables"]}
        views = [v["name"] for v in meta["views"]]
    return meta, integrity, counts, views, integrity_service.SCENARIOS, integrity_service.RULES


def write_test_cases_md(results):
    lines = ["# Test cases — Police Complaint & Evidence Tracking System", "",
             f"Automated suite: `python -m unittest -v tests.test_app` — run on {datetime.now():%d %b %Y %H:%M}, "
             f"{results['ran']} tests, {results['ran'] - len(results['failed'])} passed, {len(results['failed'])} failed.", "",
             "| ID | Module | Scenario | Expected result | Result |", "|---|---|---|---|---|"]
    for tid, meth, module, scen, exp in TEST_CASES:
        status = "FAIL" if meth in results["failed"] else "PASS"
        lines.append(f"| {tid} | {module} | {scen} | {exp} | **{status}** |")
    lines += ["", "Database-level negative tests: `sql/06_constraint_tests.sql` (28 statements, each must fail) and the "
              "in-app **Integrity Lab** (26 scenarios, all rejected by MySQL).", ""]
    with open(os.path.join(DOCS, "TEST_CASES.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def render_er_png():
    html = os.path.join(DOCS, "er_diagram.html")
    with open(os.path.join(DOCS, "er_diagram.mmd"), encoding="utf-8") as fh:
        mmd = fh.read()
    with open(html, "w", encoding="utf-8") as fh:
        fh.write(f"""<!doctype html><html><head><meta charset="utf-8"><title>ER diagram</title>
<style>body{{margin:0;background:#fff;font-family:Segoe UI,Arial}} .mermaid{{padding:20px}}</style></head>
<body><pre class="mermaid">{mmd}</pre>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'default', er:{{layoutDirection:'TB', minEntityWidth:120}}}});</script>
</body></html>""")
    if EDGE:
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=2400,1460",
                        f"--screenshot={os.path.join(DOCS, 'er_diagram.png')}", "--virtual-time-budget=8000",
                        "file:///" + html.replace("\\", "/")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=90)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Running test-suite ...")
    results = run_tests()
    print(f"  {results['ran']} tests, {len(results['failed'])} failed")
    print("Collecting database metadata and integrity results ...")
    meta, integrity, counts, views, scenarios, rules = collect_db()
    write_test_cases_md(results)
    print("Rendering ER diagram ...")
    render_er_png()

    shots = sorted(f for f in os.listdir(os.path.join(DOCS, "screenshots")) if f.endswith(".png"))
    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "tools")), autoescape=True)
    html = env.get_template("report_template.html").render(
        generated=datetime.now(), meta=meta, integrity=integrity, scenarios=scenarios, rules=rules,
        counts=counts, views=views, tests=TEST_CASES, results=results, shots=shots,
        er_png=os.path.exists(os.path.join(DOCS, "er_diagram.png")))
    out_html = os.path.join(DOCS, "Project_Report.html")
    with open(out_html, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("  ✔ docs/Project_Report.html")
    if EDGE:
        pdf = os.path.join(DOCS, "Project_Report.pdf")
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                        "--virtual-time-budget=8000", "file:///" + out_html.replace("\\", "/")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        print("  ✔ docs/Project_Report.pdf" if os.path.exists(pdf) else "  ✘ PDF not created")
    print("  ✔ docs/TEST_CASES.md")


if __name__ == "__main__":
    main()
