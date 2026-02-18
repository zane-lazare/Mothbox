"""Gunicorn configuration for Mothbox Web UI.

Uses eventlet worker for proper WebSocket support.
Single worker since the camera can only be used by one process.
"""

import os

worker_class = "eventlet"
workers = 1
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")
timeout = 120
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
max_requests = 0
