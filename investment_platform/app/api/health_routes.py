"""
Health Check API Routes

Endpoints for system health monitoring.
"""
from flask import Blueprint, jsonify
from datetime import datetime, timezone
from app import db

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
        'components': {}
    }

    # Check database connection
    try:
        db.session.execute(db.text('SELECT 1'))
        status['components']['database'] = 'ok'
    except Exception as e:
        status['components']['database'] = f'error: {str(e)}'
        status['status'] = 'degraded'

    # Market status (simplified - full implementation in Phase 2)
    now = datetime.now(timezone.utc)
    hour = now.hour
    weekday = now.weekday()

    # NYSE hours: 9:30 AM - 4:00 PM ET (approximately 14:30 - 21:00 UTC)
    if weekday < 5 and 14 <= hour < 21:
        status['market_status'] = 'open'
    else:
        status['market_status'] = 'closed'

    # Yahoo Finance status (placeholder - full check in Phase 2)
    status['components']['yahoo_finance'] = 'not_checked'

    return jsonify(status)


@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """
    GET /api/ready
    Kubernetes-style readiness probe.
    """
    try:
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
