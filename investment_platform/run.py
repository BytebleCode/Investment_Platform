"""
Production Entry Point

Run this script to start the Investment Platform.
Uses Flask threaded server for z/OS compatibility.
Usage: python run.py

To run in background (survives SSH disconnect):
    nohup python run.py > server.log 2>&1 &

Environment variables:
    PORT               - Port number (default: 5000)
    STORAGE_BACKEND    - csv, sqlite, or db2 (default: sqlite)
    DISABLE_DASHBOARD  - Set to 1 to disable dashboard
    FLASK_ENV          - production or development (default: production)
"""
import os
import sys
import socket
from datetime import datetime
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wsgi import app

# PID file location (next to run.py)
PID_FILE = Path(__file__).parent / 'server.pid'


def write_pid_log(port, ip_addr, storage, env):
    """Write PID file with server info for reconnecting after SSH."""
    pid = os.getpid()
    started = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    access_url = "http://%s:%s" % (ip_addr, port)

    content = (
        "pid=%d\n"
        "port=%d\n"
        "host=%s\n"
        "url=%s\n"
        "storage=%s\n"
        "env=%s\n"
        "started=%s\n"
        "cwd=%s\n"
    ) % (pid, port, ip_addr, access_url, storage, env, started, os.getcwd())

    try:
        PID_FILE.write_text(content)
    except Exception as e:
        print("  WARNING: Could not write PID file: %s" % e)


def cleanup_pid_file():
    """Remove PID file on shutdown."""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception:
        pass


def main():
    """Start the Investment Platform."""
    port = int(os.environ.get("PORT", "5000"))
    storage = os.environ.get("STORAGE_BACKEND", "sqlite")
    env = os.environ.get("FLASK_ENV", "production")
    dashboard = os.environ.get("DISABLE_DASHBOARD", "0")

    # Get the actual IP address for the access URL
    try:
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
    except Exception:
        ip_addr = "127.0.0.1"
    access_url = "http://%s:%s" % (ip_addr, port)

    pid = os.getpid()

    # Write PID file
    write_pid_log(port, ip_addr, storage, env)

    print("")
    print("  +============================================================+")
    print("  |         Investment Platform - Server                       |")
    print("  +============================================================+")
    print("  |  PID:        %-43s |" % pid)
    print("  |  Access:     %-43s |" % access_url)
    print("  |  Health:     %-43s |" % (access_url + "/api/health"))
    print("  |  API:        %-43s |" % (access_url + "/api"))
    print("  |  Storage:    %-43s |" % storage)
    print("  |  Environment:%-43s |" % (" " + env))
    print("  |  Dashboard:  %-43s |" % ("disabled" if dashboard in ("1", "true", "yes") else "enabled"))
    print("  |  PID file:   %-43s |" % str(PID_FILE))
    print("  |                                                            |")
    print("  |  Press Ctrl+C to stop                                      |")
    print("  +============================================================+")
    print("")

    try:
            app.run(
            host="0.0.0.0",
            port=port,
            threaded=True,
            debug=False,
            use_reloader=False,
        )
    finally:
        cleanup_pid_file()


if __name__ == "__main__":
    main()
