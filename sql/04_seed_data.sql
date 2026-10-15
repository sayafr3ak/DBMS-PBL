-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  04 - Realistic sample data (Pune city, 2026)
--  All rows pass through the triggers, so the data itself proves that
--  the business rules are consistent. Status changes are made with
--  UPDATE statements so STATUS_HISTORY is filled by the audit trigger.
--  @audit_time back-dates the audit rows to the realistic date.
-- =====================================================================

SET @current_officer_id = NULL, @audit_time = NULL, @status_remarks = NULL;

-- ---------------------------------------------------------------------
-- Stations
-- ---------------------------------------------------------------------
INSERT INTO station (station_id, station_code, station_name, district, address, phone) VALUES
(1, 'PS-SHV', 'Shivajinagar Police Station', 'Pune City',          'Shivajinagar, Pune 411005',              '02025536263'),
(2, 'PS-KTR', 'Kothrud Police Station',      'Pune City',          'Paud Road, Kothrud, Pune 411038',        '02025391000'),
(3, 'PS-HNJ', 'Hinjewadi Police Station',    'Pimpri-Chinchwad',   'Phase 1, Hinjewadi, Pune 411057',        '02022933444'),
(4, 'PS-CYB', 'Cyber Police Station',        'Pune City',          'Police HQ Campus, Shivajinagar, Pune 411005', '02029710097');

-- ---------------------------------------------------------------------
-- Officers
-- ---------------------------------------------------------------------
INSERT INTO officer (officer_id, badge_no, full_name, officer_rank, station_id, phone, email, date_joined, is_active) VALUES
(1,  'MH12-1001', 'Vikram Deshmukh',  'Inspector',               1, '9823001001', 'vikram.deshmukh@pcets.local',  '2008-06-15', 1),
(2,  'MH12-1002', 'Anjali Kulkarni',  'Sub-Inspector',           1, '9823001002', 'anjali.kulkarni@pcets.local',  '2015-03-01', 1),
(3,  'MH12-1003', 'Rohit Patil',      'Assistant Sub-Inspector', 1, '9823001003', 'rohit.patil@pcets.local',      '2012-09-10', 1),
(4,  'MH12-1004', 'Suresh Jadhav',    'Head Constable',          1, '9823001004', 'suresh.jadhav@pcets.local',    '2005-01-20', 1),
(5,  'MH12-2001', 'Meera Joshi',      'Inspector',               2, '9823002001', 'meera.joshi@pcets.local',      '2009-07-01', 1),
(6,  'MH12-2002', 'Arjun Shinde',     'Sub-Inspector',           2, '9823002002', 'arjun.shinde@pcets.local',     '2016-11-11', 1),
(7,  'MH12-2003', 'Pooja Gaikwad',    'Sub-Inspector',           2, '9823002003', 'pooja.gaikwad@pcets.local',    '2018-02-05', 1),
(8,  'MH12-2004', 'Ganesh More',      'Head Constable',          2, '9823002004', 'ganesh.more@pcets.local',      '2007-04-18', 1),
(9,  'MH14-3001', 'Rajesh Pawar',     'Inspector',               3, '9823003001', 'rajesh.pawar@pcets.local',     '2010-08-23', 1),
(10, 'MH14-3002', 'Sneha Bhosale',    'Sub-Inspector',           3, '9823003002', 'sneha.bhosale@pcets.local',    '2017-05-30', 1),
(11, 'MH14-3003', 'Amit Chavan',      'Head Constable',          3, '9823003003', 'amit.chavan@pcets.local',      '2011-12-12', 1),
(12, 'MH12-4001', 'Kavita Rao',       'Inspector',               4, '9823004001', 'kavita.rao@pcets.local',       '2011-01-03', 1),
(13, 'MH12-4002', 'Nikhil Sawant',    'Sub-Inspector',           4, '9823004002', 'nikhil.sawant@pcets.local',    '2019-06-17', 1),
(14, 'MH12-4003', 'Farhan Shaikh',    'Assistant Sub-Inspector', 4, '9823004003', 'farhan.shaikh@pcets.local',    '2014-10-09', 1),
(15, 'MH12-1006', 'Prakash Naik',     'Assistant Sub-Inspector', 1, '9823001006', 'prakash.naik@pcets.local',     '2013-03-27', 1),
(16, 'MH12-1005', 'Sandeep Kale',     'Constable',               1, '9823001005', 'sandeep.kale@pcets.local',     '1996-05-14', 0);

-- ---------------------------------------------------------------------
-- Persons (complainants, accused, witnesses)
-- ---------------------------------------------------------------------
INSERT INTO person (person_id, full_name, gender, date_of_birth, phone, email, address, id_proof_type, id_proof_no) VALUES
(1,  'Rahul Mehta',       'M', '1994-05-12', '9822011122', 'rahul.mehta@example.com', 'Flat 12, Shubham Apts, Deccan Gymkhana, Pune 411004', 'AADHAAR', '458712369874'),
(2,  'Priya Nair',        'F', '1988-11-02', '9890122334', 'priya.nair@example.com',  'B-4, Model Colony, Shivajinagar, Pune 411016', 'AADHAAR', '563214789652'),
(3,  'Sanjay Kulkarni',   'M', '1979-02-20', '9765433221', NULL, '22, Mayur Colony, Kothrud, Pune 411038',        'PAN', 'BKLPK4521D'),
(4,  'Neha Agarwal',      'F', '1991-07-08', '9923344556', 'neha.agarwal@example.com', '501, Sai Heights, Baner Road, Pune 411045', 'AADHAAR', '785412369541'),
(5,  'Karthik Iyer',      'M', '1996-01-25', '9881122233', 'karthik.iyer@example.com', 'Megapolis, Hinjewadi Phase 3, Pune 411057', 'AADHAAR', '698532147852'),
(6,  'Manoj Thakur',      'M', '1985-09-14', '9970011223', NULL, 'Karve Nagar, Pune 411052',                      'DRIVING_LICENSE', 'MH1220110012345'),
(7,  'Sunita Wagh',       'F', '1972-03-30', '9850066778', NULL, 'Shivajinagar Gaothan, Pune 411005',             'VOTER_ID', 'WGH1234567'),
(8,  'Deepak Rane',       'M', '1968-12-01', '9822334455', NULL, 'Kaspate Wasti, Wakad, Pune 411057',             'AADHAAR', '852369741258'),
(9,  'Ayesha Khan',       'F', '1993-04-17', '9767788990', 'ayesha.khan@example.com', 'East Street, Camp, Pune 411001', 'PAN', 'AKZPK1234F'),
(10, 'Vivek Sharma',      'M', '1990-10-10', '9823456789', NULL, 'Erandwane, Karve Road, Pune 411004',            'AADHAAR', '741258963014'),
(11, 'Lata Joshi',        'F', '1960-06-06', '9420011223', NULL, 'Prabhat Road Lane 3, Pune 411004',              'AADHAAR', '369852147036'),
(12, 'Imran Sayyed',      'M', '1982-08-22', '9812233445', 'imran@sayyedelectronics.example', 'Maan Road, Hinjewadi, Pune 411057', 'PAN', 'ABCPS5678K'),
(13, 'Kavya Deshpande',   'F', '1995-12-12', '9604455667', NULL, 'Kothrud Depot, Pune 411038',                    'AADHAAR', '247852369025'),
(14, 'Arvind Gupta',      'M', '1975-05-05', '9822778899', NULL, 'Aundh, Pune 411007',                            'PAN', 'AAGPG7788L'),
(15, 'Rohan Kapoor',      'M', '2002-02-02', '9011223344', NULL, 'Shivaji Housing Society, SB Road, Pune 411016', NULL, NULL),
(16, 'Sameer Pathan',     'M', '1987-01-01', '9834455667', NULL, 'Wakad, Pune 411057',                            'AADHAAR', '963258741025'),
(17, 'Tanvi Bhatt',       'F', '1998-09-09', '9145566778', NULL, 'Viman Nagar, Pune 411014',                      NULL, NULL),
(18, 'Mahesh Ghule',      'M', '1983-03-03', '9881239876', NULL, 'Ghule General Stores, Kothrud Market, Pune 411038', 'AADHAAR', '852147963025'),
(19, 'Siddharth Rao',     'M', '1992-06-15', '9673344556', 'sid.rao@example.com', 'Kalyani Nagar, Pune 411006',  'PASSPORT', 'K1234567'),
(20, 'Pallavi Shinde',    'F', '1997-08-20', '9545566778', NULL, 'Wakad, Pune 411057',                            NULL, NULL),
(21, 'Akash Salve',       'M', '1999-07-07', '9561122334', NULL, 'Laxmi Nagar, Yerawada, Pune 411006',            'AADHAAR', '632587412365'),
(22, 'Rakesh Mane',       'M', '1990-01-15', NULL,         NULL, 'Hadapsar, Pune 411028',                         NULL, NULL),
(23, 'Sunny Gill',        'M', '1997-04-04', '9876501234', NULL, 'Chandan Nagar, Pune 411014',                    NULL, NULL),
(24, 'Pankaj Verma',      'M', '1993-11-11', '7004455667', NULL, 'Karmatar, Jamtara, Jharkhand 815351',           'AADHAAR', '785236941256'),
(25, 'Vijay Londhe',      'M', '1986-02-28', '9850011234', NULL, 'Warje, Pune 411058',                            NULL, NULL),
(26, 'Babu Shaikh',       'M', '1965-10-10', NULL,         NULL, 'Near Shivajinagar Bus Stand, Pune 411005',      NULL, NULL),
(27, 'Raju Kamble',       'M', '1995-05-05', NULL,         NULL, 'Chakan, Pune 410501',                           NULL, NULL),
(28, 'Nitin Bhalerao',    'M', '1989-09-09', '9922001122', NULL, 'Chakan MIDC, Pune 410501',                      NULL, NULL),
(29, 'Ajay Wagh',         'M', '1984-12-12', '9850044332', NULL, 'Shastri Nagar, Kothrud, Pune 411038',           NULL, NULL),
(30, 'Harish Malhotra',   'M', '1980-03-15', '9811122233', NULL, 'Pimple Saudagar, Pune 411027',                  'PAN', 'AHMPM4455Q'),
(31, 'Shubham Jagtap',    'M', '1998-02-14', '9767001122', NULL, 'FC Road, Pune 411004',                          NULL, NULL),
(32, 'Ramesh Bhide',      'M', '1955-06-01', '9420334455', NULL, 'Model Colony, Shivajinagar, Pune 411016',       NULL, NULL),
(33, 'Kiran Shetty',      'F', '1992-03-22', '9890776655', NULL, 'Paud Road, Kothrud, Pune 411038',               NULL, NULL),
(34, 'Gopal Yadav',       'M', '1980-07-19', '9822990011', NULL, 'Shivajinagar, Pune 411005',                     'VOTER_ID', 'GPY7654321'),
(35, 'Anil Kadam',        'M', '1975-11-30', '9881776655', NULL, 'Maan Road, Hinjewadi, Pune 411057',             NULL, NULL),
(36, 'Swati Mohite',      'F', '1989-04-04', '9604112233', NULL, 'Nal Stop, Erandwane, Pune 411004',              NULL, NULL),
(37, 'Prakash Salunkhe',  'M', '1978-08-08', '9850998877', NULL, 'Shivajinagar, Pune 411005',                     NULL, NULL),
(38, 'Meenal Sathe',      'F', '1986-10-01', '9765112233', NULL, 'Shastri Nagar, Kothrud, Pune 411038',           NULL, NULL),
(39, 'Aditya Rane',       'M', '2009-03-15', NULL,         NULL, 'Kaspate Wasti, Wakad, Pune 411057',             NULL, NULL),
(40, 'Rekha Wagh',        'F', '1988-05-25', '9850044331', NULL, 'Shastri Nagar, Kothrud, Pune 411038',           'AADHAAR', '456123789012');

-- =====================================================================
-- CASE 1 : Mobile snatching, FC Road  -> convicted & CLOSED
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(1, 1, 1, 'Mobile phone snatched near FC Road',
 'Complainant was walking towards Goodluck Chowk when two persons on a black motorcycle snatched his Samsung Galaxy S23 and fled towards Deccan.',
 'ROBBERY', 'HIGH', '2026-03-04 20:15:00', 'FC Road near Goodluck Chowk, Pune', '2026-03-04 22:10:00', 2);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by, remarks) VALUES
(1, 2, 'LEAD',    '2026-03-04 22:30:00', 1, 'Assigned by SHO'),
(1, 3, 'SUPPORT', '2026-03-05 09:00:00', 1, 'CCTV analysis');
SET @current_officer_id = 1, @audit_time = '2026-03-04 22:35:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 1;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(1, 2, 'SITE_VISIT',  '2026-03-04 23:00:00', 'Goodluck Chowk, FC Road', 'Visited spot of offence, spoke to shopkeepers and identified CCTV cameras nearby.', 'Two CCTV cameras identified'),
(1, 3, 'CCTV_REVIEW', '2026-03-05 14:00:00', 'Hotel Vaishali, FC Road', 'Reviewed CCTV footage of 20:00-20:30 hrs; motorcycle number partially visible.', 'Vehicle MH12 xx 7781 traced'),
(1, 2, 'ARREST',      '2026-03-09 18:30:00', 'Laxmi Nagar, Yerawada', 'Accused Akash Salve arrested from his residence after vehicle trace.', 'Phone recovered');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(1, 1, 'ELECTRONIC',   'Recovered Samsung Galaxy S23 (IMEI 356789104512334), black', 1, 'INTACT', 'SL-SHV-0001', '2026-03-09 19:00:00', 2, 'Accused residence, Laxmi Nagar, Yerawada', '2026-03-09 21:05:00'),
(2, 1, 'CCTV_FOOTAGE', 'CCTV footage exported from DVR - Goodluck Chowk (pen drive 32 GB)', 1, 'INTACT', 'SL-SHV-0002', '2026-03-05 14:30:00', 3, 'Hotel Vaishali CCTV control room, FC Road', '2026-03-05 16:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(2, NULL, 3, 'Hotel Vaishali CCTV room, FC Road', 'INITIAL_SEIZURE', '2026-03-05 14:30:00', '2026-03-05 16:00:00', 1, 'Seized under panchnama'),
(2, 3,    4, 'Malkhana, Shivajinagar PS',         'STORAGE',         '2026-03-05 16:00:00', NULL,                  1, 'Deposited in malkhana, entry no. 112/2026'),
(1, NULL, 2, 'Accused residence, Yerawada',       'INITIAL_SEIZURE', '2026-03-09 19:00:00', '2026-03-09 21:00:00', 1, 'Seized under panchnama in presence of 2 panchas'),
(1, 2,    4, 'Malkhana, Shivajinagar PS',         'STORAGE',         '2026-03-09 21:00:00', '2026-05-20 10:00:00', 1, 'Malkhana entry no. 118/2026'),
(1, 4,    2, 'JMFC Court, Shivajinagar',          'COURT_PRODUCTION','2026-05-20 10:00:00', '2026-05-20 17:00:00', 1, 'Produced before court as Article A'),
(1, 2,    4, 'Malkhana, Shivajinagar PS',         'STORAGE',         '2026-05-20 17:00:00', '2026-08-25 11:00:00', 1, 'Re-deposited after court production'),
(1, 4,    2, 'Shivajinagar PS - handed to owner', 'RETURN_TO_OWNER', '2026-08-25 11:00:00', NULL,                  1, 'Returned to complainant Rahul Mehta as per court order dt. 20-08-2026');
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at, remarks) VALUES
(1, 21, 'ARRESTED', '2026-03-09 18:30:00', 'Arrested at residence');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(1, 31, 'I run a juice stall at Goodluck Chowk. At about 8:15 pm I saw two men on a black bike snatch a phone from a young man and speed towards Deccan.', '2026-03-06 11:00:00', 2, 0);
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by) VALUES
(1, 21, 'BNS', '309(4)', 'Robbery (snatching of mobile phone)', '2026-03-25', 2);
SET @current_officer_id = 1, @audit_time = '2026-03-28 12:00:00', @status_remarks = 'Charge-sheet filed before JMFC';
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 1;
INSERT INTO court_reference (complaint_id, court_case_no, court_name, court_type, filing_date, next_hearing_date, judge_name, case_stage, verdict) VALUES
(1, 'RCC-0451-2026', 'Judicial Magistrate First Class, Shivajinagar', 'MAGISTRATE', '2026-04-02', NULL, 'Hon. S. R. Kale', 'DISPOSED', 'CONVICTED');
SET @current_officer_id = 1, @audit_time = '2026-04-02 15:00:00', @status_remarks = 'Case committed to court';
UPDATE complaint SET status = 'IN_COURT' WHERE complaint_id = 1;
SET @current_officer_id = 1, @audit_time = '2026-08-20 18:00:00', @status_remarks = NULL;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-08-20', closure_type = 'CONVICTED',
       closure_remarks = 'Accused convicted by JMFC Shivajinagar; sentenced to 3 years RI and fine Rs 10,000.', closed_by = 1
 WHERE complaint_id = 1;
UPDATE assignment SET relieved_at = '2026-08-20 18:00:00' WHERE complaint_id = 1 AND relieved_at IS NULL;

-- =====================================================================
-- CASE 2 : House break-in, Model Colony -> IN_COURT
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(2, 1, 2, 'House break-in and jewellery theft at Model Colony',
 'Unknown persons broke the main door lock while the family was away and stole gold jewellery worth approx. Rs 4.2 lakh from the bedroom almirah.',
 'BURGLARY', 'HIGH', '2026-03-18 02:00:00', 'B-4, Model Colony, Shivajinagar, Pune', '2026-03-18 09:30:00', 1);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by, remarks) VALUES
(2, 2,  'LEAD',     '2026-03-18 10:00:00', 1, NULL),
(2, 15, 'FORENSIC', '2026-03-18 11:00:00', 1, 'Fingerprint lifting');
SET @current_officer_id = 1, @audit_time = '2026-03-18 10:05:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 2;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(2, 2,  'SITE_VISIT',          '2026-03-18 10:45:00', 'B-4, Model Colony', 'Spot panchnama prepared; main door lock found broken with a heavy tool.', 'Break-in confirmed'),
(2, 15, 'EVIDENCE_COLLECTION', '2026-03-18 12:00:00', 'B-4, Model Colony', 'Lifted latent fingerprints from almirah door and locker.', '4 usable prints lifted'),
(2, 15, 'FORENSIC_REQUEST',    '2026-03-19 11:00:00', 'RFSL Pune', 'Fingerprints forwarded to Regional Forensic Science Laboratory for comparison.', NULL),
(2, 2,  'INTERROGATION',       '2026-04-06 16:00:00', 'Shivajinagar PS', 'Questioned known property offender Rakesh Mane after fingerprint match.', 'Confessed and disclosed location of stolen gold'),
(2, 2,  'ARREST',              '2026-04-08 20:00:00', 'Hadapsar', 'Accused arrested; stolen jewellery recovered from rented room.', 'Recovery made');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(3, 2, 'FINGERPRINT',    'Latent fingerprints lifted from almirah and locker (4 lift cards)', 4, 'INTACT', 'SL-SHV-0003', '2026-03-18 12:30:00', 15, 'Bedroom almirah, B-4 Model Colony', '2026-03-18 13:00:00'),
(4, 2, 'CASH_VALUABLES', 'Recovered gold necklace (32 g) and two gold bangles (24 g)', 3, 'INTACT', 'SL-SHV-0004', '2026-04-08 21:00:00', 2, 'Accused rented room, Hadapsar', '2026-04-08 23:10:00'),
(5, 2, 'WEAPON',         'Iron crowbar (60 cm) used to break the door lock', 1, 'INTACT', 'SL-SHV-0005', '2026-04-08 21:15:00', 2, 'Accused rented room, Hadapsar', '2026-04-08 23:15:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(3, NULL, 15, 'B-4 Model Colony (scene)',              'INITIAL_SEIZURE',   '2026-03-18 12:30:00', '2026-03-18 18:00:00', 1, 'Lift cards sealed at scene'),
(3, 15,   4,  'Malkhana, Shivajinagar PS',              'STORAGE',           '2026-03-18 18:00:00', '2026-03-19 10:00:00', 1, NULL),
(3, 4,    15, 'Regional Forensic Science Laboratory, Pune', 'FORENSIC_ANALYSIS', '2026-03-19 10:00:00', '2026-04-15 15:00:00', 1, 'Sent for comparison with criminal records'),
(3, 15,   4,  'Malkhana, Shivajinagar PS',              'STORAGE',           '2026-04-15 15:00:00', NULL,                  1, 'Returned from RFSL with report'),
(4, NULL, 2,  'Accused rented room, Hadapsar',          'INITIAL_SEIZURE',   '2026-04-08 21:00:00', '2026-04-08 23:00:00', 1, NULL),
(4, 2,    4,  'Malkhana strong room, Shivajinagar PS',  'STORAGE',           '2026-04-08 23:00:00', NULL,                  1, 'Valuables kept in strong room'),
(5, NULL, 2,  'Accused rented room, Hadapsar',          'INITIAL_SEIZURE',   '2026-04-08 21:15:00', '2026-04-08 23:00:00', 1, NULL),
(5, 2,    4,  'Malkhana, Shivajinagar PS',              'STORAGE',           '2026-04-08 23:00:00', NULL,                  1, NULL);
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at, remarks) VALUES
(2, 22, 'ON_BAIL', '2026-04-08 20:00:00', 'Arrested 08-04-2026, bail granted 30-05-2026');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(2, 32, 'I am the night watchman of Model Colony. Around 2 am I saw a man in a dark jacket leaving B-4 carrying a bag. I could not see his face clearly.', '2026-03-18 13:30:00', 2, 0);
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by) VALUES
(2, 22, 'BNS', '331(4)', 'House-breaking by night', '2026-05-02', 2),
(2, 22, 'BNS', '305',    'Theft in a dwelling house', '2026-05-02', 2);
SET @current_officer_id = 1, @audit_time = '2026-05-04 12:00:00', @status_remarks = 'Charge-sheet submitted';
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 2;
INSERT INTO court_reference (complaint_id, court_case_no, court_name, court_type, filing_date, next_hearing_date, judge_name, case_stage, verdict) VALUES
(2, 'RCC-0782-2026', 'Judicial Magistrate First Class, Shivajinagar', 'MAGISTRATE', '2026-05-10', '2026-10-28', 'Hon. S. R. Kale', 'HEARING', 'PENDING');
SET @current_officer_id = 1, @audit_time = '2026-05-10 14:00:00', @status_remarks = 'Trial commenced';
UPDATE complaint SET status = 'IN_COURT' WHERE complaint_id = 2;

-- =====================================================================
-- CASE 3 : Two-wheeler theft, Kothrud -> CLOSED (solved)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(3, 2, 3, 'Two-wheeler stolen from society parking',
 'Honda Activa MH12 QX 4521 parked in the society parking was found missing in the morning. Handle lock was broken.',
 'VEHICLE_THEFT', 'MEDIUM', '2026-04-02 23:00:00', 'Mayur Colony society parking, Kothrud', '2026-04-03 10:15:00', 6);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(3, 6, 'LEAD', '2026-04-03 10:30:00', 5);
SET @current_officer_id = 5, @audit_time = '2026-04-03 10:35:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 3;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(3, 6, 'SITE_VISIT',  '2026-04-03 12:00:00', 'Mayur Colony', 'Inspected parking; society CCTV camera found facing the gate.', NULL),
(3, 6, 'CCTV_REVIEW', '2026-04-04 15:00:00', 'Mayur Colony society office', 'Footage shows a youth pushing the scooter out at 23:40 hrs.', 'Suspect identified through local informer'),
(3, 6, 'RAID',        '2026-04-11 06:00:00', 'Scrap yard, Chandni Chowk', 'Raid conducted at scrap yard where stolen vehicles are dismantled.', 'Vehicle found intact'),
(3, 6, 'ARREST',      '2026-04-11 07:30:00', 'Chandni Chowk', 'Accused Sunny Gill arrested.', NULL);
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(6, 3, 'VEHICLE', 'Honda Activa MH12 QX 4521, grey (recovered stolen vehicle)', 1, 'DAMAGED', NULL, '2026-04-11 07:45:00', 6, 'Scrap yard, Chandni Chowk', '2026-04-11 10:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(6, NULL, 6, 'Scrap yard, Chandni Chowk',      'INITIAL_SEIZURE', '2026-04-11 07:45:00', '2026-04-11 10:00:00', 1, NULL),
(6, 6,    8, 'Vehicle yard, Kothrud PS',       'STORAGE',         '2026-04-11 10:00:00', '2026-05-02 12:00:00', 1, NULL),
(6, 8,    6, 'Kothrud PS - handed to owner',   'RETURN_TO_OWNER', '2026-05-02 12:00:00', NULL,                  1, 'Released to owner on supurdnama under court order');
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(3, 23, 'ON_BAIL', '2026-04-11 07:30:00');
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by) VALUES
(3, 23, 'BNS', '303(2)', 'Theft of motor vehicle', '2026-04-20', 6);
SET @current_officer_id = 5, @audit_time = '2026-04-25 11:00:00', @status_remarks = 'Charge-sheet filed';
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 3;
SET @current_officer_id = 5, @audit_time = '2026-05-05 17:00:00', @status_remarks = NULL;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-05-05', closure_type = 'SOLVED',
       closure_remarks = 'Vehicle recovered and returned to owner; charge-sheet filed and case transferred to court records.', closed_by = 5
 WHERE complaint_id = 3;
UPDATE assignment SET relieved_at = '2026-05-05 17:00:00' WHERE complaint_id = 3 AND relieved_at IS NULL;

-- =====================================================================
-- CASE 4 : UPI fraud via fake KYC call -> CHARGE_SHEETED
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(4, 4, 4, 'UPI fraud of Rs 1.85 lakh via fake KYC call',
 'Caller posing as bank executive asked complainant to install a screen-sharing app for KYC update; Rs 1,85,000 debited in 6 UPI transactions.',
 'CYBER_CRIME', 'HIGH', '2026-04-11 16:20:00', 'Online - call received at Baner residence', '2026-04-12 11:00:00', 13);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(4, 13, 'LEAD',    '2026-04-12 11:15:00', 12),
(4, 14, 'SUPPORT', '2026-04-12 11:20:00', 12);
SET @current_officer_id = 12, @audit_time = '2026-04-12 11:30:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 4;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(4, 13, 'STATEMENT_RECORDED', '2026-04-12 12:00:00', 'Cyber PS', 'Detailed statement of complainant recorded with transaction IDs.', NULL),
(4, 14, 'OTHER',              '2026-04-12 15:00:00', 'Cyber PS', 'Freeze request sent to nodal officers of beneficiary banks and wallets.', 'Rs 62,000 frozen'),
(4, 14, 'OTHER',              '2026-04-25 11:00:00', 'Cyber PS', 'CDR, IMEI and IP logs analysed; location traced to Jamtara, Jharkhand.', 'Suspect located'),
(4, 13, 'RAID',               '2026-05-18 05:30:00', 'Karmatar, Jamtara, Jharkhand', 'Raid with local police at suspect house.', NULL),
(4, 13, 'ARREST',             '2026-05-18 07:00:00', 'Karmatar, Jamtara', 'Accused Pankaj Verma arrested; transit remand obtained.', 'Devices seized');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(7, 4, 'DOCUMENT',   'Certified bank statements & UPI transaction logs of complainant', 1, 'INTACT', 'SL-CYB-0001', '2026-04-14 13:00:00', 14, 'HDFC Bank, FC Road branch', '2026-04-14 17:05:00'),
(8, 4, 'ELECTRONIC', '2 mobile phones and 6 SIM cards seized from accused', 8, 'INTACT', 'SL-CYB-0002', '2026-05-18 07:30:00', 13, 'Accused house, Karmatar, Jamtara', '2026-05-21 14:10:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(7, NULL, 14, 'HDFC Bank, FC Road branch',          'INITIAL_SEIZURE',   '2026-04-14 13:00:00', '2026-04-14 17:00:00', 1, NULL),
(7, 14,   13, 'Evidence room, Cyber PS',            'STORAGE',           '2026-04-14 17:00:00', NULL,                  1, NULL),
(8, NULL, 13, 'Accused house, Jamtara',             'INITIAL_SEIZURE',   '2026-05-18 07:30:00', '2026-05-21 14:00:00', 1, 'Carried during transit remand'),
(8, 13,   14, 'Cyber Forensic Lab, CID Pune',       'FORENSIC_ANALYSIS', '2026-05-21 14:00:00', '2026-06-30 12:00:00', 1, 'Data extraction & analysis'),
(8, 14,   13, 'Evidence room, Cyber PS',            'STORAGE',           '2026-06-30 12:00:00', NULL,                  1, 'Forensic report received');
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(4, 24, 'ARRESTED', '2026-05-18 07:00:00');
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by) VALUES
(4, 24, 'BNS',    '318(4)', 'Cheating and dishonestly inducing delivery of property', '2026-08-10', 13),
(4, 24, 'IT Act', '66D',    'Cheating by personation using a computer resource', '2026-08-10', 13);
SET @current_officer_id = 12, @audit_time = '2026-08-14 16:00:00', @status_remarks = 'Charge-sheet filed in court';
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 4;

-- =====================================================================
-- CASE 5 : Laptop theft, IT park -> UNDER_INVESTIGATION (old pending)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(5, 3, 5, 'Laptop theft from IT park cafeteria',
 'Company laptop (Dell Latitude 7440) kept on a cafeteria table was stolen during lunch hour.',
 'THEFT', 'MEDIUM', '2026-04-19 13:30:00', 'Cafeteria, Tower B, Rajiv Gandhi Infotech Park Phase 1', '2026-04-20 10:00:00', 10);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(5, 10, 'LEAD',    '2026-04-20 10:20:00', 9),
(5, 11, 'SUPPORT', '2026-04-21 09:00:00', 9);
SET @current_officer_id = 9, @audit_time = '2026-04-20 10:25:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 5;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(5, 10, 'SITE_VISIT',         '2026-04-20 14:00:00', 'Tower B cafeteria', 'Visited cafeteria; collected visitor log of the day.', NULL),
(5, 11, 'CCTV_REVIEW',        '2026-04-22 11:00:00', 'IT park security control room', 'Footage shows a person in a grey hoodie picking up the bag.', 'Face not clear'),
(5, 10, 'STATEMENT_RECORDED', '2026-04-23 16:00:00', 'Hinjewadi PS', 'Statement of colleague Tanvi Bhatt recorded.', NULL);
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(9, 5, 'CCTV_FOOTAGE', 'CCTV footage of cafeteria 13:00-14:00 hrs (pen drive)', 1, 'INTACT', 'SL-HNJ-0001', '2026-04-22 12:00:00', 11, 'IT park security control room', '2026-04-22 18:10:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(9, NULL, 11, 'IT park security control room', 'INITIAL_SEIZURE', '2026-04-22 12:00:00', '2026-04-22 18:00:00', 1, NULL),
(9, 11,   10, 'Malkhana, Hinjewadi PS',        'STORAGE',         '2026-04-22 18:00:00', NULL,                  1, NULL);
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(5, 17, 'I was sitting with Karthik in the cafeteria. We went to the counter for about five minutes and when we returned the laptop bag was missing.', '2026-04-23 16:00:00', 10, 0);

-- =====================================================================
-- CASE 6 : Road-rage assault -> CLOSED (compromise)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(6, 2, 10, 'Assault during road rage incident at Paud Phata',
 'After a minor collision the car driver abused and hit the complainant with a steel water bottle causing injury on the forehead.',
 'ASSAULT', 'HIGH', '2026-05-04 19:45:00', 'Paud Phata signal, Kothrud', '2026-05-05 09:00:00', 7);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(6, 7, 'LEAD', '2026-05-05 09:15:00', 5);
SET @current_officer_id = 5, @audit_time = '2026-05-05 09:20:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 6;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(6, 7, 'MEDICAL_EXAM',       '2026-05-05 10:30:00', 'Sassoon General Hospital', 'Complainant sent for medical examination; MLC obtained.', 'Simple injury'),
(6, 7, 'STATEMENT_RECORDED', '2026-05-06 12:00:00', 'Kothrud PS', 'Statement of eye-witness Kiran Shetty recorded.', NULL),
(6, 7, 'INTERROGATION',      '2026-05-08 17:00:00', 'Kothrud PS', 'Accused Vijay Londhe questioned; notice under BNSS 35 served.', NULL);
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(10, 6, 'CLOTHING', 'Blood-stained white shirt of complainant', 1, 'PERISHABLE', 'SL-KTR-0001', '2026-05-05 11:00:00', 7, 'Sassoon General Hospital', '2026-05-05 15:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(10, NULL, 7, 'Sassoon General Hospital', 'INITIAL_SEIZURE', '2026-05-05 11:00:00', '2026-05-05 15:00:00', 1, NULL),
(10, 7,    8, 'Malkhana, Kothrud PS',     'STORAGE',         '2026-05-05 15:00:00', '2026-07-30 11:00:00', 1, NULL),
(10, 8,    7, 'Kothrud PS',               'DISPOSAL',        '2026-07-30 11:00:00', NULL,                  1, 'Destroyed as per magistrate order after compromise');
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(6, 25, 'RELEASED', '2026-05-08 17:00:00');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(6, 33, 'I was waiting at the signal. After the bikes touched, the car driver came out and hit the rider with a steel bottle.', '2026-05-06 12:00:00', 7, 0);
SET @current_officer_id = 5, @audit_time = '2026-06-15 13:00:00', @status_remarks = NULL;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-06-15', closure_type = 'COMPROMISE',
       closure_remarks = 'Parties compromised before Lok Adalat; offence compoundable; complaint withdrawn.', closed_by = 5
 WHERE complaint_id = 6;
UPDATE assignment SET relieved_at = '2026-06-15 13:00:00' WHERE complaint_id = 6 AND relieved_at IS NULL;

-- =====================================================================
-- CASE 7 : Ganja seizure -> IN_COURT
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(7, 1, 7, 'Sale of ganja from paan shop near bus stand',
 'Local resident informed that ganja is being sold to college students from a paan shop near Shivajinagar bus stand.',
 'NARCOTICS', 'CRITICAL', '2026-05-14 15:30:00', 'Paan shop near Shivajinagar bus stand', '2026-05-14 16:00:00', 1);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(7, 3, 'LEAD',    '2026-05-14 16:10:00', 1),
(7, 2, 'SUPPORT', '2026-05-14 16:10:00', 1);
SET @current_officer_id = 1, @audit_time = '2026-05-14 16:15:00', @status_remarks = 'Raid team formed';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 7;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(7, 3, 'RAID',   '2026-05-14 17:30:00', 'Paan shop near bus stand', 'Raid conducted with two independent panchas and gazetted officer.', '1.2 kg ganja found'),
(7, 3, 'ARREST', '2026-05-14 18:00:00', 'Paan shop near bus stand', 'Shop owner Babu Shaikh arrested under NDPS Act.', NULL),
(7, 2, 'FORENSIC_REQUEST', '2026-05-16 10:30:00', 'RFSL Pune', 'Representative samples sent to RFSL for chemical analysis.', NULL);
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(11, 7, 'NARCOTIC',       'Ganja (dry leaves) 1.2 kg in 6 plastic packets', 6, 'INTACT', 'SL-SHV-0006', '2026-05-14 17:45:00', 3, 'Paan shop near Shivajinagar bus stand', '2026-05-14 21:10:00'),
(12, 7, 'CASH_VALUABLES', 'Cash Rs 18,450 recovered from shop counter', 1, 'INTACT', 'SL-SHV-0007', '2026-05-14 17:50:00', 3, 'Paan shop near Shivajinagar bus stand', '2026-05-14 21:15:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(11, NULL, 3,  'Paan shop (raid site)',              'INITIAL_SEIZURE',   '2026-05-14 17:45:00', '2026-05-14 21:00:00', 1, 'Seized under NDPS panchnama'),
(11, 3,    4,  'Malkhana, Shivajinagar PS',          'STORAGE',           '2026-05-14 21:00:00', '2026-05-16 10:00:00', 1, NULL),
(11, 4,    15, 'RFSL Pune - Narcotics division',     'FORENSIC_ANALYSIS', '2026-05-16 10:00:00', '2026-06-05 16:00:00', 1, 'Samples A1-A6 for chemical analysis'),
(11, 15,   4,  'Malkhana, Shivajinagar PS',          'STORAGE',           '2026-06-05 16:00:00', NULL,                  1, 'RFSL report: positive for cannabis'),
(12, NULL, 3,  'Paan shop (raid site)',              'INITIAL_SEIZURE',   '2026-05-14 17:50:00', '2026-05-14 21:00:00', 1, NULL),
(12, 3,    4,  'Malkhana strong room, Shivajinagar PS', 'STORAGE',        '2026-05-14 21:00:00', NULL,                  1, NULL);
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(7, 26, 'ARRESTED', '2026-05-14 18:00:00');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(7, 34, 'I was called as an independent panch. In my presence police recovered six packets of a green leafy substance from the shop drawer.', '2026-05-14 20:00:00', 3, 1),
(7, 37, 'I am the second panch witness. The packets were weighed, sealed and signed by me in the presence of the accused.', '2026-05-14 20:15:00', 3, 1);
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by) VALUES
(7, 26, 'NDPS Act', '20(b)(ii)(B)', 'Possession and sale of ganja (intermediate quantity)', '2026-07-01', 3);
SET @current_officer_id = 1, @audit_time = '2026-07-05 12:00:00', @status_remarks = 'Charge-sheet filed in Special NDPS court';
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 7;
INSERT INTO court_reference (complaint_id, court_case_no, court_name, court_type, filing_date, next_hearing_date, judge_name, case_stage, verdict) VALUES
(7, 'NDPS-SC-0088-2026', 'Special NDPS Court, Pune', 'SPECIAL', '2026-07-10', '2026-10-22', 'Hon. A. M. Deshpande', 'HEARING', 'PENDING');
SET @current_officer_id = 1, @audit_time = '2026-07-10 15:00:00', @status_remarks = 'Trial before Special Court';
UPDATE complaint SET status = 'IN_COURT' WHERE complaint_id = 7;

-- =====================================================================
-- CASE 8 : Missing minor -> CLOSED (traced)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(8, 3, 8, 'Missing person - 17 year old student',
 'Complainant''s son Aditya (17) left for tuition and did not return home. Phone switched off.',
 'MISSING_PERSON', 'CRITICAL', '2026-05-31 18:00:00', 'Last seen near Wakad bus stop', '2026-06-01 08:30:00', 9);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(8, 9,  'LEAD',    '2026-06-01 08:45:00', 9),
(8, 10, 'SUPPORT', '2026-06-01 08:45:00', 9);
SET @current_officer_id = 9, @audit_time = '2026-06-01 08:50:00', @status_remarks = 'Search initiated';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 8;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(8, 9,  'STATEMENT_RECORDED', '2026-06-01 09:30:00', 'Hinjewadi PS', 'Statement of father recorded; photograph collected.', NULL),
(8, 10, 'CCTV_REVIEW',        '2026-06-01 15:00:00', 'Wakad bus stop', 'Boy seen boarding a bus towards Lonavala at 18:40 hrs.', 'Direction established'),
(8, 10, 'OTHER',              '2026-06-01 17:00:00', 'Hinjewadi PS', 'Missing person alert circulated on CCTNS, railway police and social media.', NULL),
(8, 9,  'OTHER',              '2026-06-03 11:00:00', 'Lonavala railway station', 'Boy traced by GRP Lonavala and brought back safely.', 'Traced');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(13, 8, 'DOCUMENT', 'Recent photograph and school ID card of missing person', 2, 'INTACT', NULL, '2026-06-01 09:45:00', 9, 'Complainant (father)', '2026-06-01 12:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(13, NULL, 9,  'Hinjewadi PS',               'INITIAL_SEIZURE', '2026-06-01 09:45:00', '2026-06-01 12:00:00', 1, NULL),
(13, 9,    11, 'Records room, Hinjewadi PS', 'STORAGE',         '2026-06-01 12:00:00', '2026-06-10 10:00:00', 1, NULL),
(13, 11,   9,  'Hinjewadi PS',               'RETURN_TO_OWNER', '2026-06-10 10:00:00', NULL,                  1, 'Returned to father');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(8, 39, 'I was upset about my exam results and went to Lonavala on my own. Nobody forced or harmed me.', '2026-06-03 16:00:00', 9, 1);
SET @current_officer_id = 9, @audit_time = '2026-06-05 12:00:00', @status_remarks = NULL;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-06-05', closure_type = 'SOLVED',
       closure_remarks = 'Missing minor traced at Lonavala and reunited with family; no foul play found.', closed_by = 9
 WHERE complaint_id = 8;
UPDATE assignment SET relieved_at = '2026-06-05 12:00:00' WHERE complaint_id = 8 AND relieved_at IS NULL;

-- =====================================================================
-- CASE 9 : Online job scam -> UNDER_INVESTIGATION
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(9, 4, 9, 'Online part-time job scam via Telegram',
 'Complainant was lured into "like and review" tasks on Telegram and paid Rs 74,000 as investment for higher returns.',
 'CYBER_CRIME', 'MEDIUM', '2026-06-08 12:00:00', 'Online - Telegram group', '2026-06-10 12:00:00', 14);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(9, 14, 'LEAD', '2026-06-10 12:30:00', 12);
SET @current_officer_id = 12, @audit_time = '2026-06-10 12:40:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 9;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(9, 14, 'STATEMENT_RECORDED', '2026-06-10 13:00:00', 'Cyber PS', 'Statement recorded; chat screenshots and receipts collected.', NULL),
(9, 14, 'OTHER',              '2026-06-15 11:00:00', 'Cyber PS', 'Requested subscriber details from Telegram and KYC of mule bank accounts.', 'Awaiting response');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(14, 9, 'DOCUMENT', 'Screenshots of Telegram chats and payment receipts (printout + CD)', 1, 'INTACT', 'SL-CYB-0003', '2026-06-10 13:30:00', 14, 'Complainant', '2026-06-10 18:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(14, NULL, 14, 'Cyber PS',                'INITIAL_SEIZURE', '2026-06-10 13:30:00', '2026-06-10 18:00:00', 1, NULL),
(14, 14,   13, 'Evidence room, Cyber PS', 'STORAGE',         '2026-06-10 18:00:00', NULL,                  1, NULL);

-- =====================================================================
-- CASE 10 : Chain snatching, Karve Road -> UNDER_INVESTIGATION
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(10, 2, 11, 'Gold chain snatched during morning walk',
 'Two youths on a scooter snatched the complainant''s 20 g gold mangalsutra during her morning walk.',
 'ROBBERY', 'HIGH', '2026-06-21 07:10:00', 'Karve Road near Nal Stop', '2026-06-21 09:00:00', 6);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(10, 6, 'LEAD',    '2026-06-21 09:10:00', 5),
(10, 7, 'SUPPORT', '2026-06-21 09:10:00', 5);
SET @current_officer_id = 5, @audit_time = '2026-06-21 09:15:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 10;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(10, 6, 'SITE_VISIT',    '2026-06-21 10:00:00', 'Nal Stop, Karve Road', 'Spot inspection and enquiry with morning walkers.', NULL),
(10, 7, 'CCTV_REVIEW',   '2026-06-22 12:00:00', 'Nal Stop junction', 'Smart-city camera footage reviewed; scooter without number plate seen.', NULL),
(10, 6, 'INTERROGATION', '2026-07-15 15:00:00', 'Kothrud PS', 'Two habitual chain snatchers questioned.', 'No link established');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(15, 10, 'CCTV_FOOTAGE', 'CCTV footage from Nal Stop junction cameras (07:00-07:30)', 1, 'INTACT', 'SL-KTR-0002', '2026-06-22 12:30:00', 7, 'Smart City control room', '2026-06-22 16:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(15, NULL, 7, 'Smart City control room', 'INITIAL_SEIZURE', '2026-06-22 12:30:00', '2026-06-22 16:00:00', 1, NULL),
(15, 7,    8, 'Malkhana, Kothrud PS',    'STORAGE',         '2026-06-22 16:00:00', NULL,                  1, NULL);
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(10, 36, 'I was walking behind the lady. Two boys on a white scooter came from behind, the pillion rider pulled her chain and they fled towards Paud Phata.', '2026-06-21 11:00:00', 6, 0);

-- =====================================================================
-- CASE 11 : Harassment calls -> CLOSED (insufficient evidence)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(11, 1, 13, 'Harassment through anonymous calls',
 'Complainant has been receiving repeated obscene calls from unknown international numbers for two weeks.',
 'HARASSMENT', 'MEDIUM', '2026-07-01 21:00:00', 'Complainant residence, Kothrud', '2026-07-03 11:00:00', 2);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(11, 3, 'LEAD', '2026-07-03 11:20:00', 1);
SET @current_officer_id = 1, @audit_time = '2026-07-03 11:30:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 11;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(11, 3, 'STATEMENT_RECORDED', '2026-07-03 12:00:00', 'Shivajinagar PS', 'Statement recorded with list of calling numbers.', NULL),
(11, 3, 'OTHER',              '2026-07-10 15:00:00', 'Shivajinagar PS', 'CDR requested from telecom service provider.', NULL),
(11, 3, 'OTHER',              '2026-08-20 16:00:00', 'Shivajinagar PS', 'Numbers found to be routed through foreign VoIP gateways.', 'No identifiable suspect');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(16, 11, 'DOCUMENT', 'Call log printouts and CDR report', 1, 'INTACT', NULL, '2026-07-10 15:30:00', 3, 'Telecom nodal officer (by email)', '2026-07-10 18:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(16, NULL, 3, 'Shivajinagar PS',           'INITIAL_SEIZURE', '2026-07-10 15:30:00', '2026-07-10 18:00:00', 1, NULL),
(16, 3,    4, 'Malkhana, Shivajinagar PS', 'STORAGE',         '2026-07-10 18:00:00', NULL,                  1, NULL);
SET @current_officer_id = 1, @audit_time = '2026-08-28 17:30:00', @status_remarks = NULL;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-08-28', closure_type = 'INSUFFICIENT_EVIDENCE',
       closure_remarks = 'Calls routed via foreign VoIP; suspect untraceable. Complainant informed; number blocked.', closed_by = 1
 WHERE complaint_id = 11;
UPDATE assignment SET relieved_at = '2026-08-28 17:30:00' WHERE complaint_id = 11 AND relieved_at IS NULL;

-- =====================================================================
-- CASE 12 : Warehouse burglary -> CHARGE_SHEETED
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(12, 3, 12, 'Burglary at electronics warehouse',
 'Shutter lock of the warehouse was cut and 14 LED TVs and 9 laptops worth Rs 11 lakh were stolen at night.',
 'BURGLARY', 'HIGH', '2026-07-14 01:30:00', 'Sayyed Electronics warehouse, Maan Road, Hinjewadi', '2026-07-15 08:00:00', 10);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(12, 10, 'LEAD',     '2026-07-15 08:15:00', 9),
(12, 11, 'SUPPORT',  '2026-07-15 08:15:00', 9),
(12, 15, 'FORENSIC', '2026-07-15 10:00:00', 9);
SET @current_officer_id = 9, @audit_time = '2026-07-15 08:20:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 12;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(12, 10, 'SITE_VISIT',          '2026-07-15 09:00:00', 'Warehouse, Maan Road', 'Spot panchnama; shutter lock cut with gas cutter.', NULL),
(12, 15, 'EVIDENCE_COLLECTION', '2026-07-15 11:00:00', 'Warehouse, Maan Road', 'Fingerprints lifted from shutter and lock.', '3 prints lifted'),
(12, 11, 'CCTV_REVIEW',         '2026-07-16 14:00:00', 'Maan Road', 'Tempo MH14 GU 3341 seen near warehouse at 01:20 hrs.', 'Vehicle traced to Chakan'),
(12, 10, 'RAID',                '2026-07-28 04:30:00', 'Godown, Chakan MIDC', 'Raid at rented godown in Chakan MIDC.', 'Stolen goods found'),
(12, 10, 'ARREST',              '2026-07-28 06:00:00', 'Chakan MIDC', 'Accused Raju Kamble and Nitin Bhalerao arrested.', NULL);
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(17, 12, 'FINGERPRINT', 'Fingerprints lifted from shutter lock (3 lift cards)', 3, 'INTACT', 'SL-HNJ-0002', '2026-07-15 11:30:00', 15, 'Warehouse shutter, Maan Road', '2026-07-15 18:05:00'),
(18, 12, 'ELECTRONIC',  'Recovered stolen property: 14 LED TVs and 9 laptops', 23, 'PARTIAL', 'SL-HNJ-0003', '2026-07-28 07:00:00', 10, 'Godown, Chakan MIDC', '2026-07-28 12:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(17, NULL, 15, 'Warehouse (scene)',               'INITIAL_SEIZURE',   '2026-07-15 11:30:00', '2026-07-15 18:00:00', 1, NULL),
(17, 15,   11, 'Malkhana, Hinjewadi PS',          'STORAGE',           '2026-07-15 18:00:00', '2026-07-17 10:00:00', 1, NULL),
(17, 11,   15, 'Regional Forensic Science Laboratory, Pune', 'FORENSIC_ANALYSIS', '2026-07-17 10:00:00', NULL, 1, 'Awaiting fingerprint bureau report'),
(18, NULL, 10, 'Godown, Chakan MIDC',             'INITIAL_SEIZURE',   '2026-07-28 07:00:00', '2026-07-28 12:00:00', 1, NULL),
(18, 10,   11, 'Strong room, Hinjewadi PS',       'STORAGE',           '2026-07-28 12:00:00', NULL,                  1, '2 laptops missing from recovered lot');
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(12, 27, 'ARRESTED', '2026-07-28 06:00:00'),
(12, 28, 'ON_BAIL',  '2026-07-28 06:00:00');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(12, 35, 'I am the security guard of the adjacent unit. At around 1:15 am I saw a tempo with its lights off near the warehouse and three men unloading tools.', '2026-07-15 12:00:00', 10, 0);
INSERT INTO charge (complaint_id, accused_person_id, act_name, section_code, offence_description, charged_on, charged_by) VALUES
(12, 27, 'BNS', '331(4)', 'House-breaking by night',                     '2026-09-20', 10),
(12, 27, 'BNS', '303(2)', 'Theft',                                       '2026-09-20', 10),
(12, 28, 'BNS', '317(2)', 'Dishonestly receiving stolen property',       '2026-09-20', 10);
SET @current_officer_id = 9, @audit_time = '2026-09-25 13:00:00', @status_remarks = 'Charge-sheet submitted';
UPDATE complaint SET status = 'CHARGE_SHEETED' WHERE complaint_id = 12;

-- =====================================================================
-- CASE 13 : Domestic violence -> UNDER_INVESTIGATION
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(13, 2, 40, 'Domestic violence by husband',
 'Complainant alleges repeated physical abuse and threats by her husband; latest incident on the night of 1st August.',
 'DOMESTIC_VIOLENCE', 'HIGH', '2026-08-01 22:00:00', 'Shastri Nagar, Kothrud', '2026-08-02 10:00:00', 7);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(13, 7, 'LEAD', '2026-08-02 10:15:00', 5);
SET @current_officer_id = 5, @audit_time = '2026-08-02 10:20:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 13;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(13, 7, 'STATEMENT_RECORDED', '2026-08-02 11:00:00', 'Kothrud PS', 'Statement recorded in presence of woman constable.', NULL),
(13, 7, 'MEDICAL_EXAM',       '2026-08-02 14:00:00', 'Sassoon General Hospital', 'Medical examination conducted; MLC collected.', 'Contusions on arms'),
(13, 7, 'OTHER',              '2026-08-10 11:00:00', 'Bharosa Cell, Pune', 'Counselling session arranged for both parties.', 'Husband refused to attend');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(19, 13, 'DOCUMENT', 'Medico-legal certificate (MLC) from Sassoon Hospital', 1, 'INTACT', NULL, '2026-08-02 16:00:00', 7, 'Sassoon General Hospital', '2026-08-02 18:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(19, NULL, 7, 'Sassoon General Hospital', 'INITIAL_SEIZURE', '2026-08-02 16:00:00', '2026-08-02 18:00:00', 1, NULL),
(19, 7,    8, 'Malkhana, Kothrud PS',     'STORAGE',         '2026-08-02 18:00:00', NULL,                  1, NULL);
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(13, 29, 'SUSPECT', '2026-08-02 11:00:00');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(13, 38, 'I live next door. I have often heard shouting and crying from their flat late at night, including on 1st August.', '2026-08-03 12:00:00', 7, 1);

-- =====================================================================
-- CASE 14 : Card cloning at petrol pump -> UNDER_INVESTIGATION
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(14, 4, 14, 'Credit card cloned at petrol pump',
 'Two unauthorised transactions of Rs 48,000 at Mumbai merchants within an hour of card use at a petrol pump in Aundh.',
 'FRAUD', 'HIGH', '2026-08-17 19:00:00', 'Petrol pump, Aundh-Baner Road', '2026-08-19 11:00:00', 12);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(14, 12, 'LEAD',    '2026-08-19 11:10:00', 12),
(14, 14, 'SUPPORT', '2026-08-19 11:10:00', 12);
SET @current_officer_id = 12, @audit_time = '2026-08-19 11:15:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 14;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(14, 12, 'STATEMENT_RECORDED', '2026-08-19 11:30:00', 'Cyber PS', 'Statement recorded with card statement.', NULL),
(14, 14, 'SITE_VISIT',         '2026-08-20 10:00:00', 'Petrol pump, Aundh', 'Visited pump; POS machine and staff details collected.', NULL),
(14, 14, 'CCTV_REVIEW',        '2026-08-20 13:00:00', 'Petrol pump, Aundh', 'Attendant seen swiping card twice on two devices.', 'Suspect attendant identified'),
(14, 12, 'RAID',               '2026-09-02 13:00:00', 'Petrol pump, Aundh', 'Surprise check of POS terminals.', 'Skimmer found');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(20, 14, 'ELECTRONIC', 'Card skimmer device concealed inside POS machine', 1, 'INTACT', 'SL-CYB-0004', '2026-09-02 13:30:00', 12, 'Petrol pump, Aundh', '2026-09-02 17:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(20, NULL, 12, 'Petrol pump, Aundh',            'INITIAL_SEIZURE',   '2026-09-02 13:30:00', '2026-09-02 17:00:00', 1, NULL),
(20, 12,   13, 'Evidence room, Cyber PS',       'STORAGE',           '2026-09-02 17:00:00', '2026-09-05 10:00:00', 1, NULL),
(20, 13,   14, 'Cyber Forensic Lab, CID Pune',  'FORENSIC_ANALYSIS', '2026-09-05 10:00:00', NULL,                  1, 'Memory dump of skimmer requested');
INSERT INTO witness (complaint_id, person_id, statement, statement_date, recorded_by, is_protected) VALUES
(14, 6, 'I work at the same pump. I saw my colleague use a small black device under the counter while billing cards.', '2026-08-20 14:00:00', 14, 1);

-- =====================================================================
-- CASE 15 : Bicycle theft -> CLOSED (untraced)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(15, 1, 15, 'Bicycle stolen outside university library',
 'Firefox Bad Attitude bicycle locked outside Jaykar Library was stolen in the evening.',
 'THEFT', 'LOW', '2026-09-04 17:00:00', 'Outside Jaykar Library, SPPU campus', '2026-09-05 10:00:00', 3);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(15, 3, 'LEAD', '2026-09-05 10:15:00', 1);
SET @current_officer_id = 1, @audit_time = '2026-09-05 10:20:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 15;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(15, 3, 'SITE_VISIT',  '2026-09-05 12:00:00', 'Jaykar Library', 'Spot visited; enquiry with security guards.', NULL),
(15, 3, 'CCTV_REVIEW', '2026-09-08 11:00:00', 'SPPU security office', 'No CCTV coverage at the cycle stand.', 'No lead');
SET @current_officer_id = 1, @audit_time = '2026-10-05 16:00:00', @status_remarks = NULL;
UPDATE complaint SET status = 'CLOSED', closure_date = '2026-10-05', closure_type = 'UNTRACED',
       closure_remarks = 'Property untraced despite enquiry; A-summary report submitted to court.', closed_by = 1
 WHERE complaint_id = 15;
UPDATE assignment SET relieved_at = '2026-10-05 16:00:00' WHERE complaint_id = 15 AND relieved_at IS NULL;

-- =====================================================================
-- CASE 16 : Property sale cheating -> UNDER_INVESTIGATION
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(16, 3, 16, 'Cheating in sale of flat using forged documents',
 'Accused took Rs 18 lakh as advance for a flat in Wakad using a forged sale agreement; the flat actually belongs to someone else.',
 'FRAUD', 'MEDIUM', '2026-08-30 12:00:00', 'Wakad', '2026-09-18 12:00:00', 9);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(16, 9, 'LEAD', '2026-09-18 12:15:00', 9);
SET @current_officer_id = 9, @audit_time = '2026-09-18 12:20:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 16;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(16, 9, 'STATEMENT_RECORDED', '2026-09-18 13:00:00', 'Hinjewadi PS', 'Statement recorded; documents collected.', NULL),
(16, 9, 'OTHER',              '2026-09-25 11:00:00', 'Sub-Registrar Office, Haveli', 'Index-II records verified; flat registered in a third person''s name.', 'Forgery confirmed');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(21, 16, 'DOCUMENT', 'Forged sale agreement and payment receipts', 3, 'INTACT', 'SL-HNJ-0004', '2026-09-18 13:30:00', 9, 'Complainant', '2026-09-18 17:05:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(21, NULL, 9,  'Hinjewadi PS',           'INITIAL_SEIZURE', '2026-09-18 13:30:00', '2026-09-18 17:00:00', 1, NULL),
(21, 9,    11, 'Malkhana, Hinjewadi PS', 'STORAGE',         '2026-09-18 17:00:00', NULL,                  1, NULL);
INSERT INTO complaint_accused (complaint_id, person_id, accused_status, added_at) VALUES
(16, 30, 'ABSCONDING', '2026-09-18 13:00:00');

-- =====================================================================
-- CASE 17 : Shop burglary -> REGISTERED (unassigned)
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(17, 2, 18, 'Shop burglary at Kothrud market',
 'Shop shutter found half open in the morning; cash box with approx. Rs 35,000 and cigarette cartons missing.',
 'BURGLARY', 'MEDIUM', '2026-10-01 03:00:00', 'Ghule General Stores, Kothrud market', '2026-10-02 09:00:00', 5);

-- =====================================================================
-- CASE 18 : Wallet theft -> REGISTERED
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(18, 1, 1, 'Wallet with documents stolen in PMPML bus',
 'Wallet containing Rs 3,200, driving licence and two debit cards stolen while travelling in a crowded bus.',
 'THEFT', 'LOW', '2026-10-09 18:30:00', 'PMPML bus route 94, Shivajinagar', '2026-10-10 11:00:00', 2);

-- =====================================================================
-- CASE 19 : Instagram hacking & extortion -> UNDER_INVESTIGATION
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(19, 4, 19, 'Instagram account hacked and money demanded',
 'Complainant''s Instagram account was hacked; the hacker is demanding Rs 25,000 to return access and threatening to post private photos.',
 'CYBER_CRIME', 'HIGH', '2026-10-11 22:00:00', 'Online - Instagram', '2026-10-12 10:00:00', 13);
INSERT INTO assignment (complaint_id, officer_id, assignment_role, assigned_at, assigned_by) VALUES
(19, 13, 'LEAD', '2026-10-12 10:20:00', 12);
SET @current_officer_id = 12, @audit_time = '2026-10-12 10:25:00', @status_remarks = 'Investigation started';
UPDATE complaint SET status = 'UNDER_INVESTIGATION' WHERE complaint_id = 19;
INSERT INTO investigation_activity (complaint_id, officer_id, activity_type, activity_time, location, description, outcome) VALUES
(19, 13, 'STATEMENT_RECORDED', '2026-10-12 11:00:00', 'Cyber PS', 'Statement and screenshots of extortion messages collected.', NULL),
(19, 13, 'OTHER',              '2026-10-13 15:00:00', 'Cyber PS', 'Preservation and disclosure request sent to Meta.', 'Awaiting response');
INSERT INTO evidence_item (evidence_id, complaint_id, category, description, quantity, item_condition, seal_no, collected_at, collected_by, collected_from, registered_at) VALUES
(22, 19, 'DOCUMENT', 'Screenshots of extortion messages and hacker profile (printout + CD)', 1, 'INTACT', 'SL-CYB-0005', '2026-10-12 11:30:00', 13, 'Complainant', '2026-10-12 11:35:00');
INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at, released_at, seal_intact, remarks) VALUES
(22, NULL, 13, 'Cyber PS', 'INITIAL_SEIZURE', '2026-10-12 11:30:00', NULL, 1, 'With IO for analysis');

-- =====================================================================
-- CASE 20 : Hit and run -> REGISTERED
-- =====================================================================
INSERT INTO complaint (complaint_id, station_id, complainant_id, title, description, category, priority,
                       incident_datetime, incident_location, registered_at, registered_by) VALUES
(20, 3, 20, 'Hit and run near Wakad bridge',
 'An unidentified car hit the complainant''s father on the service road and fled. Victim admitted to hospital with leg fracture.',
 'OTHER', 'HIGH', '2026-10-14 21:00:00', 'Wakad bridge service road', '2026-10-14 23:00:00', 10);

-- ---------------------------------------------------------------------
-- Application users  (demo passwords - see README)
--   admin / admin123   vikram, meera, rajesh, kavita / sho123
--   anjali, arjun, sneha, nikhil / io123   suresh, ganesh / custody123
-- ---------------------------------------------------------------------
INSERT INTO app_user (username, password_hash, user_role, officer_id) VALUES
('admin',  'pbkdf2:sha256:260000$egCWgo2hBowiTyGx$10069df5a9527f85aae6aa62cf3061808a7b2ed951f5d025ed46bd981592d092', 'ADMIN', NULL),
('vikram', 'pbkdf2:sha256:260000$saE5FJtt6Pnx8dC6$8c99d3d8a993af45060161138f6e03f9c055ede6e7ccf42c8765a9ca76fe9daf', 'SHO', 1),
('meera',  'pbkdf2:sha256:260000$saE5FJtt6Pnx8dC6$8c99d3d8a993af45060161138f6e03f9c055ede6e7ccf42c8765a9ca76fe9daf', 'SHO', 5),
('rajesh', 'pbkdf2:sha256:260000$saE5FJtt6Pnx8dC6$8c99d3d8a993af45060161138f6e03f9c055ede6e7ccf42c8765a9ca76fe9daf', 'SHO', 9),
('kavita', 'pbkdf2:sha256:260000$saE5FJtt6Pnx8dC6$8c99d3d8a993af45060161138f6e03f9c055ede6e7ccf42c8765a9ca76fe9daf', 'SHO', 12),
('anjali', 'pbkdf2:sha256:260000$iz4YOEySEN1eY0IZ$886b05f87cbe9552396d95790dd118f61f49ecee50aafac10e86e0d6660cd7d6', 'IO', 2),
('arjun',  'pbkdf2:sha256:260000$iz4YOEySEN1eY0IZ$886b05f87cbe9552396d95790dd118f61f49ecee50aafac10e86e0d6660cd7d6', 'IO', 6),
('sneha',  'pbkdf2:sha256:260000$iz4YOEySEN1eY0IZ$886b05f87cbe9552396d95790dd118f61f49ecee50aafac10e86e0d6660cd7d6', 'IO', 10),
('nikhil', 'pbkdf2:sha256:260000$iz4YOEySEN1eY0IZ$886b05f87cbe9552396d95790dd118f61f49ecee50aafac10e86e0d6660cd7d6', 'IO', 13),
('suresh', 'pbkdf2:sha256:260000$6ihlVQtWlGgDH4FB$b63b54b977cc8ab68928c752ef61a2f54dd75bd24a277db2083f3fcb5b41566c', 'CUSTODIAN', 4),
('ganesh', 'pbkdf2:sha256:260000$6ihlVQtWlGgDH4FB$b63b54b977cc8ab68928c752ef61a2f54dd75bd24a277db2083f3fcb5b41566c', 'CUSTODIAN', 8);

SET @current_officer_id = NULL, @audit_time = NULL, @status_remarks = NULL;
