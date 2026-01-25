"""
Health Check API Routes

Endpoints for system health monitoring.
"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone
from app.database import is_csv_backend, get_csv_storage, get_session

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /api/health
    Returns system health status.
    """
    status = {
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'components': {},
        'storage_backend': 'csv' if is_csv_backend() else 'database'
    }

    # Check storage backend
    try:
        if is_csv_backend():
            # For CSV, just verify we can access the storage
            storage = get_csv_storage()
            storage.get_portfolio('default')
            status['components']['storage'] = 'ok'
        else:
            # For database, execute a test query
            from app import db
            db.session.execute(db.text('SELECT 1'))
            status['components']['storage'] = 'ok'
    except Exception as e:
        status['components']['storage'] = f'error: {str(e)}'
        status['status'] = 'degraded'

    # Market status (simplified)
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()

    # NYSE hours: 9:30 AM - 4:00 PM ET (approximately 14:30 - 21:00 UTC)
    if weekday < 5 and 14 <= hour < 21:
        status['market_status'] = 'open'
    else:
        status['market_status'] = 'closed'

    return jsonify(status)


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    GET /api/ready
    Kubernetes-style readiness probe.
    """
    try:
        if is_csv_backend():
            storage = get_csv_storage()
            storage.get_portfolio('default')
        else:
            from app import db
            db.session.execute(db.text('SELECT 1'))
        return jsonify({'ready': True}), 200
    except Exception:
        return jsonify({'ready': False}), 503


@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """
    GET /api/live
    Kubernetes-style liveness probe.
    """
    return jsonify({'alive': True}), 200
