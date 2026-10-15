-- =====================================================================
--  Police Complaint & Evidence Tracking System (PCETS)
--  00 - Create database
--  Run this first when executing the scripts manually (MySQL Workbench /
--  mysql CLI). setup_db.py does this step automatically.
-- =====================================================================
DROP DATABASE IF EXISTS police_evidence_db;
CREATE DATABASE police_evidence_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;
USE police_evidence_db;
