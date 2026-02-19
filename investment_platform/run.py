"""
Production Entry Point

Run this script to start the Investment Platform using Gunicorn.
Usage: python run.py

Set DISABLE_DASHBOARD=1 to run API-only mode.
Set FLASK_ENV=development for debug logging.

Environment variables:
    GUNICORN_BIND      - Host and port (default: 0.0.0.0:5000)
    GUNICORN_WORKERS   - Number of worker processes (default: auto)
    STORAGE_BACKEND    - csv, sqlite, or db2 (default: sqlite)
    DISABLE_DASHBOARD  - Set to 1 to disable dashboard
    LOG_LEVEL          - Logging level (default: info)
"""
import os
import sys
import socket
import subprocess
import threading

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Start the Investment Platform with Gunicorn."""
    bind_addr = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")
    env = os.environ.get("FLASK_ENV", "production")
    storage = os.environ.get("STORAGE_BACKEND", "sqlite")
    dashboard = os.environ.get("DISABLE_DASHBOARD", "0")

    # Get the actual IP address and port for the access URL
    port = bind_addr.split(":")[-1] if ":" in bind_addr else "5000"
    try:
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
    except Exception:
        ip_addr = "127.0.0.1"
    access_url = "http://%s:%s" % (ip_addr, port)

    print("")
    print("  +============================================================+")
    print("  |         Investment Platform - Gunicorn Server              |")
    print("  +============================================================+")
    print("  |  Access:     %-43s |" % access_url)
    print("  |  Health:     %-43s |" % (access_url + "/api/health"))
    print("  |  API:        %-43s |" % (access_url + "/api"))
    print("  |  Storage:    %-43s |" % storage)
    print("  |  Environment:%-43s |" % (" " + env))
    print("  |  Dashboard:  %-43s |" % ("disabled" if dashboard in ("1", "true", "yes") else "enabled"))
    print("  |                                                            |")
    print("  |  Press Ctrl+C to stop                                      |")
    print("  +============================================================+")
    print("")

    config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "gunicorn.conf.py"
    )

    cmd = [
        sys.executable, "-m", "gunicorn",
        "wsgi:app",
        "-c", config_path,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        utime_count = 0
        for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace")
            if "utime" in line:
                utime_count = utime_count + 1
                if utime_count <= 2:
                    sys.stdout.write(line)
                elif utime_count == 3:
                    sys.stdout.write("  (suppressing further utime warnings)\n")
                continue
            sys.stdout.write(line)
            sys.stdout.flush()
        proc.wait()
        if proc.returncode and proc.returncode != 0:
            sys.exit(proc.returncode)
    except KeyboardInterrupt:
        print("")
        print("  Shutting down Investment Platform...")
        if proc.poll() is None:
            proc.terminate()
    except FileNotFoundError:
        print("  ERROR: gunicorn is not installed.")
        print("  Install it with: pip install gunicorn")
        sys.exit(1)


if __name__ == "__main__":
    main()
