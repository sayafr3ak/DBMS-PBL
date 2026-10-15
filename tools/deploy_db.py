"""
Loads PCETS into a HOSTED MySQL database (e.g. Clever Cloud add-on) that does not allow
CREATE TRIGGER / CREATE FUNCTION and cannot DROP/CREATE DATABASE.

Steps:
  1. schema (tables, constraints, indexes)          sql/01_schema.sql
  2. stored procedures (triggers/functions skipped)  sql/02_triggers_procedures.sql
  3. views                                           sql/03_views.sql
  4. sample data, copied from the LOCAL database (built through the triggers, so CMP/EVD numbers
     and status history are already present) via mysqldump --no-create-info

Usage (target from Clever Cloud variables):
    set MYSQL_ADDON_HOST=... & set MYSQL_ADDON_PORT=3306 & set MYSQL_ADDON_USER=... &
    set MYSQL_ADDON_PASSWORD=... & set MYSQL_ADDON_DB=...
    python tools/deploy_db.py
The local source database is read from config.ini (run `python setup_db.py` first).
"""
import configparser
import os
import subprocess
import sys

import mysql.connector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from setup_db import split_sql  # noqa: E402

MYSQLDUMP = r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe"
TABLES = ["station", "officer", "person", "complaint", "complaint_accused", "assignment", "investigation_activity",
          "evidence_item", "custody_log", "witness", "charge", "court_reference", "status_history", "app_user"]


def target_cfg():
    need = ["MYSQL_ADDON_HOST", "MYSQL_ADDON_USER", "MYSQL_ADDON_PASSWORD", "MYSQL_ADDON_DB"]
    missing = [n for n in need if not os.environ.get(n)]
    if missing:
        sys.exit("Set the target database variables first: " + ", ".join(missing))
    return dict(host=os.environ["MYSQL_ADDON_HOST"], port=int(os.environ.get("MYSQL_ADDON_PORT", "3306")),
                user=os.environ["MYSQL_ADDON_USER"], password=os.environ["MYSQL_ADDON_PASSWORD"],
                database=os.environ["MYSQL_ADDON_DB"])


def local_cfg():
    p = configparser.ConfigParser()
    p.read(os.path.join(ROOT, "config.ini"), encoding="utf-8")
    d = p["database"]
    return dict(host=d.get("host", "localhost"), port=d.get("port", "3306"), user=d.get("user", "root"),
                password=d.get("password", ""), database=d.get("database", "police_evidence_db"))


def run_file(cur, name, skip_codes=()):
    with open(os.path.join(ROOT, "sql", name), encoding="utf-8") as fh:
        stmts = split_sql(fh.read())
    done = skipped = 0
    for st in stmts:
        try:
            cur.execute(st)
            if cur.with_rows:
                cur.fetchall()
            done += 1
        except mysql.connector.Error as err:
            if err.errno in skip_codes:
                skipped += 1
                continue
            raise SystemExit(f"[ERROR] {name}: {err}\n  in: {' '.join(st.split())[:150]}")
    print(f"  ✔ {name:<28} {done} executed" + (f", {skipped} skipped (not allowed on this host)" if skipped else ""))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    tgt, src = target_cfg(), local_cfg()
    print(f"Source: {src['database']}@{src['host']}  →  target: {tgt['database']}@{tgt['host']}")

    dump = subprocess.run(
        [MYSQLDUMP, "-h", src["host"], "-P", str(src["port"]), "-u", src["user"], "--no-create-info", "--skip-triggers",
         "--complete-insert", "--skip-add-locks", "--skip-tz-utc", "--default-character-set=utf8mb4",
         src["database"], *TABLES],
        capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, MYSQL_PWD=src["password"]))
    if dump.returncode != 0:
        sys.exit("mysqldump failed: " + dump.stderr)

    conn = mysql.connector.connect(**tgt, autocommit=True, charset="utf8mb4", collation="utf8mb4_0900_ai_ci")
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.views WHERE table_schema = DATABASE()")
    for (v,) in cur.fetchall():
        cur.execute(f"DROP VIEW IF EXISTS `{v}`")
    for kind in ("PROCEDURE", "FUNCTION"):
        cur.execute("SELECT routine_name FROM information_schema.routines WHERE routine_schema = DATABASE() "
                    "AND routine_type = %s", (kind,))
        for (r,) in cur.fetchall():
            cur.execute(f"DROP {kind} IF EXISTS `{r}`")

    run_file(cur, "01_schema.sql")
    run_file(cur, "02_triggers_procedures.sql", skip_codes=(1419, 1227))   # 1419/1227: needs SUPER
    run_file(cur, "03_views.sql")

    rows = 0
    for st in split_sql(dump.stdout):
        cur.execute(st)
        if st.lstrip().upper().startswith("INSERT"):
            rows += cur.rowcount
    print(f"  ✔ sample data                  {rows} rows copied")

    print("\n  Table counts on target:")
    for t in TABLES:
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        print(f"    {t:<25} {cur.fetchone()[0]:>4}")
    cur.execute("SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = DATABASE()")
    print(f"\n  Triggers on target: {cur.fetchone()[0]}  (0 = hosted mode; the app enforces those rules)")
    conn.close()


if __name__ == "__main__":
    main()
