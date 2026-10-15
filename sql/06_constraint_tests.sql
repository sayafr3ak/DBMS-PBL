-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  06 - Negative tests: every statement below MUST FAIL.
--  Run with:  mysql -u root -p --force police_evidence_db < 06_constraint_tests.sql
--  (--force continues after each expected error so all errors are shown)
--  Each test is wrapped in a transaction and rolled back.
-- =====================================================================
USE police_evidence_db;

-- ---------- RULE 1 : unique complaint / evidence IDs -----------------
-- T01 duplicate complaint number              -> ERROR 1062 Duplicate entry
START TRANSACTION;
INSERT INTO complaint (complaint_no, station_id, complainant_id, title, description, category, incident_datetime, incident_location)
VALUES ('CMP-2026-00001', 1, 1, 'Duplicate number test', 'Should be rejected', 'THEFT', '2026-10-01 10:00', 'Pune');
ROLLBACK;

-- T02 duplicate evidence number               -> ERROR 1062 Duplicate entry
START TRANSACTION;
INSERT INTO evidence_item (evidence_no, complaint_id, category, description, collected_at, collected_by, collected_from)
VALUES ('EVD-2026-00001', 5, 'OTHER', 'Duplicate evidence id', '2026-10-01 10:00', 10, 'Test');
ROLLBACK;

-- T03 badly formatted complaint number        -> ERROR 3819 Check constraint 'chk_complaint_no'
START TRANSACTION;
INSERT INTO complaint (complaint_no, station_id, complainant_id, title, description, category, incident_datetime, incident_location)
VALUES ('FIR-12', 1, 1, 'Bad number', 'Should be rejected', 'THEFT', '2026-10-01 10:00', 'Pune');
ROLLBACK;

-- ---------- RULE 2 : complete custody transfer -----------------------
-- T04 transfer without naming the handing officer -> ERROR 3819 chk_custody_from
START TRANSACTION;
UPDATE custody_log SET released_at = '2026-10-15 10:00' WHERE evidence_id = 9 AND released_at IS NULL;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at)
VALUES (9, NULL, 11, 'Malkhana', 'STORAGE', '2026-10-15 10:00');
ROLLBACK;

-- T05 handing officer is not the current custodian -> ERROR 1644 'Incomplete custody transfer ...'
START TRANSACTION;
UPDATE custody_log SET released_at = '2026-10-15 10:00' WHERE evidence_id = 9 AND released_at IS NULL;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at)
VALUES (9, 2, 11, 'Malkhana', 'STORAGE', '2026-10-15 10:00');
ROLLBACK;

-- T06 new custody while current holder has not released -> ERROR 1644 'Incomplete custody transfer ...'
START TRANSACTION;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at)
VALUES (9, 10, 11, 'Malkhana', 'STORAGE', '2026-10-15 10:00');
ROLLBACK;

-- T07 missing location (NOT NULL)              -> ERROR 1048 Column 'location' cannot be null
START TRANSACTION;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at)
VALUES (9, 10, 11, NULL, 'STORAGE', '2026-10-15 10:00');
ROLLBACK;

-- ---------- RULE 3 : valid case status -------------------------------
-- T08 unknown status value                     -> ERROR 3819 chk_complaint_status
START TRANSACTION;
UPDATE complaint SET status = 'PENDING' WHERE complaint_id = 17;
ROLLBACK;

-- T09 illegal workflow jump REGISTERED -> IN_COURT -> ERROR 1644 'Invalid status change ...'
START TRANSACTION;
UPDATE complaint SET status = 'IN_COURT' WHERE complaint_id = 17;
ROLLBACK;

-- T10 start investigation with no officer assigned -> ERROR 1644
START TRANSACTION;
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 17;
ROLLBACK;

-- T11 charge-sheet without any charge          -> ERROR 1644
START TRANSACTION;
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 5;
ROLLBACK;

-- ---------- RULE 4 : no overlapping custody --------------------------
-- T12 second OPEN custody row for the same item -> ERROR 1062 (uq_custody_one_open) / 1644
START TRANSACTION;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at)
VALUES (22, 13, 14, 'Cyber PS', 'INVESTIGATION', '2026-10-13 09:00');
ROLLBACK;

-- T13 back-dated transfer overlapping an earlier custody period -> ERROR 1644
START TRANSACTION;
UPDATE custody_log SET released_at = '2026-10-15 10:00' WHERE evidence_id = 2 AND released_at IS NULL;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at)
VALUES (2, 4, 3, 'FC Road', 'INVESTIGATION', '2026-03-05 15:00', '2026-03-05 15:30');
ROLLBACK;

-- T14 tampering with a closed custody record   -> ERROR 1644 'Closed custody records are immutable.'
START TRANSACTION;
UPDATE custody_log SET to_officer_id = 3 WHERE custody_id = 1;
ROLLBACK;

-- T15 deleting chain-of-custody records        -> ERROR 1644
START TRANSACTION;
DELETE FROM custody_log WHERE evidence_id = 1;
ROLLBACK;

-- T16 transfer after the item was returned to owner -> ERROR 1644
START TRANSACTION;
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at)
VALUES (1, 2, 4, 'Malkhana', 'STORAGE', '2026-10-01 10:00');
ROLLBACK;

-- ---------- RULE 5 : closure details required ------------------------
-- T17 close a case without closure details     -> ERROR 3819 chk_complaint_closure
START TRANSACTION;
UPDATE complaint SET status = 'CLOSED' WHERE complaint_id = 5;
ROLLBACK;

-- T18 closure details on an open case          -> ERROR 3819 chk_complaint_closure
START TRANSACTION;
UPDATE complaint SET closure_type = 'SOLVED' WHERE complaint_id = 5;
ROLLBACK;

-- T19 closure date before registration         -> ERROR 3819 chk_complaint_closuredate
START TRANSACTION;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-01-01', closure_type = 'SOLVED',
       closure_remarks = 'test', closed_by = 10 WHERE complaint_id = 5;
ROLLBACK;

-- ---------- Other integrity rules ------------------------------------
-- T20 activity by an officer not assigned to the case -> ERROR 1644
START TRANSACTION;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, description)
VALUES (5, 2, 'SITE_VISIT', '2026-10-10 10:00', 'Unassigned officer visit');
ROLLBACK;

-- T21 assigning an inactive officer            -> ERROR 1644
START TRANSACTION;
INSERT INTO assignment (complaint_id, officer_id, assignment_role) VALUES (17, 16, 'SUPPORT');
ROLLBACK;

-- T22 two active LEAD officers on one case     -> ERROR 1062 (uq_assignment_one_lead)
START TRANSACTION;
INSERT INTO assignment (complaint_id, officer_id, assignment_role) VALUES (5, 9, 'LEAD');
ROLLBACK;

-- T23 charge against a person who is not an accused -> ERROR 1452 (fk_charge_accused)
START TRANSACTION;
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by)
VALUES (5, 1, 'BNS', '303', 'Theft', '2026-10-10', 10);
ROLLBACK;

-- T24 accused added as witness in same case    -> ERROR 1644
START TRANSACTION;
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by)
VALUES (12, 27, 'I saw everything that happened that night.', '2026-10-10 10:00', 10);
ROLLBACK;

-- T25 invalid Aadhaar format                   -> ERROR 3819 chk_person_idformat
START TRANSACTION;
INSERT INTO person (full_name, gender, address, id_proof_type, id_proof_no) VALUES ('Test', 'M', 'Pune', 'AADHAAR', '12345');
ROLLBACK;

-- T26 deleting a complaint                     -> ERROR 1644
START TRANSACTION;
DELETE FROM complaint WHERE complaint_id = 20;
ROLLBACK;

-- T27 modifying the status audit trail         -> ERROR 1644
START TRANSACTION;
UPDATE status_history SET remarks = 'tampered' WHERE history_id = 1;
ROLLBACK;

-- T28 deleting a person referenced by a complaint -> ERROR 1451 (FK)
START TRANSACTION;
DELETE FROM person WHERE person_id = 1;
ROLLBACK;
