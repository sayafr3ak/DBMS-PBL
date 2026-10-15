"""
Captures the "output screens" for the project report using headless Microsoft Edge.

1. Start the app:   python run.py   (?as=<username> in a URL picks the acting user)
2. In another terminal:
       python tools/capture_screens.py
Screenshots are written to docs/screenshots/.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "screenshots")
BASE = "http://127.0.0.1:5000"
EDGE_PATHS = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]

SCREENS = [
    # file name, url, height
    ("02_dashboard.png", "/?as=vikram", 1500),
    ("03_complaints_list.png", "/complaints/?as=vikram", 1100),
    ("04_register_complaint.png", "/complaints/new?as=vikram", 1450),
    ("05_case_overview.png", "/complaints/2?as=vikram&tab=overview", 1250),
    ("06_case_officers.png", "/complaints/12?as=vikram&tab=officers", 900),
    ("07_case_investigation_diary.png", "/complaints/12?as=vikram&tab=activities", 1300),
    ("08_case_accused_witnesses.png", "/complaints/7?as=vikram&tab=people", 1000),
    ("09_case_charges_court.png", "/complaints/2?as=vikram&tab=legal", 1050),
    ("10_case_timeline.png", "/complaints/1?as=vikram&tab=timeline", 1600),
    ("11_case_status_audit.png", "/complaints/1?as=vikram&tab=history", 900),
    ("12_evidence_list.png", "/evidence/?as=vikram", 1150),
    ("13_register_evidence.png", "/evidence/new?as=suresh&complaint=5", 1350),
    ("14_chain_of_custody.png", "/evidence/1?as=suresh", 1450),
    ("15_evidence_in_lab.png", "/evidence/17?as=suresh", 1150),
    ("16_persons.png", "/persons/?as=vikram", 1100),
    ("17_person_involvement.png", "/persons/1?as=vikram", 800),
    ("18_officers.png", "/officers/?as=admin", 1250),
    ("19_officer_profile.png", "/officers/10?as=admin", 1150),
    ("20_reports_hub.png", "/reports/?as=vikram", 1150),
    ("21_report_pending_cases.png", "/reports/pending-cases?as=vikram", 1100),
    ("22_report_officer_load.png", "/reports/officer-load?as=vikram", 1450),
    ("23_report_evidence_location.png", "/reports/evidence-location?as=vikram", 1500),
    ("24_report_custody_history.png", "/reports/custody-history?as=vikram&evidence=11", 900),
    ("25_report_witnesses.png", "/reports/witnesses?as=vikram", 1300),
    ("26_report_case_timeline.png", "/reports/case-timeline?as=vikram&complaint=2", 1500),
    ("27_report_closures.png", "/reports/closures?as=vikram", 1150),
    ("28_report_custody_audit.png", "/reports/custody-audit?as=vikram", 1200),
    ("29_integrity_lab.png", "/integrity?as=vikram&run=all", 1700),
    ("30_database_explorer.png", "/explorer?as=admin", 1400),
    ("31_search.png", "/search?q=pune&as=vikram", 1000),
    ("32_case_file_print.png", "/complaints/2/print?as=vikram", 1700),
    ("33_custody_sheet_print.png", "/evidence/11/label?as=vikram", 900),
    ("34_access_denied.png", "/officers/new?as=anjali", 800),
]


def main():
    edge = next((p for p in EDGE_PATHS if os.path.exists(p)), None)
    if not edge:
        sys.exit("Microsoft Edge not found.")
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for name, url, height in SCREENS:
        if only and name not in only:
            continue
        path = os.path.join(OUT, name)
        cmd = [edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
               f"--window-size=1440,{height}", f"--screenshot={path}", "--virtual-time-budget=4000", BASE + url]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        print(("✔ " if os.path.exists(path) else "✘ ") + name)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
