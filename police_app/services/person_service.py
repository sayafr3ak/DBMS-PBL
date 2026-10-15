"""Persons: complainants, accused and witnesses."""
from ..db import query, query_one, execute, scalar, AppError
from ..validators import Form
from .. import constants as C


def validate_person(data, prefix=""):
    """Validate person fields. `prefix` allows embedding in other forms (e.g. 'p_')."""
    f = Form({k[len(prefix):]: v for k, v in data.items() if k.startswith(prefix)} if prefix else data)
    f.text("full_name", "Full name", min_len=3, max_len=100)
    f.choice("gender", "Gender", C.GENDERS)
    f.date("date_of_birth", "Date of birth", required=False, not_future=True)
    f.phone("phone", "Phone")
    f.email("email", "Email")
    f.text("address", "Address", min_len=5, max_len=255)
    f.id_proof()
    if prefix:
        f.errors = {prefix + k: v for k, v in f.errors.items()}
    return f


def insert_person(clean, conn=None):
    return execute(
        """INSERT INTO person (full_name, gender, date_of_birth, phone, email, address, id_proof_type, id_proof_no)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (clean["full_name"], clean["gender"], clean["date_of_birth"], clean["phone"], clean["email"],
         clean["address"], clean["id_proof_type"], clean["id_proof_no"]), conn=conn)


def create_person(data):
    clean = validate_person(data).raise_if_invalid()
    return insert_person(clean)


def update_person(person_id, data):
    clean = validate_person(data).raise_if_invalid()
    execute(
        """UPDATE person SET full_name=%s, gender=%s, date_of_birth=%s, phone=%s, email=%s, address=%s,
                  id_proof_type=%s, id_proof_no=%s WHERE person_id=%s""",
        (clean["full_name"], clean["gender"], clean["date_of_birth"], clean["phone"], clean["email"],
         clean["address"], clean["id_proof_type"], clean["id_proof_no"], person_id))


def delete_person(person_id):
    # FK constraints (complaint / witness / accused) block deletion of referenced persons;
    # db.translate_db_error turns error 1451 into a readable message.
    if not execute("DELETE FROM person WHERE person_id = %s", (person_id,)):
        raise AppError("Person not found.")


def get_person(person_id):
    return query_one("SELECT * FROM person WHERE person_id = %s", (person_id,))


def involvement(person_id):
    """Every case the person is linked to, with the role played."""
    return query(
        """SELECT x.role, c.complaint_id, c.complaint_no, c.title, c.status, x.detail
             FROM (SELECT complaint_id, 'Complainant' AS role, NULL AS detail FROM complaint WHERE complainant_id = %s
                   UNION ALL
                   SELECT complaint_id, 'Accused', accused_status FROM complaint_accused WHERE person_id = %s
                   UNION ALL
                   SELECT complaint_id, 'Witness', IF(is_protected, 'Protected', NULL) FROM witness WHERE person_id = %s) x
             JOIN complaint c ON c.complaint_id = x.complaint_id
            ORDER BY c.registered_at DESC""", (person_id, person_id, person_id))


def list_persons(q=None, role=None, page=1, per_page=15):
    where, params = ["1=1"], []
    if q:
        where.append("(p.full_name LIKE %s OR p.phone LIKE %s OR p.id_proof_no LIKE %s OR p.address LIKE %s)")
        like = f"%{q}%"
        params += [like, like, like, like]
    if role == "COMPLAINANT":
        where.append("EXISTS (SELECT 1 FROM complaint c WHERE c.complainant_id = p.person_id)")
    elif role == "ACCUSED":
        where.append("EXISTS (SELECT 1 FROM complaint_accused a WHERE a.person_id = p.person_id)")
    elif role == "WITNESS":
        where.append("EXISTS (SELECT 1 FROM witness w WHERE w.person_id = p.person_id)")
    where_sql = " AND ".join(where)
    total = scalar(f"SELECT COUNT(*) FROM person p WHERE {where_sql}", params)
    rows = query(
        f"""SELECT p.*,
                   (SELECT COUNT(*) FROM complaint c WHERE c.complainant_id = p.person_id) AS as_complainant,
                   (SELECT COUNT(*) FROM complaint_accused a WHERE a.person_id = p.person_id) AS as_accused,
                   (SELECT COUNT(*) FROM witness w WHERE w.person_id = p.person_id) AS as_witness
              FROM person p WHERE {where_sql}
             ORDER BY p.full_name LIMIT %s OFFSET %s""", params + [per_page, (page - 1) * per_page])
    return rows, total


def search_persons(q, limit=8):
    like = f"%{q}%"
    return query(
        """SELECT person_id, full_name, phone, address, id_proof_type, id_proof_no
             FROM person
            WHERE full_name LIKE %s OR phone LIKE %s OR id_proof_no LIKE %s
            ORDER BY full_name LIMIT %s""", (like, like, like, limit))


def resolve_person(data, mode_field, id_field, prefix, conn):
    """
    Used by forms that either pick an existing person or create a new one
    inside the caller's transaction. Returns person_id.
    """
    mode = (data.get(mode_field) or "existing").strip()
    if mode == "existing":
        f = Form(data)
        pid = f.integer(id_field, "Person", required=True)
        if f.errors:
            from ..db import ValidationError
            raise ValidationError({id_field: "Search and select a person, or switch to 'New person'."})
        if not query_one("SELECT person_id FROM person WHERE person_id = %s", (pid,), conn=conn):
            raise AppError("Selected person does not exist.")
        return pid
    clean = validate_person(data, prefix=prefix).raise_if_invalid()
    return insert_person(clean, conn=conn)
