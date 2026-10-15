"""Start the PCETS web application:  python run.py   ->  http://127.0.0.1:5000"""
import os
import sys

from police_app.app import create_app
from police_app.config import load_app_config

app = create_app()

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    port = load_app_config()["port"]
    debug = os.environ.get("PCETS_DEBUG", "0") == "1"
    print(f"\n  Police Complaint & Evidence Tracking System\n  ➜ http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
