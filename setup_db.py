"""
Creates (or re-creates) the PCETS database and loads schema, triggers,
views and sample data.

    python setup_db.py              # uses settings from config.ini
    python setup_db.py --db pcets_test   # create a separate database (used by tests)
"""
import argparse
import os
import re
import sys

import mysql.connector

from police_app.config import load_db_config

ROOT = os.path.dirname(os.path.abspath(__file__))
SQL_DIR = os.path.join(ROOT, "sql")
SCRIPTS = [
    "01_schema.sql",
    "02_triggers_procedures.sql",
    "03_views.sql",
    "04_seed_data.sql",
]


def split_sql(text):
    """Split a SQL script into statements, honouring DELIMITER changes."""
    statements = []
    delimiter = ";"
    buffer = []
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"^DELIMITER\s+(\S+)\s*$", stripped, re.IGNORECASE)
        if match:
            delimiter = match.group(1)
            continue
        if not buffer and (stripped.startswith("--") or not stripped):
            continue
        buffer.append(line)
        if stripped.endswith(delimiter):
            statement = "\n".join(buffer).rstrip()
            statement = statement[: -len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def run_script(cursor, path):
    with open(path, encoding="utf-8") as fh:
        statements = split_sql(fh.read())
    for stmt in statements:
        try:
            cursor.execute(stmt)
            if cursor.with_rows:
                cursor.fetchall()
        except mysql.connector.Error as err:
            preview = " ".join(stmt.split())[:160]
            raise SystemExit(f"\n[ERROR] {os.path.basename(path)}: {err}\n  in: {preview}...")
    return len(statements)


def setup(database=None, quiet=False, keep_db=False):
    cfg = load_db_config()
    database = database or cfg["database"]
    conn = mysql.connector.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                                   password=cfg["password"], autocommit=True,
                                   charset="utf8mb4", collation="utf8mb4_0900_ai_ci")
    cur = conn.cursor()
    if keep_db:
        # hosted MySQL (e.g. Clever Cloud): the database already exists and cannot be dropped/created,
        # so remove existing views/routines; the schema script drops and recreates the tables.
        cur.execute(f"USE `{database}`")
        cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema = %s", (database,))
        for (name,) in cur.fetchall():
            cur.execute(f"DROP VIEW IF EXISTS `{name}`")
        cur.execute("SELECT routine_name, routine_type FROM information_schema.routines WHERE routine_schema = %s",
                    (database,))
        for name, kind in cur.fetchall():
            cur.execute(f"DROP {kind} IF EXISTS `{name}`")
    else:
        cur.execute(f"DROP DATABASE IF EXISTS `{database}`")
        cur.execute(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
        cur.execute(f"USE `{database}`")
    for script in SCRIPTS:
        count = run_script(cur, os.path.join(SQL_DIR, script))
        if not quiet:
            print(f"  ✔ {script:<30} {count:>4} statements")
    if not quiet:
        cur.execute("SELECT table_name, table_rows FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_type = 'BASE TABLE' ORDER BY table_name", (database,))
        print("\n  Tables loaded:")
        for name, _ in cur.fetchall():
            cur2 = conn.cursor()
            cur2.execute(f"SELECT COUNT(*) FROM `{name}`")
            print(f"    {name:<25} {cur2.fetchone()[0]:>4} rows")
            cur2.close()
    cur.close()
    conn.close()
    return database


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Create the PCETS database")
    parser.add_argument("--db", help="database name (default from config.ini)")
    parser.add_argument("--keep-db", action="store_true",
                        help="load into an existing database without DROP/CREATE DATABASE (hosted MySQL)")
    args = parser.parse_args()
    print("Setting up Police Complaint & Evidence Tracking database ...")
    name = setup(args.db, keep_db=args.keep_db or bool(os.environ.get("MYSQL_ADDON_HOST")))
    print(f"\nDone. Database '{name}' is ready. Start the app with:  python run.py")
