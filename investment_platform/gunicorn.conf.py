"""
Gunicorn Configuration for Production

This configuration is optimized for running on IBM z/OS mainframe.
Uses 1 worker with threads to avoid z/OS fork/signal limitations.
All characters in this file are EBCDIC-safe (Code Page 1047).

Usage:
    gunicorn wsgi:app -c gunicorn.conf.py
    python -m gunicorn wsgi:app -c gunicorn.conf.py
"""
import os

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker configuration
# z/OS USS has limited support for fork/signal-based process management.
# Use 1 worker with multiple threads instead of multiple forked workers.
# This avoids os.kill() and os.utime(fd) errors on z/OS.
workers = 1
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_class = "gthread"
max_requests = 0
max_requests_jitter = 0

# Preload the application before forking to reduce memory and startup time
preload_app = True

# Timeout configuration
timeout = 120
graceful_timeout = 30
keepalive = 5

# Worker temp directory - use /tmp to avoid utime file descriptor issues
worker_tmp_dir = "/tmp"

# Process naming
proc_name = "investment-platform"

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Logging
loglevel = os.getenv("LOG_LEVEL", "info")
accesslog = os.getenv("ACCESS_LOG", "-")
errorlog = os.getenv("ERROR_LOG", "-")
access_log_format = "%%(h)s %%(l)s %%(u)s %%(t)s \"%%(r)s\" %%(s)s %%(b)s \"%%(f)s\" \"%%(a)s\" %%(D)s"

# For production with file logging, set environment variables:
#   ACCESS_LOG=/var/log/investment-platform/access.log
#   ERROR_LOG=/var/log/investment-platform/error.log

if os.getenv("FLASK_ENV") == "development":
    accesslog = "-"
    errorlog = "-"
    loglevel = "debug"


# Lifecycle hooks

def on_starting(server):
    """Called before the master process is initialized."""
    pass


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Investment Platform server is ready")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Investment Platform shutting down")
