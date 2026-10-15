"""
Application-side input validation.

The database enforces every rule again (CHECK / FK / triggers); validating
here first gives the user a friendly, field-level message before any SQL runs.
"""
import re
from datetime import datetime, date, timedelta

from .db import ValidationError

PHONE_RE = re.compile(r"^[6-9][0-9]{9}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ID_FORMATS = {
    "AADHAAR": (re.compile(r"^[2-9][0-9]{11}$"), "12 digits, not starting with 0 or 1"),
    "PAN": (re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$"), "e.g. ABCDE1234F"),
    "VOTER_ID": (re.compile(r"^[A-Z]{3}[0-9]{7}$"), "e.g. ABC1234567"),
    "PASSPORT": (re.compile(r"^[A-Z][0-9]{7}$"), "e.g. K1234567"),
    "DRIVING_LICENSE": (re.compile(r"^[A-Z]{2}[0-9]{13}$"), "e.g. MH1220110012345"),
}


class Form:
    """Collects cleaned values and errors for one submitted form."""

    def __init__(self, data):
        self.data = data
        self.errors = {}
        self.clean = {}

    # -- helpers ---------------------------------------------------------
    def _raw(self, name):
        val = self.data.get(name)
        if val is None:
            return ""
        return val.strip() if isinstance(val, str) else val

    def error(self, name, message):
        self.errors.setdefault(name, message)

    def ok(self):
        return not self.errors

    def raise_if_invalid(self):
        if self.errors:
            raise ValidationError(self.errors)
        return self.clean

    # -- field types -----------------------------------------------------
    def text(self, name, label, required=True, min_len=0, max_len=255):
        val = self._raw(name)
        if not val:
            if required:
                self.error(name, f"{label} is required.")
            self.clean[name] = None
            return None
        if len(val) < min_len:
            self.error(name, f"{label} must be at least {min_len} characters.")
        if len(val) > max_len:
            self.error(name, f"{label} must be at most {max_len} characters.")
        self.clean[name] = val
        return val

    def choice(self, name, label, choices, required=True):
        val = self._raw(name)
        if not val:
            if required:
                self.error(name, f"Select {label.lower()}.")
            self.clean[name] = None
            return None
        if val not in choices:
            self.error(name, f"Invalid {label.lower()}.")
        self.clean[name] = val
        return val

    def integer(self, name, label, required=True, min_value=None, max_value=None):
        val = self._raw(name)
        if val == "":
            if required:
                self.error(name, f"{label} is required.")
            self.clean[name] = None
            return None
        try:
            num = int(val)
        except (TypeError, ValueError):
            self.error(name, f"{label} must be a whole number.")
            self.clean[name] = None
            return None
        if min_value is not None and num < min_value:
            self.error(name, f"{label} must be at least {min_value}.")
        if max_value is not None and num > max_value:
            self.error(name, f"{label} must be at most {max_value}.")
        self.clean[name] = num
        return num

    def boolean(self, name):
        val = self._raw(name)
        self.clean[name] = 1 if val in ("1", "on", "true", "yes", True) else 0
        return self.clean[name]

    def phone(self, name, label="Phone", required=False):
        val = self._raw(name)
        if not val:
            if required:
                self.error(name, f"{label} is required.")
            self.clean[name] = None
            return None
        val = re.sub(r"[\s-]", "", val)
        if val.startswith("+91"):
            val = val[3:]
        if not PHONE_RE.match(val):
            self.error(name, f"{label} must be a 10-digit mobile number starting with 6-9.")
        self.clean[name] = val
        return val

    def email(self, name, label="Email", required=False):
        val = self._raw(name)
        if not val:
            if required:
                self.error(name, f"{label} is required.")
            self.clean[name] = None
            return None
        if not EMAIL_RE.match(val) or len(val) > 100:
            self.error(name, f"{label} is not a valid email address.")
        self.clean[name] = val.lower()
        return val

    def date(self, name, label, required=True, not_future=False, not_before=None):
        val = self._raw(name)
        if not val:
            if required:
                self.error(name, f"{label} is required.")
            self.clean[name] = None
            return None
        try:
            d = datetime.strptime(val, "%Y-%m-%d").date()
        except ValueError:
            self.error(name, f"{label} is not a valid date.")
            self.clean[name] = None
            return None
        if not_future and d > date.today():
            self.error(name, f"{label} cannot be in the future.")
        if not_before and d < not_before:
            self.error(name, f"{label} cannot be before {not_before:%d %b %Y}.")
        self.clean[name] = d
        return d

    def datetime(self, name, label, required=True, not_future=True, not_before=None):
        val = self._raw(name)
        if not val:
            if required:
                self.error(name, f"{label} is required.")
            self.clean[name] = None
            return None
        dt = None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(val, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            self.error(name, f"{label} is not a valid date/time.")
            self.clean[name] = None
            return None
        if not_future and dt > datetime.now() + timedelta(minutes=5):
            self.error(name, f"{label} cannot be in the future.")
        if not_before and dt < not_before:
            self.error(name, f"{label} cannot be before {not_before:%d %b %Y %H:%M}.")
        self.clean[name] = dt
        return dt

    def id_proof(self, type_name="id_proof_type", no_name="id_proof_no"):
        t = self._raw(type_name) or None
        n = (self._raw(no_name) or "").upper().replace(" ", "") or None
        if t and t not in ID_FORMATS:
            self.error(type_name, "Invalid ID proof type.")
        elif t and not n:
            self.error(no_name, "Enter the ID proof number.")
        elif n and not t:
            self.error(type_name, "Select the ID proof type.")
        elif t and n:
            pattern, hint = ID_FORMATS[t]
            if not pattern.match(n):
                self.error(no_name, f"Invalid {t.replace('_', ' ').title()} number ({hint}).")
        self.clean[type_name], self.clean[no_name] = t, n
        return t, n
