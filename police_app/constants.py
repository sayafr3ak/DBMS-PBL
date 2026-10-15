"""Domain constants shared by services, routes and templates (mirror the DB CHECK lists)."""
from collections import OrderedDict

STATUSES = OrderedDict([
    ("REGISTERED", "Registered"),
    ("UNDER_INVESTIGATION", "Under Investigation"),
    ("CHARGE_SHEETED", "Charge-sheeted"),
    ("IN_COURT", "In Court"),
    ("CLOSED", "Closed"),
])

# workflow - must match trigger trg_complaint_bu
TRANSITIONS = {
    "REGISTERED": ["UNDER_INVESTIGATION", "CLOSED"],
    "UNDER_INVESTIGATION": ["CHARGE_SHEETED", "CLOSED"],
    "CHARGE_SHEETED": ["IN_COURT", "CLOSED"],
    "IN_COURT": ["CLOSED"],
    "CLOSED": ["UNDER_INVESTIGATION"],
}

CATEGORIES = OrderedDict([
    ("THEFT", "Theft"), ("BURGLARY", "Burglary"), ("ROBBERY", "Robbery"), ("ASSAULT", "Assault"),
    ("FRAUD", "Fraud"), ("CYBER_CRIME", "Cyber Crime"), ("MISSING_PERSON", "Missing Person"),
    ("NARCOTICS", "Narcotics"), ("VEHICLE_THEFT", "Vehicle Theft"), ("HARASSMENT", "Harassment"),
    ("DOMESTIC_VIOLENCE", "Domestic Violence"), ("OTHER", "Other"),
])

PRIORITIES = OrderedDict([("LOW", "Low"), ("MEDIUM", "Medium"), ("HIGH", "High"), ("CRITICAL", "Critical")])

CLOSURE_TYPES = OrderedDict([
    ("SOLVED", "Solved / detected"), ("CONVICTED", "Accused convicted"), ("ACQUITTED", "Accused acquitted"),
    ("FALSE_COMPLAINT", "False complaint"), ("INSUFFICIENT_EVIDENCE", "Insufficient evidence"),
    ("COMPROMISE", "Compromise / withdrawn"), ("UNTRACED", "Untraced (A-summary)"),
    ("TRANSFERRED", "Transferred to other unit"),
])

ASSIGNMENT_ROLES = OrderedDict([("LEAD", "Lead IO"), ("SUPPORT", "Support"), ("FORENSIC", "Forensic"),
                                ("SURVEILLANCE", "Surveillance")])

ACTIVITY_TYPES = OrderedDict([
    ("SITE_VISIT", "Site visit"), ("STATEMENT_RECORDED", "Statement recorded"),
    ("INTERROGATION", "Interrogation"), ("RAID", "Raid"), ("ARREST", "Arrest"),
    ("EVIDENCE_COLLECTION", "Evidence collection"), ("FORENSIC_REQUEST", "Forensic request"),
    ("CCTV_REVIEW", "CCTV review"), ("MEDICAL_EXAM", "Medical examination"), ("OTHER", "Other"),
])

EVIDENCE_CATEGORIES = OrderedDict([
    ("WEAPON", "Weapon"), ("DOCUMENT", "Document"), ("ELECTRONIC", "Electronic device"),
    ("BIOLOGICAL", "Biological sample"), ("NARCOTIC", "Narcotic substance"), ("VEHICLE", "Vehicle"),
    ("CCTV_FOOTAGE", "CCTV footage"), ("FINGERPRINT", "Fingerprint"), ("CLOTHING", "Clothing"),
    ("CASH_VALUABLES", "Cash / valuables"), ("OTHER", "Other"),
])

CONDITIONS = OrderedDict([("INTACT", "Intact"), ("DAMAGED", "Damaged"), ("PARTIAL", "Partial"),
                          ("PERISHABLE", "Perishable")])

CUSTODY_PURPOSES = OrderedDict([
    ("INITIAL_SEIZURE", "Initial seizure"), ("STORAGE", "Storage (malkhana)"),
    ("FORENSIC_ANALYSIS", "Forensic analysis"), ("INVESTIGATION", "Investigation"),
    ("COURT_PRODUCTION", "Court production"), ("RETURN_TO_OWNER", "Return to owner"),
    ("DISPOSAL", "Disposal"),
])
TRANSFER_PURPOSES = OrderedDict((k, v) for k, v in CUSTODY_PURPOSES.items() if k != "INITIAL_SEIZURE")
FINAL_PURPOSES = ("RETURN_TO_OWNER", "DISPOSAL")

EVIDENCE_STATUSES = OrderedDict([
    ("WITH_SEIZING_OFFICER", "With seizing officer"), ("IN_STORAGE", "In storage"), ("IN_LAB", "In forensic lab"),
    ("WITH_IO", "With IO"), ("IN_COURT", "In court"), ("RETURNED", "Returned"), ("DISPOSED", "Disposed"),
])

ACCUSED_STATUSES = OrderedDict([("SUSPECT", "Suspect"), ("ARRESTED", "Arrested"), ("ABSCONDING", "Absconding"),
                                ("ON_BAIL", "On bail"), ("RELEASED", "Released")])

ACTS = ["BNS", "BNSS", "IT Act", "NDPS Act", "Arms Act", "MV Act", "Other"]

COURT_TYPES = OrderedDict([("MAGISTRATE", "Magistrate"), ("SESSIONS", "Sessions"), ("HIGH_COURT", "High Court"),
                           ("SPECIAL", "Special Court")])
CASE_STAGES = OrderedDict([("FILED", "Filed"), ("HEARING", "Hearing"), ("ARGUMENTS", "Arguments"),
                           ("JUDGMENT_RESERVED", "Judgment reserved"), ("DISPOSED", "Disposed")])
VERDICTS = OrderedDict([("PENDING", "Pending"), ("CONVICTED", "Convicted"), ("ACQUITTED", "Acquitted"),
                        ("DISMISSED", "Dismissed"), ("SETTLED", "Settled")])

RANKS = ["Constable", "Head Constable", "Assistant Sub-Inspector", "Sub-Inspector", "Inspector",
         "Deputy SP", "Superintendent"]
GENDERS = OrderedDict([("M", "Male"), ("F", "Female"), ("O", "Other")])
ID_TYPES = OrderedDict([("AADHAAR", "Aadhaar"), ("PAN", "PAN"), ("VOTER_ID", "Voter ID"),
                        ("PASSPORT", "Passport"), ("DRIVING_LICENSE", "Driving licence")])

USER_ROLES = OrderedDict([("ADMIN", "Administrator"), ("SHO", "Station House Officer"),
                          ("IO", "Investigating Officer"), ("CUSTODIAN", "Evidence Custodian")])

# Role based access control
_ALL = {"ADMIN", "SHO", "IO", "CUSTODIAN"}
PERMISSIONS = {
    "complaint.create": {"ADMIN", "SHO", "IO"},
    "complaint.edit": {"ADMIN", "SHO"},
    "complaint.assign": {"ADMIN", "SHO"},
    "complaint.status": {"ADMIN", "SHO", "IO"},
    "complaint.close": {"ADMIN", "SHO"},
    "activity.log": {"ADMIN", "SHO", "IO"},
    "evidence.create": _ALL,
    "custody.transfer": _ALL,
    "witness.manage": {"ADMIN", "SHO", "IO"},
    "accused.manage": {"ADMIN", "SHO", "IO"},
    "charge.manage": {"ADMIN", "SHO", "IO"},
    "court.manage": {"ADMIN", "SHO", "IO"},
    "person.manage": _ALL,
    "person.delete": {"ADMIN", "SHO"},
    "officer.manage": {"ADMIN"},
    "integrity.run": {"ADMIN", "SHO"},
}

STATUS_COLORS = {
    "REGISTERED": "slate", "UNDER_INVESTIGATION": "amber", "CHARGE_SHEETED": "violet",
    "IN_COURT": "cyan", "CLOSED": "green",
}
PRIORITY_COLORS = {"LOW": "slate", "MEDIUM": "blue", "HIGH": "amber", "CRITICAL": "red"}
EVIDENCE_STATUS_COLORS = {
    "WITH_SEIZING_OFFICER": "blue", "IN_STORAGE": "slate", "IN_LAB": "violet", "WITH_IO": "amber",
    "IN_COURT": "cyan", "RETURNED": "green", "DISPOSED": "red",
}
