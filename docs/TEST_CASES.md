# Test cases — Police Complaint & Evidence Tracking System

Automated suite: `python -m unittest -v tests.test_app` — run on 16 Oct 2026 00:18, 43 tests, 43 passed, 0 failed.

| ID | Module | Scenario | Expected result | Result |
|---|---|---|---|---|
| TC-01 | Acting user | Open the app with a fresh browser | Dashboard opens directly; no login page | **PASS** |
| TC-02 | Acting user | Check the default acting user | Session uses default_user from config.ini (admin) | **PASS** |
| TC-03 | Acting user | Switch to anjali, then to an unknown user | Role/name change; unknown user rejected | **PASS** |
| TC-04 | Security (RBAC) | Custodian opens Register complaint / Add officer | HTTP 403; evidence registration allowed | **PASS** |
| TC-05 | Security | POST the user switcher without CSRF token | HTTP 400 - request rejected | **PASS** |
| TC-06 | Complaint registration | Register complaint with a NEW complainant | CMP-YYYY-NNNNN issued, status REGISTERED, person + history row created | **PASS** |
| TC-07 | Complaint registration | Register complaint and assign lead officer at once | Status UNDER_INVESTIGATION, LEAD assignment, 2 history rows | **PASS** |
| TC-08 | Input validation | Empty title, short description, invalid category, future incident time | HTTP 422 with field errors; nothing inserted | **PASS** |
| TC-09 | Input validation | Phone '12345', PAN '1234' | Field errors for phone and PAN format | **PASS** |
| TC-10 | Transactions | Valid new person + complaint with non-existent station | FK error; whole transaction rolled back - person NOT saved | **PASS** |
| TC-11 | Officer assignment | Assign LEAD and FORENSIC officers | 2 active assignments | **PASS** |
| TC-12 | Officer assignment | Assign a second LEAD without 'replace' | Rejected: case already has an active LEAD | **PASS** |
| TC-13 | Transactions | Replace current lead | Old lead relieved + new lead inserted atomically | **PASS** |
| TC-14 | Officer assignment | Assign retired (inactive) officer | Rejected by trigger trg_assignment_bi | **PASS** |
| TC-15 | Status update / activity | Move to UNDER_INVESTIGATION, log a site visit | Activity saved; audit row records acting officer & remarks | **PASS** |
| TC-16 | Activity logging | Officer not on the case logs an activity | Rejected by trigger trg_activity_bi | **PASS** |
| TC-17 | Input validation | Activity dated tomorrow | 'cannot be in the future' | **PASS** |
| TC-18 | Evidence registration | Register evidence and deposit with custodian | EVD number issued; 2 custody periods with no gap; custodian is holder | **PASS** |
| TC-19 | Evidence registration | Second item with same seal number | Rejected: seal number already used (UNIQUE) | **PASS** |
| TC-20 | Custody transfer | Transfer custodian -> forensic officer | Previous period closed at transfer time; new period opened; status IN_LAB | **PASS** |
| TC-21 | Custody transfer | Transfer dated before current custody began | Rejected; chain unchanged | **PASS** |
| TC-22 | Custody transfer | Seal not intact and no remarks | Validation error - remarks mandatory | **PASS** |
| TC-23 | Custody transfer | Transfer an item already returned to owner | Rejected - custody chain is final | **PASS** |
| TC-24 | Integrity (DB level) | Run all 26 Integrity Lab scenarios with raw SQL | Every invalid statement rejected by MySQL | **PASS** |
| TC-25 | Witness entry | Record protected witness statement (new person) | Witness row + person created; protected flag set | **PASS** |
| TC-26 | Accused | Add an existing witness as accused in same case | Rejected by trigger trg_accused_bi | **PASS** |
| TC-27 | Charges | Add accused, frame BNS 303(2) charge | Charge saved | **PASS** |
| TC-28 | Status update | Charge-sheet a case with no charges / with charges | First rejected, second accepted | **PASS** |
| TC-29 | Status update | CHARGE_SHEETED -> REGISTERED | Rejected: invalid transition | **PASS** |
| TC-30 | Court reference | Add court reference, move to IN_COURT | Both succeed | **PASS** |
| TC-31 | Court reference | Verdict CONVICTED while stage HEARING | Validation error | **PASS** |
| TC-32 | Closure | Close case without closure details | Validation error; status unchanged | **PASS** |
| TC-33 | Security (RBAC) | Investigating Officer tries to close case | HTTP 403 | **PASS** |
| TC-34 | Closure / transactions | Close with all closure details | CLOSED; all officers relieved in same transaction; appears in closures view | **PASS** |
| TC-35 | Closure | Log activity on a closed case | Rejected | **PASS** |
| TC-36 | Status update | Re-open closed case | UNDER_INVESTIGATION, closure fields cleared, full audit trail kept | **PASS** |
| TC-37 | CRUD | Create, update and delete an unreferenced person | All three succeed; ID proof upper-cased | **PASS** |
| TC-38 | CRUD / FK | Delete a complainant | Friendly 'referenced by other records' message (FK 1451) | **PASS** |
| TC-39 | CRUD | Bad badge format, valid officer, deactivate busy officer | Error, success, refusal | **PASS** |
| TC-40 | Search | Exact complaint number, name search, filtered list | Redirect to case; matching results | **PASS** |
| TC-41 | Reports | Open every report and export CSV | All 200 OK, CSV mimetype | **PASS** |
| TC-42 | Reports | Pending cases view vs closed cases | No overlap | **PASS** |
| TC-43 | Integrity (DB level) | LAG() audit over the whole custody log | 0 broken links | **PASS** |

Database-level negative tests: `sql/06_constraint_tests.sql` (28 statements, each must fail) and the in-app **Integrity Lab** (26 scenarios, all rejected by MySQL).
