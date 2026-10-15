-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  01 - Schema (DDL) : tables, keys, integrity constraints, indexes
--  Target : MySQL 8.0.16+ (CHECK constraints are enforced)
--  Normal form : every table is in 3NF (see docs/PROJECT_REPORT.md)
-- =====================================================================

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS app_user, status_history, court_reference, charge,
                     witness, custody_log, evidence_item, investigation_activity,
                     assignment, complaint_accused, complaint, person, officer, station;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- STATION : police stations / units
-- ---------------------------------------------------------------------
CREATE TABLE station (
    station_id     INT           NOT NULL AUTO_INCREMENT,
    station_code   VARCHAR(10)   NOT NULL,
    station_name   VARCHAR(100)  NOT NULL,
    district       VARCHAR(60)   NOT NULL,
    address        VARCHAR(255)  NOT NULL,
    phone          VARCHAR(15)   NULL,
    CONSTRAINT pk_station        PRIMARY KEY (station_id),
    CONSTRAINT uq_station_code   UNIQUE (station_code),
    CONSTRAINT chk_station_code  CHECK (station_code REGEXP '^PS-[A-Z]{3}$')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- OFFICER : police personnel
-- ---------------------------------------------------------------------
CREATE TABLE officer (
    officer_id     INT           NOT NULL AUTO_INCREMENT,
    badge_no       VARCHAR(12)   NOT NULL,
    full_name      VARCHAR(100)  NOT NULL,
    officer_rank   VARCHAR(30)   NOT NULL,
    station_id     INT           NOT NULL,
    phone          VARCHAR(10)   NOT NULL,
    email          VARCHAR(100)  NULL,
    date_joined    DATE          NOT NULL,
    is_active      TINYINT(1)    NOT NULL DEFAULT 1,
    CONSTRAINT pk_officer          PRIMARY KEY (officer_id),
    CONSTRAINT uq_officer_badge    UNIQUE (badge_no),
    CONSTRAINT uq_officer_phone    UNIQUE (phone),
    CONSTRAINT uq_officer_email    UNIQUE (email),
    CONSTRAINT fk_officer_station  FOREIGN KEY (station_id) REFERENCES station (station_id),
    CONSTRAINT chk_officer_rank    CHECK (officer_rank IN ('Constable','Head Constable','Assistant Sub-Inspector',
                                                          'Sub-Inspector','Inspector','Deputy SP','Superintendent')),
    CONSTRAINT chk_officer_phone   CHECK (phone REGEXP '^[6-9][0-9]{9}$'),
    CONSTRAINT chk_officer_badge   CHECK (badge_no REGEXP '^MH[0-9]{2}-[0-9]{4}$'),
    CONSTRAINT chk_officer_active  CHECK (is_active IN (0,1)),
    CONSTRAINT chk_officer_joined  CHECK (date_joined >= '1970-01-01')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- PERSON : every civilian (complainant, accused, witness)
-- ---------------------------------------------------------------------
CREATE TABLE person (
    person_id      INT           NOT NULL AUTO_INCREMENT,
    full_name      VARCHAR(100)  NOT NULL,
    gender         CHAR(1)       NOT NULL,
    date_of_birth  DATE          NULL,
    phone          VARCHAR(10)   NULL,
    email          VARCHAR(100)  NULL,
    address        VARCHAR(255)  NOT NULL,
    id_proof_type  VARCHAR(20)   NULL,
    id_proof_no    VARCHAR(20)   NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_person          PRIMARY KEY (person_id),
    CONSTRAINT uq_person_idproof  UNIQUE (id_proof_type, id_proof_no),
    CONSTRAINT chk_person_gender  CHECK (gender IN ('M','F','O')),
    CONSTRAINT chk_person_phone   CHECK (phone IS NULL OR phone REGEXP '^[6-9][0-9]{9}$'),
    CONSTRAINT chk_person_dob     CHECK (date_of_birth IS NULL OR date_of_birth >= '1900-01-01'),
    CONSTRAINT chk_person_idtype  CHECK (id_proof_type IS NULL OR
                                         id_proof_type IN ('AADHAAR','PAN','VOTER_ID','PASSPORT','DRIVING_LICENSE')),
    -- both proof columns are filled together or left empty together
    CONSTRAINT chk_person_idpair  CHECK ((id_proof_type IS NULL) = (id_proof_no IS NULL)),
    -- format of the proof number depends on its type
    CONSTRAINT chk_person_idformat CHECK (
            id_proof_type IS NULL
         OR (id_proof_type = 'AADHAAR'         AND id_proof_no REGEXP '^[2-9][0-9]{11}$')
         OR (id_proof_type = 'PAN'             AND id_proof_no REGEXP '^[A-Z]{5}[0-9]{4}[A-Z]$')
         OR (id_proof_type = 'VOTER_ID'        AND id_proof_no REGEXP '^[A-Z]{3}[0-9]{7}$')
         OR (id_proof_type = 'PASSPORT'        AND id_proof_no REGEXP '^[A-Z][0-9]{7}$')
         OR (id_proof_type = 'DRIVING_LICENSE' AND id_proof_no REGEXP '^[A-Z]{2}[0-9]{13}$'))
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- COMPLAINT : the case (FIR / complaint register)
-- ---------------------------------------------------------------------
CREATE TABLE complaint (
    complaint_id       INT           NOT NULL AUTO_INCREMENT,
    complaint_no       VARCHAR(20)   NOT NULL,           -- generated by trigger: CMP-YYYY-NNNNN
    station_id         INT           NOT NULL,
    complainant_id     INT           NOT NULL,
    title              VARCHAR(150)  NOT NULL,
    description        TEXT          NOT NULL,
    category           VARCHAR(30)   NOT NULL,
    priority           VARCHAR(10)   NOT NULL DEFAULT 'MEDIUM',
    incident_datetime  DATETIME      NOT NULL,
    incident_location  VARCHAR(255)  NOT NULL,
    registered_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    registered_by      INT           NULL,
    status             VARCHAR(25)   NOT NULL DEFAULT 'REGISTERED',
    closure_date       DATE          NULL,
    closure_type       VARCHAR(30)   NULL,
    closure_remarks    VARCHAR(500)  NULL,
    closed_by          INT           NULL,
    CONSTRAINT pk_complaint              PRIMARY KEY (complaint_id),
    CONSTRAINT uq_complaint_no           UNIQUE (complaint_no),
    CONSTRAINT fk_complaint_station      FOREIGN KEY (station_id)     REFERENCES station (station_id),
    CONSTRAINT fk_complaint_complainant  FOREIGN KEY (complainant_id) REFERENCES person (person_id),
    CONSTRAINT fk_complaint_registered   FOREIGN KEY (registered_by)  REFERENCES officer (officer_id),
    CONSTRAINT fk_complaint_closed_by    FOREIGN KEY (closed_by)      REFERENCES officer (officer_id),
    CONSTRAINT chk_complaint_no          CHECK (complaint_no REGEXP '^CMP-[0-9]{4}-[0-9]{5}$'),
    CONSTRAINT chk_complaint_category    CHECK (category IN ('THEFT','BURGLARY','ROBBERY','ASSAULT','FRAUD','CYBER_CRIME',
                                                             'MISSING_PERSON','NARCOTICS','VEHICLE_THEFT','HARASSMENT',
                                                             'DOMESTIC_VIOLENCE','OTHER')),
    CONSTRAINT chk_complaint_priority    CHECK (priority IN ('LOW','MEDIUM','HIGH','CRITICAL')),
    -- BUSINESS RULE: valid case status
    CONSTRAINT chk_complaint_status      CHECK (status IN ('REGISTERED','UNDER_INVESTIGATION','CHARGE_SHEETED',
                                                           'IN_COURT','CLOSED')),
    CONSTRAINT chk_complaint_incident    CHECK (incident_datetime <= registered_at),
    CONSTRAINT chk_complaint_closuretype CHECK (closure_type IS NULL OR
                                                closure_type IN ('SOLVED','CONVICTED','ACQUITTED','FALSE_COMPLAINT',
                                                                 'INSUFFICIENT_EVIDENCE','COMPROMISE','UNTRACED',
                                                                 'TRANSFERRED')),
    -- BUSINESS RULE: closure details required (and only allowed) when the case is CLOSED
    CONSTRAINT chk_complaint_closure     CHECK (
           (status =  'CLOSED' AND closure_date IS NOT NULL AND closure_type IS NOT NULL
                               AND closure_remarks IS NOT NULL AND closed_by IS NOT NULL)
        OR (status <> 'CLOSED' AND closure_date IS NULL AND closure_type IS NULL
                               AND closure_remarks IS NULL AND closed_by IS NULL)),
    CONSTRAINT chk_complaint_closuredate CHECK (closure_date IS NULL OR closure_date >= DATE(registered_at))
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- COMPLAINT_ACCUSED : persons accused in a complaint (M:N)
-- ---------------------------------------------------------------------
CREATE TABLE complaint_accused (
    complaint_id    INT           NOT NULL,
    person_id       INT           NOT NULL,
    accused_status  VARCHAR(15)   NOT NULL DEFAULT 'SUSPECT',
    added_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks         VARCHAR(300)  NULL,
    CONSTRAINT pk_complaint_accused   PRIMARY KEY (complaint_id, person_id),
    CONSTRAINT fk_accused_complaint   FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT fk_accused_person      FOREIGN KEY (person_id)    REFERENCES person (person_id),
    CONSTRAINT chk_accused_status     CHECK (accused_status IN ('SUSPECT','ARRESTED','ABSCONDING','ON_BAIL','RELEASED'))
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- ASSIGNMENT : officer <-> complaint (M:N with history)
-- ---------------------------------------------------------------------
CREATE TABLE assignment (
    assignment_id    INT           NOT NULL AUTO_INCREMENT,
    complaint_id     INT           NOT NULL,
    officer_id       INT           NOT NULL,
    assignment_role  VARCHAR(15)   NOT NULL DEFAULT 'SUPPORT',
    assigned_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    relieved_at      DATETIME      NULL,
    assigned_by      INT           NULL,
    remarks          VARCHAR(300)  NULL,
    -- helper columns: NULL for historic rows so UNIQUE only applies to active rows
    active_key       TINYINT GENERATED ALWAYS AS (IF(relieved_at IS NULL, 1, NULL)) STORED,
    lead_key         TINYINT GENERATED ALWAYS AS (IF(relieved_at IS NULL AND assignment_role = 'LEAD', 1, NULL)) STORED,
    CONSTRAINT pk_assignment           PRIMARY KEY (assignment_id),
    CONSTRAINT fk_assignment_complaint FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT fk_assignment_officer   FOREIGN KEY (officer_id)   REFERENCES officer (officer_id),
    CONSTRAINT fk_assignment_by        FOREIGN KEY (assigned_by)  REFERENCES officer (officer_id),
    CONSTRAINT uq_assignment_active    UNIQUE (complaint_id, officer_id, active_key),   -- no duplicate active assignment
    CONSTRAINT uq_assignment_one_lead  UNIQUE (complaint_id, lead_key),                 -- at most one active LEAD
    CONSTRAINT chk_assignment_role     CHECK (assignment_role IN ('LEAD','SUPPORT','FORENSIC','SURVEILLANCE')),
    CONSTRAINT chk_assignment_dates    CHECK (relieved_at IS NULL OR relieved_at >= assigned_at)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- INVESTIGATION_ACTIVITY : diary of investigation actions
-- ---------------------------------------------------------------------
CREATE TABLE investigation_activity (
    activity_id     INT            NOT NULL AUTO_INCREMENT,
    complaint_id    INT            NOT NULL,
    officer_id      INT            NOT NULL,
    activity_type   VARCHAR(25)    NOT NULL,
    activity_time   DATETIME       NOT NULL,
    location        VARCHAR(255)   NULL,
    description     VARCHAR(1000)  NOT NULL,
    outcome         VARCHAR(500)   NULL,
    logged_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_activity           PRIMARY KEY (activity_id),
    CONSTRAINT fk_activity_complaint FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT fk_activity_officer   FOREIGN KEY (officer_id)   REFERENCES officer (officer_id),
    CONSTRAINT chk_activity_type     CHECK (activity_type IN ('SITE_VISIT','STATEMENT_RECORDED','INTERROGATION','RAID',
                                                              'ARREST','EVIDENCE_COLLECTION','FORENSIC_REQUEST',
                                                              'CCTV_REVIEW','MEDICAL_EXAM','OTHER')),
    CONSTRAINT chk_activity_desc     CHECK (CHAR_LENGTH(TRIM(description)) >= 5)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- EVIDENCE_ITEM : seized / collected evidence
-- (current holder & location are NOT stored here - they are derived
--  from the open CUSTODY_LOG row, which keeps the table in 3NF)
-- ---------------------------------------------------------------------
CREATE TABLE evidence_item (
    evidence_id      INT           NOT NULL AUTO_INCREMENT,
    evidence_no      VARCHAR(20)   NOT NULL,              -- generated by trigger: EVD-YYYY-NNNNN
    complaint_id     INT           NOT NULL,
    category         VARCHAR(20)   NOT NULL,
    description      VARCHAR(500)  NOT NULL,
    quantity         INT           NOT NULL DEFAULT 1,
    item_condition   VARCHAR(12)   NOT NULL DEFAULT 'INTACT',
    seal_no          VARCHAR(20)   NULL,
    collected_at     DATETIME      NOT NULL,
    collected_by     INT           NOT NULL,
    collected_from   VARCHAR(255)  NOT NULL,
    registered_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_evidence            PRIMARY KEY (evidence_id),
    CONSTRAINT uq_evidence_no         UNIQUE (evidence_no),          -- BUSINESS RULE: unique evidence ID
    CONSTRAINT uq_evidence_seal       UNIQUE (seal_no),
    CONSTRAINT fk_evidence_complaint  FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT fk_evidence_collector  FOREIGN KEY (collected_by) REFERENCES officer (officer_id),
    CONSTRAINT chk_evidence_no        CHECK (evidence_no REGEXP '^EVD-[0-9]{4}-[0-9]{5}$'),
    CONSTRAINT chk_evidence_category  CHECK (category IN ('WEAPON','DOCUMENT','ELECTRONIC','BIOLOGICAL','NARCOTIC',
                                                          'VEHICLE','CCTV_FOOTAGE','FINGERPRINT','CLOTHING',
                                                          'CASH_VALUABLES','OTHER')),
    CONSTRAINT chk_evidence_qty       CHECK (quantity > 0),
    CONSTRAINT chk_evidence_condition CHECK (item_condition IN ('INTACT','DAMAGED','PARTIAL','PERISHABLE'))
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- CUSTODY_LOG : chain of custody - one row per custody period
--   received_at .. released_at  (released_at NULL = current holder)
-- ---------------------------------------------------------------------
CREATE TABLE custody_log (
    custody_id       INT           NOT NULL AUTO_INCREMENT,
    evidence_id      INT           NOT NULL,
    from_officer_id  INT           NULL,          -- NULL only for the initial seizure
    to_officer_id    INT           NOT NULL,
    location         VARCHAR(150)  NOT NULL,
    purpose          VARCHAR(20)   NOT NULL,
    received_at      DATETIME      NOT NULL,
    released_at      DATETIME      NULL,
    seal_intact      TINYINT(1)    NOT NULL DEFAULT 1,
    remarks          VARCHAR(500)  NULL,
    open_key         TINYINT GENERATED ALWAYS AS (IF(released_at IS NULL, 1, NULL)) STORED,
    CONSTRAINT pk_custody            PRIMARY KEY (custody_id),
    CONSTRAINT fk_custody_evidence   FOREIGN KEY (evidence_id)     REFERENCES evidence_item (evidence_id),
    CONSTRAINT fk_custody_from       FOREIGN KEY (from_officer_id) REFERENCES officer (officer_id),
    CONSTRAINT fk_custody_to         FOREIGN KEY (to_officer_id)   REFERENCES officer (officer_id),
    -- BUSINESS RULE: only one current (open) custodian per evidence item
    CONSTRAINT uq_custody_one_open   UNIQUE (evidence_id, open_key),
    CONSTRAINT chk_custody_purpose   CHECK (purpose IN ('INITIAL_SEIZURE','STORAGE','FORENSIC_ANALYSIS','INVESTIGATION',
                                                        'COURT_PRODUCTION','RETURN_TO_OWNER','DISPOSAL')),
    CONSTRAINT chk_custody_period    CHECK (released_at IS NULL OR released_at > received_at),
    CONSTRAINT chk_custody_self      CHECK (from_officer_id IS NULL OR from_officer_id <> to_officer_id),
    -- BUSINESS RULE: complete transfer - every transfer except the seizure names the handing officer
    CONSTRAINT chk_custody_from      CHECK ((purpose = 'INITIAL_SEIZURE') = (from_officer_id IS NULL)),
    CONSTRAINT chk_custody_seal      CHECK (seal_intact IN (0,1)),
    CONSTRAINT chk_custody_location  CHECK (CHAR_LENGTH(TRIM(location)) >= 3)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- WITNESS : person giving a statement in a complaint
-- ---------------------------------------------------------------------
CREATE TABLE witness (
    witness_id      INT           NOT NULL AUTO_INCREMENT,
    complaint_id    INT           NOT NULL,
    person_id       INT           NOT NULL,
    statement       TEXT          NOT NULL,
    statement_date  DATETIME      NOT NULL,
    recorded_by     INT           NOT NULL,
    is_protected    TINYINT(1)    NOT NULL DEFAULT 0,
    CONSTRAINT pk_witness            PRIMARY KEY (witness_id),
    CONSTRAINT uq_witness_case       UNIQUE (complaint_id, person_id),
    CONSTRAINT fk_witness_complaint  FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT fk_witness_person     FOREIGN KEY (person_id)    REFERENCES person (person_id),
    CONSTRAINT fk_witness_officer    FOREIGN KEY (recorded_by)  REFERENCES officer (officer_id),
    CONSTRAINT chk_witness_protected CHECK (is_protected IN (0,1)),
    CONSTRAINT chk_witness_statement CHECK (CHAR_LENGTH(TRIM(statement)) >= 10)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- CHARGE : legal sections invoked against an accused of a complaint
-- ---------------------------------------------------------------------
CREATE TABLE charge (
    charge_id            INT           NOT NULL AUTO_INCREMENT,
    complaint_id         INT           NOT NULL,
    accused_person_id    INT           NOT NULL,
    act_name             VARCHAR(15)   NOT NULL,
    section_code         VARCHAR(20)   NOT NULL,
    offence_description  VARCHAR(255)  NOT NULL,
    charged_on           DATE          NOT NULL,
    charged_by           INT           NOT NULL,
    CONSTRAINT pk_charge           PRIMARY KEY (charge_id),
    -- the charged person must be an accused of the same complaint
    CONSTRAINT fk_charge_accused   FOREIGN KEY (complaint_id, accused_person_id)
                                   REFERENCES complaint_accused (complaint_id, person_id),
    CONSTRAINT fk_charge_officer   FOREIGN KEY (charged_by) REFERENCES officer (officer_id),
    CONSTRAINT uq_charge           UNIQUE (complaint_id, accused_person_id, act_name, section_code),
    CONSTRAINT chk_charge_act      CHECK (act_name IN ('BNS','BNSS','IT Act','NDPS Act','Arms Act','MV Act','Other')),
    CONSTRAINT chk_charge_section  CHECK (section_code REGEXP '^[0-9]+[A-Za-z0-9()]*$')
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- COURT_REFERENCE : court case linked to a complaint
-- ---------------------------------------------------------------------
CREATE TABLE court_reference (
    court_ref_id       INT           NOT NULL AUTO_INCREMENT,
    complaint_id       INT           NOT NULL,
    court_case_no      VARCHAR(30)   NOT NULL,
    court_name         VARCHAR(150)  NOT NULL,
    court_type         VARCHAR(15)   NOT NULL,
    filing_date        DATE          NOT NULL,
    next_hearing_date  DATE          NULL,
    judge_name         VARCHAR(100)  NULL,
    case_stage         VARCHAR(20)   NOT NULL DEFAULT 'FILED',
    verdict            VARCHAR(12)   NOT NULL DEFAULT 'PENDING',
    CONSTRAINT pk_court_ref          PRIMARY KEY (court_ref_id),
    CONSTRAINT uq_court_case_no      UNIQUE (court_case_no),
    CONSTRAINT fk_court_complaint    FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT chk_court_type        CHECK (court_type IN ('MAGISTRATE','SESSIONS','HIGH_COURT','SPECIAL')),
    CONSTRAINT chk_court_stage       CHECK (case_stage IN ('FILED','HEARING','ARGUMENTS','JUDGMENT_RESERVED','DISPOSED')),
    CONSTRAINT chk_court_verdict     CHECK (verdict IN ('PENDING','CONVICTED','ACQUITTED','DISMISSED','SETTLED')),
    CONSTRAINT chk_court_hearing     CHECK (next_hearing_date IS NULL OR next_hearing_date >= filing_date),
    -- a verdict other than PENDING is only possible once the case is disposed
    CONSTRAINT chk_court_verdict_stage CHECK ((verdict = 'PENDING') = (case_stage <> 'DISPOSED'))
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- STATUS_HISTORY : audit trail of complaint status (filled by triggers)
-- ---------------------------------------------------------------------
CREATE TABLE status_history (
    history_id    INT           NOT NULL AUTO_INCREMENT,
    complaint_id  INT           NOT NULL,
    old_status    VARCHAR(25)   NULL,
    new_status    VARCHAR(25)   NOT NULL,
    changed_by    INT           NULL,
    changed_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks       VARCHAR(500)  NULL,
    CONSTRAINT pk_status_history      PRIMARY KEY (history_id),
    CONSTRAINT fk_history_complaint   FOREIGN KEY (complaint_id) REFERENCES complaint (complaint_id),
    CONSTRAINT fk_history_officer     FOREIGN KEY (changed_by)   REFERENCES officer (officer_id),
    CONSTRAINT chk_history_new        CHECK (new_status IN ('REGISTERED','UNDER_INVESTIGATION','CHARGE_SHEETED',
                                                            'IN_COURT','CLOSED')),
    CONSTRAINT chk_history_old        CHECK (old_status IS NULL OR old_status IN ('REGISTERED','UNDER_INVESTIGATION',
                                                            'CHARGE_SHEETED','IN_COURT','CLOSED')),
    CONSTRAINT chk_history_change     CHECK (old_status IS NULL OR old_status <> new_status)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------
-- APP_USER : application login accounts & roles
-- ---------------------------------------------------------------------
CREATE TABLE app_user (
    user_id        INT           NOT NULL AUTO_INCREMENT,
    username       VARCHAR(30)   NOT NULL,
    password_hash  VARCHAR(255)  NOT NULL,
    user_role      VARCHAR(10)   NOT NULL,
    officer_id     INT           NULL,
    is_active      TINYINT(1)    NOT NULL DEFAULT 1,
    last_login     DATETIME      NULL,
    created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_app_user        PRIMARY KEY (user_id),
    CONSTRAINT uq_app_username    UNIQUE (username),
    CONSTRAINT uq_app_officer     UNIQUE (officer_id),
    CONSTRAINT fk_app_officer     FOREIGN KEY (officer_id) REFERENCES officer (officer_id),
    CONSTRAINT chk_app_role       CHECK (user_role IN ('ADMIN','SHO','IO','CUSTODIAN')),
    CONSTRAINT chk_app_username   CHECK (username REGEXP '^[a-z0-9_.]{3,30}$'),
    CONSTRAINT chk_app_officer    CHECK (user_role = 'ADMIN' OR officer_id IS NOT NULL)
) ENGINE = InnoDB;

-- =====================================================================
-- INDEXES on frequently searched / joined attributes
-- (PK, UNIQUE and FK columns are indexed automatically by InnoDB)
-- =====================================================================
CREATE INDEX idx_complaint_status_reg  ON complaint (status, registered_at);
CREATE INDEX idx_complaint_category    ON complaint (category);
CREATE INDEX idx_complaint_incident    ON complaint (incident_datetime);
CREATE INDEX idx_complaint_priority    ON complaint (priority);
CREATE FULLTEXT INDEX ft_complaint_text ON complaint (title, description);
CREATE INDEX idx_person_name           ON person (full_name);
CREATE INDEX idx_person_phone          ON person (phone);
CREATE INDEX idx_officer_name          ON officer (full_name);
CREATE INDEX idx_assignment_officer    ON assignment (officer_id, relieved_at);
CREATE INDEX idx_activity_case_time    ON investigation_activity (complaint_id, activity_time);
CREATE INDEX idx_evidence_category     ON evidence_item (category);
CREATE INDEX idx_custody_evidence_time ON custody_log (evidence_id, received_at);
CREATE INDEX idx_custody_holder        ON custody_log (to_officer_id, released_at);
CREATE INDEX idx_history_case_time     ON status_history (complaint_id, changed_at);
CREATE INDEX idx_court_next_hearing    ON court_reference (next_hearing_date);
