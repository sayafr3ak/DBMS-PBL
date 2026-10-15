# Gunicorn settings used on Clever Cloud (CC_PYTHON_BACKEND=gunicorn).
# The DEV MySQL plan allows only 5 connections per user; the app opens one connection
# per request (PCETS_DB_POOL_SIZE=0), so 2 workers x 2 threads stay within the limit.
workers = 2
threads = 2
timeout = 60
accesslog = "-"
errorlog = "-"
