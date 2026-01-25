"""
Gunicorn Configuration for Production

This configuration is optimized for running on IBM z/OS mainframe.
Adjust workers and threads based on available CPU cores.

Usage:
    gunicorn wsgi:app -c gunicorn.conf.py
"""
import os
import multiprocessing

# Server socket
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:8000')
backlog = 2048

# Worker processes
# Rule of thumb: (2 x CPU cores) + 1
# On mainframe, start conservative and scale up
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'sync'  # Use 'gevent' or 'eventlet' for async if needed
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests (memory leak prevention)
max_requests_jitter = 50  # Add randomness to max_requests

# Timeout configuration
timeout = 120  # Worker timeout in seconds
graceful_timeout = 30  # Graceful shutdown timeout
keepalive = 5  # Keep-alive connections timeout

# Process naming
proc_name = 'investment-platform'

# Server mechanics
daemon = False  # Run in foreground (use systemd/supervisor for daemonization)
pidfile = '/var/run/investment-platform/gunicorn.pid'
user = None  # Run as current user (or specify 'www-data' etc.)
group = None
tmp_upload_dir = None

# Logging
loglevel = os.getenv('LOG_LEVEL', 'info')
accesslog = os.getenv('ACCESS_LOG', '/var/log/investment-platform/access.log')
errorlog = os.getenv('ERROR_LOG', '/var/log/investment-platform/error.log')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# For local development, log to stdout
if os.getenv('FLASK_ENV') == 'development':
    accesslog = '-'
    errorlog = '-'
    loglevel = 'debug'

# SSL Configuration (uncomment for HTTPS)
# keyfile = '/path/to/server.key'
# certfile = '/path/to/server.crt'
# ssl_version = 'TLSv1_2'
# cert_reqs = 0  # No client certificate required
# ciphers = 'TLSv1.2+FIPS:kRSA+FIPS:!eNULL:!aNULL'

# Security headers (applied via application middleware, not here)

# Hooks for lifecycle events
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
    server.log.info(f"Worker spawned (pid: {worker.pid})")


def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    pass


def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.info(f"Worker timeout (pid: {worker.pid})")


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")


def pre_request(worker, req):
    """Called just before a worker processes a request."""
    worker.log.debug(f"{req.method} {req.path}")


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
