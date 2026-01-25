#!/usr/bin/env python
"""
Development Entry Point

Run this script to start the Flask development server with Dash dashboard.
Usage: python run.py
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import DevelopmentConfig
from dashboard import create_dash_app

# Create Flask app
flask_app = create_app(DevelopmentConfig)

# Create Dash app integrated with Flask
dash_app = create_dash_app(flask_app)

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))

    print(f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║           Investment Platform - Development Server           ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  API Server:  http://localhost:{port}/api                      ║
    ║  Dashboard:   http://localhost:{port}/dashboard/               ║
    ║  Health:      http://localhost:{port}/api/health               ║
    ║                                                              ║
    ║  Press Ctrl+C to stop                                        ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=True,
        use_reloader=True
    )
