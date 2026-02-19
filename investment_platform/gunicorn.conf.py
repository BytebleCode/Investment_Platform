"""
Gunicorn Configuration for Production

This configuration is optimized for running on IBM z/OS mainframe.
Adjust workers and threads based on available CPU cores.
All characters in this file are EBCDIC-safe (Code Page 1047).

Usage:
    gunicorn wsgi:app -c gunicorn.conf.py
    python -m gunicorn wsgi:app -c gunicorn.conf.py
"""
import os
import multiprocessing

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# Worker processes
# Rule of thumb: (2 x CPU cores) + 1
# On mainframe, start conservative and scale up
_default_workers = multiprocessing.cpu_count() * 2 + 1
workers = int(os.getenv("GUNICORN_WORKERS", str(_default_workers)))
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout configuration
timeout = 120
graceful_timeout = 30
keepalive = 5

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


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    pass


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Investment Platform server is ready. Spawning workers")


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)" % worker.pid)


def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass


def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.info("Worker timeout (pid: %s)" % worker.pid)


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")


def pre_request(worker, req):
    """Called just before a worker processes a request."""
    worker.log.debug("%s %s" % (req.method, req.path))


def post_request(worker, req, environ, resp):
    """Called after a worker processes a request."""
    pass


def child_exit(server, worker):
    """Called in the master process after a worker exits."""
    pass


def worker_exit(server, worker):
    """Called in the worker process just after it exits."""
    pass


def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers is changed."""
    pass


def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Investment Platform shutting down")
