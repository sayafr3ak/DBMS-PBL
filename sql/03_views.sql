-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  03 - Views used by the reports and the application
-- =====================================================================

-- ---------------------------------------------------------------------
-- v_case_summary : one row per complaint with the commonly needed joins
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_case_summary AS
SELECT  c.complaint_id,
        c.complaint_no,
        c.title,
        c.category,
        c.priority,
        c.status,
        c.incident_datetime,
        c.incident_location,
        c.registered_at,
        c.closure_date,
        s.station_id,
        s.station_name,
        p.person_id      AS complainant_id,
        p.full_name      AS complainant_name,
        p.phone          AS complainant_phone,
        la.officer_id    AS lead_officer_id,
        lo.full_name     AS lead_officer_name,
        DATEDIFF(COALESCE(c.closure_date, CURDATE()), DATE(c.registered_at)) AS age_days,
        (SELECT COUNT(*) FROM evidence_item e WHERE e.complaint_id = c.complaint_id) AS evidence_count,
        (SELECT COUNT(*) FROM witness w       WHERE w.complaint_id = c.complaint_id) AS witness_count
FROM complaint c
JOIN station s ON s.station_id = c.station_id
JOIN person  p ON p.person_id  = c.complainant_id
LEFT JOIN assignment la ON la.complaint_id = c.complaint_id
                         AND la.assignment_role = 'LEAD'
                         AND la.relieved_at IS NULL
LEFT JOIN officer lo ON lo.officer_id = la.officer_id;

-- ---------------------------------------------------------------------
-- REPORT 1 : v_pending_cases - every case that is not closed
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_pending_cases AS
SELECT  c.complaint_id,
        c.complaint_no,
        c.title,
        c.category,
        c.priority,
        c.status,
        s.station_name,
        p.full_name                                   AS complainant,
        COALESCE(lo.full_name, '-- Unassigned --')     AS lead_officer,
        DATE(c.registered_at)                          AS registered_on,
        DATEDIFF(CURDATE(), DATE(c.registered_at))     AS days_pending,
        (SELECT MAX(a.activity_time) FROM investigation_activity a
          WHERE a.complaint_id = c.complaint_id)       AS last_activity,
        (SELECT COUNT(*) FROM evidence_item e
          WHERE e.complaint_id = c.complaint_id)       AS evidence_items
FROM complaint c
JOIN station s ON s.station_id = c.station_id
JOIN person  p ON p.person_id  = c.complainant_id
LEFT JOIN assignment la ON la.complaint_id = c.complaint_id AND la.assignment_role = 'LEAD' AND la.relieved_at IS NULL
LEFT JOIN officer lo ON lo.officer_id = la.officer_id
WHERE c.status <> 'CLOSED';

-- ---------------------------------------------------------------------
-- REPORT 2 : v_officer_load - workload per officer
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_officer_load AS
SELECT  o.officer_id,
        o.badge_no,
        o.full_name,
        o.officer_rank,
        s.station_name,
        o.is_active,
        COUNT(DISTINCT CASE WHEN a.relieved_at IS NULL AND c.status <> 'CLOSED' THEN a.complaint_id END) AS active_cases,
        COUNT(DISTINCT CASE WHEN a.relieved_at IS NULL AND c.status <> 'CLOSED'
                             AND a.assignment_role = 'LEAD' THEN a.complaint_id END)                    AS lead_cases,
        COUNT(DISTINCT a.complaint_id)                                                                    AS total_cases_handled,
        (SELECT COUNT(*) FROM investigation_activity ia
          WHERE ia.officer_id = o.officer_id
            AND ia.activity_time >= CURDATE() - INTERVAL 30 DAY)                                          AS activities_30d,
        (SELECT COUNT(*) FROM custody_log cl
          WHERE cl.to_officer_id = o.officer_id AND cl.released_at IS NULL
            AND cl.purpose NOT IN ('RETURN_TO_OWNER','DISPOSAL'))                                          AS evidence_in_hand
FROM officer o
JOIN station s ON s.station_id = o.station_id
LEFT JOIN assignment a ON a.officer_id = o.officer_id
LEFT JOIN complaint  c ON c.complaint_id = a.complaint_id
GROUP BY o.officer_id, o.badge_no, o.full_name, o.officer_rank, s.station_name, o.is_active;

-- ---------------------------------------------------------------------
-- REPORT 3 : v_evidence_location - where every evidence item is now
-- (status is DERIVED from the purpose of the open custody period)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_evidence_location AS
SELECT  e.evidence_id,
        e.evidence_no,
        e.category,
        e.description,
        e.seal_no,
        c.complaint_id,
        c.complaint_no,
        c.status                                         AS case_status,
        o.officer_id                                     AS holder_id,
        o.full_name                                      AS current_holder,
        o.badge_no                                       AS holder_badge,
        cl.location                                      AS current_location,
        cl.purpose                                       AS current_purpose,
        CASE cl.purpose
             WHEN 'INITIAL_SEIZURE'   THEN 'WITH_SEIZING_OFFICER'
             WHEN 'STORAGE'           THEN 'IN_STORAGE'
             WHEN 'FORENSIC_ANALYSIS' THEN 'IN_LAB'
             WHEN 'INVESTIGATION'     THEN 'WITH_IO'
             WHEN 'COURT_PRODUCTION'  THEN 'IN_COURT'
             WHEN 'RETURN_TO_OWNER'   THEN 'RETURNED'
             WHEN 'DISPOSAL'          THEN 'DISPOSED'
        END                                              AS evidence_status,
        cl.received_at                                   AS held_since,
        DATEDIFF(CURDATE(), DATE(cl.received_at))        AS days_at_location,
        cl.seal_intact,
        (SELECT COUNT(*) FROM custody_log x WHERE x.evidence_id = e.evidence_id) - 1 AS transfer_count
FROM evidence_item e
JOIN complaint   c  ON c.complaint_id = e.complaint_id
JOIN custody_log cl ON cl.evidence_id = e.evidence_id AND cl.released_at IS NULL
JOIN officer     o  ON o.officer_id   = cl.to_officer_id;

-- ---------------------------------------------------------------------
-- REPORT 4 : v_custody_history - complete chain of custody
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_custody_history AS
SELECT  cl.custody_id,
        e.evidence_id,
        e.evidence_no,
        e.description                                     AS evidence_description,
        c.complaint_no,
        ROW_NUMBER() OVER (PARTITION BY cl.evidence_id ORDER BY cl.received_at) AS step_no,
        fo.full_name                                      AS handed_over_by,
        tof.full_name                                     AS received_by,
        tof.badge_no                                      AS receiver_badge,
        cl.location,
        cl.purpose,
        cl.received_at,
        cl.released_at,
        ROUND(TIMESTAMPDIFF(MINUTE, cl.received_at, COALESCE(cl.released_at, NOW())) / 60, 1) AS hours_held,
        cl.seal_intact,
        cl.remarks
FROM custody_log cl
JOIN evidence_item e   ON e.evidence_id  = cl.evidence_id
JOIN complaint     c   ON c.complaint_id = e.complaint_id
JOIN officer       tof ON tof.officer_id = cl.to_officer_id
LEFT JOIN officer  fo  ON fo.officer_id  = cl.from_officer_id;

-- ---------------------------------------------------------------------
-- REPORT 5 : v_case_witnesses
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_case_witnesses AS
SELECT  w.witness_id,
        c.complaint_id,
        c.complaint_no,
        c.title          AS complaint_title,
        p.person_id,
        p.full_name      AS witness_name,
        p.phone          AS witness_phone,
        p.address        AS witness_address,
        w.statement,
        w.statement_date,
        o.full_name      AS recorded_by,
        w.is_protected
FROM witness w
JOIN complaint c ON c.complaint_id = w.complaint_id
JOIN person    p ON p.person_id    = w.person_id
JOIN officer   o ON o.officer_id   = w.recorded_by;

-- ---------------------------------------------------------------------
-- REPORT 6 : v_case_timeline - every event of a case in one stream
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_case_timeline AS
SELECT sh.complaint_id, sh.changed_at AS event_time, 'STATUS' AS event_type,
       CASE WHEN sh.old_status IS NULL THEN 'Complaint registered'
            ELSE CONCAT('Status: ', REPLACE(sh.old_status,'_',' '), ' → ', REPLACE(sh.new_status,'_',' ')) END AS event_title,
       sh.remarks AS details, o.full_name AS actor
  FROM status_history sh LEFT JOIN officer o ON o.officer_id = sh.changed_by
UNION ALL
SELECT a.complaint_id, a.assigned_at, 'ASSIGNMENT',
       CONCAT(o.full_name, ' assigned as ', a.assignment_role), a.remarks, ob.full_name
  FROM assignment a JOIN officer o ON o.officer_id = a.officer_id
  LEFT JOIN officer ob ON ob.officer_id = a.assigned_by
UNION ALL
SELECT ia.complaint_id, ia.activity_time, 'ACTIVITY',
       REPLACE(ia.activity_type, '_', ' '), CONCAT(ia.description, COALESCE(CONCAT(' — Outcome: ', ia.outcome), '')), o.full_name
  FROM investigation_activity ia JOIN officer o ON o.officer_id = ia.officer_id
UNION ALL
SELECT e.complaint_id, e.collected_at, 'EVIDENCE',
       CONCAT('Evidence ', e.evidence_no, ' collected'), e.description, o.full_name
  FROM evidence_item e JOIN officer o ON o.officer_id = e.collected_by
UNION ALL
SELECT e.complaint_id, cl.received_at, 'CUSTODY',
       CONCAT(e.evidence_no, ' → ', o.full_name, ' (', REPLACE(cl.purpose,'_',' '), ')'), cl.location, fo.full_name
  FROM custody_log cl JOIN evidence_item e ON e.evidence_id = cl.evidence_id
  JOIN officer o ON o.officer_id = cl.to_officer_id
  LEFT JOIN officer fo ON fo.officer_id = cl.from_officer_id
 WHERE cl.purpose <> 'INITIAL_SEIZURE'
UNION ALL
SELECT w.complaint_id, w.statement_date, 'WITNESS',
       CONCAT('Statement of ', p.full_name), LEFT(w.statement, 200), o.full_name
  FROM witness w JOIN person p ON p.person_id = w.person_id JOIN officer o ON o.officer_id = w.recorded_by
UNION ALL
SELECT ch.complaint_id, CAST(ch.charged_on AS DATETIME), 'CHARGE',
       CONCAT(ch.act_name, ' ', ch.section_code, ' against ', p.full_name), ch.offence_description, o.full_name
  FROM charge ch JOIN person p ON p.person_id = ch.accused_person_id JOIN officer o ON o.officer_id = ch.charged_by
UNION ALL
SELECT cr.complaint_id, CAST(cr.filing_date AS DATETIME), 'COURT',
       CONCAT('Filed in ', cr.court_name), CONCAT('Case No. ', cr.court_case_no, ' · Stage: ', cr.case_stage,
                                                  ' · Verdict: ', cr.verdict), NULL
  FROM court_reference cr;

-- ---------------------------------------------------------------------
-- REPORT 7 : v_closed_cases - closures with outcome
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_closed_cases AS
SELECT  c.complaint_id,
        c.complaint_no,
        c.title,
        c.category,
        s.station_name,
        DATE(c.registered_at)                                AS registered_on,
        c.closure_date,
        DATEDIFF(c.closure_date, DATE(c.registered_at))      AS days_to_close,
        c.closure_type,
        c.closure_remarks,
        o.full_name                                          AS closed_by,
        (SELECT COUNT(*) FROM charge ch WHERE ch.complaint_id = c.complaint_id)        AS charges_framed,
        (SELECT cr.verdict FROM court_reference cr WHERE cr.complaint_id = c.complaint_id
          ORDER BY cr.filing_date DESC LIMIT 1)                                         AS court_verdict
FROM complaint c
JOIN station s ON s.station_id = c.station_id
JOIN officer o ON o.officer_id = c.closed_by
WHERE c.status = 'CLOSED';

-- ---------------------------------------------------------------------
-- Extra : v_upcoming_hearings
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_upcoming_hearings AS
SELECT  cr.court_ref_id, cr.court_case_no, cr.court_name, cr.court_type, cr.next_hearing_date,
        DATEDIFF(cr.next_hearing_date, CURDATE()) AS days_left, cr.case_stage, cr.judge_name,
        c.complaint_id, c.complaint_no, c.title
FROM court_reference cr
JOIN complaint c ON c.complaint_id = cr.complaint_id
WHERE cr.next_hearing_date >= CURDATE() AND cr.case_stage <> 'DISPOSED';
