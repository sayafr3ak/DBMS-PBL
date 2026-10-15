# Gunicorn settings used on Clever Cloud (CC_PYTHON_BACKEND=gunicorn).
# The DEV MySQL plan allows only 5 connections per user: one worker process with a
# connection pool of 3 and 3 threads keeps the app well inside that limit.
import os

workers = 1
threads = int(os.environ.get("PCETS_DB_POOL_SIZE", "3"))
timeout = 60
accesslog = "-"
errorlog = "-"
