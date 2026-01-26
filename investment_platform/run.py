"""
Development Entry Point

Run this script to start the Flask development server with Dash dashboard.
Usage: python run.py

Set DISABLE_DASHBOARD=1 to run API-only mode.
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import DevelopmentConfig

# Create Flask app
flask_app = create_app(DevelopmentConfig)

# Try to create Dash app (optional - may not be available on all platforms)
dash_app = None
dashboard_enabled = not os.environ.get('DISABLE_DASHBOARD', '').lower() in ('1', 'true', 'yes')

if dashboard_enabled:
    try:
        from dashboard import create_dash_app
        dash_app = create_dash_app(flask_app)
    except ImportError as e:
        print(f"Warning: Dashboard not available ({e})")
        print("Running in API-only mode.")
        dashboard_enabled = False
    except Exception as e:
        print(f"Warning: Dashboard failed to initialize ({e})")
        print("Running in API-only mode.")
        dashboard_enabled = False

if __name__ == '__main__':
    # Get port from environment or default to 9090
    port = int(os.environ.get('PORT', 9090))

    if dashboard_enabled:
        print(f"""
    +==============================================================+
    |           Investment Platform - Development Server           |
    +==============================================================+
    |  API Server:  http://localhost:{port}/api                      |
    |  Dashboard:   http://localhost:{port}/dashboard/               |
    |  Health:      http://localhost:{port}/api/health               |
    |                                                              |
    |  Press Ctrl+C to stop                                        |
    +==============================================================+
        """)
    else:
        print(f"""
    +==============================================================+
    |       Investment Platform - API Server (No Dashboard)        |
    +==============================================================+
    |  API Server:  http://localhost:{port}/api                      |
    |  Health:      http://localhost:{port}/api/health               |
    |                                                              |
    |  Dashboard disabled or unavailable                           |
    |  Press Ctrl+C to stop                                        |
    +==============================================================+
        """)

    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=True,
        use_reloader=True
    )
