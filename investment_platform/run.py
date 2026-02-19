"""
Production Entry Point

Run this script to start the Investment Platform using Gunicorn.
Usage: python run.py

Set DISABLE_DASHBOARD=1 to run API-only mode.
Set FLASK_ENV=development for debug logging.

Environment variables:
    GUNICORN_BIND      - Host and port (default: 0.0.0.0:8000)
    GUNICORN_WORKERS   - Number of worker processes (default: auto)
    STORAGE_BACKEND    - csv, sqlite, or db2 (default: sqlite)
    DISABLE_DASHBOARD  - Set to 1 to disable dashboard
    LOG_LEVEL          - Logging level (default: info)
"""
import os
import sys
import subprocess

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Start the Investment Platform with Gunicorn."""
    bind_addr = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")
    env = os.environ.get("FLASK_ENV", "production")
    storage = os.environ.get("STORAGE_BACKEND", "sqlite")
    dashboard = os.environ.get("DISABLE_DASHBOARD", "0")

    print("")
    print("  +============================================================+")
    print("  |         Investment Platform - Gunicorn Server              |")
    print("  +============================================================+")
    print("  |  Bind:       %-43s |" % bind_addr)
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
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("")
        print("  Shutting down Investment Platform...")
    except FileNotFoundError:
        print("  ERROR: gunicorn is not installed.")
        print("  Install it with: pip install gunicorn")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print("  ERROR: Gunicorn exited with code %d" % exc.returncode)
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
