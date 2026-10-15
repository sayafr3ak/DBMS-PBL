"""Evidence registration and chain-of-custody transfers."""
from ..db import query, query_one, execute, scalar, transaction, AppError, ValidationError
from ..validators import Form
from .. import constants as C


def list_evidence(filters, page=1, per_page=12):
    where, params = ["1=1"], []
    q = (filters.get("q") or "").strip()
    if q:
        like = f"%{q}%"
        where.append("(v.evidence_no LIKE %s OR v.description LIKE %s OR v.complaint_no LIKE %s "
                     "OR v.seal_no LIKE %s OR v.current_location LIKE %s OR v.current_holder LIKE %s)")
        params += [like] * 6
    if filters.get("status"):
        where.append("v.evidence_status = %s")
        params.append(filters["status"])
    if filters.get("category"):
        where.append("v.category = %s")
        params.append(filters["category"])
    if filters.get("holder"):
        where.append("v.holder_id = %s")
        params.append(filters["holder"])
    where_sql = " AND ".join(where)
    total = scalar(f"SELECT COUNT(*) FROM v_evidence_location v WHERE {where_sql}", params)
    rows = query(f"""SELECT v.*, c.title AS complaint_title FROM v_evidence_location v
                       JOIN complaint c ON c.complaint_id = v.complaint_id
                      WHERE {where_sql} ORDER BY v.evidence_no DESC LIMIT %s OFFSET %s""",
                 params + [per_page, (page - 1) * per_page])
    return rows, total


def get_evidence(evidence_id):
    row = query_one(
        """SELECT e.*, c.complaint_no, c.title AS complaint_title, c.status AS case_status,
                  o.full_name AS collected_by_name, o.badge_no AS collector_badge,
                  v.holder_id, v.current_holder, v.holder_badge, v.current_location, v.current_purpose,
                  v.evidence_status, v.held_since, v.days_at_location, v.transfer_count, v.seal_intact
             FROM evidence_item e
             JOIN complaint c ON c.complaint_id = e.complaint_id
             JOIN officer o ON o.officer_id = e.collected_by
             LEFT JOIN v_evidence_location v ON v.evidence_id = e.evidence_id
            WHERE e.evidence_id = %s""", (evidence_id,))
    if not row:
        raise AppError("Evidence item not found.")
    return row


def custody_chain(evidence_id):
    return query(
        """SELECT cl.*, fo.full_name AS from_name, fo.badge_no AS from_badge,
                  t.full_name AS to_name, t.badge_no AS to_badge, t.officer_rank AS to_rank,
                  ROUND(TIMESTAMPDIFF(MINUTE, cl.received_at, COALESCE(cl.released_at, NOW())) / 60, 1) AS hours_held
             FROM custody_log cl
             JOIN officer t ON t.officer_id = cl.to_officer_id
             LEFT JOIN officer fo ON fo.officer_id = cl.from_officer_id
            WHERE cl.evidence_id = %s ORDER BY cl.received_at, cl.custody_id""", (evidence_id,))


def register_evidence(data):
    """
    ONE transaction:
      1. INSERT evidence_item           (trigger issues EVD-YYYY-NNNNN)
      2. INSERT custody_log (INITIAL_SEIZURE, held by collecting officer)
      3. optional: release it and deposit with a custodian (STORAGE)
    """
    f = Form(data)
    complaint_id = f.integer("complaint_id", "Complaint", min_value=1)
    f.choice("category", "Category", C.EVIDENCE_CATEGORIES)
    f.text("description", "Description", min_len=5, max_len=500)
    f.integer("quantity", "Quantity", min_value=1, max_value=100000)
    f.choice("item_condition", "Condition", C.CONDITIONS)
    seal = f.text("seal_no", "Seal number", required=False, max_len=20)
    collected_at = f.datetime("collected_at", "Collected at", not_future=True)
    f.integer("collected_by", "Collecting officer", min_value=1)
    f.text("collected_from", "Collected from", min_len=3, max_len=255)
    deposit = f.boolean("deposit_now")
    if deposit:
        f.integer("custodian_id", "Custodian", min_value=1)
        f.text("storage_location", "Storage location", min_len=3, max_len=150)
        dep_at = f.datetime("deposit_at", "Deposit time", not_future=True)
        if collected_at and dep_at and dep_at <= collected_at:
            f.error("deposit_at", "Deposit time must be after the collection time.")
        if f.clean.get("custodian_id") and f.clean.get("custodian_id") == f.clean.get("collected_by"):
            f.error("custodian_id", "Custodian must be different from the collecting officer.")
    if complaint_id:
        comp = query_one("SELECT status, incident_datetime FROM complaint WHERE complaint_id = %s", (complaint_id,))
        if not comp:
            f.error("complaint_id", "Complaint not found.")
        elif comp["status"] == "CLOSED":
            f.error("complaint_id", "Evidence cannot be added to a closed case.")
        elif collected_at and collected_at < comp["incident_datetime"]:
            f.error("collected_at", "Evidence cannot be collected before the incident.")
    clean = f.raise_if_invalid()
    if seal:
        clean["seal_no"] = seal.upper()

    with transaction() as conn:
        evidence_id = execute(
            """INSERT INTO evidence_item (complaint_id, category, description, quantity, item_condition, seal_no,
                                          collected_at, collected_by, collected_from)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (clean["complaint_id"], clean["category"], clean["description"], clean["quantity"],
             clean["item_condition"], clean["seal_no"], clean["collected_at"], clean["collected_by"],
             clean["collected_from"]), conn=conn)
        execute("""INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose, received_at,
                                            seal_intact, remarks)
                   VALUES (%s, NULL, %s, %s, 'INITIAL_SEIZURE', %s, 1, 'Seized at collection')""",
                (evidence_id, clean["collected_by"], clean["collected_from"][:150], clean["collected_at"]), conn=conn)
        if deposit:
            _do_transfer(conn, evidence_id, clean["custodian_id"], clean["storage_location"], "STORAGE",
                         clean["deposit_at"], 1, "Deposited at registration")
        number = scalar("SELECT evidence_no FROM evidence_item WHERE evidence_id = %s", (evidence_id,), conn=conn)
    return evidence_id, number


def _do_transfer(conn, evidence_id, to_officer_id, location, purpose, transfer_at, seal_intact, remarks):
    # Lock the open custody row -> concurrent transfers of the same item are serialised
    current = query_one("""SELECT custody_id, to_officer_id, received_at, purpose FROM custody_log
                            WHERE evidence_id = %s AND released_at IS NULL FOR UPDATE""", (evidence_id,), conn=conn)
    if not current:
        raise AppError("This evidence item has no current custodian.")
    if current["purpose"] in C.FINAL_PURPOSES:
        raise AppError("This evidence item has already been returned/disposed. The chain is final.")
    if current["to_officer_id"] == to_officer_id:
        raise AppError("The receiving officer already holds this item.")
    if transfer_at <= current["received_at"]:
        raise AppError(f"Transfer time must be after {current['received_at']:%d %b %Y %H:%M}, "
                       "when the current custodian received the item.")
    execute("UPDATE custody_log SET released_at = %s WHERE custody_id = %s",
            (transfer_at, current["custody_id"]), conn=conn)
    return execute("""INSERT INTO custody_log (evidence_id, from_officer_id, to_officer_id, location, purpose,
                                               received_at, seal_intact, remarks)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                   (evidence_id, current["to_officer_id"], to_officer_id, location, purpose, transfer_at,
                    seal_intact, remarks), conn=conn)


def transfer_custody(evidence_id, data):
    """Close the current custody period and open the next one atomically."""
    get_evidence(evidence_id)
    f = Form(data)
    f.integer("to_officer_id", "Receiving officer", min_value=1)
    f.text("location", "Location", min_len=3, max_len=150)
    f.choice("purpose", "Purpose", C.TRANSFER_PURPOSES)
    f.datetime("transfer_at", "Transfer time", not_future=True)
    seal = f.boolean("seal_intact")
    remarks = f.text("remarks", "Remarks", required=False, max_len=500)
    if not seal and not remarks:
        f.error("remarks", "Explain the seal condition - remarks are mandatory when the seal is broken.")
    if f.clean.get("purpose") in C.FINAL_PURPOSES and not remarks:
        f.error("remarks", "Remarks (order / authority) are mandatory for return or disposal.")
    clean = f.raise_if_invalid()
    with transaction() as conn:
        return _do_transfer(conn, evidence_id, clean["to_officer_id"], clean["location"], clean["purpose"],
                            clean["transfer_at"], seal, remarks)


def update_evidence(evidence_id, data):
    ev = get_evidence(evidence_id)
    if ev["case_status"] == "CLOSED":
        raise AppError("Evidence of a closed case cannot be edited.")
    f = Form(data)
    f.text("description", "Description", min_len=5, max_len=500)
    f.integer("quantity", "Quantity", min_value=1, max_value=100000)
    f.choice("item_condition", "Condition", C.CONDITIONS)
    seal = f.text("seal_no", "Seal number", required=False, max_len=20)
    clean = f.raise_if_invalid()
    execute("UPDATE evidence_item SET description=%s, quantity=%s, item_condition=%s, seal_no=%s WHERE evidence_id=%s",
            (clean["description"], clean["quantity"], clean["item_condition"], seal.upper() if seal else None,
             evidence_id))
