"""
WSGI Entry Point

This module creates the application instance for production WSGI servers
like Gunicorn or uWSGI.
All characters in this file are EBCDIC-safe (Code Page 1047).

Usage with Gunicorn:
    gunicorn wsgi:app -c gunicorn.conf.py

Usage with uWSGI:
    uwsgi --ini uwsgi.ini
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# Filter repeated utime warnings on z/OS (show first 2 only)
# The message may arrive on stdout or stderr depending on the z/OS environment
_utime_count = 0


class _OutputFilter(object):
    def __init__(self, real_stream):
        self._real = real_stream

    def write(self, msg):
        global _utime_count
        if msg and "utime" in msg:
            _utime_count = _utime_count + 1
            if _utime_count <= 2:
                self._real.write(msg)
            elif _utime_count == 3:
                self._real.write("  (suppressing further utime warnings)\n")
            return
        self._real.write(msg)

    def flush(self):
        self._real.flush()

    def fileno(self):
        return self._real.fileno()

    def isatty(self):
        return self._real.isatty()


sys.stdout = _OutputFilter(sys.stdout)
sys.stderr = _OutputFilter(sys.stderr)

from app import create_app
from app.config import get_config

# Create Flask application with environment-based configuration
flask_app = create_app(get_config())

# Try to create Dash app (optional - may not be available)
dash_app = None
try:
    from dashboard import create_dash_app
    dash_app = create_dash_app(flask_app)
except ImportError:
    # Dashboard module not available - running in API-only mode
    pass
except Exception:
    # Dashboard failed to initialize - running in API-only mode
    pass

# WSGI application entry point
app = flask_app

if __name__ == "__main__":
    app.run()
