"""Configuration loading.

Priority (highest first):
  1. PCETS_DB_* / PCETS_* environment variables
  2. MYSQL_ADDON_* variables injected by Clever Cloud when the MySQL add-on is linked
  3. config.ini (local development)
"""
import configparser
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.ini")


def _read():
    parser = configparser.ConfigParser()
    parser.read(CONFIG_PATH, encoding="utf-8")
    return parser


def _pick(env_names, ini_value, default):
    for name in env_names:
        if os.environ.get(name):
            return os.environ[name]
    return ini_value if ini_value not in (None, "") else default


def load_db_config():
    p = _read()
    sect = p["database"] if p.has_section("database") else {}
    return {
        "host": _pick(["PCETS_DB_HOST", "MYSQL_ADDON_HOST"], sect.get("host"), "localhost"),
        "port": int(_pick(["PCETS_DB_PORT", "MYSQL_ADDON_PORT"], sect.get("port"), "3306")),
        "user": _pick(["PCETS_DB_USER", "MYSQL_ADDON_USER"], sect.get("user"), "root"),
        "password": _pick(["PCETS_DB_PASSWORD", "MYSQL_ADDON_PASSWORD"], sect.get("password"), ""),
        "database": _pick(["PCETS_DB_NAME", "MYSQL_ADDON_DB"], sect.get("database"), "police_evidence_db"),
    }


def db_pool_size():
    """Clever Cloud DEV MySQL allows only 5 connections per user and runs several gunicorn
    workers, so there the default is 0 = one connection per request (no idle pooled connections)."""
    p = _read()
    sect = p["database"] if p.has_section("database") else {}
    default = "0" if os.environ.get("MYSQL_ADDON_HOST") else "8"
    return int(_pick(["PCETS_DB_POOL_SIZE"], sect.get("pool_size"), default))


def load_app_config():
    p = _read()
    sect = p["app"] if p.has_section("app") else {}
    return {
        "secret_key": _pick(["PCETS_SECRET_KEY"], sect.get("secret_key"), "dev-secret"),
        "port": int(_pick(["PCETS_PORT", "PORT"], sect.get("port"), "5000")),
        "default_user": _pick(["PCETS_DEFAULT_USER"], sect.get("default_user"), "admin"),
    }
