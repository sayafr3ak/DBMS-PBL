-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  02 - Triggers, stored procedures & functions
--  Enforces the business rules that a CHECK constraint cannot express
--  (rules that need to look at other rows / other tables).
--
--  Session variables used by the application:
--    @current_officer_id : officer performing the action (audit trail)
--    @status_remarks     : remark recorded with a status change
--    @audit_time         : optional timestamp override (used by seed data)
-- =====================================================================

DROP TRIGGER IF EXISTS trg_complaint_bi;
DROP TRIGGER IF EXISTS trg_complaint_ai;
DROP TRIGGER IF EXISTS trg_complaint_bu;
DROP TRIGGER IF EXISTS trg_complaint_au;
DROP TRIGGER IF EXISTS trg_complaint_bd;
DROP TRIGGER IF EXISTS trg_assignment_bi;
DROP TRIGGER IF EXISTS trg_activity_bi;
DROP TRIGGER IF EXISTS trg_evidence_bi;
DROP TRIGGER IF EXISTS trg_custody_bi;
DROP TRIGGER IF EXISTS trg_custody_bu;
DROP TRIGGER IF EXISTS trg_custody_bd;
DROP TRIGGER IF EXISTS trg_witness_bi;
DROP TRIGGER IF EXISTS trg_accused_bi;
DROP TRIGGER IF EXISTS trg_charge_bi;
DROP TRIGGER IF EXISTS trg_court_bi;
DROP TRIGGER IF EXISTS trg_history_bu;
DROP TRIGGER IF EXISTS trg_history_bd;
DROP PROCEDURE IF EXISTS sp_transfer_custody;
DROP PROCEDURE IF EXISTS sp_close_complaint;
DROP FUNCTION IF EXISTS fn_current_holder;
DROP FUNCTION IF EXISTS fn_case_age_days;

DELIMITER $$

-- ---------------------------------------------------------------------
-- COMPLAINT
-- ---------------------------------------------------------------------
-- Generates the unique complaint number CMP-YYYY-NNNNN and forces every
-- new complaint to start in REGISTERED status.
CREATE TRIGGER trg_complaint_bi
BEFORE INSERT ON complaint
FOR EACH ROW
BEGIN
    DECLARE v_seq INT;
    IF NEW.registered_at IS NULL THEN
        SET NEW.registered_at = NOW();
    END IF;
    -- forms work at minute precision, so the stored timestamp is truncated to the minute
    SET NEW.registered_at = NEW.registered_at - INTERVAL SECOND(NEW.registered_at) SECOND;
    IF NEW.status <> 'REGISTERED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A new complaint must start with status REGISTERED.';
    END IF;
    IF NEW.complaint_no IS NULL OR NEW.complaint_no = '' THEN
        SELECT COALESCE(MAX(CAST(SUBSTRING(complaint_no, 10) AS UNSIGNED)), 0) + 1
          INTO v_seq
          FROM complaint
         WHERE complaint_no LIKE CONCAT('CMP-', YEAR(NEW.registered_at), '-%');
        SET NEW.complaint_no = CONCAT('CMP-', YEAR(NEW.registered_at), '-', LPAD(v_seq, 5, '0'));
    END IF;
END$$

-- First entry of the status history
CREATE TRIGGER trg_complaint_ai
AFTER INSERT ON complaint
FOR EACH ROW
BEGIN
    INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, changed_at, remarks)
    VALUES (NEW.complaint_id, NULL, 'REGISTERED', NEW.registered_by, NEW.registered_at,
            'Complaint registered');
END$$

-- BUSINESS RULE: valid case status transitions (workflow)
--   REGISTERED          -> UNDER_INVESTIGATION | CLOSED
--   UNDER_INVESTIGATION -> CHARGE_SHEETED      | CLOSED
--   CHARGE_SHEETED      -> IN_COURT            | CLOSED
--   IN_COURT            -> CLOSED
--   CLOSED              -> UNDER_INVESTIGATION (re-open)
CREATE TRIGGER trg_complaint_bu
BEFORE UPDATE ON complaint
FOR EACH ROW
BEGIN
    DECLARE v_msg VARCHAR(255);
    DECLARE v_cnt INT;

    IF NEW.complaint_no <> OLD.complaint_no THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Complaint number cannot be changed once issued.';
    END IF;

    IF NEW.status <> OLD.status THEN
        IF NOT (
               (OLD.status = 'REGISTERED'          AND NEW.status IN ('UNDER_INVESTIGATION','CLOSED'))
            OR (OLD.status = 'UNDER_INVESTIGATION' AND NEW.status IN ('CHARGE_SHEETED','CLOSED'))
            OR (OLD.status = 'CHARGE_SHEETED'      AND NEW.status IN ('IN_COURT','CLOSED'))
            OR (OLD.status = 'IN_COURT'            AND NEW.status = 'CLOSED')
            OR (OLD.status = 'CLOSED'              AND NEW.status = 'UNDER_INVESTIGATION')
        ) THEN
            SET v_msg = CONCAT('Invalid status change: ', OLD.status, ' -> ', NEW.status, '.');
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
        END IF;

        IF OLD.status = 'REGISTERED' AND NEW.status = 'UNDER_INVESTIGATION' THEN
            SELECT COUNT(*) INTO v_cnt FROM assignment
             WHERE complaint_id = NEW.complaint_id AND relieved_at IS NULL;
            IF v_cnt = 0 THEN
                SIGNAL SQLSTATE '45000'
                   SET MESSAGE_TEXT = 'Assign at least one officer before starting the investigation.';
            END IF;
        END IF;

        IF NEW.status = 'CHARGE_SHEETED' THEN
            SELECT COUNT(*) INTO v_cnt FROM charge WHERE complaint_id = NEW.complaint_id;
            IF v_cnt = 0 THEN
                SIGNAL SQLSTATE '45000'
                   SET MESSAGE_TEXT = 'A case cannot be charge-sheeted without at least one charge.';
            END IF;
        END IF;

        IF NEW.status = 'IN_COURT' THEN
            SELECT COUNT(*) INTO v_cnt FROM court_reference WHERE complaint_id = NEW.complaint_id;
            IF v_cnt = 0 THEN
                SIGNAL SQLSTATE '45000'
                   SET MESSAGE_TEXT = 'Add a court reference before moving the case to IN_COURT.';
            END IF;
        END IF;
    ELSEIF OLD.status = 'CLOSED' AND (NEW.title <> OLD.title OR NEW.description <> OLD.description
                                      OR NEW.category <> OLD.category OR NEW.incident_datetime <> OLD.incident_datetime) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A closed complaint cannot be edited. Re-open it first.';
    END IF;
END$$

-- Audit trail: every status change is written to STATUS_HISTORY
CREATE TRIGGER trg_complaint_au
AFTER UPDATE ON complaint
FOR EACH ROW
BEGIN
    IF NEW.status <> OLD.status THEN
        INSERT INTO status_history (complaint_id, old_status, new_status, changed_by, changed_at, remarks)
        VALUES (NEW.complaint_id, OLD.status, NEW.status,
                COALESCE(@current_officer_id, NEW.closed_by),
                COALESCE(@audit_time, NOW()),
                COALESCE(@status_remarks,
                         IF(NEW.status = 'CLOSED', NEW.closure_remarks, CONCAT('Status changed to ', NEW.status))));
    END IF;
END$$

CREATE TRIGGER trg_complaint_bd
BEFORE DELETE ON complaint
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000'
       SET MESSAGE_TEXT = 'Complaints are permanent records and cannot be deleted. Close the case instead.';
END$$

-- ---------------------------------------------------------------------
-- ASSIGNMENT
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_assignment_bi
BEFORE INSERT ON assignment
FOR EACH ROW
BEGIN
    DECLARE v_active TINYINT;
    DECLARE v_status VARCHAR(25);
    DECLARE v_reg DATETIME;

    SET NEW.assigned_at = NEW.assigned_at - INTERVAL SECOND(NEW.assigned_at) SECOND;
    SELECT is_active INTO v_active FROM officer WHERE officer_id = NEW.officer_id;
    IF v_active = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Inactive officers cannot be assigned to a case.';
    END IF;

    SELECT status, registered_at INTO v_status, v_reg FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status = 'CLOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Officers cannot be assigned to a closed case.';
    END IF;
    IF NEW.assigned_at < v_reg THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Assignment time cannot be before the complaint was registered.';
    END IF;
END$$

-- ---------------------------------------------------------------------
-- INVESTIGATION ACTIVITY
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_activity_bi
BEFORE INSERT ON investigation_activity
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(25);
    DECLARE v_reg DATETIME;
    DECLARE v_cnt INT;

    SELECT status, registered_at INTO v_status, v_reg FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status = 'CLOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Activities cannot be logged on a closed case.';
    END IF;
    IF NEW.activity_time < v_reg THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Activity time cannot be before the complaint registration.';
    END IF;
    IF NEW.activity_time > NOW() + INTERVAL 5 MINUTE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Activity time cannot be in the future.';
    END IF;

    -- the officer must have been assigned to the case at the time of the activity
    SELECT COUNT(*) INTO v_cnt FROM assignment
     WHERE complaint_id = NEW.complaint_id
       AND officer_id   = NEW.officer_id
       AND assigned_at <= NEW.activity_time
       AND (relieved_at IS NULL OR relieved_at >= NEW.activity_time);
    IF v_cnt = 0 THEN
        SIGNAL SQLSTATE '45000'
           SET MESSAGE_TEXT = 'Only an officer assigned to this case (at that time) can log an activity.';
    END IF;
END$$

-- ---------------------------------------------------------------------
-- EVIDENCE ITEM
-- ---------------------------------------------------------------------
-- Generates the unique evidence number EVD-YYYY-NNNNN
CREATE TRIGGER trg_evidence_bi
BEFORE INSERT ON evidence_item
FOR EACH ROW
BEGIN
    DECLARE v_seq INT;
    DECLARE v_status VARCHAR(25);
    DECLARE v_incident DATETIME;
    DECLARE v_active TINYINT;

    SELECT status, incident_datetime INTO v_status, v_incident FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status = 'CLOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Evidence cannot be registered against a closed case.';
    END IF;
    IF NEW.collected_at < v_incident THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Evidence cannot be collected before the incident occurred.';
    END IF;
    IF NEW.collected_at > NOW() + INTERVAL 5 MINUTE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Collection time cannot be in the future.';
    END IF;
    SELECT is_active INTO v_active FROM officer WHERE officer_id = NEW.collected_by;
    IF v_active = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Collecting officer is not active.';
    END IF;

    IF NEW.registered_at IS NULL THEN
        SET NEW.registered_at = NOW();
    END IF;
    IF NEW.evidence_no IS NULL OR NEW.evidence_no = '' THEN
        SELECT COALESCE(MAX(CAST(SUBSTRING(evidence_no, 10) AS UNSIGNED)), 0) + 1
          INTO v_seq
          FROM evidence_item
         WHERE evidence_no LIKE CONCAT('EVD-', YEAR(NEW.collected_at), '-%');
        SET NEW.evidence_no = CONCAT('EVD-', YEAR(NEW.collected_at), '-', LPAD(v_seq, 5, '0'));
    END IF;
END$$

-- ---------------------------------------------------------------------
-- CUSTODY LOG  (chain of custody)
-- ---------------------------------------------------------------------
-- BUSINESS RULES:
--   * complete custody transfer: handing officer = current holder and the
--     new period starts exactly when the previous one was released (no gap)
--   * no overlapping custody periods for the same evidence item
--   * nothing can follow a RETURN_TO_OWNER / DISPOSAL entry
CREATE TRIGGER trg_custody_bi
BEFORE INSERT ON custody_log
FOR EACH ROW
BEGIN
    DECLARE v_rows INT;
    DECLARE v_last_to INT;
    DECLARE v_last_released DATETIME;
    DECLARE v_last_purpose VARCHAR(20);
    DECLARE v_overlap INT;
    DECLARE v_collected DATETIME;
    DECLARE v_active TINYINT;

    SELECT is_active INTO v_active FROM officer WHERE officer_id = NEW.to_officer_id;
    IF v_active = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Custody cannot be given to an inactive officer.';
    END IF;

    SELECT collected_at INTO v_collected FROM evidence_item WHERE evidence_id = NEW.evidence_id;
    IF NEW.received_at < v_collected THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Custody cannot start before the evidence was collected.';
    END IF;
    IF NEW.received_at > NOW() + INTERVAL 5 MINUTE THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Custody transfer time cannot be in the future.';
    END IF;

    SELECT COUNT(*) INTO v_rows FROM custody_log WHERE evidence_id = NEW.evidence_id;

    IF v_rows = 0 THEN
        IF NEW.purpose <> 'INITIAL_SEIZURE' THEN
            SIGNAL SQLSTATE '45000'
               SET MESSAGE_TEXT = 'The first custody entry of an evidence item must be INITIAL_SEIZURE.';
        END IF;
    ELSE
        IF NEW.purpose = 'INITIAL_SEIZURE' THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This evidence item already has an initial seizure entry.';
        END IF;

        SELECT to_officer_id, released_at, purpose
          INTO v_last_to, v_last_released, v_last_purpose
          FROM custody_log
         WHERE evidence_id = NEW.evidence_id
         ORDER BY received_at DESC, custody_id DESC
         LIMIT 1;

        IF v_last_purpose IN ('RETURN_TO_OWNER','DISPOSAL') THEN
            SIGNAL SQLSTATE '45000'
               SET MESSAGE_TEXT = 'Evidence has already been returned/disposed - the custody chain is final.';
        END IF;
        IF NEW.from_officer_id IS NULL OR NEW.from_officer_id <> v_last_to THEN
            SIGNAL SQLSTATE '45000'
               SET MESSAGE_TEXT = 'Incomplete custody transfer: the handing officer is not the current custodian.';
        END IF;
        IF v_last_released IS NULL THEN
            SIGNAL SQLSTATE '45000'
               SET MESSAGE_TEXT = 'Incomplete custody transfer: the current custodian has not released the item.';
        END IF;
        IF NEW.received_at <> v_last_released THEN
            SIGNAL SQLSTATE '45000'
               SET MESSAGE_TEXT = 'Custody gap/overlap: new custody must start exactly when the previous custody ended.';
        END IF;
    END IF;

    -- no overlapping custody periods (half-open intervals [received, released))
    SELECT COUNT(*) INTO v_overlap FROM custody_log
     WHERE evidence_id = NEW.evidence_id
       AND NEW.received_at < COALESCE(released_at, '9999-12-31 23:59:59')
       AND COALESCE(NEW.released_at, '9999-12-31 23:59:59') > received_at;
    IF v_overlap > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Overlapping custody period for this evidence item.';
    END IF;
END$$

-- Custody rows are append-only: the only allowed change is closing an open
-- period (setting released_at once).
CREATE TRIGGER trg_custody_bu
BEFORE UPDATE ON custody_log
FOR EACH ROW
BEGIN
    IF OLD.released_at IS NOT NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Closed custody records are immutable.';
    END IF;
    IF NEW.evidence_id <> OLD.evidence_id OR NEW.to_officer_id <> OLD.to_officer_id
       OR NOT (NEW.from_officer_id <=> OLD.from_officer_id) OR NEW.received_at <> OLD.received_at
       OR NEW.purpose <> OLD.purpose OR NEW.location <> OLD.location THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Custody records are append-only; only the release time can be set.';
    END IF;
    IF OLD.purpose IN ('RETURN_TO_OWNER','DISPOSAL') AND NEW.released_at IS NOT NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A final custody entry (returned/disposed) cannot be released.';
    END IF;
END$$

CREATE TRIGGER trg_custody_bd
BEFORE DELETE ON custody_log
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Chain-of-custody records cannot be deleted.';
END$$

-- ---------------------------------------------------------------------
-- WITNESS / ACCUSED / CHARGE / COURT
-- ---------------------------------------------------------------------
CREATE TRIGGER trg_witness_bi
BEFORE INSERT ON witness
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(25);
    DECLARE v_cnt INT;
    SELECT status INTO v_status FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status = 'CLOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Witnesses cannot be added to a closed case.';
    END IF;
    SELECT COUNT(*) INTO v_cnt FROM complaint_accused
     WHERE complaint_id = NEW.complaint_id AND person_id = NEW.person_id;
    IF v_cnt > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'An accused person cannot be a witness in the same case.';
    END IF;
END$$

CREATE TRIGGER trg_accused_bi
BEFORE INSERT ON complaint_accused
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(25);
    DECLARE v_complainant INT;
    DECLARE v_cnt INT;
    SELECT status, complainant_id INTO v_status, v_complainant FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status = 'CLOSED' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Accused cannot be added to a closed case.';
    END IF;
    IF v_complainant = NEW.person_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The complainant cannot be accused in the same complaint.';
    END IF;
    SELECT COUNT(*) INTO v_cnt FROM witness WHERE complaint_id = NEW.complaint_id AND person_id = NEW.person_id;
    IF v_cnt > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A witness cannot be accused in the same case.';
    END IF;
END$$

CREATE TRIGGER trg_charge_bi
BEFORE INSERT ON charge
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(25);
    SELECT status INTO v_status FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status IN ('REGISTERED','CLOSED') THEN
        SIGNAL SQLSTATE '45000'
           SET MESSAGE_TEXT = 'Charges can only be framed while the case is under investigation or later (not closed).';
    END IF;
END$$

CREATE TRIGGER trg_court_bi
BEFORE INSERT ON court_reference
FOR EACH ROW
BEGIN
    DECLARE v_status VARCHAR(25);
    SELECT status INTO v_status FROM complaint WHERE complaint_id = NEW.complaint_id;
    IF v_status NOT IN ('CHARGE_SHEETED','IN_COURT') THEN
        SIGNAL SQLSTATE '45000'
           SET MESSAGE_TEXT = 'A court reference can only be added after the case is charge-sheeted.';
    END IF;
END$$

-- Status history is an audit log: no updates, no deletes
CREATE TRIGGER trg_history_bu
BEFORE UPDATE ON status_history
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Status history is an audit log and cannot be modified.';
END$$

CREATE TRIGGER trg_history_bd
BEFORE DELETE ON status_history
FOR EACH ROW
BEGIN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Status history is an audit log and cannot be deleted.';
END$$

-- ---------------------------------------------------------------------
-- FUNCTIONS
-- ---------------------------------------------------------------------
CREATE FUNCTION fn_current_holder(p_evidence_id INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_holder INT DEFAULT NULL;
    SELECT to_officer_id INTO v_holder FROM custody_log
     WHERE evidence_id = p_evidence_id AND released_at IS NULL
     LIMIT 1;
    RETURN v_holder;
END$$

CREATE FUNCTION fn_case_age_days(p_complaint_id INT)
RETURNS INT
READS SQL DATA
BEGIN
    DECLARE v_days INT DEFAULT NULL;
    SELECT DATEDIFF(COALESCE(closure_date, CURDATE()), DATE(registered_at)) INTO v_days
      FROM complaint WHERE complaint_id = p_complaint_id;
    RETURN v_days;
END$$

-- ---------------------------------------------------------------------
-- STORED PROCEDURES (transactional)
-- ---------------------------------------------------------------------
-- Atomic custody transfer: closes the current custody period and opens the
-- new one in a single transaction. Any error rolls back both steps.
CREATE PROCEDURE sp_transfer_custody(
    IN p_evidence_id   INT,
    IN p_to_officer_id INT,
    IN p_location      VARCHAR(150),
    IN p_purpose       VARCHAR(20),
    IN p_transfer_at   DATETIME,
    IN p_seal_intact   TINYINT,
    IN p_remarks       VARCHAR(500)
)
BEGIN
    DECLARE v_custody_id INT;
    DECLARE v_holder INT;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
        -- lock the current custody row so two transfers cannot run concurrently
        SELECT custody_id, to_officer_id INTO v_custody_id, v_holder
          FROM custody_log
         WHERE evidence_id = p_evidence_id AND released_at IS NULL
         FOR UPDATE;

        IF v_custody_id IS NULL THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Evidence item has no current custodian.';
        END IF;

        UPDATE custody_log SET released_at = p_transfer_at WHERE custody_id = v_custody_id;

        INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose,
                                 received_at, seal_intact, remarks)
        VALUES (p_evidence_id, v_holder, p_to_officer_id, p_location, p_purpose,
                p_transfer_at, p_seal_intact, p_remarks);
    COMMIT;
END$$

-- Atomic case closure: closes the complaint and relieves all active officers
CREATE PROCEDURE sp_close_complaint(
    IN p_complaint_id INT,
    IN p_closed_by    INT,
    IN p_closure_type VARCHAR(30),
    IN p_remarks      VARCHAR(500),
    IN p_closure_date DATE
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
        UPDATE complaint
           SET status = 'CLOSED', closure_date = p_closure_date, closure_type = p_closure_type,
               closure_remarks = p_remarks, closed_by = p_closed_by
         WHERE complaint_id = p_complaint_id;

        UPDATE assignment SET relieved_at = GREATEST(NOW(), assigned_at)
         WHERE complaint_id = p_complaint_id AND relieved_at IS NULL;
    COMMIT;
END$$

DELIMITER ;
