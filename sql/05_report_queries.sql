-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  05 - Report & demonstration queries
--  Joins, sub-queries (nested / correlated / EXISTS), aggregation,
--  GROUP BY / HAVING, window functions, views and CTEs.
-- =====================================================================
USE police_evidence_db;

-- ---------------------------------------------------------------------
-- A. REQUIRED REPORTS (via views)
-- ---------------------------------------------------------------------
-- Q1  Pending cases, oldest first
SELECT complaint_no, title, status, priority, lead_officer, days_pending
  FROM v_pending_cases
 ORDER BY days_pending DESC;

-- Q2  Officer load (active officers only, busiest first)
SELECT full_name, officer_rank, station_name, active_cases, lead_cases, activities_30d, evidence_in_hand
  FROM v_officer_load
 WHERE is_active = 1
 ORDER BY active_cases DESC, lead_cases DESC;

-- Q3  Evidence location - everything currently in a forensic lab
SELECT evidence_no, complaint_no, description, current_holder, current_location, days_at_location
  FROM v_evidence_location
 WHERE evidence_status = 'IN_LAB'
 ORDER BY days_at_location DESC;

-- Q4  Custody history (chain of custody) of one evidence item
SELECT step_no, handed_over_by, received_by, location, purpose, received_at, released_at, hours_held
  FROM v_custody_history
 WHERE evidence_no = 'EVD-2026-00001'
 ORDER BY step_no;

-- Q5  Witnesses of a case
SELECT witness_name, witness_phone, statement_date, recorded_by,
       IF(is_protected = 1, 'PROTECTED', 'Normal') AS protection
  FROM v_case_witnesses
 WHERE complaint_no = 'CMP-2026-00007';

-- Q6  Complete case timeline
SELECT event_time, event_type, event_title, details, actor
  FROM v_case_timeline
 WHERE complaint_id = 2
 ORDER BY event_time;

-- Q7  Closures with time taken
SELECT complaint_no, title, closure_type, closure_date, days_to_close, closed_by, court_verdict
  FROM v_closed_cases
 ORDER BY closure_date DESC;

-- ---------------------------------------------------------------------
-- B. JOINS
-- ---------------------------------------------------------------------
-- Q8  INNER JOIN (5 tables): accused with charges, case and station
SELECT c.complaint_no, s.station_name, p.full_name AS accused, ca.accused_status,
       ch.act_name, ch.section_code, ch.offence_description
  FROM charge ch
  JOIN complaint_accused ca ON ca.complaint_id = ch.complaint_id AND ca.person_id = ch.accused_person_id
  JOIN person p             ON p.person_id     = ch.accused_person_id
  JOIN complaint c          ON c.complaint_id  = ch.complaint_id
  JOIN station s            ON s.station_id    = c.station_id
 ORDER BY c.complaint_no;

-- Q9  LEFT JOIN: every registered complaint and its (possibly missing) lead officer
SELECT c.complaint_no, c.title, c.status, o.full_name AS lead_officer
  FROM complaint c
  LEFT JOIN assignment a ON a.complaint_id = c.complaint_id AND a.assignment_role = 'LEAD' AND a.relieved_at IS NULL
  LEFT JOIN officer o    ON o.officer_id   = a.officer_id
 WHERE c.status <> 'CLOSED';

-- Q10 SELF-JOIN style: custody hand-overs between officers of DIFFERENT stations
SELECT e.evidence_no, fo.full_name AS from_officer, fs.station_code AS from_station,
       t.full_name AS to_officer, ts.station_code AS to_station, cl.received_at
  FROM custody_log cl
  JOIN evidence_item e ON e.evidence_id = cl.evidence_id
  JOIN officer fo ON fo.officer_id = cl.from_officer_id
  JOIN officer t  ON t.officer_id  = cl.to_officer_id
  JOIN station fs ON fs.station_id = fo.station_id
  JOIN station ts ON ts.station_id = t.station_id
 WHERE fo.station_id <> t.station_id;

-- Q11 Persons who appear in more than one role / case (complainant, accused, witness)
SELECT p.full_name, x.role, c.complaint_no
  FROM person p
  JOIN (SELECT complainant_id AS person_id, complaint_id, 'COMPLAINANT' AS role FROM complaint
        UNION ALL SELECT person_id, complaint_id, 'ACCUSED' FROM complaint_accused
        UNION ALL SELECT person_id, complaint_id, 'WITNESS' FROM witness) x ON x.person_id = p.person_id
  JOIN complaint c ON c.complaint_id = x.complaint_id
 WHERE p.person_id IN (SELECT complainant_id FROM complaint GROUP BY complainant_id HAVING COUNT(*) > 1)
 ORDER BY p.full_name;

-- ---------------------------------------------------------------------
-- C. AGGREGATION, GROUP BY, HAVING
-- ---------------------------------------------------------------------
-- Q12 Cases by status per station (pivot with conditional aggregation)
SELECT s.station_name,
       COUNT(*)                                     AS total,
       SUM(c.status = 'REGISTERED')                 AS registered,
       SUM(c.status = 'UNDER_INVESTIGATION')        AS under_investigation,
       SUM(c.status IN ('CHARGE_SHEETED','IN_COURT')) AS charge_sheeted_or_court,
       SUM(c.status = 'CLOSED')                     AS closed,
       ROUND(100 * SUM(c.status = 'CLOSED') / COUNT(*), 1) AS closure_rate_pct
  FROM complaint c JOIN station s ON s.station_id = c.station_id
 GROUP BY s.station_name
 ORDER BY total DESC;

-- Q13 Categories with more than one complaint and average closing time
SELECT category, COUNT(*) AS complaints,
       ROUND(AVG(CASE WHEN status = 'CLOSED' THEN DATEDIFF(closure_date, DATE(registered_at)) END), 1) AS avg_days_to_close
  FROM complaint
 GROUP BY category
HAVING COUNT(*) > 1
 ORDER BY complaints DESC;

-- Q14 Monthly registrations in 2026
SELECT DATE_FORMAT(registered_at, '%Y-%m') AS month, COUNT(*) AS registered,
       SUM(priority IN ('HIGH','CRITICAL')) AS high_priority_cases
  FROM complaint
 WHERE YEAR(registered_at) = 2026
 GROUP BY DATE_FORMAT(registered_at, '%Y-%m')
 ORDER BY month;

-- Q15 Evidence count by category and current status
SELECT category, evidence_status, COUNT(*) AS items
  FROM v_evidence_location
 GROUP BY category, evidence_status WITH ROLLUP;

-- ---------------------------------------------------------------------
-- D. NESTED / CORRELATED SUB-QUERIES
-- ---------------------------------------------------------------------
-- Q16 Officers handling more active cases than the average officer (nested)
SELECT full_name, active_cases
  FROM v_officer_load
 WHERE active_cases > (SELECT AVG(active_cases) FROM v_officer_load WHERE is_active = 1);

-- Q17 Open cases with NO investigation activity in the last 30 days (NOT EXISTS)
SELECT c.complaint_no, c.title, c.status
  FROM complaint c
 WHERE c.status <> 'CLOSED'
   AND NOT EXISTS (SELECT 1 FROM investigation_activity a
                    WHERE a.complaint_id = c.complaint_id
                      AND a.activity_time >= CURDATE() - INTERVAL 30 DAY);

-- Q18 Most recent activity of each case (correlated sub-query)
SELECT c.complaint_no, a.activity_type, a.activity_time, o.full_name
  FROM investigation_activity a
  JOIN complaint c ON c.complaint_id = a.complaint_id
  JOIN officer o   ON o.officer_id   = a.officer_id
 WHERE a.activity_time = (SELECT MAX(a2.activity_time) FROM investigation_activity a2
                           WHERE a2.complaint_id = a.complaint_id);

-- Q19 Evidence items that have visited a forensic lab at least once (IN)
SELECT evidence_no, description
  FROM evidence_item
 WHERE evidence_id IN (SELECT evidence_id FROM custody_log WHERE purpose = 'FORENSIC_ANALYSIS');

-- Q20 Complaints whose evidence count is above the overall average (derived table)
SELECT c.complaint_no, c.title, ev.cnt AS evidence_items
  FROM complaint c
  JOIN (SELECT complaint_id, COUNT(*) AS cnt FROM evidence_item GROUP BY complaint_id) ev
    ON ev.complaint_id = c.complaint_id
 WHERE ev.cnt > (SELECT COUNT(*) / COUNT(DISTINCT complaint_id) FROM evidence_item);

-- ---------------------------------------------------------------------
-- E. WINDOW FUNCTIONS & CTE
-- ---------------------------------------------------------------------
-- Q21 Rank officers by number of activities logged, within their station
SELECT s.station_name, o.full_name, COUNT(a.activity_id) AS activities,
       RANK() OVER (PARTITION BY s.station_id ORDER BY COUNT(a.activity_id) DESC) AS rank_in_station
  FROM officer o
  JOIN station s ON s.station_id = o.station_id
  LEFT JOIN investigation_activity a ON a.officer_id = o.officer_id
 GROUP BY s.station_id, s.station_name, o.officer_id, o.full_name;

-- Q22 Time spent in each status by every case (LEAD window function on audit trail)
WITH status_periods AS (
    SELECT complaint_id, new_status, changed_at,
           LEAD(changed_at) OVER (PARTITION BY complaint_id ORDER BY changed_at) AS next_change
      FROM status_history
)
SELECT c.complaint_no, sp.new_status AS status_name, sp.changed_at AS entered_at,
       DATEDIFF(COALESCE(sp.next_change, NOW()), sp.changed_at) AS days_in_status
  FROM status_periods sp JOIN complaint c ON c.complaint_id = sp.complaint_id
 ORDER BY c.complaint_no, sp.changed_at;

-- Q23 Chain-of-custody integrity audit: any gap or overlap between consecutive periods?
WITH chain AS (
    SELECT evidence_id, custody_id, received_at, released_at,
           LAG(released_at)  OVER (PARTITION BY evidence_id ORDER BY received_at) AS prev_released,
           LAG(to_officer_id) OVER (PARTITION BY evidence_id ORDER BY received_at) AS prev_holder,
           from_officer_id
      FROM custody_log
)
SELECT e.evidence_no, ch.custody_id,
       CASE WHEN ch.prev_released IS NULL AND ch.from_officer_id IS NULL THEN 'OK (seizure)'
            WHEN ch.prev_released = ch.received_at AND ch.prev_holder = ch.from_officer_id THEN 'OK'
            ELSE 'BROKEN CHAIN' END AS integrity
  FROM chain ch JOIN evidence_item e ON e.evidence_id = ch.evidence_id
 ORDER BY e.evidence_no, ch.received_at;

-- Q24 Upcoming court hearings in the next 30 days
SELECT court_case_no, court_name, next_hearing_date, days_left, complaint_no, title
  FROM v_upcoming_hearings
 WHERE days_left <= 30
 ORDER BY next_hearing_date;

-- Q25 Stored function usage
SELECT complaint_no, fn_case_age_days(complaint_id) AS age_days FROM complaint ORDER BY age_days DESC LIMIT 5;
